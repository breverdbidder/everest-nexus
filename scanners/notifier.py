"""
Nexus Notifier — Telegram alert routing by priority
P0/P1 → instant
P2 → digest only
P3 → silent (dashboard only)
"""
import os
import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

BOT_TOKEN  = os.environ.get("BIDDEED_BOT_TOKEN", "")
CHAT_ID    = os.environ.get("BIDDEED_BOT_CHAT_ID", "740118343")
NEXUS_URL  = "https://nexus.zonewise.ai"

# Priority color prefixes
PRIORITY_EMOJI = {"P0": "🔴", "P1": "🟠", "P2": "🟡", "P3": "⚪"}


def send_telegram(text: str, parse_mode: str = "HTML") -> bool:
    """Send a Telegram message. Returns True on success."""
    if not BOT_TOKEN:
        logger.warning("BIDDEED_BOT_TOKEN not set — skipping Telegram")
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": parse_mode}
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")
        return False


def route_by_priority(task: dict, event: str = "created") -> bool:
    """
    Route notification based on priority:
    P0/P1 → instant Telegram
    P2/P3 → silent (dashboard only)
    """
    priority = task.get("priority", "P3")
    if priority in ("P0", "P1"):
        return notify_task(task, event)
    return False  # digest/silent


def notify_task(task: dict, event: str = "created") -> bool:
    priority = task.get("priority", "P2")
    emoji    = PRIORITY_EMOJI.get(priority, "⚪")
    desc     = task.get("description", "")[:200]
    task_id  = task.get("task_id", "")
    owner    = task.get("owner", "Claude Code")
    project  = task.get("project", "")

    if event == "blocked":
        text = (
            f"🚫 <b>BLOCKED</b> [{priority}]\n"
            f"{desc}\n"
            f"Owner: {owner} | Project: {project}\n"
            f"Task: <code>{task_id}</code>"
        )
    elif event == "resolved":
        text = (
            f"✅ <b>RESOLVED</b> [{priority}]\n"
            f"{desc}\n"
            f"Task: <code>{task_id}</code>"
        )
    elif event == "created":
        text = (
            f"{emoji} <b>NEW {priority}</b>: {desc}\n"
            f"Owner: {owner} | Project: {project}\n"
            f"Task: <code>{task_id}</code>"
        )
    else:
        text = f"{emoji} [{priority}] {desc} — <i>{event}</i>"

    return send_telegram(text)


def notify_p0_escalation(task: dict, elapsed_hours: float) -> bool:
    desc    = task.get("description", "")[:200]
    task_id = task.get("task_id", "")
    owner   = task.get("owner", "Claude Code")
    count   = task.get("escalation_count", 0)

    if elapsed_hours >= 4:
        text = (
            f"⚠️ <b>ACCOUNTABILITY</b> — P0 task started {elapsed_hours:.1f}h ago\n\n"
            f"{desc}\n\n"
            f"Owner: {owner}\n"
            f"Status? Be honest. Link: {NEXUS_URL}/tasks\n"
            f"Task: <code>{task_id}</code>"
        )
    else:
        text = (
            f"🔴 <b>P0 REMINDER #{count}</b>: {desc}\n"
            f"{elapsed_hours:.1f}h elapsed. Owner: {owner}\n"
            f"Task: <code>{task_id}</code> | {NEXUS_URL}/tasks"
        )
    return send_telegram(text)


def format_task_list(tasks: list, title: str = "Active Tasks") -> str:
    if not tasks:
        return f"<b>{title}</b>\nNone — all clear ✅"

    lines = [f"<b>{title}</b>\n"]
    for t in tasks[:20]:
        emoji  = PRIORITY_EMOJI.get(t.get("priority", "P3"), "⚪")
        tid    = t.get("task_id", "?")
        desc   = t.get("description", "")[:80]
        status = t.get("status", "")
        lines.append(f"{emoji} <code>{tid}</code> [{status}] {desc}")

    return "\n".join(lines)


def send_digest(stats: dict) -> bool:
    """Build and send the 9AM/5PM digest."""
    now = datetime.utcnow().strftime("%b %d %H:%M UTC")
    p0_tasks   = stats.get("p0_tasks", [])
    p1_tasks   = stats.get("p1_tasks", [])[:5]
    completed  = stats.get("completed_since_last", 0)
    created    = stats.get("created_since_last", 0)
    blocked    = stats.get("blocked_count", 0)
    repo_h     = stats.get("repos_healthy", 0)
    repo_t     = stats.get("repos_total", 0)
    wf_pass    = stats.get("workflows_passing", 0)
    wf_total   = stats.get("workflows_total", 0)
    stale_cnt  = stats.get("stale_count", 0)

    p0_section = "\n".join(
        f"  🔴 {t.get('task_id','?')} {t.get('description','')[:60]}"
        for t in p0_tasks
    ) or "  None — all clear ✅"

    p1_section = "\n".join(
        f"  🟠 {t.get('task_id','?')} {t.get('description','')[:60]}"
        for t in p1_tasks
    ) or "  None"

    text = (
        f"🧠 <b>BRAIN DIGEST</b> — {now}\n\n"
        f"🔴 <b>P0 CRITICAL ({len(p0_tasks)})</b>\n{p0_section}\n\n"
        f"📊 <b>Since last digest:</b>\n"
        f"• {completed} completed\n"
        f"• {created} new\n"
        f"• {blocked} blocked\n\n"
        f"🟠 <b>P1 needing attention ({len(p1_tasks)})</b>\n{p1_section}\n\n"
        f"📦 <b>Ecosystem health:</b>\n"
        f"• Repos: {repo_h}/{repo_t} healthy\n"
        f"• Workflows: {wf_pass}/{wf_total} passing\n"
        f"• Stale items: {stale_cnt}\n\n"
        f"🔗 {NEXUS_URL}"
    )[:4096]

    return send_telegram(text)


def notify_repo_event(repo_name: str, event: str, detail: str = "") -> bool:
    events = {
        "archived":  f"📦 <b>Archived:</b> {repo_name} — {detail}",
        "ci_failed": f"🔴 <b>CI FAILED:</b> {repo_name} — {detail}",
        "stale":     f"⏰ <b>Stale repo:</b> {repo_name} — {detail}",
    }
    text = events.get(event, f"📡 {repo_name}: {event} — {detail}")
    return send_telegram(text)


def notify_s1_complete() -> bool:
    text = (
        "✅ <b>NEXUS S1 COMPLETE</b>\n\n"
        "All S1 tasks executed:\n"
        "• 9 Supabase tables created (nexus_ prefix)\n"
        "• Task engine + escalation engine live\n"
        "• Workflow scanner ready (50 repos)\n"
        "• Telegram commands wired\n"
        "• pg_cron jobs scheduled\n"
        "• nexus_repos seeded (50 repos, tiered)\n\n"
        f"Dashboard: {NEXUS_URL}\n"
        "Next: S2 — Repo + Data Intelligence"
    )
    return send_telegram(text)
