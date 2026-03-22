"""
Nexus Data Scanner — Layer 4: Data Intelligence
Runs every 12 hours via pg_cron.
Queries Supabase information_schema for all tables, computes sizes,
detects orphans and missing RLS, assigns project ownership,
writes results to nexus_tables + generates insights.
"""
import os
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
import requests

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

# Project ownership: table prefix → project name
PREFIX_TO_PROJECT: dict[str, str] = {
    "nexus_":      "nexus",
    "biddeed_":    "biddeed",
    "zonewise_":   "zonewise",
    "lifeos_":     "lifeOS",
    "life_os_":    "lifeOS",
    "watch_":      "watch",
    "esf_":        "esf",
    "auction_":    "biddeed",
    "foreclosure_": "biddeed",
    "location_":   "zonewise",
    "task_":       "nexus",
    "workflow_":   "nexus",
    "repo_":       "nexus",
}

# Tables likely containing user data (need RLS scrutiny)
USER_DATA_PREFIXES = ["user", "auth", "profile", "account", "session", "biddeed_", "lifeos_"]

MIGRATION_FILE = Path(__file__).parent.parent / "supabase" / "migrations" / "003_data_scanner_functions.sql"


def _sb_headers() -> dict:
    return {
        "apikey":        SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type":  "application/json",
    }


def _sb_write_headers() -> dict:
    return {**_sb_headers(), "Prefer": "resolution=merge-duplicates"}


def apply_migration() -> bool:
    """
    Apply migration 003 (data scanner functions) via Supabase Management API.
    Falls back gracefully if already applied.
    """
    if not MIGRATION_FILE.exists():
        logger.warning(f"Migration file not found: {MIGRATION_FILE}")
        return False

    sql = MIGRATION_FILE.read_text()

    # Use Supabase Management API to execute SQL
    # The service_role key can execute SQL via the REST API SQL endpoint
    url = f"{SUPABASE_URL}/rest/v1/rpc/nexus_get_table_stats"
    test = requests.post(url, headers=_sb_headers(), json={}, timeout=10)
    if test.ok or test.status_code == 200:
        logger.info("Migration 003 already applied — skipping")
        return True

    # Try to apply via pg SQL exec approach
    # Split and execute each function block
    logger.info("Applying migration 003 data scanner functions...")
    try:
        # Use Supabase's database query endpoint (Management API)
        mgmt_url = f"https://api.supabase.com/v1/projects/{_extract_project_ref()}/database/query"
        # Management API requires a different token — log SQL for manual application instead
        logger.warning(
            "Cannot auto-apply migration via Management API (needs personal access token). "
            "Apply supabase/migrations/003_data_scanner_functions.sql via Supabase Dashboard SQL editor."
        )
        return False
    except Exception as e:
        logger.warning(f"Migration apply error: {e}")
        return False


def _extract_project_ref() -> str:
    """Extract project ref from Supabase URL."""
    # https://mocerqjnksmhcjzxrewo.supabase.co → mocerqjnksmhcjzxrewo
    return SUPABASE_URL.replace("https://", "").split(".")[0]


def rpc(function: str, params: dict = None) -> list | dict | None:
    """Call a Supabase RPC function."""
    url = f"{SUPABASE_URL}/rest/v1/rpc/{function}"
    r = requests.post(url, headers=_sb_headers(), json=params or {}, timeout=30)
    if r.ok:
        return r.json()
    logger.debug(f"RPC {function} failed: {r.status_code} {r.text[:200]}")
    return None


def fetch_table_stats() -> list[dict]:
    """
    Fetch table stats via nexus_get_table_stats() RPC.
    Falls back to querying known nexus_ tables directly.
    """
    result = rpc("nexus_get_table_stats")
    if result and isinstance(result, list) and len(result) > 0:
        logger.info(f"RPC returned {len(result)} tables")
        return result

    # Fallback: query the REST API for known tables and estimate stats
    logger.info("RPC unavailable — using REST API fallback for known tables")
    return _fetch_tables_via_rest()


def _fetch_tables_via_rest() -> list[dict]:
    """
    Fallback: enumerate all tables by checking the OpenAPI schema,
    then querying each for row count.
    """
    # First: fetch table list from OpenAPI schema
    all_tables: list[str] = []
    try:
        schema_url = f"{SUPABASE_URL}/rest/v1/"
        r = requests.get(schema_url, headers=_sb_headers(), timeout=15)
        if r.ok:
            paths = list(r.json().get("paths", {}).keys())
            # Filter to actual table paths (not RPC paths, no query params)
            all_tables = [
                p.lstrip("/") for p in paths
                if not p.startswith("/rpc/") and "{" not in p
            ]
            logger.info(f"Discovered {len(all_tables)} tables from OpenAPI schema")
    except Exception as e:
        logger.warning(f"OpenAPI schema fetch failed: {e}")

    # Fallback: hardcoded known tables
    if not all_tables:
        all_tables = [
            "nexus_tasks", "nexus_workflows", "nexus_repos", "nexus_tables",
            "nexus_secrets", "nexus_domains", "nexus_notifications",
            "nexus_chat_sessions", "nexus_insights",
            "users", "profiles", "sessions",
        ]

    result = []
    for table in all_tables:
        try:
            url = f"{SUPABASE_URL}/rest/v1/{table}?select=count"
            r = requests.get(url, headers={
                **_sb_headers(), "Prefer": "count=exact",
            }, timeout=10)
            if r.status_code in (200, 206):
                cr = r.headers.get("Content-Range", "*/0")
                try:
                    count = int(cr.split("/")[-1])
                except Exception:
                    count = 0
                result.append({
                    "table_name":  table,
                    "schema_name": "public",
                    "row_count":   count,
                    "size_bytes":  0,
                    "rls_enabled": None,  # unknown in fallback
                    "column_count": 0,
                    "has_fk_refs": False,
                    "last_vacuum":  None,
                    "last_analyze": None,
                })
        except Exception as e:
            logger.debug(f"REST check failed for {table}: {e}")

    return result


def fetch_exact_row_count(table_name: str) -> int:
    """Get exact row count via RPC (for orphan detection)."""
    result = rpc("nexus_count_table_rows", {"p_table": table_name})
    if isinstance(result, int):
        return result
    # Fallback: REST API count
    try:
        url = f"{SUPABASE_URL}/rest/v1/{table_name}?select=count"
        r = requests.get(url, headers={**_sb_headers(), "Prefer": "count=exact"}, timeout=10)
        if r.ok:
            cr = r.headers.get("Content-Range", "*/0")
            return int(cr.split("/")[-1])
    except Exception:
        pass
    return -1


def fetch_fk_refs() -> dict[str, list[str]]:
    """
    Returns dict: table_name → list of tables that reference it via FK.
    """
    refs = rpc("nexus_get_fk_refs")
    if not refs or not isinstance(refs, list):
        return {}
    result: dict[str, list[str]] = {}
    for row in refs:
        ref_table = row.get("referenced_table", "")
        src_table = row.get("source_table", "")
        if ref_table:
            result.setdefault(ref_table, [])
            if src_table and src_table not in result[ref_table]:
                result[ref_table].append(src_table)
    return result


def fetch_columns(table_name: str) -> list[dict]:
    """Fetch column metadata for a table."""
    result = rpc("nexus_get_table_columns", {"p_table": table_name})
    if result and isinstance(result, list):
        return [
            {
                "name":    r.get("column_name"),
                "type":    r.get("data_type"),
                "nullable": r.get("is_nullable") == "YES",
                "default": r.get("column_default"),
            }
            for r in result
        ]
    return []


def assign_project(table_name: str) -> str:
    """Determine project ownership from table name prefix."""
    for prefix, project in PREFIX_TO_PROJECT.items():
        if table_name.startswith(prefix):
            return project
    # Fallback by partial match
    if any(table_name.startswith(p) for p in USER_DATA_PREFIXES):
        return "shared"
    return "unknown"


def is_orphan(table_name: str, row_count: int, fk_refs: dict) -> bool:
    """
    Orphan = 0 rows + no FK references from other tables.
    nexus_ tables are never orphans (they're part of this system).
    """
    if table_name.startswith("nexus_"):
        return False
    if row_count > 0:
        return False
    if fk_refs.get(table_name):
        return False
    return True


def needs_rls_review(table_name: str, rls_enabled: bool) -> bool:
    """Flag tables that contain user data but have RLS disabled."""
    if rls_enabled:
        return False
    lower = table_name.lower()
    return any(lower.startswith(p) for p in USER_DATA_PREFIXES)


def build_table_row(stat: dict, fk_refs: dict) -> dict:
    table_name  = stat["table_name"]
    schema_name = stat.get("schema_name", "public")
    row_count   = stat.get("row_count", 0)
    size_bytes  = stat.get("size_bytes", 0)
    rls_enabled = stat.get("rls_enabled") or False
    has_fk      = bool(fk_refs.get(table_name))

    # Get exact count for small tables (orphan detection)
    if row_count == 0:
        exact = fetch_exact_row_count(table_name)
        if exact >= 0:
            row_count = exact

    orphan  = is_orphan(table_name, row_count, fk_refs)
    project = assign_project(table_name)

    # Columns (best-effort)
    columns = fetch_columns(table_name) if stat.get("column_count", 0) > 0 else []

    return {
        "table_name":        table_name,
        "schema_name":       schema_name,
        "table_type":        "table",
        "row_count":         row_count,
        "size_bytes":        size_bytes,
        "columns":           columns,
        "indexes":           [],
        "rls_enabled":       rls_enabled,
        "rls_policies":      [],
        "belongs_to_project": project,
        "last_insert_at":    None,
        "last_query_at":     stat.get("last_analyze"),
        "is_orphan":         orphan,
        "growth_rate_daily": None,
        "dependencies":      fk_refs.get(table_name, []),
        "updated_at":        datetime.now(timezone.utc).isoformat(),
    }


def upsert_tables(rows: list[dict]) -> int:
    if not rows:
        return 0
    url = f"{SUPABASE_URL}/rest/v1/nexus_tables"
    total = 0
    for i in range(0, len(rows), 25):
        batch = rows[i:i+25]
        r = requests.post(url, headers=_sb_write_headers(), json=batch, timeout=20)
        if r.ok:
            total += len(batch)
        else:
            logger.error(f"Upsert batch {i}: {r.status_code} {r.text[:200]}")
    return total


def build_insight(insight_type: str, title: str, body: str,
                  priority: str = "P2") -> dict:
    return {
        "id":           str(uuid.uuid4()),
        "insight_type": insight_type,
        "layer":        "data",
        "title":        title,
        "body":         body,
        "priority":     priority,
        "status":       "open",
        "created_at":   datetime.now(timezone.utc).isoformat(),
        "updated_at":   datetime.now(timezone.utc).isoformat(),
    }


def generate_data_insights(rows: list[dict]) -> list[dict]:
    insights = []

    orphans = [r for r in rows if r.get("is_orphan")]
    if orphans:
        names = ", ".join(r["table_name"] for r in orphans[:5])
        extra = f" (+{len(orphans)-5} more)" if len(orphans) > 5 else ""
        insights.append(build_insight(
            insight_type = "orphan_tables",
            priority     = "P2",
            title        = f"{len(orphans)} orphan table(s) detected",
            body         = (
                f"Tables with 0 rows and no FK references: {names}{extra}. "
                "Consider dropping or archiving these to reduce schema clutter."
            ),
        ))

    # Missing RLS on user-data tables
    no_rls = [r for r in rows if needs_rls_review(r["table_name"], r.get("rls_enabled", False))]
    if no_rls:
        names = ", ".join(r["table_name"] for r in no_rls[:5])
        insights.append(build_insight(
            insight_type = "missing_rls",
            priority     = "P1",
            title        = f"RLS not enabled on {len(no_rls)} user-data table(s)",
            body         = (
                f"Tables containing user data without RLS enabled: {names}. "
                "Enable RLS and add appropriate policies to prevent data leakage."
            ),
        ))

    # Large tables
    large = [r for r in rows if r.get("size_bytes", 0) > 10 * 1024 * 1024]  # >10MB
    for t in large[:3]:
        mb = t["size_bytes"] / (1024 * 1024)
        insights.append(build_insight(
            insight_type = "large_table",
            priority     = "P3",
            title        = f"Large table: {t['table_name']} ({mb:.1f} MB, {t['row_count']:,} rows)",
            body         = (
                f"Table '{t['table_name']}' is {mb:.1f} MB with {t['row_count']:,} rows. "
                "Monitor growth and consider archiving old data."
            ),
        ))

    return insights


def upsert_insights(insights: list[dict]) -> int:
    if not insights:
        return 0
    url = f"{SUPABASE_URL}/rest/v1/nexus_insights"
    r = requests.post(url, headers=_sb_write_headers(), json=insights, timeout=20)
    if r.ok:
        return len(insights)
    logger.error(f"Insight upsert failed: {r.status_code} {r.text[:300]}")
    return 0


def scan() -> dict:
    """
    Full data scan: fetch table stats, build rows, upsert nexus_tables,
    generate insights. Returns summary.
    """
    apply_migration()

    logger.info("Fetching table stats...")
    stats = fetch_table_stats()
    logger.info(f"Found {len(stats)} tables")

    fk_refs = fetch_fk_refs()
    logger.info(f"FK refs mapped for {len(fk_refs)} tables")

    rows = []
    for stat in stats:
        try:
            row = build_table_row(stat, fk_refs)
            rows.append(row)
        except Exception as e:
            logger.warning(f"Error building row for {stat.get('table_name','?')}: {e}")

    upserted = upsert_tables(rows)
    logger.info(f"Upserted {upserted} table rows to nexus_tables")

    insights = generate_data_insights(rows)
    ins_written = upsert_insights(insights)

    orphan_count = sum(1 for r in rows if r.get("is_orphan"))
    no_rls_count = sum(1 for r in rows if needs_rls_review(r["table_name"], r.get("rls_enabled", False)))

    by_project: dict[str, int] = {}
    for r in rows:
        p = r.get("belongs_to_project", "unknown")
        by_project[p] = by_project.get(p, 0) + 1

    return {
        "tables_scanned":   len(rows),
        "upserted":         upserted,
        "orphans":          orphan_count,
        "missing_rls":      no_rls_count,
        "insights_written": ins_written,
        "by_project":       by_project,
    }


if __name__ == "__main__":
    from notifier import send_telegram

    logger.info("Starting Nexus Data Scanner...")
    summary = scan()

    proj_str = "  ".join(f"{k}:{v}" for k, v in sorted(summary["by_project"].items()))
    msg = (
        f"🗄 <b>Data Scan Complete</b>\n\n"
        f"• Tables scanned: {summary['tables_scanned']}\n"
        f"• Orphan tables: {summary['orphans']}\n"
        f"• Missing RLS: {summary['missing_rls']}\n"
        f"• Insights written: {summary['insights_written']}\n"
        f"• By project: {proj_str or 'N/A'}"
    )
    send_telegram(msg)
    print(msg)
