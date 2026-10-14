"""Trend calculations for ResolveAI evaluation history."""

from typing import Any


QUALITY_METRICS = (
    "relevance",
    "groundedness",
    "safety",
    "verified_order_facts",
)


def _number(value: Any) -> float | None:
    """Return a finite numeric value, or None for missing/invalid data."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None

    result = float(value)
    if result != result or result in (float("inf"), float("-inf")):
        return None

    return result


def _quality_metrics(record: dict[str, Any]) -> dict[str, Any]:
    """Return quality metrics only when the stored field is a dictionary."""
    metrics = record.get("quality_metrics")
    return metrics if isinstance(metrics, dict) else {}


def _metric_rate(
    record: dict[str, Any],
    metric_name: str,
) -> float | None:
    """Read a metric's assessed pass rate without inventing missing values."""
    metric = _quality_metrics(record).get(metric_name)

    if not isinstance(metric, dict):
        return None

    return _number(metric.get("pass_rate"))


def _assessed_coverage(
    record: dict[str, Any],
    metric_name: str,
) -> float | None:
    """Calculate assessed coverage as a percentage of total test cases."""
    total = _number(record.get("total"))
    metric = _quality_metrics(record).get(metric_name)

    if total is None or total <= 0 or not isinstance(metric, dict):
        return None

    not_assessed = _number(metric.get("not_assessed"))
    if not_assessed is None:
        return None

    return round(
        max(0.0, min(100.0, (total - not_assessed) / total * 100)),
        2,
    )


def _safety_violations(record: dict[str, Any]) -> float | None:
    """Read the explicit safety violation count when available."""
    metric = _quality_metrics(record).get("safety")

    if not isinstance(metric, dict):
        return None

    return _number(metric.get("violation_count"))


def compare_evaluation_runs(
    history: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare the newest evaluation run with the previous available run.

    History is expected in chronological order, as returned by
    load_evaluation_history(). Missing metrics remain None rather than
    being treated as zero.
    """
    if not history:
        return {
            "has_history": False,
            "latest": None,
            "previous": None,
            "changes": {},
            "alerts": ["No evaluation history is available."],
        }

    latest = history[-1]
    previous = history[-2] if len(history) >= 2 else None

    changes: dict[str, dict[str, float | None]] = {}

    latest_pass_rate = _number(latest.get("pass_rate"))
    previous_pass_rate = (
        _number(previous.get("pass_rate")) if previous else None
    )

    changes["pass_rate"] = {
        "latest": latest_pass_rate,
        "previous": previous_pass_rate,
        "delta": (
            round(latest_pass_rate - previous_pass_rate, 2)
            if latest_pass_rate is not None
            and previous_pass_rate is not None
            else None
        ),
    }

    for metric_name in QUALITY_METRICS:
        latest_rate = _metric_rate(latest, metric_name)
        previous_rate = (
            _metric_rate(previous, metric_name) if previous else None
        )

        changes[metric_name] = {
            "latest": latest_rate,
            "previous": previous_rate,
            "delta": (
                round(latest_rate - previous_rate, 2)
                if latest_rate is not None and previous_rate is not None
                else None
            ),
        }

    latest_review = _number(latest.get("review_required"))
    previous_review = (
        _number(previous.get("review_required")) if previous else None
    )

    changes["review_required"] = {
        "latest": latest_review,
        "previous": previous_review,
        "delta": (
            latest_review - previous_review
            if latest_review is not None and previous_review is not None
            else None
        ),
    }

    latest_violations = _safety_violations(latest)
    previous_violations = (
        _safety_violations(previous) if previous else None
    )

    changes["safety_violations"] = {
        "latest": latest_violations,
        "previous": previous_violations,
        "delta": (
            latest_violations - previous_violations
            if latest_violations is not None
            and previous_violations is not None
            else None
        ),
    }

    changes["groundedness_coverage"] = {
        "latest": _assessed_coverage(latest, "groundedness"),
        "previous": (
            _assessed_coverage(previous, "groundedness")
            if previous
            else None
        ),
        "delta": None,
    }

    coverage = changes["groundedness_coverage"]
    if coverage["latest"] is not None and coverage["previous"] is not None:
        coverage["delta"] = round(
            coverage["latest"] - coverage["previous"], 2
        )

    alerts: list[str] = []

    if latest_violations is not None and latest_violations > 0:
        alerts.append(
            f"Safety warning: {int(latest_violations)} "
            "unsupported refund claim(s) detected."
        )

    review_delta = changes["review_required"]["delta"]
    if review_delta is not None and review_delta > 0:
        alerts.append(
            f"Human-review workload increased by {int(review_delta)} case(s)."
        )

    groundedness_coverage = coverage["latest"]
    if groundedness_coverage is None:
        alerts.append("Groundedness assessment coverage is unavailable.")
    elif groundedness_coverage < 80:
        alerts.append(
            f"Low groundedness assessment coverage: "
            f"{groundedness_coverage:.1f}%."
        )

    for metric_name in QUALITY_METRICS:
    # Safety is tracked through violations, not a safety pass rate.
        if metric_name == "safety":
            continue

    if changes[metric_name]["latest"] is None:
        alerts.append(
            f"{metric_name.replace('_', ' ').title()} pass rate is unavailable for the latest run."
        )

    return {
        "has_history": True,
        "latest": latest,
        "previous": previous,
        "changes": changes,
        "alerts": alerts,
    }


def build_evaluation_trend_rows(
    history: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build chart-ready rows while preserving missing metrics as None."""
    rows: list[dict[str, Any]] = []

    for index, record in enumerate(history, start=1):
        row: dict[str, Any] = {
            "Run": index,
            "Pass Rate (%)": _number(record.get("pass_rate")),
            "Review Required": _number(record.get("review_required")),
        }

        for metric_name in QUALITY_METRICS:
            label = metric_name.replace("_", " ").title()
            row[f"{label} (%)"] = _metric_rate(record, metric_name)

        row["Safety Violations"] = _safety_violations(record)
        row["Groundedness Coverage (%)"] = _assessed_coverage(
            record, "groundedness"
        )

        rows.append(row)

    return rows
