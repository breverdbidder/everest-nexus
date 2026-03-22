"""
Nexus Repo Scanner — Layer 3: Repo Intelligence
Runs every 6 hours via pg_cron.
Fetches all breverdbidder repos, classifies tier, computes health score,
scans latest CI status, updates nexus_repos.
"""
import os
import logging
import time
from datetime import datetime, timezone
from typing import Optional
import requests

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

GH_TOKEN     = os.environ.get("GH_PAT", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
ORG          = "breverdbidder"

# ── Tier sets (from spec) ──────────────────────────────────────────────────

CORE_REPOS = {
    "everest-nexus", "zonewise-web", "biddeed-ai", "biddeed-ai-ui",
    "cli-anything-biddeed", "zonewise", "claude-code-telegram-control",
    "zonewise-scraper-v4", "life-os",
}

ACTIVE_REPOS = {
    "biddeed-brain", "biddeed-landing", "zonewise-landing",
    "brevard-bidder-landing", "cliproxy-gateway", "zonewise-modal", "cctop",
    "brevard-bidder-scraper", "foreclosure-auction-pipeline",
    "location-intelligence-api", "api-layer", "zonewise-agents",
    "zonewise-agent-teams", "agents-command-center", "everest-dispatch",
    "contextbridge", "skillforge-ai", "goviralbitch", "gstack",
}

MONITORED_REPOS = {
    "claude-skills-library", "ai-tools-library", "ssot-task-manager",
    "brevard-bidder-ai-skills", "qa-agentic-pipeline", "zonewise-desktop",
    "zonewise-gtm", "zonewise-loans", "biddeed-conversational-ai",
    "claude-code-telegram-control-1", "gemini-gateway", "visual-explainer",
    "michael-d1-pathway", "tax-insurance-optimizer", "esdp-pipeline",
    "autoresearch-mirror", "dap-debug-workflow", "excalidraw-diagram-skill",
    "repo-swarm", "context-boot-mcp-server", "auction-scraper-playwright",
    "agency-agents", "superpowers",
}

ARCHIVED_REPOS = {
    "zonewise-rebrand-mission", "zonewise-traycer-specs", "zonewise-ai",
    "zonewise-desktop-v2", "zonewise-lobster",
}

CONSOLIDATION = {
    "zonewise-family": {
        "repos": ["zonewise", "zonewise-web", "zonewise-desktop", "zonewise-landing",
                  "zonewise-agents", "zonewise-agent-teams", "zonewise-gtm",
                  "zonewise-loans", "zonewise-scraper-v4", "zonewise-modal"],
        "rec": ("Merge zonewise-agents + zonewise-agent-teams into cli-anything-biddeed. "
                "Archive zonewise-desktop + zonewise-gtm + zonewise-loans (inactive). "
                "Keep zonewise-web + zonewise + zonewise-landing."),
    },
    "biddeed-family": {
        "repos": ["biddeed-ai", "biddeed-ai-ui", "biddeed-landing",
                  "biddeed-conversational-ai", "brevard-bidder-landing", "biddeed-brain"],
        "rec": ("Merge biddeed-ai + biddeed-ai-ui into monorepo. "
                "Archive biddeed-conversational-ai (superseded). "
                "Merge landing pages into one."),
    },
    "infra-family": {
        "repos": ["claude-code-telegram-control", "claude-code-telegram-control-1",
                  "cliproxy-gateway", "agents-command-center", "everest-dispatch"],
        "rec": ("Archive telegram-control-1 (duplicate). "
                "Merge agents-command-center into cli-anything."),
    },
}

REPO_CONSOLIDATION: dict = {}
for _group, _data in CONSOLIDATION.items():
    for _repo in _data["repos"]:
        REPO_CONSOLIDATION[_repo] = (_group, _data["rec"])


def _gh_headers() -> dict:
    return {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}


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
    if r.status_code in (404, 403):
        return {}
    r.raise_for_status()
    return r.json()


def classify_tier(name: str, gh_archived: bool) -> str:
    if gh_archived or name in ARCHIVED_REPOS:
        return "archived"
    if name in CORE_REPOS:
        return "core"
    if name in ACTIVE_REPOS:
        return "active"
    return "monitored"


def compute_health_score(stale_days: int, tier: str, ci_status: str,
                         open_issues: int, description: str, topics: list) -> int:
    score = 100
    if stale_days > 90:
        score -= 30
    elif stale_days > 7 and tier == "core":
        score -= 20
    elif stale_days > 14 and tier == "active":
        score -= 15
    elif stale_days > 30 and tier == "monitored":
        score -= 10

    if ci_status == "failure":
        score -= 25
    elif ci_status == "none":
        score -= 5

    if open_issues > 10:
        score -= 10
    if not (description or "").strip():
        score -= 5
    if not topics:
        score -= 5

    return max(0, min(100, score))


def fetch_all_repos() -> list:
    """Paginate through all breverdbidder repos."""
    repos = []
    page = 1
    while True:
        batch = _gh_get("/user/repos", params={"per_page": 100, "page": page, "affiliation": "owner"})
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
        time.sleep(0.3)
    return repos


def fetch_ci_status(repo_name: str) -> tuple[str, Optional[str], Optional[str]]:
    """
    Returns (ci_status, run_url, run_at) by checking the latest workflow run.
    ci_status: 'success' | 'failure' | 'pending' | 'none'
    """
    try:
        data = _gh_get(f"/repos/{ORG}/{repo_name}/actions/runs", params={"per_page": 1})
        runs = data.get("workflow_runs", []) if isinstance(data, dict) else []
        if not runs:
            return "none", None, None
        run = runs[0]
        conclusion = run.get("conclusion") or "pending"
        status     = run.get("status", "")
        # Map GitHub conclusions to our schema values
        if conclusion == "success":
            ci = "success"
        elif conclusion in ("failure", "timed_out", "action_required"):
            ci = "failure"
        elif status in ("in_progress", "queued", "waiting"):
            ci = "pending"
        else:
            ci = "none"
        return ci, run.get("html_url"), run.get("updated_at")
    except Exception as e:
        logger.debug(f"CI fetch failed for {repo_name}: {e}")
        return "none", None, None


def build_repo_row(gh_repo: dict, fetch_ci: bool = True) -> dict:
    name       = gh_repo["name"]
    tier       = classify_tier(name, gh_repo.get("archived", False))
    description = gh_repo.get("description") or ""
    topics      = gh_repo.get("topics") or []
    last_push_raw = gh_repo.get("pushed_at")

    stale_days = 0
    if last_push_raw:
        push_dt    = datetime.fromisoformat(last_push_raw.replace("Z", "+00:00"))
        stale_days = (datetime.now(timezone.utc) - push_dt).days

    ci_status, ci_url, ci_at = ("none", None, None)
    if fetch_ci and tier in ("core", "active"):
        ci_status, ci_url, ci_at = fetch_ci_status(name)
        time.sleep(0.2)  # Rate-limit friendliness

    cgroup, crec = REPO_CONSOLIDATION.get(name, (None, None))

    health = compute_health_score(
        stale_days, tier, ci_status,
        gh_repo.get("open_issues_count", 0), description, topics
    )

    return {
        "repo_name":                    name,
        "full_name":                    gh_repo.get("full_name", f"{ORG}/{name}"),
        "tier":                         tier,
        "description":                  description,
        "language":                     gh_repo.get("language") or "",
        "topics":                       topics,
        "default_branch":               gh_repo.get("default_branch", "main"),
        "is_private":                   gh_repo.get("private", False),
        "created_at_gh":                gh_repo.get("created_at"),
        "last_push_at":                 last_push_raw,
        "open_issues":                  gh_repo.get("open_issues_count", 0),
        "size_kb":                      gh_repo.get("size", 0),
        "stale_days":                   stale_days,
        "last_ci_status":               ci_status,
        "last_ci_url":                  ci_url,
        "last_ci_at":                   ci_at,
        "health_score":                 health,
        "consolidation_group":          cgroup,
        "consolidation_recommendation": crec,
        "contributors":                 [],
        "dependencies":                 [],
    }


def upsert_repos(rows: list) -> int:
    url = f"{SUPABASE_URL}/rest/v1/nexus_repos"
    total = 0
    for i in range(0, len(rows), 25):
        batch = rows[i:i+25]
        r = requests.post(url, headers=_sb_headers(), json=batch, timeout=20)
        if r.ok:
            total += len(batch)
        else:
            logger.error(f"Upsert batch {i}: {r.status_code} {r.text[:200]}")
    return total


def get_repo_count() -> int:
    url = f"{SUPABASE_URL}/rest/v1/nexus_repos?select=id"
    r = requests.get(url, headers={
        "apikey":        SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Prefer":        "count=exact",
    }, timeout=15)
    if r.ok:
        content_range = r.headers.get("Content-Range", "*/0")
        try:
            return int(content_range.split("/")[-1])
        except Exception:
            return len(r.json())
    return 0


def scan(fetch_ci: bool = True, limit: int = 200) -> dict:
    """
    Full repo scan: fetch from GitHub, classify, compute health, upsert.
    Returns summary dict.
    """
    logger.info("Fetching all repos from GitHub...")
    gh_repos = fetch_all_repos()
    logger.info(f"Found {len(gh_repos)} repos from GitHub")

    rows = []
    for gh in gh_repos[:limit]:
        try:
            row = build_repo_row(gh, fetch_ci=fetch_ci)
            rows.append(row)
        except Exception as e:
            logger.warning(f"Error building row for {gh.get('name','?')}: {e}")

    logger.info(f"Built {len(rows)} repo rows — upserting...")
    upserted = upsert_repos(rows)

    tiers = {}
    for row in rows:
        t = row["tier"]
        tiers[t] = tiers.get(t, 0) + 1

    total_in_db = get_repo_count()
    return {
        "scanned":   len(rows),
        "upserted":  upserted,
        "tiers":     tiers,
        "total_db":  total_in_db,
    }


if __name__ == "__main__":
    from notifier import send_telegram

    logger.info("Starting Nexus Repo Scanner...")
    summary = scan(fetch_ci=True)

    tier_str = "  ".join(f"{t}:{c}" for t, c in sorted(summary["tiers"].items()))
    msg = (
        f"🔍 <b>Repo Scan Complete</b>\n\n"
        f"• Scanned: {summary['scanned']} repos\n"
        f"• In DB: {summary['total_db']}\n"
        f"• Tiers: {tier_str}\n"
        f"• CI status updated for core/active repos ✓"
    )
    send_telegram(msg)
    print(msg)
