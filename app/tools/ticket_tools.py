"""Persistent support ticket creation, lookup, status management, and auditing."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.tools.audit_log import log_audit_event


logger = logging.getLogger(__name__)

TICKETS_FILE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "database"
    / "support_tickets.json"
)

VALID_PRIORITIES = {"low", "medium", "high"}
VALID_STATUSES = {"Open", "In Progress", "Resolved"}


def _record_audit_safely(
    action: str,
    outcome: str,
    *,
    order_id: str | None = None,
    ticket_id: str | None = None,
    details: str = "",
) -> None:
    """Record an audit event without breaking the ticket workflow."""
    try:
        log_audit_event(
            action,
            outcome,
            order_id=order_id,
            ticket_id=ticket_id,
            details=details,
        )
    except Exception:
        # Keep ticket operations running, but make audit failures observable.
        logger.exception(
            "Failed to record audit event: action=%s outcome=%s",
            action,
            outcome,
        )
def _load_tickets() -> list[dict]:
    TICKETS_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not TICKETS_FILE.exists():
        return []

    with TICKETS_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("Ticket database must contain a JSON list.")

    return data


def _save_tickets(tickets: list[dict]) -> None:
    TICKETS_FILE.parent.mkdir(parents=True, exist_ok=True)

    with TICKETS_FILE.open("w", encoding="utf-8") as file:
        json.dump(tickets, file, indent=2)


def create_ticket(
    order_id: str,
    issue: str,
    priority: str = "medium",
) -> dict:
    """Create a ticket, reusing an existing active ticket for the same order."""
    order_id = order_id.strip().upper()
    issue = issue.strip()
    priority = priority.strip().lower()

    if not order_id:
        _record_audit_safely(
            "ticket_create", "failure",
            details="Rejected: order ID is required.",
        )
        return {"success": False, "error": "Order ID is required."}

    if not issue:
        _record_audit_safely(
            "ticket_create", "failure",
            order_id=order_id,
            details="Rejected: issue description is required.",
        )
        return {"success": False, "error": "Issue description is required."}

    if priority not in VALID_PRIORITIES:
        _record_audit_safely(
            "ticket_create", "failure",
            order_id=order_id,
            details="Rejected: invalid priority.",
        )
        return {
            "success": False,
            "error": "Priority must be low, medium, or high.",
        }

    tickets = _load_tickets()

    for existing in tickets:
        if (
            existing["order_id"] == order_id
            and existing["status"] in {"Open", "In Progress"}
        ):
            _record_audit_safely(
                "ticket_reuse",
                "success",
                order_id=order_id,
                ticket_id=existing["ticket_id"],
                details="Reused an existing active ticket.",
            )
            return {
                "success": True,
                "created": False,
                "message": "An active ticket already exists for this order.",
                **existing,
            }

    ticket = {
        "ticket_id": f"TKT-{uuid4().hex[:8].upper()}",
        "order_id": order_id,
        "issue": issue,
        "priority": priority,
        "status": "Open",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    tickets.append(ticket)
    _save_tickets(tickets)

    _record_audit_safely(
        "ticket_create",
        "success",
        order_id=order_id,
        ticket_id=ticket["ticket_id"],
        details=f"Created ticket with priority {priority}.",
    )

    return {"success": True, "created": True, **ticket}


def list_tickets() -> list[dict]:
    """Return all saved support tickets."""
    return _load_tickets()


def get_ticket(ticket_id: str) -> dict:
    """Find a ticket by its ID."""
    ticket_id = ticket_id.strip().upper()

    for ticket in _load_tickets():
        if ticket["ticket_id"] == ticket_id:
            return {"success": True, **ticket}

    return {"success": False, "error": "Ticket not found."}


def update_ticket_status(ticket_id: str, status: str) -> dict:
    """Update a ticket's status and record the action."""
    ticket_id = ticket_id.strip().upper()
    status = status.strip().title()

    if status not in VALID_STATUSES:
        _record_audit_safely(
            "ticket_status_update",
            "failure",
            ticket_id=ticket_id or None,
            details="Rejected: invalid status.",
        )
        return {
            "success": False,
            "error": "Status must be Open, In Progress, or Resolved.",
        }

    tickets = _load_tickets()

    for ticket in tickets:
        if ticket["ticket_id"] == ticket_id:
            previous_status = ticket["status"]
            ticket["status"] = status
            ticket["updated_at"] = datetime.now(timezone.utc).isoformat()
            _save_tickets(tickets)

            _record_audit_safely(
                "ticket_status_update",
                "success",
                order_id=ticket.get("order_id"),
                ticket_id=ticket_id,
                details=(
                    f"Status changed from {previous_status} to {status}."
                ),
            )

            return {"success": True, **ticket}

    _record_audit_safely(
        "ticket_status_update",
        "failure",
        ticket_id=ticket_id or None,
        details="Ticket not found.",
    )
    return {"success": False, "error": "Ticket not found."}
