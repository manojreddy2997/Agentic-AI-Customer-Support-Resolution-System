import pytest

from mcp_agent_llm import validate_request
from mcp_agent import customer_response


def test_valid_order_lookup_is_accepted():
    args, error = validate_request(
        "What is the status of ORD1002?",
        "get_order",
        {"order_id": "ORD1002"},
    )

    assert error is None
    assert args == {"order_id": "ORD1002"}


def test_explicit_ticket_request_is_accepted():
    args, error = validate_request(
        "Please raise a support ticket for ORD1002",
        "create_support_ticket",
        {
            "order_id": "ORD1002",
            "issue": "Delayed delivery",
            "priority": "high",
        },
    )

    assert error is None
    assert args["order_id"] == "ORD1002"


def test_advice_request_cannot_create_ticket():
    args, error = validate_request(
        "My order ORD1002 is delayed. What should I do?",
        "create_support_ticket",
        {
            "order_id": "ORD1002",
            "issue": "Delayed delivery",
            "priority": "high",
        },
    )

    assert args is None
    assert error is not None
    assert "explicit request" in error.lower()


def test_mismatched_order_id_is_rejected():
    args, error = validate_request(
        "What is the status of ORD1002?",
        "get_order",
        {"order_id": "ORD1003"},
    )

    assert args is None
    assert error is not None
    assert "order id" in error.lower()


def test_unknown_tool_is_rejected():
    args, error = validate_request(
        "What is the status of ORD1002?",
        "delete_order",
        {"order_id": "ORD1002"},
    )

    assert args is None
    assert error is not None
    assert "not permitted" in error.lower()


def test_multiple_order_ids_are_rejected():
    args, error = validate_request(
        "Compare ORD1002 with ORD1003",
        "get_order",
        {"order_id": "ORD1002"},
    )

    assert args is None
    assert error is not None
    assert "exactly one order id" in error.lower()


def test_invalid_tool_arguments_are_rejected():
    args, error = validate_request(
        "What is the status of ORD1002?",
        "get_order",
        {"order_id": "ORD1002", "extra": "unexpected"},
    )

    assert args is None
    assert error is not None


def test_failed_tool_result_is_not_reported_as_success():
    answer = customer_response(
        "get_order",
        {
            "success": False,
            "error": "Order not found",
        },
        "What is the status of INVALID999?",
    )

    assert "couldn't complete" in answer.lower()
    assert "Order not found" in answer


def test_customer_declining_ticket_is_not_authorization():
    question = "I do not want to raise a ticket for ORD1002"

    args, error = validate_request(
        question,
        "create_support_ticket",
        {
            "order_id": "ORD1002",
            "issue": "Delayed delivery",
            "priority": "high",
        },
    )

    assert args is None
    assert error is not None


@pytest.mark.parametrize(
    "question",
    [
        "Don't create a ticket for ORD1002",
        "Please don't open a ticket for ORD1002",
        "I don't want to escalate ORD1002",
    ],
)
def test_negative_ticket_intent_is_rejected(question):
    args, error = validate_request(
        question,
        "create_support_ticket",
        {
            "order_id": "ORD1002",
            "issue": "Delayed delivery",
            "priority": "high",
        },
    )

    assert args is None
    assert error is not None


def test_declined_ticket_request_is_rejected_before_mcp_call():
    question = (
        "Don't create a ticket for ORD1002. "
        "Just tell me its delivery status."
    )

    args, error = validate_request(
        question,
        "create_support_ticket",
        {
            "order_id": "ORD1002",
            "issue": "Delayed delivery",
            "priority": "high",
        },
    )

    # Validation must block the proposed write action.
    assert args is None
    assert error is not None


def test_ticket_creation_failure_is_not_reported_as_success():
    answer = customer_response(
        "create_support_ticket",
        {
            "success": False,
            "error": "Order not found",
        },
        "Please raise a support ticket for ORD1002",
    )

    assert "couldn't complete" in answer.lower()
    assert "Order not found" in answer
    assert "created successfully" not in answer.lower()
