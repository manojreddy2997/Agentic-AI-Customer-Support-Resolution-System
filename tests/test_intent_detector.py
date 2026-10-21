import pytest

from app.agents.intent_detector import detect_intent


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("", "empty"),
        ("   ", "empty"),
        ("Where is my order ORD1002?", "delivery_issue"),
        (
            "My package hasn't arrived. Can you check ORD1002?",
            "delivery_issue",
        ),
        (
            "My order is delayed. Please help.",
            "delivery_issue",
        ),
        (
            "Is ORD1002 eligible for a refund?",
            "refund_inquiry",
        ),
        (
            "Please escalate ORD1002 and create a support ticket.",
            "ticket_escalation",
        ),
        (
            "Can you open a ticket for me?",
            "ticket_escalation",
        ),
        (
            "What is the status of my order?",
            "order_status",
        ),
        (
            "What is the status of ORD1002?",
            "order_status",
        ),
        (
            "Show me the status of ORD1002",
            "order_status",
        ),
        (
            "When will my package arrive?",
            "order_status",
        ),
        (
            "What is your return policy?",
            "general_question",
        ),
    ],
)
def test_detect_intent(message, expected):
    assert detect_intent(message) == expected
