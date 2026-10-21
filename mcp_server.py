
"""MCP server backed by the existing support application's tools."""

import logging

from mcp.server.fastmcp import FastMCP

from app.tools.order_tools import lookup_order
from app.tools.ticket_tools import create_ticket
from app.tools.audit_log import log_audit_event

logger = logging.getLogger(__name__)

mcp = FastMCP("Customer Support Tools")


@mcp.tool()
def get_order(order_id: str) -> dict:
    """Look up an order using the application's order database."""

    if not isinstance(order_id, str) or not order_id.strip():
        return {
            "success": False,
            "error": "Please provide an order ID.",
        }

    result = lookup_order(order_id)

    try:
        log_audit_event(
            action="mcp_order_lookup",
            outcome="success" if result.get("success") else "failure",
            order_id=result.get("order_id", order_id.strip().upper()),
            details="Order lookup through MCP.",
        )
    except Exception:
        logger.exception("Failed to audit MCP order lookup")

    return result


@mcp.tool()
def create_support_ticket(
    order_id: str,
    issue: str,
    priority: str = "medium",
) -> dict:
    """Create or reuse a support ticket for a verified delayed order."""

    if not isinstance(order_id, str) or not order_id.strip():
        return {
            "success": False,
            "error": "Please provide an order ID.",
        }

    if not isinstance(issue, str) or not issue.strip():
        return {
            "success": False,
            "error": "Please provide an issue description.",
        }

    if not isinstance(priority, str):
        return {
            "success": False,
            "error": "Priority must be low, medium, or high.",
        }

    # Verify the order using the application's source of truth.
    order = lookup_order(order_id)

    if not order.get("success"):
        return {
            "success": False,
            "error": "Order not found. No ticket was created.",
        }

    if order.get("status") != "Delayed":
        return {
            "success": False,
            "error": (
                "This MCP workflow only creates tickets for delayed orders. "
                f"Current order status: {order.get('status', 'Unknown')}."
            ),
        }

    # Reuse existing persistence, validation, deduplication, and auditing.
    result = create_ticket(
        order_id=order["order_id"],
        issue=issue,
        priority=priority,
    )

    try:
        log_audit_event(
            action="mcp_ticket_request",
            outcome="success" if result.get("success") else "failure",
            order_id=order["order_id"],
            ticket_id=result.get("ticket_id"),
            details="Ticket request handled through MCP.",
        )
    except Exception:
        logger.exception("Failed to audit MCP ticket request")

    return result


if __name__ == "__main__":
    mcp.run()
