"""
Seed Repos — Populate nexus_repos with all 50 breverdbidder repos,
correct tiers, consolidation groups, and health scores.
Run once after migration.
"""
import os
import sys
import json
import logging
import requests
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

GH_TOKEN     = os.environ.get("GH_PAT", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
ORG          = "breverdbidder"

# ── Tier classification (from spec + observation) ─────────────────────────

CORE_REPOS = {
    "everest-nexus",
    "zonewise-web",
    "biddeed-ai",
    "biddeed-ai-ui",
    "cli-anything-biddeed",
    "zonewise",
    "claude-code-telegram-control",
    "zonewise-scraper-v4",
    "life-os",
}

ACTIVE_REPOS = {
    "biddeed-brain",
    "biddeed-landing",
    "zonewise-landing",
    "brevard-bidder-landing",
    "cliproxy-gateway",
    "zonewise-modal",
    "cctop",
    "brevard-bidder-scraper",
    "foreclosure-auction-pipeline",
    "location-intelligence-api",
    "api-layer",
    "zonewise-agents",
    "zonewise-agent-teams",
    "agents-command-center",
    "everest-dispatch",
    "contextbridge",
    "skillforge-ai",
    "goviralbitch",
    "gstack",
}

MONITORED_REPOS = {
    "claude-skills-library",
    "ai-tools-library",
    "ssot-task-manager",
    "brevard-bidder-ai-skills",
    "qa-agentic-pipeline",
    "zonewise-desktop",
    "zonewise-gtm",
    "zonewise-loans",
    "biddeed-conversational-ai",
    "claude-code-telegram-control-1",
    "gemini-gateway",
    "visual-explainer",
    "michael-d1-pathway",
    "tax-insurance-optimizer",
    "esdp-pipeline",
    "autoresearch-mirror",
    "dap-debug-workflow",
    "excalidraw-diagram-skill",
    "repo-swarm",
    "context-boot-mcp-server",
    "auction-scraper-playwright",
    "esdp-pipeline",
    "agency-agents",
    "superpowers",
}

ARCHIVED_REPOS = {
    "zonewise-rebrand-mission",
    "zonewise-traycer-specs",
    "zonewise-ai",
    "zonewise-desktop-v2",
    "zonewise-lobster",
}

# ── Consolidation groups ──────────────────────────────────────────────────

CONSOLIDATION = {
    "zonewise-family": {
        "repos": ["zonewise", "zonewise-web", "zonewise-desktop", "zonewise-landing",
                  "zonewise-agents", "zonewise-agent-teams", "zonewise-gtm",
                  "zonewise-loans", "zonewise-scraper-v4", "zonewise-modal"],
        "rec": "Merge zonewise-agents + zonewise-agent-teams into cli-anything-biddeed. "
               "Archive zonewise-desktop + zonewise-gtm + zonewise-loans (inactive). "
               "Keep zonewise-web + zonewise + zonewise-landing.",
    },
    "biddeed-family": {
        "repos": ["biddeed-ai", "biddeed-ai-ui", "biddeed-landing",
                  "biddeed-conversational-ai", "brevard-bidder-landing",
                  "biddeed-brain"],
        "rec": "Merge biddeed-ai + biddeed-ai-ui into monorepo. "
               "Archive biddeed-conversational-ai (superseded). "
               "Merge landing pages into one.",
    },
    "infra-family": {
        "repos": ["claude-code-telegram-control", "claude-code-telegram-control-1",
                  "cliproxy-gateway", "agents-command-center", "everest-dispatch"],
        "rec": "Archive telegram-control-1 (duplicate). "
               "Merge agents-command-center into cli-anything.",
    },
}

# Reverse lookup: repo → (group, rec)
REPO_CONSOLIDATION = {}
for group, data in CONSOLIDATION.items():
    for repo in data["repos"]:
        REPO_CONSOLIDATION[repo] = (group, data["rec"])


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


def compute_health_score(repo: dict, tier: str) -> int:
    """0-100 health score per spec formula."""
    score = 100
    stale_days   = repo.get("stale_days", 0)
    ci_status    = repo.get("last_ci_status", "none")
    open_issues  = repo.get("open_issues", 0)
    description  = repo.get("description") or ""
    topics       = repo.get("topics") or []

    # Staleness deductions
    if stale_days > 90:
        score -= 30
    elif stale_days > 7 and tier == "core":
        score -= 20
    elif stale_days > 14 and tier == "active":
        score -= 15
    elif stale_days > 30 and tier == "monitored":
        score -= 10

    # CI deductions
    if ci_status == "failure":
        score -= 25
    elif ci_status == "none":
        score -= 5

    # Other deductions
    if open_issues > 10:
        score -= 10
    if not description.strip():
        score -= 5
    if not topics:
        score -= 5

    return max(0, min(100, score))


def classify_tier(repo_name: str, gh_archived: bool) -> str:
    if gh_archived or repo_name in ARCHIVED_REPOS:
        return "archived"
    if repo_name in CORE_REPOS:
        return "core"
    if repo_name in ACTIVE_REPOS:
        return "active"
    if repo_name in MONITORED_REPOS:
        return "monitored"
    return "monitored"  # default for unknown repos


def fetch_gh_repos() -> list:
    """Fetch all repos from GitHub API (paginated)."""
    repos = []
    page  = 1
    while True:
        url = f"https://api.github.com/user/repos"
        r = requests.get(url, headers=_gh_headers(),
                         params={"per_page": 100, "page": page, "affiliation": "owner"},
                         timeout=20)
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def build_repo_row(gh_repo: dict) -> dict:
    name       = gh_repo["name"]
    full_name  = gh_repo.get("full_name", f"{ORG}/{name}")
    tier       = classify_tier(name, gh_repo.get("archived", False))
    desc       = gh_repo.get("description") or ""
    lang       = gh_repo.get("language") or ""
    topics     = gh_repo.get("topics") or []
    default_br = gh_repo.get("default_branch", "main")
    is_private = gh_repo.get("private", False)

    # Parse timestamps
    created_at_gh = gh_repo.get("created_at")
    last_push_raw = gh_repo.get("pushed_at")
    last_push_at  = last_push_raw

    # Compute stale_days
    stale_days = 0
    if last_push_raw:
        push_dt    = datetime.fromisoformat(last_push_raw.replace("Z", "+00:00"))
        stale_days = (datetime.now(timezone.utc) - push_dt).days

    # Consolidation group
    cgroup, crec = REPO_CONSOLIDATION.get(name, (None, None))

    row = {
        "repo_name":                 name,
        "full_name":                 full_name,
        "tier":                      tier,
        "description":               desc,
        "language":                  lang,
        "topics":                    topics,
        "default_branch":            default_br,
        "is_private":                is_private,
        "created_at_gh":             created_at_gh,
        "last_push_at":              last_push_at,
        "open_issues":               gh_repo.get("open_issues_count", 0),
        "size_kb":                   gh_repo.get("size", 0),
        "stale_days":                stale_days,
        "last_ci_status":            "none",  # updated by repo_scanner.py
        "consolidation_group":       cgroup,
        "consolidation_recommendation": crec,
        "contributors":              [],
        "dependencies":              [],
    }

    row["health_score"] = compute_health_score(row, tier)
    return row


def seed_repos(limit: int = 60) -> dict:
    """
    Fetch all repos, build rows, upsert into nexus_repos.
    Returns summary.
    """
    logger.info("Fetching repos from GitHub...")
    gh_repos = fetch_gh_repos()
    logger.info(f"Found {len(gh_repos)} repos")

    rows = []
    for gh in gh_repos[:limit]:
        try:
            row = build_repo_row(gh)
            rows.append(row)
        except Exception as e:
            logger.warning(f"Skipping {gh.get('name','?')}: {e}")

    # Upsert in batches
    url = f"{SUPABASE_URL}/rest/v1/nexus_repos"
    batch_size = 25
    total = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        r = requests.post(url, headers=_sb_headers(), json=batch, timeout=20)
        if not r.ok:
            logger.error(f"Upsert batch {i} failed: {r.status_code} {r.text[:200]}")
        else:
            total += len(batch)

    # Count by tier
    tiers = {}
    for row in rows:
        t = row["tier"]
        tiers[t] = tiers.get(t, 0) + 1

    summary = {
        "total_seeded": total,
        "tiers":        tiers,
        "consolidation_groups": len(CONSOLIDATION),
    }
    logger.info(f"Seed complete: {summary}")
    return summary


def verify_seed() -> dict:
    """Verify nexus_repos row count from Supabase."""
    url = f"{SUPABASE_URL}/rest/v1/nexus_repos?select=repo_name,tier"
    r = requests.get(url, headers={
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }, timeout=15)
    rows = r.json() if r.ok else []
    tiers = {}
    for row in rows:
        t = row.get("tier", "?")
        tiers[t] = tiers.get(t, 0) + 1
    return {"total": len(rows), "tiers": tiers}


if __name__ == "__main__":
    from notifier import send_telegram

    logger.info("Starting nexus_repos seed...")
    summary = seed_repos(limit=60)
    verify  = verify_seed()

    msg = (
        f"✅ <b>nexus_repos Seeded</b>\n\n"
        f"• Total repos: {verify['total']}\n"
        f"• Core: {verify['tiers'].get('core', 0)}\n"
        f"• Active: {verify['tiers'].get('active', 0)}\n"
        f"• Monitored: {verify['tiers'].get('monitored', 0)}\n"
        f"• Archived: {verify['tiers'].get('archived', 0)}\n\n"
        f"Consolidation groups: {summary['consolidation_groups']}\n"
        f"Health scores computed ✓"
    )
    send_telegram(msg)
    print(msg)
