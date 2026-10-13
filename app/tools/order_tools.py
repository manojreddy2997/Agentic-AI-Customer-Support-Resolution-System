
"""Mock order database and safe order lookup tool."""

MOCK_ORDERS = {
    "ORD1001": {
        "status": "Delivered",
        "item": "Wireless Headphones",
        "expected_delivery": "2026-10-09",
        "actual_delivery": "2026-10-09",
        "refund_eligible": False,
    },
    "ORD1002": {
        "status": "Delayed",
        "item": "Mechanical Keyboard",
        "expected_delivery": "2026-10-10",
        "actual_delivery": None,
        "refund_eligible": True,
    },
    "ORD1003": {
        "status": "Processing",
        "item": "Laptop Stand",
        "expected_delivery": "2026-10-16",
        "actual_delivery": None,
        "refund_eligible": False,
    },
}


def lookup_order(order_id: str) -> dict:
    """Return a mock order record or a safe not-found result."""

    normalized_id = order_id.strip().upper()

    if not normalized_id:
        return {
            "success": False,
            "error": "Please provide an order ID.",
        }

    order = MOCK_ORDERS.get(normalized_id)

    if order is None:
        return {
            "success": False,
            "error": "Order not found. Please check the order ID.",
        }

    return {
        "success": True,
        "order_id": normalized_id,
        **order,
    }
