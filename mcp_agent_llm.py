
"""LLM-driven customer-support agent using MCP and Ollama."""

import asyncio
import sys
from pathlib import Path

import ollama
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from app.core.config import LLM_TIMEOUT_SECONDS

from mcp_agent import (
    MODEL,
    TOOLS,
    ALLOWED_TOOLS,
    validate_arguments,
    parse_tool_result,
    customer_response,
    is_explicit_ticket_request,
    extract_order_ids,
)


SYSTEM_PROMPT = """
You select tools for a customer-support application.

Rules:
1. Use get_order to check order status, delivery details, or refund
   eligibility.
2. Use create_support_ticket only if the user explicitly requests
   a support ticket, asks to raise/open/create a ticket, or explicitly
   requests escalation.
3. Asking "What should I do?" is NOT permission to create a ticket.
   In that case, use get_order to obtain verified information.
4. Extract the order ID exactly from the user's message.
5. For ticket requests, provide a concise issue and priority.
6. Never claim a tool succeeded without its actual result.
7. Never approve or process refunds.
8. Return one structured tool call for requests involving an order.
"""


def validate_request(question, tool_name, args):
    """Validate tool selection against the user's explicit intent."""

    if tool_name not in ALLOWED_TOOLS:
        return None, "The requested tool is not permitted."

    order_ids = extract_order_ids(question)

    if len(set(order_ids)) != 1:
        return None, (
            "Please provide exactly one order ID, such as ORD1002."
        )

    expected_order_id = order_ids[0]

    if not isinstance(args, dict):
        return None, "The tool returned invalid arguments."

    provided_order_id = args.get("order_id")

    if (
        not isinstance(provided_order_id, str)
        or provided_order_id.upper() != expected_order_id
    ):
        return None, (
            "The selected tool did not match the order ID "
            "in your request."
        )

    explicit_ticket = is_explicit_ticket_request(question)

    # Creating a ticket requires explicit user intent.
    if tool_name == "create_support_ticket" and not explicit_ticket:
        return None, (
            "I can check your order, but I need an explicit request "
            "to raise a support ticket before creating one."
        )

    # Do not reject safe read-only lookups just because the request
    # discusses what to do about a delay.
    safe_args, error = validate_arguments(tool_name, args)

    if error:
        return None, "The selected tool arguments failed validation."

    return safe_args, None


async def main():
    server_file = Path(__file__).with_name("mcp_server.py")

    params = StdioServerParameters(
        command=sys.executable,
        args=[str(server_file)],
    )

    print("Starting LLM-driven MCP customer-support agent...")
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
                    f"MCP server is missing tools: {sorted(missing)}"
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

                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": question},
                ]

                try:
                    try:
                        response = await asyncio.wait_for(
                            asyncio.to_thread(
                                ollama.chat,
                                model=MODEL,
                                messages=messages,
                                tools=TOOLS,
                           ),
                            timeout=LLM_TIMEOUT_SECONDS,
                        )
                    except asyncio.TimeoutError:
                        print(
                             "Agent: The AI model took too long to respond. "
                             "Please try again.\n"
                        )
                        continue

                    message = response.message
                    calls = message.tool_calls or []

                    if not calls:
                        print(
                            "Agent: I couldn't select a verified support "
                            "action. Please rephrase your request.\n"
                        )
                        continue

                    if len(calls) != 1:
                        print(
                            "Agent: Multiple tool calls were requested. "
                            "I stopped the request for safety.\n"
                        )
                        continue

                    call = calls[0]
                    tool_name = call.function.name
                    args = call.function.arguments

                    safe_args, rejection = validate_request(
                        question,
                        tool_name,
                        args,
                    )

                    if rejection:
                        print(f"Agent: {rejection}\n")
                        continue

                    # The MCP server remains responsible for executing
                    # the tool and enforcing its business rules.
                    result_obj = await session.call_tool(
                        tool_name,
                        safe_args,
                    )

                    result = parse_tool_result(result_obj)

                    # Final claims come from the verified tool result,
                    # not free-form LLM text.
                    answer = customer_response(
                        tool_name,
                        result,
                        question,
                    )

                    # For advice requests, give safe general guidance
                    # after the actual order status has been verified.
                    if (
                        tool_name == "get_order"
                        and result.get("success") is True
                        and not is_explicit_ticket_request(question)
                        and any(
                            phrase in question.lower()
                            for phrase in (
                                "what should i do",
                                "what can i do",
                                "next step",
                                "how can i resolve",
                            )
                        )
                    ):
                        answer += (
                            " You can contact customer support for an "
                            "update. If you want a formal escalation, "
                            "you can explicitly ask me to raise a "
                            "support ticket."
                        )

                    print(f"Agent: {answer}\n")

                except Exception as exc:
                    print(
                        "Agent: The request failed. Check that Ollama "
                        "and the MCP server are running correctly."
                    )
                    print(f"Diagnostic: {type(exc).__name__}\n")


if __name__ == "__main__":
    asyncio.run(main())
