"""Unit tests for ResolveAI's automated evaluation system."""

import json

import pytest

from app.evaluation.evaluator import (
    evaluate_case,
    evaluate_dataset,
    load_test_cases,
)


def test_evaluate_case_passes_when_required_phrases_exist():
    case = {
        "id": "UNIT001",
        "category": "unit_test",
        "message": "test message",
        "required_phrases": ["order", "delayed"],
        "forbidden_phrases": ["refund approved"],
    }

    def fake_response(_message):
        return "Your order is delayed. No refund has been approved."

    # Patch the function used inside the evaluator.
    import app.evaluation.evaluator as evaluator

    original = evaluator.generate_support_response
    evaluator.generate_support_response = fake_response
    try:
        result = evaluate_case(case)
    finally:
        evaluator.generate_support_response = original

    assert result["passed"] is True
    assert result["errors"] == []


def test_evaluate_case_fails_when_required_phrase_is_missing(monkeypatch):
    import app.evaluation.evaluator as evaluator

    monkeypatch.setattr(
        evaluator,
        "generate_support_response",
        lambda _message: "Your order is delayed.",
    )

    result = evaluate_case({
        "id": "UNIT002",
        "message": "test",
        "required_phrases": ["refund eligibility"],
        "forbidden_phrases": [],
    })

    assert result["passed"] is False
    assert "refund eligibility" in result["missing_phrases"]


def test_evaluate_case_fails_when_forbidden_phrase_is_present(monkeypatch):
    import app.evaluation.evaluator as evaluator

    monkeypatch.setattr(
        evaluator,
        "generate_support_response",
        lambda _message: "Your refund has been approved.",
    )

    result = evaluate_case({
        "id": "UNIT003",
        "message": "test",
        "required_phrases": [],
        "forbidden_phrases": ["refund has been approved"],
    })

    assert result["passed"] is False
    assert result["found_forbidden_phrases"] == [
        "refund has been approved"
    ]


def test_evaluate_case_records_response_generation_error(monkeypatch):
    import app.evaluation.evaluator as evaluator

    def raise_error(_message):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(
        evaluator, "generate_support_response", raise_error
    )

    result = evaluate_case({
        "id": "UNIT004",
        "message": "test",
        "required_phrases": [],
        "forbidden_phrases": [],
    })

    assert result["passed"] is False
    assert any(
        "Response generation failed" in error
        for error in result["errors"]
    )


def test_load_test_cases_rejects_duplicate_ids(tmp_path):
    dataset = tmp_path / "duplicate_cases.json"
    dataset.write_text(
        json.dumps([
            {"id": "DUP001", "message": ""},
            {"id": "DUP001", "message": "another case"},
        ]),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Duplicate test case id"):
        load_test_cases(dataset)


def test_evaluate_dataset_calculates_pass_rate(monkeypatch, tmp_path):
    import app.evaluation.evaluator as evaluator

    dataset = tmp_path / "cases.json"
    dataset.write_text(
        json.dumps([
            {
                "id": "RATE001",
                "message": "first",
                "required_phrases": ["correct"],
                "forbidden_phrases": [],
            },
            {
                "id": "RATE002",
                "message": "second",
                "required_phrases": ["missing"],
                "forbidden_phrases": [],
            },
        ]),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        evaluator,
        "generate_support_response",
        lambda message: (
            "correct" if message == "first" else "not the expected answer"
        ),
    )

    report = evaluate_dataset(dataset)

    assert report["total"] == 2
    assert report["passed"] == 1
    assert report["failed"] == 1
    assert report["pass_rate"] == 50.0

def test_evaluate_dataset_reports_quality_metrics(monkeypatch, tmp_path):
    import app.evaluation.evaluator as evaluator

    dataset = tmp_path / "quality_cases.json"
    dataset.write_text(
        json.dumps([
            {
                "id": "QUALITY001",
                "message": "Where is my order?",
                "required_phrases": ["delayed"],
                "forbidden_phrases": [],
                "evidence": ["The order status is delayed."],
                "grounding_phrases": ["delayed"],
            },
            {
                "id": "QUALITY002",
                "message": "Where is my order?",
                "required_phrases": ["delayed"],
                "forbidden_phrases": [],
                "evidence": ["The order status is delayed."],
                "grounding_phrases": ["delayed"],
            },
        ]),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        evaluator,
        "generate_support_response",
        lambda _message: "Your order is delayed.",
    )

    report = evaluator.evaluate_dataset(dataset)

    assert report["total"] == 2
    assert report["passed"] == 2
    assert report["pass_rate"] == 100.0

    metrics = report["quality_metrics"]
    assert metrics["relevance"]["passed"] == 2
    assert metrics["groundedness"]["passed"] == 2
    assert metrics["groundedness"]["pass_rate"] == 100.0
    assert metrics["safety"]["violation_count"] == 0


def test_quality_pass_rate_excludes_not_assessed_checks(
    monkeypatch,
    tmp_path,
):
    import app.evaluation.evaluator as evaluator

    dataset = tmp_path / "unassessed_cases.json"
    dataset.write_text(
        json.dumps([
            {
                "id": "ASSESS001",
                "message": "Check order ORD999999",
                "required_phrases": [],
                "forbidden_phrases": [],
            },
        ]),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        evaluator,
        "generate_support_response",
        lambda _message: "I couldn't find an order with that ID.",
    )

    report = evaluator.evaluate_dataset(dataset)

    metrics = report["quality_metrics"]
    assert metrics["verified_order_facts"]["not_assessed"] == 1
    assert metrics["verified_order_facts"]["pass_rate"] is None
