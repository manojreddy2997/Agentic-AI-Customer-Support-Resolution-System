
import json
import logging

from app.agent_logging import configure_logging, log_event, logger


def capture_log_event(monkeypatch, event, **fields):
    """Capture the JSON message passed to the logger."""
    captured = []

    monkeypatch.setattr(
        logger,
        "info",
        lambda message, *args, **kwargs: captured.append(message),
    )

    configure_logging()
    log_event(event, **fields)

    assert captured, "Expected a log message"
    return captured[-1]


def test_sensitive_fields_are_redacted(monkeypatch):
    message = capture_log_event(
        monkeypatch,
        "security_test",
        tool="get_order",
        password="secret123",
        access_token="abc123",
        latency_ms=120,
    )

    record = json.loads(message)

    assert record["password"] == "[REDACTED]"
    assert record["access_token"] == "[REDACTED]"
    assert record["tool"] == "get_order"
    assert record["latency_ms"] == 120
    assert "secret123" not in message
    assert "abc123" not in message


def test_nested_sensitive_fields_are_redacted(monkeypatch):
    message = capture_log_event(
        monkeypatch,
        "nested_security_test",
        details={
            "password": "nested-secret",
            "status": "success",
        },
    )

    record = json.loads(message)

    assert record["details"]["password"] == "[REDACTED]"
    assert record["details"]["status"] == "success"
    assert "nested-secret" not in message
