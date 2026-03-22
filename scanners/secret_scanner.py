"""
Nexus Secret Scanner — Layer 5: Secret Intelligence
Fetches all GitHub Actions secrets for every breverdbidder repo.
Returns names + updated_at (NOT values). Cross-references shared secrets,
flags stale (>365 days), flags known-dead PATs.
Runs daily at 6AM UTC via pg_cron.
"""
import os
import logging
import time
import json
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import requests

logger = logging.getLogger(__name__)

GH_TOKEN     = os.environ.get("GH_PAT", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
ORG          = "breverdbidder"

# Known dead secrets — flagged per spec
KNOWN_DEAD = {"PAT1", "PAT2", "PAT3"}

# Stale threshold in days
STALE_DAYS = 365


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
    for i in range(0, len(rows), 50):
        batch = rows[i:i+50]
        r = requests.post(url, headers=_sb_headers(), json=batch, timeout=20)
        r.raise_for_status()


def _write_insight(insight: dict) -> None:
    try:
        url = f"{SUPABASE_URL}/rest/v1/nexus_insights"
        headers = {**_sb_headers(), "Prefer": "resolution=ignore-duplicates"}
        requests.post(url, headers=headers, json=insight, timeout=10)
    except Exception as e:
        logger.warning(f"Failed to write insight: {e}")


def fetch_repo_secrets(repo_name: str) -> list:
    """Fetch all secret names + metadata for a repo (not values)."""
    secrets = []
    page = 1
    while True:
        data = _gh_get(
            f"/repos/{ORG}/{repo_name}/actions/secrets",
            params={"per_page": 100, "page": page},
        )
        if not isinstance(data, dict):
            break
        items = data.get("secrets", [])
        if not items:
            break
        secrets.extend(items)
        if len(items) < 100:
            break
        page += 1
        time.sleep(0.1)
    return secrets


def fetch_org_secrets() -> list:
    """Fetch org-level secrets visible to repos."""
    secrets = []
    page = 1
    while True:
        data = _gh_get(
            f"/orgs/{ORG}/actions/secrets",
            params={"per_page": 100, "page": page},
        )
        if not isinstance(data, dict):
            break
        items = data.get("secrets", [])
        if not items:
            break
        secrets.extend(items)
        if len(items) < 100:
            break
        page += 1
        time.sleep(0.1)
    return secrets


def get_all_repo_names() -> list:
    """Fetch active repo names from nexus_repos."""
    url = f"{SUPABASE_URL}/rest/v1/nexus_repos?select=repo_name&tier=not.eq.archived"
    r = requests.get(url, headers={
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }, timeout=15)
    if r.ok:
        return [row["repo_name"] for row in r.json()]
    return []


def is_stale(updated_at_str: str) -> bool:
    """Return True if secret hasn't been updated in STALE_DAYS days."""
    if not updated_at_str:
        return True
    try:
        updated = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - updated) > timedelta(days=STALE_DAYS)
    except Exception:
        return False


def scan_all_secrets(repo_names: list = None) -> dict:
    """
    Scan secrets for all repos. Cross-reference, detect stale, flag dead.
    Returns summary dict.
    """
    if repo_names is None:
        repo_names = get_all_repo_names()

    now = datetime.now(timezone.utc).isoformat()

    # secret_name → list of (repo_name, updated_at)
    secret_map: dict[str, list[tuple[str, str]]] = defaultdict(list)

    # Collect all secrets per repo
    repo_secret_data: dict[str, list[dict]] = {}
    for repo_name in repo_names:
        logger.info(f"Fetching secrets: {repo_name}")
        try:
            secrets = fetch_repo_secrets(repo_name)
            repo_secret_data[repo_name] = secrets
            for s in secrets:
                secret_map[s["name"]].append((repo_name, s.get("updated_at", "")))
        except Exception as e:
            logger.error(f"Failed to fetch secrets for {repo_name}: {e}")
        time.sleep(0.2)

    # Collect org secrets
    try:
        org_secrets = fetch_org_secrets()
        for s in org_secrets:
            secret_map[s["name"]].append(("__org__", s.get("updated_at", "")))
    except Exception as e:
        logger.warning(f"Failed to fetch org secrets: {e}")
        org_secrets = []

    # Build rows for nexus_secrets
    rows = []
    stale_count = 0
    dead_count  = 0
    shared_count = 0

    for repo_name, secrets in repo_secret_data.items():
        for s in secrets:
            name       = s["name"]
            updated_at = s.get("updated_at", "")
            created_at = s.get("created_at", "")

            # Determine sharing
            all_occurrences = secret_map[name]
            shared_repos    = [r for r, _ in all_occurrences if r != repo_name and r != "__org__"]
            is_shared       = len(all_occurrences) > 1

            # Determine status
            if name in KNOWN_DEAD:
                status = "expired"
                dead_count += 1
            elif is_stale(updated_at):
                status = "unknown"  # stale but not confirmed expired
                stale_count += 1
            else:
                status = "active"

            if is_shared:
                shared_count += 1

            row = {
                "repo_name":              repo_name,
                "secret_name":            name,
                "created_at_gh":          created_at or None,
                "updated_at_gh":          updated_at or None,
                "is_org_secret":          False,
                "is_shared_across_repos": is_shared,
                "shared_with":            shared_repos,
                "status":                 status,
                "notes":                  "Known dead — rotate or remove" if name in KNOWN_DEAD else None,
                "updated_at":             now,
            }
            rows.append(row)

    # Add org secrets
    for s in org_secrets:
        name       = s["name"]
        updated_at = s.get("updated_at", "")
        created_at = s.get("created_at", "")

        if name in KNOWN_DEAD:
            status = "expired"
        elif is_stale(updated_at):
            status = "unknown"
        else:
            status = "active"

        row = {
            "repo_name":              "__org__",
            "secret_name":            name,
            "created_at_gh":          created_at or None,
            "updated_at_gh":          updated_at or None,
            "is_org_secret":          True,
            "is_shared_across_repos": True,
            "shared_with":            [],
            "status":                 status,
            "notes":                  "Known dead — rotate or remove" if name in KNOWN_DEAD else None,
            "updated_at":             now,
        }
        rows.append(row)

    # Upsert all rows
    if rows:
        _sb_upsert("nexus_secrets", rows)
        logger.info(f"Upserted {len(rows)} secret rows")

    # Generate insights
    _generate_insights(secret_map, repo_secret_data)

    summary = {
        "repos_scanned":  len(repo_names),
        "total_secrets":  len(rows),
        "stale_count":    stale_count,
        "dead_count":     dead_count,
        "shared_count":   shared_count,
        "scanned_at":     now,
    }
    logger.info(f"Secret scan complete: {summary}")
    return summary


def _generate_insights(secret_map: dict, repo_secret_data: dict) -> None:
    """Write insights for dead, stale, and inconsistently-shared secrets."""
    now = datetime.now(timezone.utc).isoformat()

    # Dead secrets
    for name in KNOWN_DEAD:
        if name in secret_map:
            repos_with_dead = [r for r, _ in secret_map[name] if r != "__org__"]
            _write_insight({
                "layer":           "secret",
                "insight_type":    "dead_secret",
                "severity":        "critical",
                "title":           f"Dead secret in use: {name}",
                "body":            f"{name} is a known-dead PAT still present in {len(repos_with_dead)} repo(s): {', '.join(repos_with_dead[:5])}. Remove or replace immediately.",
                "recommendation":  f"DELETE {name} from all repos — it is revoked and provides no access",
                "affected_entity": name,
                "auto_fixable":    False,
                "resolved":        False,
            })

    # Stale secrets (not dead, not updated in 365+ days)
    stale_secrets = []
    for name, occurrences in secret_map.items():
        if name in KNOWN_DEAD:
            continue
        for repo, updated_at in occurrences:
            if is_stale(updated_at):
                stale_secrets.append((name, repo, updated_at))

    if stale_secrets:
        # Group by secret name
        by_name: dict[str, list] = defaultdict(list)
        for name, repo, updated_at in stale_secrets:
            by_name[name].append(repo)

        for name, repos in list(by_name.items())[:20]:  # cap at 20 insights
            _write_insight({
                "layer":           "secret",
                "insight_type":    "stale_secret",
                "severity":        "warning",
                "title":           f"Stale secret: {name} (not rotated in 365+ days)",
                "body":            f"{name} found in {len(repos)} repo(s) with no rotation in over a year. Repos: {', '.join(repos[:5])}.",
                "recommendation":  f"ROTATE {name} — last updated >365 days ago",
                "affected_entity": name,
                "auto_fixable":    False,
                "resolved":        False,
            })

    # Shared secrets with inconsistent update times
    for name, occurrences in secret_map.items():
        if name in KNOWN_DEAD or len(occurrences) < 2:
            continue
        updated_times = [updated_at for _, updated_at in occurrences if updated_at]
        if len(updated_times) < 2:
            continue
        # Check if some copies are significantly more stale than others
        parsed = []
        for t in updated_times:
            try:
                parsed.append(datetime.fromisoformat(t.replace("Z", "+00:00")))
            except Exception:
                pass
        if len(parsed) >= 2:
            spread = (max(parsed) - min(parsed)).days
            if spread > 30 and len(occurrences) >= 5:
                _write_insight({
                    "layer":           "secret",
                    "insight_type":    "inconsistent_shared_secret",
                    "severity":        "warning",
                    "title":           f"Inconsistently rotated shared secret: {name}",
                    "body":            f"{name} is shared across {len(occurrences)} repos but copies have {spread}-day spread in update times. Some repos may have stale credentials.",
                    "recommendation":  f"SYNC rotation of {name} across all repos simultaneously",
                    "affected_entity": name,
                    "auto_fixable":    False,
                    "resolved":        False,
                })


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    import json as _json
    summary = scan_all_secrets()
    print(_json.dumps(summary, indent=2))
