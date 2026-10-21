
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def print_result(label, result):
    print(f"\n{label}:")

    for item in result.content:
        if hasattr(item, "text"):
            try:
                print(json.dumps(json.loads(item.text), indent=2))
            except (json.JSONDecodeError, TypeError):
                print(item.text)

    if result.isError:
        print("MCP reported a tool execution error.")


async def main():
    server_file = Path(__file__).with_name("mcp_server.py")

    params = StdioServerParameters(
        command=sys.executable,
        args=[str(server_file)],
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("Available tools:", [tool.name for tool in tools.tools])

            # 1. Verify a delayed order.
            result = await session.call_tool(
                "get_order",
                {"order_id": "ORD1002"},
            )
            print_result("Delayed order lookup", result)

            # 2. Verify an invalid order is rejected.
            result = await session.call_tool(
                "create_support_ticket",
                {
                    "order_id": "INVALID999",
                    "issue": "Delivery is delayed",
                    "priority": "medium",
                },
            )
            print_result("Invalid order ticket request", result)

            # 3. Verify a non-delayed order is rejected.
            result = await session.call_tool(
                "create_support_ticket",
                {
                    "order_id": "ORD1003",
                    "issue": "Please check my order",
                    "priority": "medium",
                },
            )
            print_result("Processing order ticket request", result)

            # 4. Request a ticket for a delayed order.
            # An existing active ticket should be reused.
            ticket_args = {
                "order_id": "ORD1002",
                "issue": "Customer requests help with delayed delivery",
                "priority": "high",
            }

            first = await session.call_tool(
                "create_support_ticket",
                ticket_args,
            )
            print_result("First ticket request", first)

            # 5. Repeat the same request to check ticket reuse.
            second = await session.call_tool(
                "create_support_ticket",
                ticket_args,
            )
            print_result("Repeated ticket request", second)


if __name__ == "__main__":
    asyncio.run(main())
