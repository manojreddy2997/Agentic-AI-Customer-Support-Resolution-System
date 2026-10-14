
"""Regression tests for ResolveAI response quality diagnostics."""

from app.evaluation.evaluator import (
    _check_groundedness,
    _check_relevance,
    _check_safety,
    _check_verified_order_facts,
)


def test_safety_detects_affirmative_refund_processing_claim():
    violations = _check_safety("Your refund has been processed.")

    assert violations


def test_safety_allows_explicit_refund_processing_denial():
    violations = _check_safety("No refund has been processed.")

    assert violations == []


def test_relevance_flags_empty_response():
    result = _check_relevance("Where is my order?", "")

    assert result["status"] == "fail"
    assert result["lexical_overlap"] == 0.0


def test_relevance_reports_low_overlap_for_unrelated_response():
    result = _check_relevance(
        "Where is my order?",
        "Photosynthesis converts light into chemical energy.",
    )

    assert result["status"] == "review_required"


def test_groundedness_passes_when_phrase_exists_in_evidence():
    result = _check_groundedness(
        "Your order is delayed.",
        {
            "evidence": "The verified order status is delayed.",
            "grounding_phrases": ["delayed"],
        },
    )

    assert result["status"] == "pass"
    assert result["unsupported_phrases"] == []


def test_groundedness_fails_when_checked_phrase_is_not_in_evidence():
    result = _check_groundedness(
        "Your refund is guaranteed.",
        {
            "evidence": "Refund eligibility depends on the order record.",
            "grounding_phrases": ["guaranteed"],
        },
    )

    assert result["status"] == "fail"
    assert result["unsupported_phrases"] == ["guaranteed"]


def test_groundedness_is_not_assessed_without_evidence():
    result = _check_groundedness(
        "Your order is delayed.",
        {"grounding_phrases": ["delayed"]},
    )

    assert result["status"] == "not_assessed"


def test_verified_order_facts_accept_correct_information():
    result = _check_verified_order_facts(
        "Check ORD1002",
        (
            "Order ORD1002 is currently marked Delayed. "
            "Mechanical Keyboard. Expected delivery: 2026-10-10"
        ),
    )

    assert result["status"] == "pass"
    assert result["violations"] == []


def test_verified_order_facts_detect_incorrect_information():
    result = _check_verified_order_facts(
        "Check ORD1002",
        (
            "Order ORD1002 is currently marked Delivered. "
            "Wireless Headphones. Expected delivery: 2026-10-20"
        ),
    )

    assert result["status"] == "fail"
    assert len(result["violations"]) == 3


def test_verified_order_facts_skip_unknown_orders():
    result = _check_verified_order_facts(
        "Check ORD999999",
        "Order ORD999999 has been delivered.",
    )

    assert result["status"] == "not_assessed"
