
from test_safe_multi_tool_dispatcher import dispatch_tool
import test_safe_multi_tool_dispatcher as dispatcher

def test_valid_order_can_be_found():
    """A valid order should be returned by the order tool."""

    result = dispatch_tool(
        "get_order",
        {"order_id": "ORD1002"}
    )

    assert result["success"] is True
    assert result["order"]["order_id"] == "ORD1002"
    assert result["order"]["status"] == "Delayed"


def test_missing_order_is_rejected():
    """An unknown order should not be treated as a valid order."""

    result = dispatch_tool(
        "get_order",
        {"order_id": "ORD9999"}
    )

    assert result["success"] is False
    assert result["error"] == "Order not found"


def test_unapproved_tool_is_rejected():
    """The dispatcher must reject tools outside its allowlist."""

    result = dispatch_tool(
        "delete_all_orders",
        {}
    )

    assert result["success"] is False
    assert "Tool not approved" in result["error"]


def test_invalid_arguments_are_rejected():
    """The dispatcher must reject unexpected arguments."""

    result = dispatch_tool(
        "get_order",
        {
            "order_id": "ORD1002",
            "delete_database": True
        }
    )

    assert result["success"] is False
    assert result["error"] == "Missing or unexpected arguments"

from unittest.mock import patch

import test_safe_multi_tool_dispatcher as dispatcher


def test_missing_order_never_checks_refund_policy():
    """A missing order must stop the refund workflow."""

    with patch.object(
        dispatcher,
        "check_refund_policy",
        wraps=dispatcher.check_refund_policy
    ) as policy_mock:

        result = dispatcher.check_order_refund("ORD9999")

        assert result["success"] is False
        assert result["step"] == "order_lookup"
        policy_mock.assert_not_called()

def test_valid_order_checks_policy_with_verified_status():
    """The policy must use the verified order status."""

    original_policy = dispatcher.check_refund_policy

    with patch.object(
        dispatcher,
        "check_refund_policy",
        wraps=original_policy
    ) as policy_mock:

        # Update the registry too, because dispatch_tool uses it.
        original_function, required_arguments = (
            dispatcher.TOOL_REGISTRY["check_refund_policy"]
        )

        dispatcher.TOOL_REGISTRY["check_refund_policy"] = (
            policy_mock,
            required_arguments
        )

        try:
            result = dispatcher.check_order_refund("ORD1002")

            assert result["success"] is True
            assert result["order"]["status"] == "Delayed"

            policy_mock.assert_called_once_with(order_status="Delayed")

            assert result["policy"]["eligibility"] == "needs_review"

        finally:
            # Restore the original registry entry.
            dispatcher.TOOL_REGISTRY["check_refund_policy"] = (
                original_function,
                required_arguments
            )

def test_ticket_is_not_created_for_missing_order():
    """A support ticket requires a verified order."""

    with patch.object(
        dispatcher,
        "create_support_ticket",
        wraps=dispatcher.create_support_ticket
    ) as ticket_mock:

        original_function, required_arguments = (
            dispatcher.TOOL_REGISTRY["create_support_ticket"]
        )

        dispatcher.TOOL_REGISTRY["create_support_ticket"] = (
            ticket_mock,
            required_arguments
        )

        try:
            result = dispatcher.dispatch_tool(
                "create_support_ticket",
                {
                    "order_id": "ORD9999",
                    "issue": "Order delivery problem"
                }
            )

            assert result["success"] is False
            assert "Order not found" in result["error"]
            ticket_mock.assert_not_called()

        finally:
            dispatcher.TOOL_REGISTRY["create_support_ticket"] = (
                original_function,
                required_arguments
            )

def test_empty_ticket_issue_is_rejected():
    """A ticket must have a meaningful issue description."""

    result = dispatcher.dispatch_tool(
        "create_support_ticket",
        {
            "order_id": "ORD1002",
            "issue": "   "
        }
    )

    assert result["success"] is False
    assert result["error"] == "Issue description is required"

def test_valid_order_can_create_support_ticket():
    """A valid order and issue should create a ticket."""

    result = dispatcher.dispatch_tool(
        "create_support_ticket",
        {
            "order_id": "ORD1002",
            "issue": "My delivery is delayed"
        }
    )

    assert result["success"] is True
    assert result["ticket"]["order_id"] == "ORD1002"
    assert result["ticket"]["issue"] == "My delivery is delayed"
    assert result["ticket"]["status"] == "Open"
    assert result["ticket"]["ticket_id"].startswith("TKT-")

def test_failed_ticket_request_does_not_add_ticket():
    """A missing order must not change the ticket database."""

    tickets_before = len(dispatcher.TICKETS)

    result = dispatcher.dispatch_tool(
        "create_support_ticket",
        {
            "order_id": "ORD9999",
            "issue": "My delivery is delayed"
        }
    )

    assert result["success"] is False
    assert len(dispatcher.TICKETS) == tickets_before



