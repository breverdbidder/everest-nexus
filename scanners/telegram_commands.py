"""
Nexus Telegram Command Handlers
Commands: /tasks /p0 /p1 /stale /bump /demote /done /skip /block /digest /nexus
Wire into bot_v4.py in claude-code-telegram-control via:
    from nexus.telegram_commands import handle_nexus_command
"""
import os
import logging
import sys
sys.path.insert(0, os.path.dirname(__file__))

from task_engine import (
    get_active, get_by_priority, get_stale, get_blocked,
    update_status, bump_priority, demote_priority, get_task, create_task
)
from notifier import format_task_list, send_telegram, send_digest
from escalation import build_and_send_digest

logger = logging.getLogger(__name__)
NEXUS_URL = "https://nexus.zonewise.ai"

COMMAND_REGISTRY = {
    "/tasks", "/p0", "/p1", "/stale",
    "/bump", "/demote", "/done", "/skip", "/block",
    "/digest", "/nexus",
}


def is_nexus_command(text: str) -> bool:
    """Check if the message is a Nexus command."""
    if not text:
        return False
    cmd = text.strip().split()[0].lower()
    return cmd in COMMAND_REGISTRY


def handle_nexus_command(text: str, chat_id: str = None) -> str:
    """
    Route a Telegram command to the correct handler.
    Returns the response text (also sends it via Telegram if chat_id provided).
    """
    parts   = text.strip().split()
    cmd     = parts[0].lower() if parts else ""
    args    = parts[1:] if len(parts) > 1 else []

    try:
        if cmd == "/tasks":
            response = _cmd_tasks()
        elif cmd == "/p0":
            response = _cmd_priority("P0")
        elif cmd == "/p1":
            response = _cmd_priority("P1")
        elif cmd == "/stale":
            response = _cmd_stale()
        elif cmd == "/bump":
            response = _cmd_bump(args)
        elif cmd == "/demote":
            response = _cmd_demote(args)
        elif cmd == "/done":
            response = _cmd_done(args)
        elif cmd == "/skip":
            response = _cmd_skip(args)
        elif cmd == "/block":
            response = _cmd_block(args)
        elif cmd == "/digest":
            response = _cmd_digest()
        elif cmd == "/nexus":
            response = _cmd_nexus()
        else:
            response = f"Unknown Nexus command: {cmd}"

    except Exception as e:
        logger.error(f"Command {cmd} failed: {e}")
        response = f"⚠️ Error executing {cmd}: {e}"

    if chat_id:
        send_telegram(response)

    return response


# ── Command handlers ─────────────────────────────────────────────────────────

def _cmd_tasks() -> str:
    tasks = get_active(limit=20)
    return format_task_list(tasks, "Active Tasks (by priority)")


def _cmd_priority(priority: str) -> str:
    tasks = get_by_priority(priority)
    emoji = {"P0": "🔴", "P1": "🟠", "P2": "🟡", "P3": "⚪"}.get(priority, "")
    return format_task_list(tasks, f"{emoji} {priority} Tasks")


def _cmd_stale() -> str:
    tasks = get_stale(limit=15)
    if not tasks:
        return "✅ No stale tasks — all within SLA"
    lines = [f"⏰ <b>Stale Tasks (past SLA)</b>\n"]
    for t in tasks:
        tid   = t.get("task_id", "?")
        desc  = t.get("description", "")[:70]
        prio  = t.get("priority", "?")
        sla   = t.get("sla_deadline", "")[:10]
        lines.append(f"• <code>{tid}</code> [{prio}] {desc} (SLA: {sla})")
    return "\n".join(lines)


def _cmd_bump(args: list) -> str:
    if not args:
        return "Usage: /bump <task_id>"
    task_id = args[0].upper()
    result  = bump_priority(task_id)
    if not result:
        return f"Task {task_id} not found"
    new_p = result.get("priority", "?")
    desc  = result.get("description", "")[:60]
    return f"⬆️ <code>{task_id}</code> bumped to <b>{new_p}</b>\n{desc}"


def _cmd_demote(args: list) -> str:
    if not args:
        return "Usage: /demote <task_id>"
    task_id = args[0].upper()
    result  = demote_priority(task_id)
    if not result:
        return f"Task {task_id} not found"
    new_p = result.get("priority", "?")
    desc  = result.get("description", "")[:60]
    return f"⬇️ <code>{task_id}</code> demoted to <b>{new_p}</b>\n{desc}"


def _cmd_done(args: list) -> str:
    if not args:
        return "Usage: /done <task_id>"
    task_id = args[0].upper()
    task    = get_task(task_id)
    if not task:
        return f"Task {task_id} not found"
    update_status(task_id, "success")
    desc = task.get("description", "")[:80]
    prio = task.get("priority", "P2")
    # Instant notify for P0/P1
    if prio in ("P0", "P1"):
        send_telegram(f"✅ <b>RESOLVED [{prio}]</b>: {desc}\nTask: <code>{task_id}</code>")
    return f"✅ <code>{task_id}</code> marked <b>success</b>"


def _cmd_skip(args: list) -> str:
    if not args:
        return "Usage: /skip <task_id>"
    task_id = args[0].upper()
    task    = get_task(task_id)
    if not task:
        return f"Task {task_id} not found"
    update_status(task_id, "skipped")
    return f"⏭️ <code>{task_id}</code> marked <b>skipped</b>"


def _cmd_block(args: list) -> str:
    if not args:
        return "Usage: /block <task_id> [reason...]"
    task_id = args[0].upper()
    reason  = " ".join(args[1:]) if len(args) > 1 else "No reason given"
    task    = get_task(task_id)
    if not task:
        return f"Task {task_id} not found"

    update_status(task_id, "blocked", error_message=reason)
    desc = task.get("description", "")[:80]
    send_telegram(
        f"🚫 <b>BLOCKED</b>: <code>{task_id}</code>\n"
        f"{desc}\n"
        f"Reason: {reason}"
    )
    return f"🚫 <code>{task_id}</code> marked <b>blocked</b>"


def _cmd_digest() -> str:
    result = build_and_send_digest()
    return "📊 Digest sent!" if result else "⚠️ Digest failed"


def _cmd_nexus() -> str:
    # Quick stats from Supabase
    try:
        import os, requests
        sb_url = os.environ.get("SUPABASE_URL", "")
        sb_key = os.environ.get("SUPABASE_KEY", "")
        headers = {
            "apikey": sb_key,
            "Authorization": f"Bearer {sb_key}",
        }
        tasks  = requests.get(f"{sb_url}/rest/v1/nexus_tasks?select=priority,status&status=not.in.(success,failed,cancelled,skipped,timeout)", headers=headers, timeout=10).json()
        repos  = requests.get(f"{sb_url}/rest/v1/nexus_repos?select=tier", headers=headers, timeout=10).json()
        wfs    = requests.get(f"{sb_url}/rest/v1/nexus_workflows?select=is_dead", headers=headers, timeout=10).json()

        p0 = sum(1 for t in tasks if t.get("priority") == "P0")
        p1 = sum(1 for t in tasks if t.get("priority") == "P1")
        p2 = sum(1 for t in tasks if t.get("priority") == "P2")
        dead_wf = sum(1 for w in wfs if w.get("is_dead"))

        return (
            f"🧠 <b>Nexus Quick Stats</b>\n\n"
            f"Tasks: 🔴P0={p0} 🟠P1={p1} 🟡P2={p2}\n"
            f"Repos: {len(repos)} tracked\n"
            f"Workflows: {len(wfs)} ({dead_wf} dead)\n\n"
            f"🔗 {NEXUS_URL}"
        )
    except Exception as e:
        return f"🧠 Nexus Dashboard\n🔗 {NEXUS_URL}\n(Stats unavailable: {e})"


# ── Hook for bot_v4.py integration ──────────────────────────────────────────

def process_message(message: dict) -> bool:
    """
    Process a Telegram message dict (from bot_v4.py webhook/polling).
    Returns True if handled as a Nexus command.
    """
    text    = message.get("text", "")
    chat_id = str(message.get("chat", {}).get("id", ""))

    if not is_nexus_command(text):
        return False

    response = handle_nexus_command(text, chat_id=chat_id)
    logger.info(f"Nexus command '{text.split()[0]}' handled for chat {chat_id}")
    return True


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    cmd = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "/nexus"
    print(f"Testing command: {cmd}")
    print(handle_nexus_command(cmd))
