
"""Persistent storage for ResolveAI evaluation reports."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_HISTORY_FILE = PROJECT_ROOT / "data" / "evaluation" / "history.jsonl"


def save_evaluation_report(
    report: dict[str, Any],
    history_path: Path = DEFAULT_HISTORY_FILE,
) -> dict[str, Any]:
    """Append one evaluation report to the JSONL history."""
    history_path.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total": int(report.get("total", 0)),
        "passed": int(report.get("passed", 0)),
        "failed": int(report.get("failed", 0)),
        "pass_rate": float(report.get("pass_rate", 0.0)),
        "results": report.get("results", []),
    }

    with history_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")

    return record


def load_evaluation_history(
    history_path: Path = DEFAULT_HISTORY_FILE,
) -> list[dict[str, Any]]:
    """Load saved reports, skipping malformed lines safely."""
    if not history_path.exists():
        return []

    records = []

    with history_path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            if isinstance(record, dict):
                record["_line_number"] = line_number
                records.append(record)

    return records
