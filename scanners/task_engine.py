"""
Nexus Task Engine — Layer 1: Task Intelligence
- create_task, update_status, auto_assign_priority
- compute_sla_deadline, get_active, get_stale
"""
import os
import re
import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import quote as _urlq
import requests

logger = logging.getLogger(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
TASKS_TABLE  = "nexus_tasks"

# SLA deadlines per priority
SLA_HOURS = {"P0": 2, "P1": 24, "P2": 72, "P3": 720}

# Keywords that auto-trigger P0
P0_KEYWORDS = re.compile(
    r'\b(blocker|critical|down|broken|production|prod|outage|incident)\b', re.IGNORECASE
)
P1_KEYWORDS = re.compile(
    r'\b(deploy|launch|release|ariel)\b', re.IGNORECASE
)


def _headers() -> dict:
    return {
        "apikey":        SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type":  "application/json",
        "Prefer":        "return=representation",
    }


def _q(value) -> str:
    """Sanitize a value for PostgREST URL filter interpolation.
    Prevents injection via task_id, priority, or other user-controlled params."""
    return _urlq(str(value), safe="")


def _sb(method: str, path: str, **kwargs):
    """Thin Supabase REST wrapper."""
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    r = requests.request(method, url, headers=_headers(), timeout=15, **kwargs)
    r.raise_for_status()
    return r.json() if r.text else None


# ── Priority auto-assignment ────────────────────────────────────────────────

def auto_assign_priority(description: str, status: str = "queued",
                         owner: str = "Claude Code", triggered_by: str = "") -> str:
    """Return P0/P1/P2/P3 based on content + context rules."""
    if status == "blocked":
        return "P0"
    if P0_KEYWORDS.search(description):
        return "P0"
    if owner.lower() == "ariel":
        return "P1"
    if P1_KEYWORDS.search(description):
        return "P1"
    if triggered_by in ("claude_ai", "telegram"):
        return "P1"
    return "P2"


# ── SLA deadline ────────────────────────────────────────────────────────────

def compute_sla_deadline(priority: str, from_time: Optional[datetime] = None) -> datetime:
    base = from_time or datetime.now(timezone.utc)
    hours = SLA_HOURS.get(priority, 72)
    return base + timedelta(hours=hours)


# ── Task CRUD ────────────────────────────────────────────────────────────────

def create_task(
    description: str,
    priority: Optional[str] = None,
    project: str = "",
    owner: str = "Claude Code",
    task_type: str = "manual",
    platform: str = "shared",
    triggered_by: str = "claude_code",
    source_chat_id: str = "",
    auto_priority: bool = True,
    **kwargs
) -> dict:
    """Insert a new task into nexus_tasks. Returns the created row."""
    task_id = f"T-{uuid.uuid4().hex[:8].upper()}"

    if auto_priority or not priority:
        priority = auto_assign_priority(description, owner=owner, triggered_by=triggered_by)

    sla = compute_sla_deadline(priority)

    payload = {
        "task_id":       task_id,
        "description":   description,
        "priority":      priority,
        "status":        "queued",
        "project":       project,
        "owner":         owner,
        "task_type":     task_type,
        "platform":      platform,
        "triggered_by":  triggered_by,
        "source_chat_id": source_chat_id,
        "sla_deadline":  sla.isoformat(),
        "auto_priority": auto_priority,
        **kwargs,
    }

    result = _sb("POST", TASKS_TABLE, json=payload)
    row = result[0] if isinstance(result, list) else result
    logger.info(f"Created task {task_id} [{priority}]: {description[:60]}")
    return row


def update_status(task_id: str, status: str, **extra) -> dict:
    """Update status + optional fields. Handles timestamps automatically."""
    now = datetime.now(timezone.utc).isoformat()
    payload = {"status": status, "updated_at": now, **extra}

    if status == "running":
        payload.setdefault("started_at", now)
    elif status in ("success", "failed", "cancelled", "skipped", "timeout"):
        payload.setdefault("completed_at", now)
    elif status == "dispatched":
        payload.setdefault("dispatched_at", now)

    result = _sb("PATCH", f"{TASKS_TABLE}?task_id=eq.{_q(task_id)}", json=payload)
    return result[0] if isinstance(result, list) and result else {}


def bump_priority(task_id: str) -> dict:
    """Promote task one level: P3→P2→P1→P0."""
    task = get_task(task_id)
    if not task:
        return {}
    order = ["P3", "P2", "P1", "P0"]
    current = task.get("priority", "P2")
    idx = order.index(current) if current in order else 1
    new_priority = order[min(idx + 1, 3)]
    sla = compute_sla_deadline(new_priority)
    return _sb("PATCH", f"{TASKS_TABLE}?task_id=eq.{_q(task_id)}",
               json={"priority": new_priority, "sla_deadline": sla.isoformat(),
                     "auto_priority": False})[0]


def demote_priority(task_id: str) -> dict:
    """Demote task one level: P0→P1→P2→P3."""
    task = get_task(task_id)
    if not task:
        return {}
    order = ["P3", "P2", "P1", "P0"]
    current = task.get("priority", "P2")
    idx = order.index(current) if current in order else 2
    new_priority = order[max(idx - 1, 0)]
    return _sb("PATCH", f"{TASKS_TABLE}?task_id=eq.{_q(task_id)}",
               json={"priority": new_priority, "auto_priority": False})[0]


# ── Queries ────────────────────────────────────────────────────────────────

def get_task(task_id: str) -> Optional[dict]:
    results = _sb("GET", f"{TASKS_TABLE}?task_id=eq.{_q(task_id)}&limit=1")
    return results[0] if results else None


def get_active(limit: int = 50) -> list:
    """Return active (non-terminal) tasks ordered by priority."""
    return _sb("GET",
        f"{TASKS_TABLE}?"
        "status=not.in.(success,failed,cancelled,skipped,timeout)&"
        "order=priority.asc,created_at.asc&"
        f"limit={int(limit)}"
    ) or []


def get_by_priority(priority: str, limit: int = 20) -> list:
    return _sb("GET",
        f"{TASKS_TABLE}?"
        f"priority=eq.{_q(priority)}&"
        "status=not.in.(success,failed,cancelled,skipped,timeout)&"
        "order=created_at.asc&"
        f"limit={int(limit)}"
    ) or []


def get_stale(limit: int = 30) -> list:
    """Return tasks past their SLA deadline."""
    now = datetime.now(timezone.utc).isoformat()
    return _sb("GET",
        f"{TASKS_TABLE}?"
        f"sla_deadline=lt.{_q(now)}&"
        "status=not.in.(success,failed,cancelled,skipped,timeout)&"
        "order=priority.asc,sla_deadline.asc&"
        f"limit={int(limit)}"
    ) or []


def get_blocked() -> list:
    return _sb("GET",
        f"{TASKS_TABLE}?status=eq.blocked&order=created_at.asc"
    ) or []


def get_p0_open() -> list:
    return _sb("GET",
        f"{TASKS_TABLE}?"
        "priority=eq.P0&"
        "status=not.in.(success,failed,cancelled,skipped,timeout)&"
        "order=created_at.asc"
    ) or []


def get_digest_stats(since_hours: int = 12) -> dict:
    """Gather stats for the digest message."""
    from datetime import datetime, timezone, timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=since_hours)).isoformat()

    p0_tasks = get_p0_open()

    completed = _sb("GET",
        f"{TASKS_TABLE}?"
        f"status=eq.success&completed_at=gt.{_q(cutoff)}&select=task_id"
    ) or []

    created = _sb("GET",
        f"{TASKS_TABLE}?"
        f"created_at=gt.{_q(cutoff)}&select=task_id"
    ) or []

    blocked = get_blocked()
    p1_tasks = get_by_priority("P1")
    stale = get_stale()

    # Repo + workflow stats from nexus_repos / nexus_workflows
    try:
        repos = _sb("GET", "nexus_repos?select=health_score,tier") or []
        repos_healthy = sum(1 for r in repos if r.get("health_score", 0) >= 70)
        repos_total   = len(repos)
    except Exception:
        repos_healthy = repos_total = 0

    try:
        wfs = _sb("GET", "nexus_workflows?select=last_run_status,state") or []
        wf_passing = sum(1 for w in wfs if w.get("last_run_status") == "success")
        wf_total   = len(wfs)
    except Exception:
        wf_passing = wf_total = 0

    return {
        "p0_tasks":            p0_tasks,
        "p1_tasks":            p1_tasks,
        "completed_since_last": len(completed),
        "created_since_last":  len(created),
        "blocked_count":       len(blocked),
        "repos_healthy":       repos_healthy,
        "repos_total":         repos_total,
        "workflows_passing":   wf_passing,
        "workflows_total":     wf_total,
        "stale_count":         len(stale),
    }


# ── Priority re-evaluation ───────────────────────────────────────────────────

def recompute_priorities() -> int:
    """Re-evaluate auto_priority=true tasks. Returns count updated."""
    tasks = _sb("GET",
        f"{TASKS_TABLE}?"
        "auto_priority=eq.true&"
        "status=not.in.(success,failed,cancelled,skipped,timeout)&"
        "select=task_id,description,status,owner,triggered_by,priority"
    ) or []

    updated = 0
    for t in tasks:
        new_p = auto_assign_priority(
            t.get("description", ""),
            status=t.get("status", "queued"),
            owner=t.get("owner", ""),
            triggered_by=t.get("triggered_by", ""),
        )
        if new_p != t.get("priority"):
            _sb("PATCH", f"{TASKS_TABLE}?task_id=eq.{_q(t['task_id'])}",
                json={"priority": new_p,
                      "sla_deadline": compute_sla_deadline(new_p).isoformat()})
            updated += 1

    logger.info(f"Recomputed priorities: {updated} tasks updated")
    return updated


if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO)
    print("Task engine self-test...")
    stats = get_digest_stats()
    print(json.dumps(stats, indent=2, default=str))
