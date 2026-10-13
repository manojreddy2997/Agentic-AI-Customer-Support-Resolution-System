
"""Append-only JSONL audit logging for ResolveAI support actions."""

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


AUDIT_LOG_FILE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "database"
    / "audit_log.jsonl"
)


def log_audit_event(
    action: str,
    outcome: str,
    *,
    order_id: str | None = None,
    ticket_id: str | None = None,
    details: str = "",
) -> dict:
    """Record an action without storing the full customer conversation."""

    event = {
        "event_id": f"AUD-{uuid4().hex[:12].upper()}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "outcome": outcome,
        "order_id": order_id,
        "ticket_id": ticket_id,
        "details": details[:500],
    }

    AUDIT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Each event occupies one line, preserving earlier records.
    with AUDIT_LOG_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event, ensure_ascii=False) + "\n")

    return event


def list_audit_events(limit: int = 100) -> list[dict]:
    """Return the most recent audit events, newest first."""

    if limit < 1:
        raise ValueError("limit must be at least 1")

    if not AUDIT_LOG_FILE.exists():
        return []

    events = []

    with AUDIT_LOG_FILE.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                events.append(json.loads(line))

    return list(reversed(events[-limit:]))
