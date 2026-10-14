"""Rule-based intent detection for customer support messages."""

import re


def detect_intent(message: str) -> str:
    """Classify a customer message into a support intent."""

    if not message or not message.strip():
        return "empty"

    text = re.sub(r"\s+", " ", message.lower()).strip()

    # Explicit requests to escalate or create a support ticket.
    ticket_patterns = [
        r"\b(create|open|raise|make)\b.{0,30}\bticket\b",
        r"\bsupport ticket\b",
        r"\bescalat(e|ion|ing)\b",
        r"\bspeak to (a |the )?(human|agent|person|manager)\b",
        r"\bcontact (a |the )?(human|agent|support team)\b",
    ]

    if any(re.search(pattern, text) for pattern in ticket_patterns):
        return "ticket_escalation"

    # Refund-related questions take priority over general order lookup.
    refund_patterns = [
        r"\brefund(s|ed|ing|able)?\b",
        r"\bmoney back\b",
        r"\breimburse(ment|d)?\b",
    ]

    if any(re.search(pattern, text) for pattern in refund_patterns):
        return "refund_inquiry"

    # Delivery problems and missing packages.
    delivery_patterns = [
        r"\b(delayed|late|overdue|missing)\b",
        r"\bnot arrived\b",
        r"\bhasn't arrived\b",
        r"\bhaven't received\b",
        r"\bnever received\b",
        r"\bwhere is my (order|package|parcel|delivery)\b",
        r"\b(package|parcel|order)\b.{0,30}\b(stuck|lost|delayed)\b",
        r"\bdelivery problem\b",
    ]

    if any(re.search(pattern, text) for pattern in delivery_patterns):
        return "delivery_issue"

    # Direct product/item questions should use verified order data.
    product_patterns = [
        r"\b(what|which)\s+(is\s+)?(the\s+)?(product|item)\b",
        r"\b(product|item)\b.{0,30}\b(order|ord\d+)\b",
        r"\bwhat did i order\b",
        r"\bwhat have i ordered\b",
    ]

    has_order_id = bool(re.search(r"\bord\d+\b", text))

    if has_order_id and any(
        re.search(pattern, text) for pattern in product_patterns
    ):
        return "order_status"

    # General order lookup and status requests.
    order_patterns = [
        r"\b(order|package|parcel)\b.{0,30}\b(status|track|tracking|details|information|info)\b",
        r"\b(status|track|tracking|details|information|info)\b.{0,30}\b(order|package|parcel)\b",
        r"\b(check|look up|lookup|find|show|get|view)\b.{0,30}\border\b",
        r"\bwhere is (my )?(order|package|parcel)\b",
        r"\bwhen will (my )?(order|package|parcel)\b",
        r"\bexpected delivery\b",
    ]

    if has_order_id and any(
        re.search(pattern, text) for pattern in order_patterns
    ):
        return "order_status"

    if any(re.search(pattern, text) for pattern in order_patterns):
        return "order_status"

    return "general_question"