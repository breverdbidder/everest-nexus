"""
Seed Workflows — Initial full scan of all 50 repos.
Run once after migration to populate nexus_workflows.
"""
import logging
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from workflow_scanner import scan_all_repos
from notifier import send_telegram

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main():
    logger.info("Starting initial workflow seed for all repos...")
    summary = scan_all_repos()

    msg = (
        f"✅ <b>Workflow Seed Complete</b>\n\n"
        f"• Repos scanned: {summary['repos_scanned']}\n"
        f"• Workflows found: {summary['workflows_found']}\n"
        f"• Dead workflows: {summary['dead_count']}\n"
        f"• Failing workflows: {summary['failing_count']}\n\n"
        f"Data live in nexus_workflows ✓"
    )
    send_telegram(msg)
    print(msg)
    return summary


if __name__ == "__main__":
    main()
