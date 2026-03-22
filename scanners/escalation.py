"""
Nexus Escalation Engine
- check_p0_escalation: runs every 2hr, sends P0 reminders
- send_accountability: fires at 4hr mark
- build_digest: builds 9AM/5PM digest and sends it
"""
import os
import logging
from datetime import datetime, timezone, timedelta

from task_engine import get_p0_open, get_digest_stats, _sb
from notifier import notify_p0_escalation, send_digest, send_telegram

logger = logging.getLogger(__name__)

SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
TASKS_TABLE  = "nexus_tasks"


def _headers() -> dict:
    return {
        "apikey":        SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type":  "application/json",
        "Prefer":        "return=representation",
    }


def check_p0_escalation() -> int:
    """
    Runs every 2 hours (pg_cron: '0 */2 * * *').
    For each open P0 task:
      - < 4h elapsed  → send P0 REMINDER (every 2hr)
      - >= 4h elapsed → send ACCOUNTABILITY message
    Increments escalation_count each time.
    Returns number of escalations fired.
    """
    import requests

    p0_tasks = get_p0_open()
    now = datetime.now(timezone.utc)
    fired = 0

    for task in p0_tasks:
        created_raw = task.get("created_at") or task.get("started_at")
        if not created_raw:
            continue

        created = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
        elapsed_hours = (now - created).total_seconds() / 3600
        count = task.get("escalation_count", 0) + 1

        notify_p0_escalation(task, elapsed_hours)

        # Update escalation metadata
        url = f"{os.environ.get('SUPABASE_URL')}/rest/v1/{TASKS_TABLE}?task_id=eq.{task['task_id']}"
        requests.patch(url, headers=_headers(), json={
            "escalation_count":   count,
            "last_escalated_at":  now.isoformat(),
        }, timeout=10)

        logger.info(f"Escalated P0 {task['task_id']} (count={count}, elapsed={elapsed_hours:.1f}h)")
        fired += 1

    return fired


def send_accountability(task: dict, elapsed_hours: float):
    """
    4hr accountability check — called when elapsed >= 4h.
    Sends a direct accountability challenge.
    """
    desc    = task.get("description", "")[:200]
    task_id = task.get("task_id", "?")
    owner   = task.get("owner", "Claude Code")

    text = (
        f"⚠️ <b>ACCOUNTABILITY CHECK</b>\n\n"
        f"P0 task <code>{task_id}</code> has been open for {elapsed_hours:.1f} hours.\n\n"
        f"<b>{desc}</b>\n\n"
        f"Owner: {owner}\n"
        f"What's the honest status? Reply /done {task_id} or /block {task_id} with reason.\n\n"
        f"https://nexus.zonewise.ai/tasks"
    )
    send_telegram(text)


def build_and_send_digest() -> bool:
    """
    Builds and sends the BRAIN DIGEST.
    Called by pg_cron at 9AM EST (14:00 UTC) and 5PM EST (22:00 UTC).
    """
    try:
        stats = get_digest_stats(since_hours=8)
        return send_digest(stats)
    except Exception as e:
        logger.error(f"Digest failed: {e}")
        send_telegram(f"⚠️ Digest build failed: {e}")
        return False


def check_staleness() -> int:
    """
    Runs every 5 minutes (pg_cron: '*/5 * * * *').
    Updates stale_days on nexus_repos and flags overdue tasks.
    Returns count of stale items found.
    """
    now = datetime.now(timezone.utc)
    stale_count = 0

    # Update repo staleness
    try:
        repos = _sb("GET", "nexus_repos?select=repo_name,last_push_at") or []
        import requests as req
        url_base = os.environ.get("SUPABASE_URL", "")

        for repo in repos:
            push_raw = repo.get("last_push_at")
            if not push_raw:
                continue
            push_at = datetime.fromisoformat(push_raw.replace("Z", "+00:00"))
            stale_days = (now - push_at).days

            req.patch(
                f"{url_base}/rest/v1/nexus_repos?repo_name=eq.{repo['repo_name']}",
                headers=_headers(),
                json={"stale_days": stale_days},
                timeout=10,
            )
            if stale_days > 7:
                stale_count += 1

    except Exception as e:
        logger.error(f"Staleness check failed: {e}")

    return stale_count


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    cmd = sys.argv[1] if len(sys.argv) > 1 else "escalation"
    if cmd == "digest":
        result = build_and_send_digest()
        print(f"Digest sent: {result}")
    elif cmd == "staleness":
        count = check_staleness()
        print(f"Stale repos updated: {count}")
    else:
        count = check_p0_escalation()
        print(f"P0 escalations fired: {count}")
