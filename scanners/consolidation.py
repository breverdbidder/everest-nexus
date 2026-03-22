"""
Nexus Consolidation Engine — Layer 3 sub-module
Detects repo families, generates consolidation recommendations → nexus_insights,
provides archive_repo function (GitHub API PATCH archived=true).
"""
import os
import logging
import uuid
from datetime import datetime, timezone
import requests

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

GH_TOKEN     = os.environ.get("GH_PAT", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
ORG          = "breverdbidder"

# ── Family definitions (from spec) ─────────────────────────────────────────

FAMILIES: dict[str, dict] = {
    "zonewise-family": {
        "repos":  ["zonewise", "zonewise-web", "zonewise-desktop", "zonewise-landing",
                   "zonewise-agents", "zonewise-agent-teams", "zonewise-gtm",
                   "zonewise-loans", "zonewise-scraper-v4", "zonewise-modal"],
        "keep":   ["zonewise-web", "zonewise", "zonewise-landing", "zonewise-scraper-v4",
                   "zonewise-modal"],
        "merge":  [("zonewise-agents", "cli-anything-biddeed"),
                   ("zonewise-agent-teams", "cli-anything-biddeed")],
        "archive": ["zonewise-desktop", "zonewise-gtm", "zonewise-loans"],
        "recommendation": (
            "Merge zonewise-agents + zonewise-agent-teams into cli-anything-biddeed. "
            "Archive zonewise-desktop + zonewise-gtm + zonewise-loans (inactive). "
            "Keep zonewise-web + zonewise + zonewise-landing."
        ),
    },
    "biddeed-family": {
        "repos":  ["biddeed-ai", "biddeed-ai-ui", "biddeed-landing",
                   "biddeed-conversational-ai", "brevard-bidder-landing", "biddeed-brain"],
        "keep":   ["biddeed-ai", "biddeed-ai-ui", "biddeed-landing", "biddeed-brain"],
        "merge":  [("biddeed-ai", "biddeed-ai-ui")],  # into monorepo
        "archive": ["biddeed-conversational-ai", "brevard-bidder-landing"],
        "recommendation": (
            "Merge biddeed-ai + biddeed-ai-ui into monorepo. "
            "Archive biddeed-conversational-ai (superseded). "
            "Merge landing pages into one."
        ),
    },
    "infra-family": {
        "repos":  ["claude-code-telegram-control", "claude-code-telegram-control-1",
                   "cliproxy-gateway", "agents-command-center", "everest-dispatch"],
        "keep":   ["claude-code-telegram-control", "cliproxy-gateway", "everest-dispatch"],
        "merge":  [("agents-command-center", "cli-anything-biddeed")],
        "archive": ["claude-code-telegram-control-1"],
        "recommendation": (
            "Archive telegram-control-1 (duplicate). "
            "Merge agents-command-center into cli-anything."
        ),
    },
}

# Archive candidates: no push in 90+ days
ARCHIVE_THRESHOLD_DAYS = 90


def _gh_headers() -> dict:
    return {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}


def _sb_headers() -> dict:
    return {
        "apikey":        SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type":  "application/json",
        "Prefer":        "resolution=merge-duplicates",
    }


# ── Family detection ────────────────────────────────────────────────────────

def detect_families(repos: list[dict]) -> dict[str, list[str]]:
    """
    Given a list of repo dicts from nexus_repos, return detected families
    based on both explicit FAMILIES config and name-prefix matching.
    """
    result = {}
    repo_names = {r["repo_name"] for r in repos}

    # Explicit families
    for family, data in FAMILIES.items():
        matched = [r for r in data["repos"] if r in repo_names]
        if matched:
            result[family] = matched

    # Dynamic prefix detection (catch any not in explicit families)
    prefixes: dict[str, list[str]] = {}
    covered = {repo for rlist in result.values() for repo in rlist}
    for name in repo_names:
        if name in covered:
            continue
        parts = name.split("-")
        if len(parts) >= 2:
            prefix = parts[0]
            prefixes.setdefault(prefix, []).append(name)

    for prefix, names in prefixes.items():
        if len(names) >= 2:
            key = f"{prefix}-family"
            if key not in result:
                result[key] = names

    return result


# ── Archive candidates ──────────────────────────────────────────────────────

def find_archive_candidates(repos: list[dict]) -> list[dict]:
    """
    Find repos that are non-archived, stale 90+ days, not in a core set.
    """
    core_repos = {
        "everest-nexus", "zonewise-web", "biddeed-ai", "biddeed-ai-ui",
        "cli-anything-biddeed", "zonewise", "claude-code-telegram-control",
        "zonewise-scraper-v4", "life-os",
    }
    candidates = []
    for r in repos:
        if r.get("tier") == "archived":
            continue
        if r.get("repo_name") in core_repos:
            continue
        stale = r.get("stale_days", 0)
        if stale >= ARCHIVE_THRESHOLD_DAYS:
            candidates.append(r)
    return sorted(candidates, key=lambda x: x.get("stale_days", 0), reverse=True)


# ── Insight generation ──────────────────────────────────────────────────────

def build_insight(insight_type: str, title: str, body: str,
                  layer: str = "repos", priority: str = "P2",
                  repo_name: str = None) -> dict:
    return {
        "id":           str(uuid.uuid4()),
        "insight_type": insight_type,
        "layer":        layer,
        "title":        title,
        "body":         body,
        "priority":     priority,
        "repo_name":    repo_name,
        "status":       "open",
        "created_at":   datetime.now(timezone.utc).isoformat(),
        "updated_at":   datetime.now(timezone.utc).isoformat(),
    }


def generate_recommendations(repos: list[dict]) -> list[dict]:
    """
    Generate consolidation + archive insights for nexus_insights.
    """
    insights = []
    families = detect_families(repos)

    # Family consolidation recommendations
    for family_key, family_repos in families.items():
        if family_key not in FAMILIES:
            continue
        fdata = FAMILIES[family_key]
        rec   = fdata["recommendation"]
        insight = build_insight(
            insight_type = "consolidation",
            layer        = "repos",
            priority     = "P2",
            title        = f"Consolidate {family_key} ({len(family_repos)} repos)",
            body         = rec,
        )
        insights.append(insight)

    # Archive candidates
    candidates = find_archive_candidates(repos)
    for r in candidates[:10]:  # top 10 most stale
        name  = r["repo_name"]
        stale = r["stale_days"]
        insight = build_insight(
            insight_type = "archive_candidate",
            layer        = "repos",
            priority     = "P3",
            title        = f"Archive candidate: {name} ({stale} days stale)",
            body         = (
                f"Repo '{name}' has had no pushes in {stale} days "
                f"(tier: {r.get('tier','?')}, health: {r.get('health_score',0)}). "
                "Consider archiving if not actively needed."
            ),
            repo_name    = name,
        )
        insights.append(insight)

    # Dead CI on core repos
    for r in repos:
        if r.get("tier") == "core" and r.get("last_ci_status") == "failure":
            insight = build_insight(
                insight_type = "ci_failure",
                layer        = "repos",
                priority     = "P0",
                title        = f"CI failing on CORE repo: {r['repo_name']}",
                body         = (
                    f"Core repo '{r['repo_name']}' has a failing CI run. "
                    f"Last run: {r.get('last_ci_url','N/A')}. "
                    "Investigate immediately."
                ),
                repo_name    = r["repo_name"],
            )
            insights.append(insight)

    return insights


def upsert_insights(insights: list[dict]) -> int:
    if not insights:
        return 0
    url = f"{SUPABASE_URL}/rest/v1/nexus_insights"
    r = requests.post(url, headers=_sb_headers(), json=insights, timeout=20)
    if r.ok:
        return len(insights)
    logger.error(f"Upsert insights failed: {r.status_code} {r.text[:300]}")
    return 0


def fetch_repos_from_db() -> list[dict]:
    url = f"{SUPABASE_URL}/rest/v1/nexus_repos?select=repo_name,tier,stale_days,health_score,last_ci_status,last_ci_url&limit=200"
    r = requests.get(url, headers={
        "apikey":        SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }, timeout=20)
    if r.ok:
        return r.json()
    logger.error(f"Failed to fetch repos: {r.status_code}")
    return []


# ── Archive action ──────────────────────────────────────────────────────────

def archive_repo(repo_name: str, dry_run: bool = False) -> bool:
    """
    Archive a repo via GitHub API PATCH + update nexus_repos tier.
    Returns True on success.
    """
    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Archiving {repo_name}...")

    if not dry_run:
        # Step 1: Call GitHub API
        gh_url = f"https://api.github.com/repos/{ORG}/{repo_name}"
        r = requests.patch(gh_url, headers=_gh_headers(), json={"archived": True}, timeout=20)
        if not r.ok:
            logger.error(f"GitHub archive failed for {repo_name}: {r.status_code} {r.text[:200]}")
            return False

        # Step 2: Update nexus_repos
        sb_url = f"{SUPABASE_URL}/rest/v1/nexus_repos?repo_name=eq.{repo_name}"
        headers = {**_sb_headers(), "Prefer": "return=minimal"}
        headers.pop("Prefer")  # override
        headers["Prefer"] = "return=minimal"
        r2 = requests.patch(sb_url, headers={
            "apikey":        SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type":  "application/json",
            "Prefer":        "return=minimal",
        }, json={"tier": "archived"}, timeout=20)
        if not r2.ok:
            logger.warning(f"DB update failed for {repo_name}: {r2.status_code}")

    logger.info(f"Archived {repo_name} ✓")
    return True


# ── Main ────────────────────────────────────────────────────────────────────

def run() -> dict:
    """
    Detect families, generate recommendations, write to nexus_insights.
    Returns summary.
    """
    repos    = fetch_repos_from_db()
    families = detect_families(repos)
    insights = generate_recommendations(repos)
    written  = upsert_insights(insights)
    candidates = find_archive_candidates(repos)

    summary = {
        "repos_analyzed":   len(repos),
        "families_detected": len(families),
        "insights_written":  written,
        "archive_candidates": len(candidates),
        "families":          {k: len(v) for k, v in families.items()},
    }
    logger.info(f"Consolidation complete: {summary}")
    return summary


if __name__ == "__main__":
    from notifier import send_telegram

    logger.info("Running Nexus Consolidation Engine...")
    summary = run()

    families_str = "\n".join(f"  • {k}: {v} repos" for k, v in summary["families"].items())
    msg = (
        f"🗂 <b>Consolidation Engine Complete</b>\n\n"
        f"• Repos analyzed: {summary['repos_analyzed']}\n"
        f"• Families detected: {summary['families_detected']}\n"
        f"• Insights written: {summary['insights_written']}\n"
        f"• Archive candidates: {summary['archive_candidates']}\n\n"
        f"<b>Families:</b>\n{families_str}"
    )
    send_telegram(msg)
    print(msg)
