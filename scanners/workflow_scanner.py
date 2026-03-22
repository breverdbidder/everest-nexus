"""
Nexus Workflow Scanner — Layer 2: Workflow Intelligence
Scans all repos under breverdbidder for GitHub Actions workflows.
Runs every 6 hours via pg_cron.
"""
import os
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Optional
import requests

logger = logging.getLogger(__name__)

GH_TOKEN     = os.environ.get("GH_PAT", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
ORG          = "breverdbidder"
COST_PER_MIN = 0.008  # ubuntu-latest $/min


def _gh_headers() -> dict:
    return {
        "Authorization": f"token {GH_TOKEN}",
        "Accept":        "application/vnd.github.v3+json",
    }


def _sb_headers() -> dict:
    return {
        "apikey":        SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type":  "application/json",
        "Prefer":        "resolution=merge-duplicates",
    }


def _gh_get(path: str, params: dict = None) -> dict | list:
    url = f"https://api.github.com{path}"
    r = requests.get(url, headers=_gh_headers(), params=params, timeout=20)
    if r.status_code == 404:
        return {}
    r.raise_for_status()
    return r.json()


def _sb_upsert(table: str, rows: list) -> None:
    if not rows:
        return
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    # Upsert in batches of 50
    for i in range(0, len(rows), 50):
        batch = rows[i:i+50]
        r = requests.post(url, headers=_sb_headers(), json=batch, timeout=20)
        r.raise_for_status()


def fetch_workflows(repo_name: str) -> list:
    """Return list of workflow objects for a repo."""
    data = _gh_get(f"/repos/{ORG}/{repo_name}/actions/workflows")
    return data.get("workflows", []) if isinstance(data, dict) else []


def fetch_runs(repo_name: str, workflow_id: int, days: int = 30) -> list:
    """Fetch up to 50 runs for a workflow in the last N days."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    data = _gh_get(
        f"/repos/{ORG}/{repo_name}/actions/workflows/{workflow_id}/runs",
        params={"per_page": 50, "created": f">={since}"},
    )
    return data.get("workflow_runs", []) if isinstance(data, dict) else []


def compute_health(runs: list) -> dict:
    """Compute success_rate, avg_duration, total_runs from run list."""
    if not runs:
        return {
            "total_runs_30d": 0,
            "success_rate_30d": None,
            "avg_duration_seconds": None,
            "last_run_at": None,
            "last_run_status": None,
            "last_run_url": None,
        }

    completed = [r for r in runs if r.get("conclusion")]
    successes  = [r for r in completed if r.get("conclusion") == "success"]
    rate = (len(successes) / len(completed) * 100) if completed else 0

    durations = []
    for r in completed:
        started  = r.get("run_started_at") or r.get("created_at")
        updated  = r.get("updated_at")
        if started and updated:
            try:
                s = datetime.fromisoformat(started.replace("Z", "+00:00"))
                u = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                durations.append((u - s).total_seconds())
            except Exception:
                pass

    avg_dur = int(sum(durations) / len(durations)) if durations else None

    latest = runs[0]
    return {
        "total_runs_30d":       len(runs),
        "success_rate_30d":     round(rate, 2),
        "avg_duration_seconds": avg_dur,
        "last_run_at":          latest.get("created_at"),
        "last_run_status":      latest.get("conclusion") or latest.get("status"),
        "last_run_url":         latest.get("html_url"),
    }


def detect_dead(workflow: dict, runs: list) -> bool:
    """A workflow is 'dead' if state=active but 0 runs in 30 days."""
    return workflow.get("state") == "active" and len(runs) == 0


def estimate_monthly_cost(runs: list, avg_duration_seconds: Optional[int]) -> float:
    if not avg_duration_seconds or not runs:
        return 0.0
    runs_per_day = len(runs) / 30
    runs_per_month = runs_per_day * 30
    minutes_per_run = avg_duration_seconds / 60
    return round(runs_per_month * minutes_per_run * COST_PER_MIN, 4)


def parse_trigger_types(workflow: dict) -> list:
    """Extract trigger types from workflow YAML config."""
    # GitHub API doesn't return full YAML triggers in workflow list,
    # but `on` field may be in the workflow file content.
    # Use workflow name heuristics + schedule check.
    triggers = []
    name = workflow.get("name", "").lower()
    path = workflow.get("path", "").lower()
    if "schedule" in name or "cron" in name:
        triggers.append("schedule")
    if "dispatch" in path or "dispatch" in name:
        triggers.append("workflow_dispatch")
    if not triggers:
        triggers = ["push"]
    return triggers


def scan_repo(repo_name: str) -> list:
    """Scan all workflows in a single repo. Returns rows for nexus_workflows."""
    rows = []
    try:
        workflows = fetch_workflows(repo_name)
        if not workflows:
            return []

        for wf in workflows:
            wf_id   = wf.get("id")
            runs    = fetch_runs(repo_name, wf_id)
            health  = compute_health(runs)
            is_dead = detect_dead(wf, runs)
            triggers = parse_trigger_types(wf)
            is_sched = "schedule" in triggers
            avg_dur  = health.get("avg_duration_seconds")
            cost     = estimate_monthly_cost(runs, avg_dur)

            # Write insight if dead or failing
            if is_dead or (health.get("success_rate_30d") is not None
                           and health["success_rate_30d"] < 50
                           and health["total_runs_30d"] > 0):
                _write_insight(repo_name, wf, health, is_dead)

            row = {
                "repo_name":            repo_name,
                "workflow_name":        wf.get("name", ""),
                "workflow_path":        wf.get("path", ""),
                "workflow_id":          wf_id,
                "state":                wf.get("state", ""),
                "trigger_types":        triggers,
                "last_run_at":          health["last_run_at"],
                "last_run_status":      health["last_run_status"],
                "last_run_url":         health["last_run_url"],
                "total_runs_30d":       health["total_runs_30d"],
                "success_rate_30d":     health["success_rate_30d"],
                "avg_duration_seconds": avg_dur,
                "is_scheduled":         is_sched,
                "is_dead":              is_dead,
                "estimated_cost_30d":   cost,
                "updated_at":           datetime.now(timezone.utc).isoformat(),
            }
            rows.append(row)
            time.sleep(0.1)  # gentle rate limiting

    except Exception as e:
        logger.error(f"scan_repo({repo_name}) failed: {e}")

    return rows


def _write_insight(repo_name: str, wf: dict, health: dict, is_dead: bool) -> None:
    wf_name = wf.get("name", "")
    if is_dead:
        title = f"Dead workflow: {wf_name} in {repo_name}"
        body  = f"State: active, but 0 runs in 30 days. Consider disabling or deleting."
        sev   = "warning"
        itype = "dead_workflow"
        rec   = f"DELETE: {wf_name} in {repo_name} — no runs in 30 days"
    else:
        rate = health.get("success_rate_30d", 0)
        title = f"Failing workflow: {wf_name} in {repo_name} ({rate:.0f}% success)"
        body  = f"Only {rate:.0f}% success rate in 30 days ({health['total_runs_30d']} runs)."
        sev   = "critical" if rate == 0 else "warning"
        itype = "failing_workflow"
        rec   = f"DISABLE: {wf_name} in {repo_name} — {rate:.0f}% success rate"

    insight = {
        "layer":           "workflow",
        "insight_type":    itype,
        "severity":        sev,
        "title":           title,
        "body":            body,
        "recommendation":  rec,
        "affected_entity": f"{repo_name}/{wf_name}",
        "auto_fixable":    False,
        "resolved":        False,
    }
    try:
        url = f"{SUPABASE_URL}/rest/v1/nexus_insights"
        headers = {**_sb_headers(), "Prefer": "resolution=ignore-duplicates"}
        requests.post(url, headers=headers, json=insight, timeout=10)
    except Exception as e:
        logger.warning(f"Failed to write insight: {e}")


def scan_all_repos(repo_names: Optional[list] = None) -> dict:
    """
    Scan all repos (or a provided list).
    Returns summary: {repos_scanned, workflows_found, dead_count, failing_count}
    """
    if repo_names is None:
        # Fetch from nexus_repos
        url = f"{SUPABASE_URL}/rest/v1/nexus_repos?select=repo_name&tier=not.eq.archived"
        r = requests.get(url, headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        }, timeout=15)
        repos_data = r.json() if r.ok else []
        repo_names = [row["repo_name"] for row in repos_data]

    total_workflows = 0
    dead_count      = 0
    failing_count   = 0

    for repo_name in repo_names:
        logger.info(f"Scanning workflows: {repo_name}")
        rows = scan_repo(repo_name)
        if rows:
            _sb_upsert("nexus_workflows", rows)
            total_workflows += len(rows)
            dead_count      += sum(1 for r in rows if r.get("is_dead"))
            failing_count   += sum(
                1 for r in rows
                if r.get("success_rate_30d") is not None
                and r["success_rate_30d"] < 50
                and r["total_runs_30d"] > 0
            )
        time.sleep(0.5)

    summary = {
        "repos_scanned":    len(repo_names),
        "workflows_found":  total_workflows,
        "dead_count":       dead_count,
        "failing_count":    failing_count,
        "scanned_at":       datetime.now(timezone.utc).isoformat(),
    }
    logger.info(f"Workflow scan complete: {summary}")
    return summary


if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO)
    summary = scan_all_repos()
    print(json.dumps(summary, indent=2))
