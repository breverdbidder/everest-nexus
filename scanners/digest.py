#!/usr/bin/env python3
"""
digest.py — Nexus Brain Digest Builder
========================================
Builds and sends the 9AM (morning) and 5PM (evening) EST digests.

Schedule (UTC):
  Morning digest:  14:00 UTC = 9AM EST / 10AM EDT
  Evening digest:  22:00 UTC = 5PM EST / 6PM EDT

Usage:
  python scanners/digest.py            # auto-detect morning/evening
  python scanners/digest.py morning    # force morning digest
  python scanners/digest.py evening    # force evening digest
  python scanners/digest.py test       # send test digest (no time check)

GHA schedule cron:
  Morning: '0 14 * * *'
  Evening: '0 22 * * *'
"""
import os
import sys
import logging
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from task_engine import (
    get_p0_open, get_by_priority, get_stale, get_blocked,
    get_digest_stats, _sb,
)
from notifier import send_telegram
from escalation import check_p0_escalation
from automation_health import format_automation_health_section

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("digest")

NEXUS_URL = "https://nexus.zonewise.ai"


# ── Digest sections ───────────────────────────────────────────────────────────

def _fmt_task_line(t: dict, max_len: int = 65) -> str:
    emoji  = {"P0": "🔴", "P1": "🟠", "P2": "🟡", "P3": "⚪"}.get(t.get("priority", "P3"), "⚪")
    tid    = t.get("task_id", "?")
    desc   = t.get("description", "")[:max_len]
    proj   = t.get("project", "")
    proj_s = f" [{proj}]" if proj else ""
    return f"  {emoji} <code>{tid}</code>{proj_s} {desc}"


def _p0_section(p0_tasks: list) -> str:
    if not p0_tasks:
        return "  None — all clear ✅"
    return "\n".join(_fmt_task_line(t) for t in p0_tasks)


def _p1_section(p1_tasks: list) -> str:
    if not p1_tasks:
        return "  None"
    return "\n".join(_fmt_task_line(t) for t in p1_tasks[:5])


def _stale_section(stale_tasks: list) -> str:
    if not stale_tasks:
        return "  None"
    lines = []
    for t in stale_tasks[:5]:
        sla   = (t.get("sla_deadline") or "")[:10]
        prio  = t.get("priority", "?")
        tid   = t.get("task_id", "?")
        desc  = t.get("description", "")[:55]
        lines.append(f"  ⏰ <code>{tid}</code> [{prio}] {desc} (SLA: {sla})")
    extra = len(stale_tasks) - 5
    if extra > 0:
        lines.append(f"  … and {extra} more")
    return "\n".join(lines)


# ── Digest builder ────────────────────────────────────────────────────────────

def build_morning_digest() -> str:
    """Morning digest: full overview — what's open, what's blocked, ecosystem health."""
    now_str = datetime.now(timezone.utc).strftime("%b %d %H:%M UTC")
    stats   = get_digest_stats(since_hours=12)  # Last 12h

    p0_tasks    = stats.get("p0_tasks", [])
    p1_tasks    = stats.get("p1_tasks", [])
    completed   = stats.get("completed_since_last", 0)
    created     = stats.get("created_since_last", 0)
    blocked     = stats.get("blocked_count", 0)
    repo_h      = stats.get("repos_healthy", 0)
    repo_t      = stats.get("repos_total", 0)
    wf_pass     = stats.get("workflows_passing", 0)
    wf_total    = stats.get("workflows_total", 0)
    stale_cnt   = stats.get("stale_count", 0)

    stale_tasks = get_stale(limit=5)
    blocked_tasks = get_blocked()

    # Build blocked section
    blocked_section = ""
    if blocked_tasks:
        blocked_lines = "\n".join(_fmt_task_line(t) for t in blocked_tasks[:3])
        blocked_section = f"\n🚫 <b>Blocked ({len(blocked_tasks)})</b>\n{blocked_lines}\n"

    text = (
        f"🌅 <b>MORNING DIGEST</b> — {now_str}\n\n"

        f"🔴 <b>P0 CRITICAL ({len(p0_tasks)})</b>\n"
        f"{_p0_section(p0_tasks)}\n\n"

        f"📊 <b>Last 12 hours:</b>\n"
        f"• ✅ {completed} completed\n"
        f"• 🆕 {created} new tasks\n"
        f"• 🚫 {blocked} blocked\n"
        f"{blocked_section}\n"

        f"🟠 <b>P1 needing attention ({len(p1_tasks)})</b>\n"
        f"{_p1_section(p1_tasks)}\n\n"

        f"⏰ <b>Stale (past SLA) — {stale_cnt}</b>\n"
        f"{_stale_section(stale_tasks)}\n\n"

        f"📦 <b>Ecosystem health:</b>\n"
        f"• Repos: {repo_h}/{repo_t} healthy\n"
        f"• Workflows: {wf_pass}/{wf_total} passing\n\n"

        + format_automation_health_section(since_hours=12) + "\n"

        + f"🔗 {NEXUS_URL}"
    )
    return text[:4096]


def build_evening_digest() -> str:
    """Evening digest: EOD wrap-up — what got done, what's still open."""
    now_str = datetime.now(timezone.utc).strftime("%b %d %H:%M UTC")
    stats   = get_digest_stats(since_hours=8)  # Since morning

    p0_tasks  = stats.get("p0_tasks", [])
    p1_tasks  = stats.get("p1_tasks", [])
    completed = stats.get("completed_since_last", 0)
    created   = stats.get("created_since_last", 0)
    blocked   = stats.get("blocked_count", 0)
    repo_h    = stats.get("repos_healthy", 0)
    repo_t    = stats.get("repos_total", 0)
    wf_pass   = stats.get("workflows_passing", 0)
    wf_total  = stats.get("workflows_total", 0)
    stale_cnt = stats.get("stale_count", 0)

    # EOD verdict
    if len(p0_tasks) == 0 and completed >= 3:
        verdict = "✅ Solid day — no P0s open"
    elif len(p0_tasks) > 0:
        verdict = f"⚠️ {len(p0_tasks)} P0(s) still open — needs attention overnight"
    elif completed == 0:
        verdict = "😶 Quiet day — 0 tasks completed"
    else:
        verdict = f"🟡 Decent — {completed} done, {len(p0_tasks)} P0s open"

    text = (
        f"🌆 <b>EVENING DIGEST</b> — {now_str}\n"
        f"{verdict}\n\n"

        f"🔴 <b>P0 CRITICAL ({len(p0_tasks)})</b>\n"
        f"{_p0_section(p0_tasks)}\n\n"

        f"📊 <b>Since morning:</b>\n"
        f"• ✅ {completed} completed\n"
        f"• 🆕 {created} new tasks\n"
        f"• 🚫 {blocked} blocked\n\n"

        f"🟠 <b>P1 still open ({len(p1_tasks)})</b>\n"
        f"{_p1_section(p1_tasks)}\n\n"

        f"📦 <b>Ecosystem health:</b>\n"
        f"• Repos: {repo_h}/{repo_t} healthy\n"
        f"• Workflows: {wf_pass}/{wf_total} passing\n"
        f"• Stale items: {stale_cnt}\n\n"

        + format_automation_health_section(since_hours=8) + "\n"

        + f"🔗 {NEXUS_URL}"
    )
    return text[:4096]


# ── Auto-detect morning/evening ───────────────────────────────────────────────

def detect_digest_type() -> str:
    """Return 'morning' (14 UTC) or 'evening' (22 UTC) based on current hour."""
    hour = datetime.now(timezone.utc).hour
    if 13 <= hour < 17:
        return "morning"
    if 21 <= hour < 24:
        return "evening"
    return "morning"  # Default for manual/test runs


# ── Send functions ────────────────────────────────────────────────────────────

def send_morning_digest() -> bool:
    logger.info("Building morning digest…")
    try:
        # Run P0 escalation check before morning digest
        fired = check_p0_escalation()
        if fired:
            logger.info(f"P0 escalation: {fired} fired before digest")

        text = build_morning_digest()
        ok   = send_telegram(text)
        logger.info(f"Morning digest sent: {ok}")
        return ok
    except Exception as e:
        logger.error(f"Morning digest failed: {e}")
        send_telegram(f"⚠️ Morning digest failed: {e}")
        return False


def send_evening_digest() -> bool:
    logger.info("Building evening digest…")
    try:
        text = build_evening_digest()
        ok   = send_telegram(text)
        logger.info(f"Evening digest sent: {ok}")
        return ok
    except Exception as e:
        logger.error(f"Evening digest failed: {e}")
        send_telegram(f"⚠️ Evening digest failed: {e}")
        return False


def send_test_digest() -> bool:
    """Test both digests — safe for manual runs."""
    logger.info("Sending test digests…")
    morning = build_morning_digest()
    evening = build_evening_digest()

    ok1 = send_telegram(f"<b>[TEST] Morning Preview:</b>\n\n{morning}"[:4096])
    ok2 = send_telegram(f"<b>[TEST] Evening Preview:</b>\n\n{evening}"[:4096])
    return ok1 and ok2


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "auto"

    if mode == "morning":
        ok = send_morning_digest()
    elif mode == "evening":
        ok = send_evening_digest()
    elif mode == "test":
        ok = send_test_digest()
    elif mode == "auto":
        digest_type = detect_digest_type()
        logger.info(f"Auto-detected digest type: {digest_type}")
        ok = send_morning_digest() if digest_type == "morning" else send_evening_digest()
    else:
        print(f"Usage: python digest.py [morning|evening|test|auto]")
        sys.exit(1)

    sys.exit(0 if ok else 1)
