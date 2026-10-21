
import json
import re
import ollama

from test_safe_multi_tool_dispatcher import dispatch_tool


MODEL = "llama3.2:3b"
MAX_TOOL_EXECUTIONS = 5
MAX_AGENT_TURNS = 6


# Tools available to the local LLM.
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_order",
            "description": "Look up a customer's order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"}
                },
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_refund_policy",
            "description": (
                "Check refund policy for a specific order. "
                "The application verifies the order first."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"}
                },
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_support_ticket",
            "description": (
                "Create a simulated support ticket for an existing order."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "issue": {"type": "string"}
                },
                "required": ["order_id", "issue"]
            }
        }
    }
]


MODEL_TOOL_ARGUMENTS = {
    "get_order": {"order_id"},
    "check_refund_policy": {"order_id"},
    "create_support_ticket": {"order_id", "issue"}
}

INTERNAL_TOOL_ARGUMENTS = {
    "get_order": {"order_id"},
    "check_refund_policy": {"order_status"},
    "create_support_ticket": {"order_id", "issue"}
}


def valid_order_id(order_id):
    """Check the order ID format."""
    return (
        isinstance(order_id, str)
        and re.fullmatch(r"ORD\d+", order_id) is not None
    )


def run_agent(question):
    messages = [
        {
            "role": "system",
            "content": (
                "You are a customer-support assistant. "
                "Use tools to verify order information. "
                "Never invent an order status or policy result. "
                "For refund questions, verify the exact order first. "
                "Treat Python tool results as the source of truth. "
                "If eligibility is needs_review, explain that further "
                "review is required. Never claim a refund was approved, "
                "denied, or processed unless a tool explicitly confirms it. "
                "Do not invent delivery dates or promises. "
                "Support tickets in this demo are simulated."
            )
        },
        {
            "role": "user",
            "content": question
        }
    ]

    tool_execution_count = 0

    def execute_internal_tool(tool_name, arguments):
        """Execute only approved tools with the exact expected arguments."""
        nonlocal tool_execution_count

        if tool_name not in INTERNAL_TOOL_ARGUMENTS:
            return {
                "success": False,
                "error": f"Tool not approved: {tool_name}"
            }

        if not isinstance(arguments, dict):
            return {
                "success": False,
                "error": "Arguments must be a dictionary"
            }

        if set(arguments) != INTERNAL_TOOL_ARGUMENTS[tool_name]:
            return {
                "success": False,
                "error": "Missing or unexpected arguments"
            }

        if tool_execution_count >= MAX_TOOL_EXECUTIONS:
            return {
                "success": False,
                "error": "Maximum tool execution limit reached"
            }

        tool_execution_count += 1

        result = dispatch_tool(tool_name, arguments)

        print(f"Tool executed: {tool_name}")
        print(f"Tool result: {result}")

        return result

    def handle_model_tool(tool_name, arguments):
        """Validate the model's request and enforce safe workflows."""

        if tool_name not in MODEL_TOOL_ARGUMENTS:
            return {
                "success": False,
                "error": f"Tool not approved: {tool_name}"
            }

        if not isinstance(arguments, dict):
            return {
                "success": False,
                "error": "Arguments must be a dictionary"
            }

        if set(arguments) != MODEL_TOOL_ARGUMENTS[tool_name]:
            return {
                "success": False,
                "error": "Missing or unexpected arguments"
            }

        if tool_name == "get_order":
            order_id = arguments["order_id"]

            if not valid_order_id(order_id):
                return {
                    "success": False,
                    "error": "Invalid order ID"
                }

            return execute_internal_tool(
                "get_order",
                {"order_id": order_id}
            )

        if tool_name == "check_refund_policy":
            order_id = arguments["order_id"]

            if not valid_order_id(order_id):
                return {
                    "success": False,
                    "error": "Invalid order ID"
                }

            # Always verify the exact order first.
            order_result = execute_internal_tool(
                "get_order",
                {"order_id": order_id}
            )

            if not order_result.get("success"):
                return {
                    "success": False,
                    "step": "order_verification",
                    "error": order_result.get(
                        "error", "Order could not be verified"
                    )
                }

            # Only trust the status returned by the order tool.
            verified_status = order_result["order"]["status"]

            # Check the policy using that verified status.
            policy_result = execute_internal_tool(
                "check_refund_policy",
                {"order_status": verified_status}
            )

            return {
                "success": policy_result.get("success", False),
                "order": order_result["order"],
                "policy": policy_result
            }

        if tool_name == "create_support_ticket":
            order_id = arguments["order_id"]
            issue = arguments["issue"]

            if not valid_order_id(order_id):
                return {
                    "success": False,
                    "error": "Invalid order ID"
                }

            if not isinstance(issue, str) or not issue.strip():
                return {
                    "success": False,
                    "error": "Issue description is required"
                }

            # Verify the order before creating a simulated ticket.
            order_result = execute_internal_tool(
                "get_order",
                {"order_id": order_id}
            )

            if not order_result.get("success"):
                return {
                    "success": False,
                    "error": "Order could not be verified; no ticket created"
                }

            return execute_internal_tool(
                "create_support_ticket",
                {
                    "order_id": order_id,
                    "issue": issue.strip()
                }
            )

        return {
            "success": False,
            "error": "Unsupported tool"
        }

    for _ in range(MAX_AGENT_TURNS):
        response = ollama.chat(
            model=MODEL,
            messages=messages,
            tools=TOOLS
        )

        tool_calls = getattr(response.message, "tool_calls", None)

        if not tool_calls:
            content = response.message.content or ""

            # Recover when Ollama returns malformed tool-call text
            # instead of actually requesting a tool.
            order_match = re.search(
                r"\bORD\d+\b",
                question,
                re.IGNORECASE
            )

            refund_question = re.search(
                r"\b(refund|money back)\b",
                question,
                re.IGNORECASE
            )

            if refund_question and order_match and tool_execution_count == 0:
                order_id = order_match.group(0).upper()

                print("\nFallback: running verified refund workflow.")

                result = handle_model_tool(
                    "check_refund_policy",
                    {"order_id": order_id}
                )

                # Do not ask the LLM to reinterpret an error or invent
                # a result. Report failures deterministically.
                if not result.get("success"):
                    if result.get("step") == "order_verification":
                        return (
                            f"I could not verify order {order_id}. "
                            "Please check the order ID before continuing."
                        )

                    return (
                        "I could not complete the refund-policy check. "
                        "No refund was approved or processed."
                    )

                # Give Ollama the actual verified result.
                messages.append({
                    "role": "user",
                    "content": (
                        "The application verified this result. "
                        "Use only these facts to answer. Do not claim "
                        "approval or processing of a refund. Result: "
                        + json.dumps(result)
                    )
                })

                # Continue to obtain a natural-language response.
                continue

            # Never show raw tool-call syntax as a customer-facing answer.
            if re.search(
                r"\b(check_refund_policy|get_order|create_support_ticket)"
                r"\s*[\(\{]",
                content,
                re.IGNORECASE
            ):
                return (
                    "I couldn't complete the request safely. "
                    "Please try again."
                )

            return content

        # Keep the assistant's tool-call message in the conversation.
        messages.append(response.message)

        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            arguments = tool_call.function.arguments

            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = None

            print(f"\nLLM requested: {tool_name}")
            print(f"Arguments: {arguments}")

            result = handle_model_tool(tool_name, arguments)

            messages.append({
                "role": "tool",
                "name": tool_name,
                "content": json.dumps(result)
            })

    return (
        "The agent reached its maximum number of turns. "
        "Please try a simpler question."
    )


if __name__ == "__main__":
    question = input("Ask a customer-support question: ").strip()

    if not question:
        print("Please enter a question.")
    else:
        try:
            answer = run_agent(question)
            print("\nFinal answer:\n")
            print(answer)
        except Exception as exc:
            print(
                "\nThe agent could not complete the request. "
                "Check that Ollama is running and the model is installed."
            )
            print(f"Technical error type: {type(exc).__name__}")
