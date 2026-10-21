
"""Structured JSON logging with basic sensitive-field redaction."""

import json
import logging
from datetime import datetime, timezone
from app.core.config import LOG_LEVEL

logger = logging.getLogger("customer_support_agent")

SENSITIVE_FIELD_NAMES = {
    "password",
    "passwd",
    "token",
    "access_token",
    "refresh_token",
    "api_key",
    "authorization",
    "secret",
    "customer_email",
    "phone_number",
}

REDACTED = "[REDACTED]"


def configure_logging():
    """Configure console logging without duplicate handlers."""
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)


def _redact_fields(fields):
    """Redact values whose field names indicate sensitive information."""
    safe_fields = {}

    for key, value in fields.items():
        normalized_key = key.lower().replace("-", "_")

        if normalized_key in SENSITIVE_FIELD_NAMES:
            safe_fields[key] = REDACTED
        elif isinstance(value, dict):
            safe_fields[key] = _redact_fields(value)
        else:
            safe_fields[key] = value

    return safe_fields


def log_event(event, **fields):
    """Write a structured JSON event with sensitive fields redacted."""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **_redact_fields(fields),
    }
    logger.info(json.dumps(record, default=str))
