
"""Read-only analytics for the ResolveAI dashboard."""

from collections import Counter
from typing import Any

from app.tools.ticket_tools import list_tickets


VALID_STATUSES = ("Open", "In Progress", "Resolved")
VALID_PRIORITIES = ("low", "medium", "high")


def calculate_ticket_metrics(
    tickets: list[dict[str, Any]],
) -> dict[str, Any]:
    """Calculate dashboard metrics from the supplied ticket records."""

    status_counts = Counter(
        ticket.get("status", "Unknown")
        for ticket in tickets
    )

    priority_counts = Counter(
        str(ticket.get("priority", "unknown")).lower()
        for ticket in tickets
    )

    total = len(tickets)
    resolved = status_counts["Resolved"]

    resolution_rate = (
        round((resolved / total) * 100, 2)
        if total
        else 0.0
    )

    return {
        "total_tickets": total,
        "open_tickets": status_counts["Open"],
        "in_progress_tickets": status_counts["In Progress"],
        "resolved_tickets": resolved,
        "resolution_rate": resolution_rate,
        "high_priority_tickets": priority_counts["high"],
        "status_counts": {
            status: status_counts[status]
            for status in VALID_STATUSES
        },
        "priority_counts": {
            priority: priority_counts[priority]
            for priority in VALID_PRIORITIES
        },
    }


def get_dashboard_metrics() -> dict[str, Any]:
    """Load real saved tickets and calculate their metrics."""
    tickets = list_tickets()
    return calculate_ticket_metrics(tickets)
