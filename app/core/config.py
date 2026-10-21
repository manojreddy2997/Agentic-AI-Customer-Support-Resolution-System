
"""Centralized configuration for the customer-support agent."""

import os


def _positive_int(name: str, default: int) -> int:
    """Read a positive integer environment variable."""
    raw_value = os.getenv(name)

    if raw_value is None:
        return default

    try:
        value = int(raw_value)
    except ValueError:
        return default

    return value if value > 0 else default


APP_NAME = os.getenv(
    "APP_NAME",
    "Agentic AI Customer Support",
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "llama3.2:3b",
)

MCP_TIMEOUT_SECONDS = _positive_int(
    "MCP_TIMEOUT_SECONDS",
    15,
)

LLM_TIMEOUT_SECONDS = _positive_int(
    "LLM_TIMEOUT_SECONDS",
    30,
)

LOG_LEVEL = os.getenv(
    "LOG_LEVEL",
    "INFO",
).upper()

if LOG_LEVEL not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
    LOG_LEVEL = "INFO"
