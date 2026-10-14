
"""Customer support agent with intent detection, RAG, and controlled tools."""

import re

import ollama

from app.agents.intent_detector import detect_intent
from app.rag.knowledge_base import search_knowledge_base
from app.tools.order_tools import lookup_order
from app.tools.ticket_tools import create_ticket


MODEL_NAME = "llama3.2:3b"

SYSTEM_PROMPT = """
You are a professional customer support AI agent.

Use supplied company policies and verified order information.
Never invent facts, ticket IDs, delivery dates, or completed actions.
Never claim a refund was approved or processed.
Refund eligibility is not refund approval.
No refund-processing tool is available.

Answer the customer's exact question directly.
Use only the supplied policy context for company-specific rules.
Do not invent return windows, refund amounts, or processing timelines.
Do not invent a support team or promise a future outcome.
Do not ask for information already provided.
Be concise, natural, polite, and accurate.
"""


DELIVERY_QUESTION_PATTERN = re.compile(
    r"\b(delivery|delayed|delay|late|tracking|shipment|shipping|"
    r"arrived|missing|package|parcel)\b",
    re.IGNORECASE,
)


def _get_policy_context(message: str) -> tuple[list[dict], str]:
    """Retrieve relevant policy documents and format their source names."""
    results = search_knowledge_base(message, top_k=2)
    sources = ", ".join(item["source"] for item in results)
    return results, sources


def _ask_ollama(message: str, policy_results: list[dict]) -> str:
    """Generate a response grounded in the retrieved policy documents."""
    if policy_results:
        policy_context = "\n\n".join(
            f"Source: {item['source']}\n{item['content']}"
            for item in policy_results
        )
    else:
        policy_context = (
            "No relevant company policy was retrieved. "
            "Do not invent company-specific rules."
        )

    prompt = (
        f"Customer question:\n{message}\n\n"
        f"Retrieved policy context:\n{policy_context}\n\n"
        "Answer the question directly using the relevant policy. "
        "If the policy does not provide the answer, say that the "
        "information is unavailable."
    )

    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        return response["message"]["content"].strip()
    except Exception:
        return (
            "I'm unable to generate a response right now. "
            "Please try again shortly."
        )


def _is_general_refund_policy_question(
    message: str,
    intent: str,
    order: dict | None,
) -> bool:
    """Identify general refund questions that can be answered from policy."""
    if order is not None:
        return False

    mentions_refund = bool(
        re.search(
            r"\b(refund|refunds|refundable|return|returns|"
            r"reimburse|reimbursement|money back)\b",
            message,
            re.IGNORECASE,
        )
    )

    if not mentions_refund:
        return False

    # Mixed delivery/refund questions need context from both policies.
    if DELIVERY_QUESTION_PATTERN.search(message):
        return False

    return intent in ("refund_inquiry", "general_question")



def _answer_general_refund_policy(
    policy_results: list[dict],
    message: str = "",
) -> str | None:
    """Answer refund-policy questions clearly using retrieved policy."""
    refund_policy_found = any(
        item["source"] == "refund_policy.txt"
        for item in policy_results
    )

    if not refund_policy_found:
        return None

    asks_for_guarantee = bool(
        re.search(
            r"\b(guarantee|guaranteed|promise|certain|definitely)\b",
            message,
            re.IGNORECASE,
        )
    )

    if asks_for_guarantee:
        answer = (
            "I can't guarantee that you'll receive a refund. "
            "Refund eligibility depends on your order record and the "
            "applicable policy. If you share your order ID, I can check "
            "the available order information. This application cannot "
            "approve or process refunds."
        )
    else:
        answer = (
            "Our refund policy states that a delayed order may be eligible "
            "for a refund when its order record explicitly marks "
            "`refund_eligible` as true. Eligibility does not mean a refund "
            "has been approved or processed. To check a specific order, "
            "please provide your order ID. This application cannot approve "
            "or process refunds."
        )

    return answer + "\n\nPolicy sources consulted: refund_policy.txt"


def generate_support_response(message: str) -> str:
    """Route customer requests while protecting critical workflows."""
    if not message or not message.strip():
        return "Please enter a message so I can help you."

    message = message.strip()
    intent = detect_intent(message)

    # Step 1: Retrieve relevant company policies.
    policy_results, sources = _get_policy_context(message)

    # Step 2: Verify an order ID if one was supplied.
    order_match = re.search(r"\bORD\d+\b", message, re.IGNORECASE)
    order = None

    if order_match:
        order_id = order_match.group(0).upper()
        order = lookup_order(order_id)

        if not order["success"]:
            return (
                f"I couldn't find an order matching {order_id}. "
                "Please check the order ID and try again."
            )

    # Step 3: Handle explicit ticket and escalation requests.
    if intent == "ticket_escalation":
        if order is None:
            return (
                "Please provide your order ID so I can verify the order "
                "before using the ticket workflow."
            )

        if order["status"] != "Delayed":
            return (
                f"Order {order['order_id']} is currently marked "
                f"{order['status']}. This ticket workflow currently "
                "supports delayed orders only."
            )

        ticket = create_ticket(
            order_id=order["order_id"],
            issue=message,
            priority="high",
        )

        if not ticket["success"]:
            return (
                "I verified your order, but the ticket operation failed: "
                f"{ticket.get('error', 'Unknown error')}."
            )

        if ticket.get("created") is False:
            action_text = "I found an existing active ticket and reused it."
        else:
            action_text = "Your support ticket was created successfully."

        return (
            f"{action_text}\n\n"
            f"Order ID: {order['order_id']}\n"
            f"Order status: {order['status']}\n"
            f"Ticket ID: {ticket['ticket_id']}\n"
            f"Ticket status: {ticket['status']}\n"
            f"Priority: {ticket['priority']}"
        )

    # Step 4: Answer refund questions using verified order information.
    if intent == "refund_inquiry" and order is not None:
        if order["refund_eligible"]:
            eligibility_text = (
                "The order record indicates that this order is eligible "
                "for a refund under the mock business rule."
            )
        else:
            eligibility_text = (
                "The order record does not mark this order as eligible "
                "for a refund under the mock business rule."
            )

        answer = (
            f"Order {order['order_id']} is currently marked "
            f"{order['status']}. {eligibility_text} "
            "Eligibility does not mean a refund has been approved or "
            "processed. No refund has been processed by this application."
        )

        if sources:
            answer += f"\n\nPolicy sources consulted: {sources}"

        return answer

    # Step 5: Handle verified order and delivery questions.
    if intent in ("order_status", "delivery_issue") and order is not None:
        answer = (
            f"Order {order['order_id']} — {order['item']}\n"
            f"Status: {order['status']}\n"
            f"Expected delivery: {order['expected_delivery']}"
        )

        actual_delivery = order.get("actual_delivery")
        if actual_delivery:
            answer += f"\nActual delivery: {actual_delivery}"

        if order["status"] == "Delayed":
            answer += (
                "\nI'm sorry your order is delayed. "
                "You can request a support ticket if you need further help."
            )

        if sources:
            answer += f"\n\nPolicy sources consulted: {sources}"

        return answer

    # Step 6: Use a controlled answer for general refund-policy questions.
    if _is_general_refund_policy_question(message, intent, order):
        refund_answer = _answer_general_refund_policy(
    policy_results,
    message,
)
        if refund_answer is not None:
            return refund_answer

    # Step 7: Use the LLM for other general questions.
    # No ticket is created unless the explicit ticket workflow is requested.
    answer = _ask_ollama(message, policy_results)

    if sources:
        answer += f"\n\nPolicy sources consulted: {sources}"

    return answer
