
"""Local Ollama agent connected to the customer-support MCP server.

Safety features:
- Calls only explicitly approved MCP tools.
- Validates tool names and arguments.
- Uses verified tool results for final customer responses.
- Never claims that a refund was approved or processed.
- Does not create duplicate active support tickets when the server
  correctly enforces that business rule.
- Handles MCP timeouts without claiming unconfirmed success.
"""
import time

from app.agent_logging import configure_logging, log_event
import asyncio
import json
import re
import sys
from pathlib import Path


from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


from app.core.config import (
    OLLAMA_MODEL,
    MCP_TIMEOUT_SECONDS,
)

MODEL = OLLAMA_MODEL
MAX_TOOL_CALLS = 3
configure_logging()
log_event("agent_started", model=MODEL)

ALLOWED_TOOLS = {"get_order", "create_support_ticket"}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_order",
            "description": "Look up an order using its exact order ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "Order ID, for example ORD1002",
                    }
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_support_ticket",
            "description": (
                "Request a support ticket for a delayed order. "
                "Use only when the customer explicitly asks to raise a "
                "ticket, create a support ticket, or escalate the delay. "
                "The MCP server validates the order and ticket rules."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "Order ID, for example ORD1002",
                    },
                    "issue": {
                        "type": "string",
                        "description": "Brief description of the customer's issue",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Support ticket priority",
                    },
                },
                "required": ["order_id", "issue", "priority"],
            },
        },
    },
]


def validate_arguments(name, args):
    """Validate tool names and argument shapes before MCP calls."""

    if name not in ALLOWED_TOOLS:
        return None, {
            "success": False,
            "error": "Tool not approved.",
        }

    if not isinstance(args, dict):
        return None, {
            "success": False,
            "error": "Invalid tool arguments.",
        }

    if name == "get_order":
        if (
            set(args) != {"order_id"}
            or not isinstance(args["order_id"], str)
            or not args["order_id"].strip()
        ):
            return None, {
                "success": False,
                "error": "Invalid get_order arguments.",
            }

    elif name == "create_support_ticket":
        expected = {"order_id", "issue", "priority"}

        if (
            set(args) != expected
            or not isinstance(args["order_id"], str)
            or not args["order_id"].strip()
            or not isinstance(args["issue"], str)
            or not args["issue"].strip()
            or not isinstance(args["priority"], str)
            or args["priority"] not in {"low", "medium", "high"}
        ):
            return None, {
                "success": False,
                "error": "Invalid create_support_ticket arguments.",
            }

    return args, None


def parse_tool_result(result_obj):
    """Convert an MCP CallToolResult into a safe Python dictionary."""

    if getattr(result_obj, "isError", False):
        return {
            "success": False,
            "error": "The MCP tool reported an error.",
        }

    texts = [
        item.text
        for item in (getattr(result_obj, "content", None) or [])
        if hasattr(item, "text")
    ]

    for item_text in texts:
        try:
            parsed = json.loads(item_text)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError):
            continue

    return {
        "success": False,
        "error": "The tool did not return a valid structured result.",
    }


def is_explicit_ticket_request(question):
    """Detect explicit ticket requests while rejecting clear negation."""

    text = question.lower()

    negative_patterns = [
        r"\b(?:do not|don't|dont|never)\s+"
        r"(?:want to\s+)?(?:raise|create|open|submit)\b"
        r".{0,35}\bticket\b",
        r"\b(?:do not|don't|dont)\s+"
        r"(?:want|need)\s+(?:a\s+)?"
        r"(?:support\s+)?ticket\b",
        r"\b(?:do not|don't|dont|never)\s+"
        r"(?:want to\s+)?escalate\b",
        r"\bno\s+(?:support\s+)?ticket\b",
    ]

    if any(re.search(pattern, text) for pattern in negative_patterns):
        return False

    positive_patterns = [
        r"\braise\b.{0,35}\bticket\b",
        r"\bcreate\b.{0,35}\bticket\b",
        r"\bopen\b.{0,35}\bticket\b",
        r"\bsubmit\b.{0,35}\bticket\b",
        r"\bescalat(?:e|ion|ing)\b",
        r"\brequest\b.{0,25}\bsupport ticket\b",
    ]

    return any(re.search(pattern, text) for pattern in positive_patterns)


def extract_order_ids(question):
    """Extract likely order IDs without inventing or modifying them."""

    return re.findall(r"\b[A-Z]{2,}\d+\b", question.upper())


def customer_response(tool_name, result, question):
    """Build the final answer from verified tool output, not LLM claims."""

    if not isinstance(result, dict):
        return "I couldn't verify the result from the support system."

    if result.get("outcome_unknown") is True:
        return (
            "I couldn't confirm the outcome of that operation. "
            "Please check the support system before trying again."
        )

    if result.get("success") is not True:
        error = result.get("error", "The request could not be completed.")
        return f"I couldn't complete that request: {error}"

    if tool_name == "get_order":
        order_id = result.get("order_id", "your order")
        status = result.get("status")

        if not isinstance(status, str) or not status.strip():
            return (
                f"I found a response for {order_id}, but the support "
                "system did not provide a valid order status."
            )

        response = f"Order {order_id} status: {status}."

        expected_date = result.get("expected_delivery")
        if not expected_date:
            expected_date = result.get("expected_delivery_date")

        if isinstance(expected_date, str) and expected_date.strip():
            response += f" Expected delivery date: {expected_date}."

        item = result.get("item")
        if isinstance(item, str) and item.strip():
            response += f" Item: {item}."

        if status.lower() == "delayed":
            response += (
                " The order is marked as delayed in the support system."
            )

        if any(
            word in question.lower()
            for word in ("refund", "money back", "reimbursement")
        ):
            eligible = result.get("refund_eligible")

            if eligible is True:
                response += (
                    " The order record indicates refund eligibility, "
                    "but this does not mean a refund has been approved "
                    "or processed. I cannot process refunds through "
                    "this assistant."
                )
            elif eligible is False:
                response += (
                    " The order record does not mark this order as "
                    "refund-eligible. This assistant cannot approve "
                    "or process refunds."
                )
            else:
                response += (
                    " I cannot verify refund eligibility from the "
                    "available order record."
                )

        return response

    if tool_name == "create_support_ticket":
        ticket_id = result.get("ticket_id")
        created = result.get("created")
        status = result.get("status")

        if not ticket_id:
            return (
                "The support system did not confirm a ticket ID, "
                "so I cannot confirm ticket creation."
            )

        if created is True:
            response = f"Support ticket {ticket_id} was created."
        elif created is False:
            response = (
                f"You already have an active support ticket: {ticket_id}. "
                "The existing ticket was reused; no duplicate was created."
            )
        else:
            return (
                "The support system returned a ticket reference, "
                "but did not confirm whether a new ticket was created."
            )

        if isinstance(status, str) and status.strip():
            response += f" Ticket status: {status}."

        return response

    return "The support system returned a result I cannot safely summarize."



async def call_mcp_tool(session, name, args):
    """Validate, execute, time, and log an MCP tool call."""

    safe_args = validate_arguments(name, args)

    if safe_args is None:
        log_event(
            "mcp_tool_rejected",
            tool=name,
            reason="argument_validation_failed",
        )
        return {
            "success": False,
            "error": "The requested operation could not be validated.",
        }

    started = time.monotonic()

    try:
        result_obj = await asyncio.wait_for(
            session.call_tool(name, safe_args),
            timeout=MCP_TIMEOUT_SECONDS,
        )

        result = parse_tool_result(result_obj)
        duration_ms = round(
            (time.monotonic() - started) * 1000
        )

        log_event(
            "mcp_tool_completed" if result.get("success") else "mcp_tool_failed",
            tool=name,
            duration_ms=duration_ms,
            success=bool(result.get("success")),
        )

        return result

    except asyncio.TimeoutError:
        duration_ms = round(
            (time.monotonic() - started) * 1000
        )

        log_event(
            "mcp_tool_timeout",
            tool=name,
            duration_ms=duration_ms,
            outcome="unknown",
        )

        return {
            "success": False,
            "error": (
                "The support operation timed out. Its outcome may be "
                "unknown; check the support system before trying again."
            ),
            "outcome_unknown": True,
        }

    except Exception as exc:
        duration_ms = round(
            (time.monotonic() - started) * 1000
        )

        log_event(
            "mcp_tool_error",
            tool=name,
            error_type=type(exc).__name__,
            duration_ms=duration_ms,
        )

        return {
            "success": False,
            "error": (
                f"MCP tool execution failed ({type(exc).__name__}). "
                "No successful result was confirmed."
            ),
        }

async def main():
    server_file = Path(__file__).with_name("mcp_server.py")

    params = StdioServerParameters(
        command=sys.executable,
        args=[str(server_file)],
    )

    print("Starting local MCP-powered customer-support agent...")
    print(f"Model: {MODEL}")
    print("Type 'exit' to quit.\n")

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            available = await session.list_tools()
            available_names = {tool.name for tool in available.tools}

            missing = ALLOWED_TOOLS - available_names
            if missing:
                raise RuntimeError(
                    f"MCP server is missing required tools: {sorted(missing)}"
                )

            while True:
                try:
                    question = input("You: ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\nGoodbye!")
                    break

                if question.lower() in {"exit", "quit"}:
                    print("Goodbye!")
                    break

                if not question:
                    continue

                order_ids = extract_order_ids(question)

                if len(set(order_ids)) != 1:
                    print(
                        "Agent: Please include exactly one order ID, "
                        "such as ORD1002.\n"
                    )
                    continue

                order_id = order_ids[0]
                wants_ticket = is_explicit_ticket_request(question)

                if wants_ticket:
                    args = {
                        "order_id": order_id,
                        "issue": question,
                        "priority": "medium",
                    }

                    result = await call_mcp_tool(
                        session,
                        "create_support_ticket",
                        args,
                    )

                    print(
                        "Agent:",
                        customer_response(
                            "create_support_ticket",
                            result,
                            question,
                        ),
                        "\n",
                    )
                    continue

                result = await call_mcp_tool(
                    session,
                    "get_order",
                    {"order_id": order_id},
                )

                print(
                    "Agent:",
                    customer_response("get_order", result, question),
                    "\n",
                )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")
