
import json

from app.tools import ticket_tools
from app.tools.order_tools import lookup_order


def test_delayed_order_refund_eligibility():
    result = lookup_order("ORD1002")

    assert result["success"] is True
    assert result["status"] == "Delayed"
    assert result["refund_eligible"] is True


def test_unknown_order_is_not_found():
    result = lookup_order("ORD9999")

    assert result["success"] is False


def test_order_lookup_normalizes_id():
    result = lookup_order("ord1002")

    assert result["success"] is True
    assert result["order_id"] == "ORD1002"


def test_empty_order_id_is_rejected():
    result = lookup_order("")

    assert result["success"] is False


def test_create_ticket_and_persist(monkeypatch, tmp_path):
    database_file = tmp_path / "support_tickets.json"
    monkeypatch.setattr(ticket_tools, "TICKETS_FILE", database_file)

    result = ticket_tools.create_ticket(
        order_id="ord1002",
        issue="Order is three days late",
        priority="high",
    )

    assert result["success"] is True
    assert result["order_id"] == "ORD1002"
    assert result["priority"] == "high"
    assert result["status"] == "Open"
    assert result["ticket_id"].startswith("TKT-")

    saved_data = json.loads(database_file.read_text(encoding="utf-8"))
    assert len(saved_data) == 1
    assert saved_data[0]["ticket_id"] == result["ticket_id"]


def test_reject_empty_ticket_issue(monkeypatch, tmp_path):
    monkeypatch.setattr(
        ticket_tools, "TICKETS_FILE",
        tmp_path / "support_tickets.json",
    )

    result = ticket_tools.create_ticket(
        order_id="ORD1002",
        issue="   ",
    )

    assert result["success"] is False
    assert not ticket_tools.TICKETS_FILE.exists()


def test_reject_invalid_priority(monkeypatch, tmp_path):
    monkeypatch.setattr(
        ticket_tools, "TICKETS_FILE",
        tmp_path / "support_tickets.json",
    )

    result = ticket_tools.create_ticket(
        order_id="ORD1002",
        issue="Delayed delivery",
        priority="urgent",
    )

    assert result["success"] is False


def test_list_tickets(monkeypatch, tmp_path):
    monkeypatch.setattr(
        ticket_tools, "TICKETS_FILE",
        tmp_path / "support_tickets.json",
    )

    ticket_tools.create_ticket("ORD1002", "Delayed delivery")

    tickets = ticket_tools.list_tickets()

    assert len(tickets) == 1
    assert tickets[0]["issue"] == "Delayed delivery"


def test_duplicate_ticket_reuses_active_ticket(monkeypatch, tmp_path):
    database_file = tmp_path / "support_tickets.json"
    monkeypatch.setattr(ticket_tools, "TICKETS_FILE", database_file)

    first = ticket_tools.create_ticket(
        "ORD1002", "Delayed delivery", "high"
    )
    second = ticket_tools.create_ticket(
        "ORD1002", "Still waiting", "medium"
    )

    assert first["created"] is True
    assert second["created"] is False
    assert first["ticket_id"] == second["ticket_id"]
    assert len(ticket_tools.list_tickets()) == 1


def test_get_ticket_by_id(monkeypatch, tmp_path):
    monkeypatch.setattr(
        ticket_tools, "TICKETS_FILE",
        tmp_path / "support_tickets.json",
    )

    created = ticket_tools.create_ticket("ORD1002", "Delayed delivery")
    result = ticket_tools.get_ticket(created["ticket_id"].lower())

    assert result["success"] is True
    assert result["ticket_id"] == created["ticket_id"]


def test_update_ticket_status(monkeypatch, tmp_path):
    monkeypatch.setattr(
        ticket_tools, "TICKETS_FILE",
        tmp_path / "support_tickets.json",
    )

    created = ticket_tools.create_ticket("ORD1002", "Delayed delivery")
    result = ticket_tools.update_ticket_status(
        created["ticket_id"], "In Progress"
    )

    assert result["success"] is True
    assert result["status"] == "In Progress"


def test_reject_invalid_ticket_status(monkeypatch, tmp_path):
    monkeypatch.setattr(
        ticket_tools, "TICKETS_FILE",
        tmp_path / "support_tickets.json",
    )

    created = ticket_tools.create_ticket("ORD1002", "Delayed delivery")
    result = ticket_tools.update_ticket_status(
        created["ticket_id"], "Cancelled"
    )

    assert result["success"] is False


from app.rag import knowledge_base


def test_refund_query_retrieves_refund_policy():
    results = knowledge_base.search_knowledge_base(
        "Is my delayed order eligible for a refund?"
    )

    assert results
    assert results[0]["source"] == "refund_policy.txt"
    assert "eligibility" in results[0]["content"].lower()


def test_delivery_query_retrieves_delivery_policy():
    results = knowledge_base.search_knowledge_base(
        "What should I do about a delayed delivery?"
    )

    assert results
    assert results[0]["source"] == "delivery_policy.txt"


def test_empty_query_returns_no_results():
    assert knowledge_base.search_knowledge_base("   ") == []


def test_top_k_limits_results():
    results = knowledge_base.search_knowledge_base(
        "order delivery refund policy",
        top_k=1,
    )

    assert len(results) <= 1


def test_missing_knowledge_base_returns_no_results(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        knowledge_base,
        "KNOWLEDGE_BASE_DIR",
        tmp_path / "missing",
    )

    assert knowledge_base.search_knowledge_base(
        "refund policy"
    ) == []

from app.agents import support_agent


def test_refund_response_uses_verified_order_data(monkeypatch):
    monkeypatch.setattr(
        support_agent,
        "_get_policy_context",
        lambda message: ([], ""),
    )

    response = support_agent.generate_support_response(
        "Is ORD1002 eligible for a refund?"
    )

    assert "eligible for a refund" in response.lower()
    assert "Delayed" in response
    assert "No refund has been processed" in response


def test_ticket_response_reports_existing_ticket(monkeypatch):
    monkeypatch.setattr(
        support_agent,
        "_get_policy_context",
        lambda message: ([], ""),
    )

    monkeypatch.setattr(
        support_agent,
        "create_ticket",
        lambda **kwargs: {
            "success": True,
            "created": False,
            "ticket_id": "TKT-TEST1234",
            "status": "Open",
            "priority": "high",
        },
    )

    response = support_agent.generate_support_response(
        "Please escalate ORD1002 and create a support ticket."
    )

    assert "existing active ticket" in response.lower()
    assert "TKT-TEST1234" in response
    assert "ORD1002" in response
    assert "Open" in response
    assert "high" in response


def test_unknown_order_never_creates_ticket(monkeypatch):
    def fail_if_called(**kwargs):
        raise AssertionError("Ticket tool should not be called")

    monkeypatch.setattr(
        support_agent,
        "create_ticket",
        fail_if_called,
    )

    response = support_agent.generate_support_response(
        "Please escalate ORD9999 and create a support ticket."
    )

    assert "couldn't find an order" in response.lower()


def test_empty_message_is_handled():
    response = support_agent.generate_support_response("   ")

    assert "enter a message" in response.lower()


def test_general_return_policy_uses_controlled_response(monkeypatch):
    def fail_if_called(**kwargs):
        raise AssertionError(
            "Ollama should not be called for a controlled refund-policy answer"
        )

    monkeypatch.setattr(support_agent.ollama, "chat", fail_if_called)

    response = support_agent.generate_support_response(
        "What is your return policy?"
    )

    assert "delayed order may be eligible" in response.lower()
    assert "approved or processed" in response.lower()
    assert "refund_policy.txt" in response
    assert "delivery_policy.txt" not in response


def test_general_refund_eligibility_question_uses_refund_policy(
    monkeypatch,
):
    def fail_if_called(**kwargs):
        raise AssertionError(
            "Ollama should not be called for a controlled refund-policy answer"
        )

    monkeypatch.setattr(support_agent.ollama, "chat", fail_if_called)

    response = support_agent.generate_support_response(
        "How do I know if my order qualifies for a refund?"
    )

    assert "refund_eligible" in response
    assert "approved or processed" in response.lower()
    assert "refund_policy.txt" in response
    assert "delivery_policy.txt" not in response
