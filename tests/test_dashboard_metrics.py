
from app.dashboard_metrics import (
    calculate_ticket_metrics,
    get_dashboard_metrics,
)


def test_metrics_count_real_ticket_records():
    tickets = [
        {"status": "Open", "priority": "high"},
        {"status": "In Progress", "priority": "medium"},
        {"status": "Resolved", "priority": "low"},
        {"status": "Resolved", "priority": "high"},
    ]

    metrics = calculate_ticket_metrics(tickets)

    assert metrics["total_tickets"] == 4
    assert metrics["open_tickets"] == 1
    assert metrics["in_progress_tickets"] == 1
    assert metrics["resolved_tickets"] == 2
    assert metrics["resolution_rate"] == 50.0
    assert metrics["high_priority_tickets"] == 2


def test_priority_breakdown():
    tickets = [
        {"status": "Open", "priority": "high"},
        {"status": "Open", "priority": "high"},
        {"status": "Resolved", "priority": "medium"},
    ]

    metrics = calculate_ticket_metrics(tickets)

    assert metrics["priority_counts"] == {
        "low": 0,
        "medium": 1,
        "high": 2,
    }


def test_empty_ticket_list():
    metrics = calculate_ticket_metrics([])

    assert metrics["total_tickets"] == 0
    assert metrics["resolution_rate"] == 0.0
    assert metrics["status_counts"]["Open"] == 0


def test_dashboard_metrics_read_saved_tickets():
    metrics = get_dashboard_metrics()

    assert metrics["total_tickets"] >= 0
    assert metrics["total_tickets"] == (
        metrics["open_tickets"]
        + metrics["in_progress_tickets"]
        + metrics["resolved_tickets"]
        + sum(
            1
            for ticket in __import__(
                "app.tools.ticket_tools",
                fromlist=["list_tickets"],
            ).list_tickets()
            if ticket.get("status") not in (
                "Open",
                "In Progress",
                "Resolved",
            )
        )
    )
