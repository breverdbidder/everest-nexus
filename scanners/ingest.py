#!/usr/bin/env python3
"""
Nexus Ingest — Claude AI CLI Task Ingestion Wrapper
====================================================
Designed to be called from bash_tool during Claude AI chat sessions.

Usage (from bash/shell):
  python scanners/ingest.py task "description" [--priority P1] [--project nexus] [--owner Ariel]
  python scanners/ingest.py session '{"session_id":"...","summary":"...","tokens_used":1234}'
  python scanners/ingest.py batch '[{"description":"..."},{"description":"..."}]'
  python scanners/ingest.py status T-ABC12345 running
  python scanners/ingest.py done T-ABC12345
  python scanners/ingest.py block T-ABC12345 "blocked by missing API key"

Exit codes: 0=success, 1=error
Stdout: JSON result on success, error message on failure
"""
import os
import sys
import json
import argparse
import logging

sys.path.insert(0, os.path.dirname(__file__))

from task_engine import create_task, update_status, get_task, get_active, get_by_priority
from notifier import route_by_priority, send_telegram

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

NEXUS_URL = "https://nexus.zonewise.ai"


# ── Supabase direct REST for sessions ────────────────────────────────────────

def _sb_post(table: str, payload: dict) -> dict:
    import requests
    url = f"{os.environ.get('SUPABASE_URL', '')}/rest/v1/{table}"
    headers = {
        "apikey":        os.environ.get("SUPABASE_KEY", ""),
        "Authorization": f"Bearer {os.environ.get('SUPABASE_KEY', '')}",
        "Content-Type":  "application/json",
        "Prefer":        "return=representation",
    }
    r = requests.post(url, headers=headers, json=payload, timeout=15)
    r.raise_for_status()
    result = r.json()
    return result[0] if isinstance(result, list) and result else result


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_task(args) -> dict:
    """Push a single task to nexus_tasks."""
    description = args.description
    priority    = args.priority or None
    project     = args.project or ""
    owner       = args.owner or "Claude Code"
    task_type   = args.type or "claude_ai"
    platform    = args.platform or "shared"
    chat_id     = args.chat_id or ""

    row = create_task(
        description=description,
        priority=priority,
        project=project,
        owner=owner,
        task_type=task_type,
        platform=platform,
        triggered_by="claude_ai",
        source_chat_id=chat_id,
        auto_priority=(priority is None),
    )

    # Route notification
    route_by_priority(row, event="created")

    return row


def cmd_session(args) -> dict:
    """Push a chat session summary to nexus_chat_sessions."""
    try:
        payload = json.loads(args.json_payload)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")

    # Ensure triggered_by is set
    payload.setdefault("triggered_by", "claude_ai")
    payload.setdefault("platform", "shared")

    row = _sb_post("nexus_chat_sessions", payload)
    return row


def cmd_batch(args) -> list:
    """Push multiple tasks at once."""
    try:
        tasks = json.loads(args.json_payload)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")

    if not isinstance(tasks, list):
        raise ValueError("batch expects a JSON array")

    results = []
    for i, t in enumerate(tasks):
        desc     = t.get("description", f"Task {i+1}")
        priority = t.get("priority")
        project  = t.get("project", "")
        owner    = t.get("owner", "Claude Code")

        row = create_task(
            description=desc,
            priority=priority,
            project=project,
            owner=owner,
            task_type=t.get("task_type", "claude_ai"),
            platform=t.get("platform", "shared"),
            triggered_by="claude_ai",
            auto_priority=(priority is None),
        )
        results.append(row)

    return results


def cmd_status(args) -> dict:
    """Update task status."""
    task_id = args.task_id.upper()
    status  = args.new_status

    valid = {"queued","dispatched","running","blocked","success","failed","timeout","cancelled","skipped"}
    if status not in valid:
        raise ValueError(f"Invalid status '{status}'. Valid: {', '.join(sorted(valid))}")

    extra = {}
    if args.message:
        if status in ("failed", "blocked"):
            extra["error_message"] = args.message
        else:
            extra["result_summary"] = args.message

    row = update_status(task_id, status, **extra)

    # Notify on block/done for P0/P1
    task = get_task(task_id)
    if task:
        if status == "blocked":
            route_by_priority(task, event="blocked")
        elif status == "success" and task.get("priority") in ("P0", "P1"):
            route_by_priority(task, event="resolved")

    return row


def cmd_done(args) -> dict:
    """Mark a task as success (shorthand)."""
    task_id = args.task_id.upper()
    task    = get_task(task_id)
    if not task:
        raise ValueError(f"Task {task_id} not found")

    row = update_status(task_id, "success",
                        result_summary=args.message or "Completed via ingest CLI")

    if task.get("priority") in ("P0", "P1"):
        route_by_priority(task, event="resolved")

    return row


def cmd_block(args) -> dict:
    """Mark a task as blocked."""
    task_id = args.task_id.upper()
    reason  = args.reason or "Blocked via ingest CLI"

    task = get_task(task_id)
    if not task:
        raise ValueError(f"Task {task_id} not found")

    row = update_status(task_id, "blocked", error_message=reason)
    route_by_priority(task, event="blocked")
    return row


def cmd_list(args) -> list:
    """List active tasks (quick view)."""
    if args.priority:
        return get_by_priority(args.priority.upper())
    return get_active(limit=20)


# ── CLI parser ────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ingest",
        description="Nexus Ingest — push tasks from Claude AI bash_tool",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # task
    p_task = sub.add_parser("task", help="Push a single task")
    p_task.add_argument("description", help="Task description")
    p_task.add_argument("--priority", "-p", choices=["P0","P1","P2","P3"], help="Override auto-priority")
    p_task.add_argument("--project", "-P", help="Project name (e.g. nexus, biddeed)")
    p_task.add_argument("--owner", "-o", help="Task owner (default: Claude Code)")
    p_task.add_argument("--type",   "-t", help="Task type (default: claude_ai)")
    p_task.add_argument("--platform", help="Platform (default: shared)")
    p_task.add_argument("--chat-id", dest="chat_id", help="Source chat session ID")

    # session
    p_sess = sub.add_parser("session", help="Push a chat session summary")
    p_sess.add_argument("json_payload", help="JSON object with session fields")

    # batch
    p_batch = sub.add_parser("batch", help="Push multiple tasks as JSON array")
    p_batch.add_argument("json_payload", help="JSON array of task objects")

    # status
    p_status = sub.add_parser("status", help="Update task status")
    p_status.add_argument("task_id",    help="Task ID (e.g. T-ABC12345)")
    p_status.add_argument("new_status", help="New status")
    p_status.add_argument("--message",  "-m", help="Result summary or error message")

    # done
    p_done = sub.add_parser("done", help="Mark task as success")
    p_done.add_argument("task_id", help="Task ID")
    p_done.add_argument("--message", "-m", help="Completion summary")

    # block
    p_block = sub.add_parser("block", help="Mark task as blocked")
    p_block.add_argument("task_id", help="Task ID")
    p_block.add_argument("reason", nargs="?", default=None, help="Reason for blocking")

    # list
    p_list = sub.add_parser("list", help="List active tasks")
    p_list.add_argument("--priority", "-p", choices=["P0","P1","P2","P3"], help="Filter by priority")

    return parser


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = build_parser()
    args   = parser.parse_args()

    try:
        if args.command == "task":
            result = cmd_task(args)
        elif args.command == "session":
            result = cmd_session(args)
        elif args.command == "batch":
            result = cmd_batch(args)
        elif args.command == "status":
            result = cmd_status(args)
        elif args.command == "done":
            result = cmd_done(args)
        elif args.command == "block":
            result = cmd_block(args)
        elif args.command == "list":
            result = cmd_list(args)
        else:
            parser.print_help()
            sys.exit(1)

        print(json.dumps(result, indent=2, default=str))
        sys.exit(0)

    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
