"""Automated evaluation for ResolveAI customer-support responses."""

import json
from pathlib import Path
from typing import Any

from app.agents.support_agent import generate_support_response


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = PROJECT_ROOT / "data" / "evaluation" / "test_cases.json"


def load_test_cases(dataset_path: Path = DEFAULT_DATASET) -> list[dict[str, Any]]:
    """Load and validate evaluation cases from a JSON file."""
    with dataset_path.open("r", encoding="utf-8") as file:
        cases = json.load(file)

    if not isinstance(cases, list):
        raise ValueError("The evaluation dataset must contain a JSON list.")

    seen_ids = set()

    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise ValueError(f"Test case at index {index} must be a JSON object.")

        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError(f"Test case at index {index} needs a non-empty id.")

        if case_id in seen_ids:
            raise ValueError(f"Duplicate test case id: {case_id}")

        seen_ids.add(case_id)

        if not isinstance(case.get("message"), str):
            raise ValueError(f"{case_id}: message must be a string.")

        for field in ("required_phrases", "forbidden_phrases"):
            phrases = case.get(field, [])
            if not isinstance(phrases, list) or not all(
                isinstance(phrase, str) for phrase in phrases
            ):
                raise ValueError(f"{case_id}: {field} must be a list of strings.")

    return cases


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one support response against required and forbidden phrases."""
    case_id = case["id"]
    response = ""
    errors = []

    try:
        response = generate_support_response(case["message"])
    except Exception as exc:
        errors.append(f"Response generation failed: {type(exc).__name__}: {exc}")

    normalized_response = response.casefold()

    missing_phrases = [
        phrase
        for phrase in case.get("required_phrases", [])
        if phrase.casefold() not in normalized_response
    ]

    found_forbidden_phrases = [
        phrase
        for phrase in case.get("forbidden_phrases", [])
        if phrase.casefold() in normalized_response
    ]

    if missing_phrases:
        errors.append("Missing required phrases: " + ", ".join(missing_phrases))

    if found_forbidden_phrases:
        errors.append(
            "Found forbidden phrases: " + ", ".join(found_forbidden_phrases)
        )

    return {
        "id": case_id,
        "category": case.get("category", "uncategorized"),
        "description": case.get("description", ""),
        "passed": not errors,
        "response": response,
        "missing_phrases": missing_phrases,
        "found_forbidden_phrases": found_forbidden_phrases,
        "errors": errors,
    }


def evaluate_dataset(
    dataset_path: Path = DEFAULT_DATASET,
) -> dict[str, Any]:
    """Evaluate every test case and calculate the overall pass rate."""
    cases = load_test_cases(dataset_path)
    results = [evaluate_case(case) for case in cases]

    total = len(results)
    passed = sum(result["passed"] for result in results)
    failed = total - passed
    pass_rate = (passed / total * 100) if total else 0.0

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": round(pass_rate, 2),
        "results": results,
    }
