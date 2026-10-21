
# test_safe_multi_tool_dispatcher.py

# Simulated order database
ORDERS = {
    "ORD1002": {
        "order_id": "ORD1002",
        "status": "Delayed"
    },
    "ORD1003": {
        "order_id": "ORD1003",
        "status": "Delivered"
    }
}

# Simulated refund policy
def check_refund_policy(order_status: str) -> dict:
    if order_status == "Delayed":
        return {
            "success": True,
            "eligibility": "needs_review",
            "message": (
                "The order is delayed. Refund eligibility "
                "requires further review."
            )
        }

    if order_status == "Delivered":
        return {
            "success": True,
            "eligibility": "needs_review",
            "message": (
                "The order is delivered. Refund eligibility "
                "requires further review."
            )
        }

    return {
        "success": False,
        "eligibility": "unknown",
        "error": "Cannot assess policy for this order status."
    }

# Tool 1: Look up an order
def get_order(order_id: str) -> dict:
    if not isinstance(order_id, str) or not order_id.startswith("ORD"):
        return {"success": False, "error": "Invalid order ID"}

    order = ORDERS.get(order_id)

    if order is None:
        return {"success": False, "error": "Order not found"}

    return {"success": True, "order": order}


# Tool 2: Check policy
# Tool 3: Create a simulated support ticket
TICKETS = []

def create_support_ticket(order_id: str, issue: str) -> dict:
    if order_id not in ORDERS:
        return {"success": False, "error": "Order not found"}

    if not isinstance(issue, str) or not issue.strip():
        return {"success": False, "error": "Issue description is required"}

    ticket = {
        "ticket_id": f"TKT-{len(TICKETS) + 1:04d}",
        "order_id": order_id,
        "issue": issue.strip(),
        "status": "Open"
    }
    TICKETS.append(ticket)

    return {"success": True, "ticket": ticket}


# Allowlist: only these tools can be executed
TOOL_REGISTRY = {
    "get_order": (get_order, {"order_id"}),
    "check_refund_policy": (check_refund_policy, {"order_status"}),
    "create_support_ticket": (
        create_support_ticket,
        {"order_id", "issue"}
    )
}


# Safe dispatcher: validate tool name and arguments

# Safe dispatcher: validate tool name and arguments
def dispatch_tool(tool_name: str, arguments: dict) -> dict:
    if tool_name not in TOOL_REGISTRY:
        return {
            "success": False,
            "error": f"Tool not approved: {tool_name}"
        }

    if not isinstance(arguments, dict):
        return {
            "success": False,
            "error": "Arguments must be a dictionary"
        }

    function, required_arguments = TOOL_REGISTRY[tool_name]

    if set(arguments.keys()) != required_arguments:
        return {
            "success": False,
            "error": "Missing or unexpected arguments"
        }

    try:
        # Safety gate: verify the order before creating a ticket.
        if tool_name == "create_support_ticket":
            order_result = get_order(arguments["order_id"])

            if not order_result["success"]:
                return {
                    "success": False,
                    "error": order_result["error"]
                }

        result = function(**arguments)
        return result

    except Exception:
        # Avoid exposing internal exception details.
        return {
            "success": False,
            "error": "Tool execution failed"
        }


# Workflow: verify the order BEFORE checking refund policy
def check_order_refund(order_id: str) -> dict:
    order_result = dispatch_tool(
        "get_order",
        {"order_id": order_id}
    )

    print("Step 1 - Order lookup:", order_result)

    if not order_result["success"]:
        return {
            "success": False,
            "step": "order_lookup",
            "error": order_result["error"]
        }

    status = order_result["order"]["status"]

    policy_result = dispatch_tool(
        "check_refund_policy",
        {"order_status": status}
    )

    print("Step 2 - Policy check:", policy_result)

    return {
        "success": policy_result["success"],
        "order": order_result["order"],
        "policy": policy_result
    }


if __name__ == "__main__":
    print("=== Valid order ===")
    print(check_order_refund("ORD1002"))

    print("\n=== Missing order ===")
    print(check_order_refund("ORD9999"))

    print("\n=== Reject an unapproved tool ===")
    print(dispatch_tool("delete_all_orders", {}))
