#!/usr/bin/env python3
"""
bot_nexus.py — Standalone Nexus Telegram Bot (long-polling)
============================================================
Handles all Nexus commands via Telegram polling.
Commands: /tasks /p0 /p1 /stale /bump /demote /done /skip /block /digest /nexus

Run directly:
  python scanners/bot_nexus.py

Or import and call handle_update() from an existing bot framework.
"""
import os
import sys
import time
import logging
import requests

sys.path.insert(0, os.path.dirname(__file__))

from telegram_commands import handle_nexus_command, is_nexus_command
from notifier import send_telegram

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("bot_nexus")

BOT_TOKEN  = os.environ.get("BIDDEED_BOT_TOKEN", "")
CHAT_ID    = os.environ.get("BIDDEED_BOT_CHAT_ID", "740118343")
API_BASE   = f"https://api.telegram.org/bot{BOT_TOKEN}"
NEXUS_URL  = "https://nexus.zonewise.ai"

# Commands not handled by telegram_commands.py but shown in /help
HELP_TEXT = """🧠 <b>Nexus Brain Commands</b>

<b>View</b>
/tasks — Active tasks by priority
/p0 — P0 critical only
/p1 — P1 items only
/stale — Past SLA deadline
/nexus — Quick stats + dashboard link

<b>Actions</b>
/bump &lt;id&gt; — Priority up (P3→P2→P1→P0)
/demote &lt;id&gt; — Priority down
/done &lt;id&gt; — Mark complete ✅
/skip &lt;id&gt; — Mark skipped ⏭️
/block &lt;id&gt; [reason] — Mark blocked 🚫

<b>Digest</b>
/digest — Force immediate digest now

🔗 """ + NEXUS_URL


# ── Telegram API helpers ──────────────────────────────────────────────────────

def _api(method: str, **params) -> dict:
    """Call Telegram Bot API."""
    url = f"{API_BASE}/{method}"
    try:
        r = requests.post(url, json=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.error(f"API call {method} failed: {e}")
        return {}


def send_message(chat_id: str, text: str, parse_mode: str = "HTML") -> dict:
    return _api("sendMessage", chat_id=chat_id, text=text[:4096], parse_mode=parse_mode)


def get_updates(offset: int = 0, timeout: int = 30) -> list:
    result = _api("getUpdates", offset=offset, timeout=timeout, allowed_updates=["message"])
    return result.get("result", [])


# ── Update handler ────────────────────────────────────────────────────────────

def handle_update(update: dict) -> bool:
    """
    Process a single Telegram update.
    Returns True if the message was handled as a Nexus command.
    """
    message = update.get("message", {})
    if not message:
        return False

    text    = message.get("text", "").strip()
    chat_id = str(message.get("chat", {}).get("id", ""))
    user    = message.get("from", {})
    username = user.get("username") or user.get("first_name", "unknown")

    if not text or not chat_id:
        return False

    # /help is handled locally
    if text.lower() in ("/help", "/start"):
        send_message(chat_id, HELP_TEXT)
        logger.info(f"Sent help to {username} ({chat_id})")
        return True

    if not is_nexus_command(text):
        return False

    logger.info(f"Command '{text.split()[0]}' from {username} ({chat_id})")

    response = handle_nexus_command(text, chat_id=None)  # We send ourselves
    send_message(chat_id, response)
    return True


# ── Long-polling loop ─────────────────────────────────────────────────────────

def run_polling(max_retries: int = -1):
    """
    Start long-polling loop.
    max_retries=-1 means run forever.
    """
    if not BOT_TOKEN:
        logger.error("BIDDEED_BOT_TOKEN not set — cannot start bot")
        sys.exit(1)

    logger.info("bot_nexus starting long-poll loop…")
    send_telegram("🤖 <b>bot_nexus started</b> — Nexus commands active\n" + NEXUS_URL)

    offset     = 0
    retries    = 0
    poll_count = 0

    while max_retries == -1 or retries < max_retries:
        try:
            updates = get_updates(offset=offset, timeout=30)
            poll_count += 1

            for update in updates:
                update_id = update.get("update_id", 0)
                try:
                    handle_update(update)
                except Exception as e:
                    logger.error(f"Error handling update {update_id}: {e}")
                offset = max(offset, update_id + 1)

            retries = 0  # Reset on success

        except KeyboardInterrupt:
            logger.info("Shutting down (KeyboardInterrupt)")
            break
        except Exception as e:
            retries += 1
            logger.error(f"Polling error (retry {retries}): {e}")
            time.sleep(min(30, retries * 5))

    logger.info(f"bot_nexus stopped after {poll_count} polls")


# ── One-shot command sender (for GHA/cron use) ────────────────────────────────

def send_command_response(command: str, target_chat_id: str = None):
    """
    Execute a Nexus command and send the response to Telegram.
    Used by GHA workflows that need to push a one-shot message.
    """
    chat = target_chat_id or CHAT_ID
    response = handle_nexus_command(command, chat_id=None)
    return send_message(chat, response)


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Nexus Telegram Bot")
    parser.add_argument(
        "--command", "-c",
        help="Execute a single command and exit (e.g. --command '/digest')",
    )
    parser.add_argument(
        "--chat-id",
        default=CHAT_ID,
        help="Target chat_id for --command mode",
    )
    args = parser.parse_args()

    if args.command:
        result = send_command_response(args.command, args.chat_id)
        print(f"Sent: {result}")
    else:
        run_polling()
