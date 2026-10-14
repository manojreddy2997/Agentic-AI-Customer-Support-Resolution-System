"""Tests for ResolveAI evaluation trend calculations."""

from app.evaluation.trends import (
    build_evaluation_trend_rows,
    compare_evaluation_runs,
)


def make_record(
    pass_rate=80.0,
    review_required=2,
    relevance=80.0,
    groundedness=75.0,
    safety=100.0,
    violations=0,
    groundedness_not_assessed=1,
    total=5,
):
    return {
        "total": total,
        "passed": 4,
        "failed": 1,
        "pass_rate": pass_rate,
        "review_required": review_required,
        "quality_metrics": {
            "relevance": {
                "pass_rate": relevance,
                "not_assessed": 0,
            },
            "groundedness": {
                "pass_rate": groundedness,
                "not_assessed": groundedness_not_assessed,
            },
            "safety": {
                "pass_rate": safety,
                "violation_count": violations,
                "not_assessed": 0,
            },
            "verified_order_facts": {
                "pass_rate": 100.0,
                "not_assessed": 3,
            },
        },
    }


def test_compare_latest_run_with_previous_run():
    previous = make_record(
        pass_rate=70.0,
        review_required=1,
        relevance=70.0,
        groundedness=60.0,
        groundedness_not_assessed=2,
    )
    latest = make_record(
        pass_rate=80.0,
        review_required=3,
        relevance=90.0,
        groundedness=75.0,
        groundedness_not_assessed=1,
    )

    result = compare_evaluation_runs([previous, latest])

    assert result["has_history"] is True
    assert result["changes"]["pass_rate"]["delta"] == 10.0
    assert result["changes"]["relevance"]["delta"] == 20.0
    assert result["changes"]["groundedness"]["delta"] == 15.0
    assert result["changes"]["review_required"]["delta"] == 2
    assert result["changes"]["groundedness_coverage"]["latest"] == 80.0
    assert result["changes"]["groundedness_coverage"]["previous"] == 60.0
    assert result["changes"]["groundedness_coverage"]["delta"] == 20.0
    assert any("workload increased" in alert for alert in result["alerts"])


def test_empty_history_returns_helpful_result():
    result = compare_evaluation_runs([])

    assert result["has_history"] is False
    assert result["latest"] is None
    assert result["previous"] is None
    assert result["alerts"] == [
        "No evaluation history is available."
    ]


def test_single_run_has_no_previous_run_delta():
    result = compare_evaluation_runs([make_record()])

    assert result["previous"] is None
    assert result["changes"]["pass_rate"]["delta"] is None
    assert result["changes"]["relevance"]["delta"] is None


def test_missing_quality_metrics_are_not_treated_as_zero():
    old_record = {
        "total": 3,
        "passed": 2,
        "failed": 1,
        "pass_rate": 66.67,
    }

    result = compare_evaluation_runs([old_record])

    assert result["changes"]["relevance"]["latest"] is None
    assert result["changes"]["relevance"]["delta"] is None
    assert result["changes"]["safety_violations"]["latest"] is None
    assert any(
        "coverage is unavailable" in alert
        for alert in result["alerts"]
    )


def test_safety_violations_trigger_alert():
    result = compare_evaluation_runs([
        make_record(violations=2)
    ])

    assert result["changes"]["safety_violations"]["latest"] == 2
    assert any(
        "Safety warning" in alert
        for alert in result["alerts"]
    )


def test_low_groundedness_coverage_triggers_alert():
    record = make_record(
        groundedness_not_assessed=2,
        total=5,
    )

    result = compare_evaluation_runs([record])

    assert result["changes"]["groundedness_coverage"]["latest"] == 60.0
    assert any(
        "Low groundedness assessment coverage" in alert
        for alert in result["alerts"]
    )


def test_trend_rows_preserve_missing_values():
    rows = build_evaluation_trend_rows([
        make_record(),
        {
            "total": 2,
            "pass_rate": 50.0,
        },
    ])

    assert len(rows) == 2
    assert rows[0]["Run"] == 1
    assert rows[0]["Relevance (%)"] == 80.0
    assert rows[1]["Pass Rate (%)"] == 50.0
    assert rows[1]["Relevance (%)"] is None
    assert rows[1]["Safety Violations"] is None
