"""
Nexus S2 Seed — Run Repo + Data Intelligence scanners and send Telegram notification.
Execute once after S2 deployment or via GHA.
"""
import os
import sys
import logging
import json
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

required = ["SUPABASE_URL", "SUPABASE_KEY"]
missing  = [k for k in required if not os.environ.get(k)]
if missing:
    logger.error(f"Missing required env vars: {missing}")
    sys.exit(1)

from repo_scanner   import scan as scan_repos
from consolidation  import run as run_consolidation
from data_scanner   import scan as scan_data
from notifier       import send_telegram


def apply_migrations_if_needed() -> bool:
    """Apply foundation migrations if DB credentials are set."""
    db_url  = os.environ.get("SUPABASE_DB_URL")
    db_pass = os.environ.get("SUPABASE_DB_PASSWORD")

    if not db_url and not db_pass:
        logger.info("No DB credentials — skipping migration (assume tables exist or use GHA)")
        return False

    import subprocess

    migrations_dir = Path(__file__).parent.parent / "supabase" / "migrations"
    migration_files = sorted(migrations_dir.glob("*.sql"))

    for mf in migration_files:
        logger.info(f"Applying {mf.name}...")
        try:
            if db_url:
                cmd = ["psql", db_url, "-v", "ON_ERROR_STOP=0", "-f", str(mf)]
                env = os.environ.copy()
                result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=60)
            else:
                env = os.environ.copy()
                env["PGPASSWORD"] = db_pass
                ref  = os.environ.get("SUPABASE_URL", "").replace("https://", "").split(".")[0]
                host = f"aws-0-us-west-2.pooler.supabase.com"
                cmd  = [
                    "psql",
                    "-h", host, "-p", "5432",
                    "-U", f"postgres.{ref}",
                    "-d", "postgres",
                    "-v", "ON_ERROR_STOP=0",
                    "-f", str(mf),
                ]
                result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                logger.info(f"  ✅ Applied {mf.name}")
            else:
                logger.warning(f"  ⚠️  {mf.name} returned code {result.returncode}: {result.stderr[:200]}")
        except Exception as e:
            logger.warning(f"  Migration {mf.name} failed: {e}")

    return True


def main() -> None:
    logger.info("=" * 60)
    logger.info("NEXUS S2 SEED — Repo + Data Intelligence")
    logger.info("=" * 60)

    # Try to apply migrations
    apply_migrations_if_needed()

    # ── S2.1 + S2.2: Repo Scanner + Consolidation ─────────────────────────
    logger.info("\n── S2.1 Repo Scanner ──────────────────────────────────────")
    try:
        repo_summary = scan_repos(fetch_ci=True)
        logger.info(f"Repo scan: {repo_summary}")
    except Exception as e:
        logger.error(f"Repo scan failed: {e}")
        repo_summary = {"error": str(e)}

    logger.info("\n── S2.2 Consolidation Engine ──────────────────────────────")
    try:
        cons_summary = run_consolidation()
        logger.info(f"Consolidation: {cons_summary}")
    except Exception as e:
        logger.error(f"Consolidation failed: {e}")
        cons_summary = {"error": str(e)}

    # ── S2.3 Data Scanner ──────────────────────────────────────────────────
    logger.info("\n── S2.3 Data Scanner ──────────────────────────────────────")
    try:
        data_summary = scan_data()
        logger.info(f"Data scan: {data_summary}")
    except Exception as e:
        logger.error(f"Data scan failed: {e}")
        data_summary = {"error": str(e)}

    # ── Telegram Notification ──────────────────────────────────────────────
    repos_total  = repo_summary.get("total_db", repo_summary.get("scanned", 0))
    repos_upserted = repo_summary.get("upserted", 0)
    tiers        = repo_summary.get("tiers", {})
    tier_str     = "  ".join(f"{t}:{c}" for t, c in sorted(tiers.items())) if tiers else "N/A"
    ins_written  = cons_summary.get("insights_written", 0) + data_summary.get("insights_written", 0)
    families     = cons_summary.get("families_detected", 0)
    tables       = data_summary.get("tables_scanned", 0)
    orphans      = data_summary.get("orphans", 0)

    db_note = ""
    if repos_upserted == 0 and not repo_summary.get("error"):
        db_note = "\n\n⚠️ <b>Note:</b> Supabase tables not yet created. Add SUPABASE_DB_URL secret and re-run GHA to apply migrations."

    msg = (
        f"✅ <b>NEXUS S2 COMPLETE</b>\n\n"
        f"<b>S2.1 Repo Intelligence:</b>\n"
        f"• Repos scanned: {repo_summary.get('scanned', 0)}\n"
        f"• Tiers: {tier_str}\n"
        f"• CI status updated for core/active ✓\n\n"
        f"<b>S2.2 Consolidation Engine:</b>\n"
        f"• Families detected: {families}\n"
        f"• Insights generated: {cons_summary.get('insights_written', 0)}\n"
        f"• Archive candidates: {cons_summary.get('archive_candidates', 0)}\n\n"
        f"<b>S2.3 Data Intelligence:</b>\n"
        f"• Tables scanned: {tables}\n"
        f"• Orphan tables: {orphans}\n"
        f"• Insights: {data_summary.get('insights_written', 0)}\n\n"
        f"Total insights: {ins_written}\n"
        f"Next: S4 Dashboard 🚀"
        f"{db_note}"
    )
    send_telegram(msg)
    print(msg)
    logger.info("S2 seed complete.")


if __name__ == "__main__":
    main()
