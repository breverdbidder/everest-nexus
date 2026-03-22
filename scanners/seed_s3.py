"""
Nexus S3 Seed — Run secret + domain scanners and send Telegram notification.
Execute once after S3 deployment or via GHA.
"""
import os
import sys
import logging
import json
import subprocess

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Validate required env vars
required = ["SUPABASE_URL", "SUPABASE_KEY"]
missing  = [k for k in required if not os.environ.get(k)]
if missing:
    logger.error(f"Missing required env vars: {missing}")
    sys.exit(1)

from secret_scanner import scan_all_secrets
from domain_scanner  import scan_all_domains
from notifier        import notify_s3_complete


def apply_migrations_if_needed() -> bool:
    """Apply foundation migration if SUPABASE_DB_URL is set and tables are missing."""
    db_url  = os.environ.get("SUPABASE_DB_URL")
    db_pass = os.environ.get("SUPABASE_DB_PASSWORD")

    if not db_url and not db_pass:
        logger.info("No DB credentials — skipping migration (assume tables exist or use GHA workflow)")
        return False

    migration_path = os.path.join(
        os.path.dirname(__file__), "..", "supabase", "migrations", "001_nexus_foundation.sql"
    )
    migration_path = os.path.abspath(migration_path)

    if not os.path.exists(migration_path):
        logger.warning(f"Migration file not found: {migration_path}")
        return False

    try:
        if db_url:
            cmd = ["psql", db_url, "-v", "ON_ERROR_STOP=1", "-f", migration_path]
            env = os.environ.copy()
        else:
            cmd = [
                "psql",
                "-h", "aws-0-us-east-1.pooler.supabase.com",
                "-p", "5432",
                "-U", "postgres.mocerqjnksmhcjzxrewo",
                "-d", "postgres",
                "-v", "ON_ERROR_STOP=1",
                "-f", migration_path,
            ]
            env = {**os.environ, "PGPASSWORD": db_pass}

        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            logger.info("✅ Migration 001 applied successfully")
            return True
        else:
            logger.warning(f"Migration returned non-zero: {result.stderr[:300]}")
            return False
    except Exception as e:
        logger.warning(f"Migration apply failed: {e}")
        return False


def main():
    logger.info("=== Nexus S3 Seed: Secret + Domain Intelligence ===")

    # Apply migrations if we have DB credentials
    apply_migrations_if_needed()

    # S3.1: Secret scanner
    logger.info("--- S3.1: Secret Scanner ---")
    try:
        secret_summary = scan_all_secrets()
        logger.info(f"Secret scan: {json.dumps(secret_summary)}")
    except Exception as e:
        logger.error(f"Secret scanner failed: {e}")
        secret_summary = {
            "error": str(e), "total_secrets": 0, "stale_count": 0,
            "dead_count": 0, "shared_count": 0, "repos_scanned": 0,
        }

    # S3.2: Domain scanner
    logger.info("--- S3.2: Domain Scanner ---")
    try:
        domain_summary = scan_all_domains()
        logger.info(f"Domain scan: {json.dumps(domain_summary)}")
    except Exception as e:
        logger.error(f"Domain scanner failed: {e}")
        domain_summary = {
            "error": str(e), "domains_scanned": 0, "active_count": 0,
            "ssl_ok_count": 0, "expiry_warnings": 0,
        }

    # S3.3: Telegram notification
    logger.info("--- S3.3: Telegram Notify ---")
    try:
        sent = notify_s3_complete(secret_summary, domain_summary)
        logger.info("Telegram sent" if sent else "Telegram skipped")
    except Exception as e:
        logger.error(f"Telegram notify failed: {e}")

    logger.info("=== S3 Seed Complete ===")
    result = {"secrets": secret_summary, "domains": domain_summary}
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    main()
