#!/usr/bin/env python3
"""
automation_health.py — gh-aw Automation Health for Nexus Digest
================================================================
Queries GitHub Actions API for recent runs of the 4 gh-aw agents
across all 6 repos, plus Supabase sentinel_runs for escalations.

Returns a formatted section for inclusion in the morning/evening digest.
"""
import os
import logging
import requests
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("automation_health")

REPOS = [
    "breverdbidder/brevard-bidder-scraper",
    "breverdbidder/cli-anything-biddeed",
    "breverdbidder/biddeed-ai",
    "breverdbidder/zonewise-web",
    "breverdbidder/zonewise-scraper-v4",
    "breverdbidder/everest-nexus",
]

AGENT_WORKFLOWS = [
    "doc-sync-agent",
    "issue-triage-agent",
    "ci-failure-agent",
    "pr-gate-agent",
]

GH_API = "https://api.github.com"


def _gh_headers() -> dict:
    token = os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    return {"Accept": "application/vnd.github+json"}


def _get_workflow_runs(repo: str, workflow: str, since_hours: int = 24) -> list:
    """Fetch recent workflow runs for a specific workflow in a repo."""
    url = f"{GH_API}/repos/{repo}/actions/workflows/{workflow}.lock.yml/runs"
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=since_hours)).isoformat()
    params = {"per_page": 20, "created": f">={cutoff[:10]}"}
    try:
        r = requests.get(url, headers=_gh_headers(), params=params, timeout=10)
        if r.status_code == 404:
            return []
        r.raise_for_status()
        return r.json().get("workflow_runs", [])
    except Exception as e:
        logger.debug(f"workflow_runs fetch failed {repo}/{workflow}: {e}")
        return []


def _get_sentinel_escalations(since_hours: int = 24) -> list:
    """Query Supabase sentinel_runs for escalation events in the last N hours."""
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        return []

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=since_hours)).isoformat()
    try:
        r = requests.get(
            f"{url}/rest/v1/sentinel_runs",
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
            params={
                "select": "id,event_type,repo,created_at,details",
                "event_type": "eq.escalation",
                "created_at": f"gte.{cutoff}",
                "order": "created_at.desc",
                "limit": "10",
            },
            timeout=10,
        )
        if r.status_code in (200, 206):
            return r.json() or []
        return []
    except Exception as e:
        logger.debug(f"sentinel_runs fetch failed: {e}")
        return []


def get_automation_health(since_hours: int = 24) -> dict:
    """
    Returns a dict with counts for each agent workflow and sentinel status.

    Keys:
      doc_sync_prs_merged    int
      doc_sync_pending       int
      issues_labeled         int
      ci_failures_diagnosed  int
      ci_fix_prs_open        int
      prs_auto_merged        int
      prs_awaiting_review    int
      sentinel_escalations   list[dict]
    """
    stats = {
        "doc_sync_prs_merged": 0,
        "doc_sync_pending": 0,
        "issues_labeled": 0,
        "ci_failures_diagnosed": 0,
        "ci_fix_prs_open": 0,
        "prs_auto_merged": 0,
        "prs_awaiting_review": 0,
        "sentinel_escalations": [],
    }

    for repo in REPOS:
        # doc-sync-agent: count successful runs (each success = potential PR merged)
        for run in _get_workflow_runs(repo, "doc-sync-agent", since_hours):
            if run.get("conclusion") == "success":
                stats["doc_sync_prs_merged"] += 1
            elif run.get("status") in ("queued", "in_progress"):
                stats["doc_sync_pending"] += 1

        # issue-triage-agent: count successful runs = issues labeled
        for run in _get_workflow_runs(repo, "issue-triage-agent", since_hours):
            if run.get("conclusion") == "success":
                stats["issues_labeled"] += 1

        # ci-failure-agent: count successful runs = failures diagnosed
        for run in _get_workflow_runs(repo, "ci-failure-agent", since_hours):
            if run.get("conclusion") == "success":
                stats["ci_failures_diagnosed"] += 1
            elif run.get("status") in ("queued", "in_progress"):
                stats["ci_fix_prs_open"] += 1

        # pr-gate-agent: count by conclusion label applied
        for run in _get_workflow_runs(repo, "pr-gate-agent", since_hours):
            if run.get("conclusion") == "success":
                # We can't easily distinguish LOW vs HIGH from run alone
                # Count success = processed; distinguish by checking run name/title
                name = (run.get("name") or run.get("display_title") or "").lower()
                if "low" in name or "auto-merge" in name:
                    stats["prs_auto_merged"] += 1
                else:
                    stats["prs_awaiting_review"] += 1
            elif run.get("conclusion") in (None, ""):
                stats["prs_awaiting_review"] += 1

    # Sentinel escalations
    stats["sentinel_escalations"] = _get_sentinel_escalations(since_hours)

    return stats


def format_automation_health_section(since_hours: int = 24) -> str:
    """Returns a formatted Telegram-safe HTML string for the Automation Health digest section."""
    try:
        h = get_automation_health(since_hours)
    except Exception as e:
        logger.warning(f"automation_health fetch failed: {e}")
        return "🤖 <b>Automation Health:</b> unavailable\n"

    escalations = h["sentinel_escalations"]
    if escalations:
        sentinel_line = f"⚠️ {len(escalations)} escalation(s): " + ", ".join(
            e.get("repo", "?") for e in escalations[:3]
        )
    else:
        sentinel_line = "✅ All clear"

    section = (
        f"🤖 <b>Automation Health ({since_hours}h):</b>\n"
        f"• Doc Sync: {h['doc_sync_prs_merged']} PRs merged"
        + (f", {h['doc_sync_pending']} pending" if h["doc_sync_pending"] else "")
        + "\n"
        f"• Issue Triage: {h['issues_labeled']} issues labeled\n"
        f"• CI Failures: {h['ci_failures_diagnosed']} diagnosed"
        + (f", {h['ci_fix_prs_open']} fix PRs open" if h["ci_fix_prs_open"] else "")
        + "\n"
        f"• PR Gate: {h['prs_auto_merged']} auto-merged, {h['prs_awaiting_review']} awaiting review\n"
        f"• Sentinel: {sentinel_line}\n"
    )
    return section
