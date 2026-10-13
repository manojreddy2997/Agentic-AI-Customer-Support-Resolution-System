
import json

from app.evaluation.history import (
    load_evaluation_history,
    save_evaluation_report,
)


def sample_report():
    return {
        "total": 5,
        "passed": 4,
        "failed": 1,
        "pass_rate": 80.0,
        "results": [
            {"id": "EV001", "passed": True},
            {"id": "EV002", "passed": False},
        ],
    }


def test_save_evaluation_report_creates_history_file(tmp_path):
    history_file = tmp_path / "history.jsonl"

    record = save_evaluation_report(sample_report(), history_file)

    assert history_file.exists()
    assert record["total"] == 5
    assert record["passed"] == 4
    assert record["failed"] == 1
    assert record["pass_rate"] == 80.0
    assert "timestamp" in record


def test_load_evaluation_history_returns_saved_reports(tmp_path):
    history_file = tmp_path / "history.jsonl"

    save_evaluation_report(sample_report(), history_file)
    history = load_evaluation_history(history_file)

    assert len(history) == 1
    assert history[0]["total"] == 5
    assert history[0]["results"][0]["id"] == "EV001"


def test_history_keeps_multiple_runs(tmp_path):
    history_file = tmp_path / "history.jsonl"

    save_evaluation_report(sample_report(), history_file)
    save_evaluation_report(sample_report(), history_file)

    history = load_evaluation_history(history_file)

    assert len(history) == 2


def test_missing_history_file_returns_empty_list(tmp_path):
    history_file = tmp_path / "missing.jsonl"

    assert load_evaluation_history(history_file) == []


def test_malformed_json_line_is_skipped(tmp_path):
    history_file = tmp_path / "history.jsonl"
    history_file.write_text(
        '{"total": 1}\nnot valid json\n{"total": 2}\n',
        encoding="utf-8",
    )

    history = load_evaluation_history(history_file)

    assert len(history) == 2
    assert history[0]["total"] == 1
    assert history[1]["total"] == 2
