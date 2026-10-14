
"""Automated evaluation for ResolveAI customer-support responses."""

import json
import re
from pathlib import Path
from typing import Any

from app.agents.support_agent import generate_support_response


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = PROJECT_ROOT / "data" / "evaluation" / "test_cases.json"


def load_test_cases(
    dataset_path: str | Path = DEFAULT_DATASET,
) -> list[dict[str, Any]]:
    """Load test cases and reject duplicate IDs."""
    path = Path(dataset_path)

    if not path.exists():
        raise FileNotFoundError(f"Evaluation dataset not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        cases = json.load(file)

    if not isinstance(cases, list):
        raise ValueError("The evaluation dataset must contain a JSON list.")

    seen_ids: set[str] = set()

    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise ValueError(f"Test case at index {index} must be an object.")

        case_id = str(case.get("id", "")).strip()

        if case_id:
            if case_id in seen_ids:
                raise ValueError(f"Duplicate test case id: {case_id}")
            seen_ids.add(case_id)

    return cases


def _tokens(text: str) -> set[str]:
    """Return lowercase alphanumeric tokens."""
    return set(re.findall(r"\b[a-z0-9]+\b", text.lower()))




def _check_relevance(message: str, response: str) -> dict[str, Any]:
    """Estimate relevance using lexical overlap and a narrow intent check."""
    message_tokens = _tokens(message)
    response_tokens = _tokens(response)
    normalized_message = message.lower()
    normalized_response = response.lower()

    if not response.strip():
        status = "fail"
        matched_tokens = set()
        overlap = 0.0
    elif not message_tokens:
        # Empty input is a validation case, not a relevance failure.
        status = "not_assessed"
        matched_tokens = set()
        overlap = 0.0
    else:
        matched_tokens = message_tokens & response_tokens
        overlap = len(matched_tokens) / len(message_tokens)

        asks_refund_guarantee = (
            "refund" in normalized_message
            and any(
                phrase in normalized_message
                for phrase in (
                    "guarantee",
                    "guaranteed",
                    "promise",
                    "will i get",
                    "will i receive",
                )
            )
        )

        directly_addresses_guarantee = (
            asks_refund_guarantee
            and any(
                phrase in normalized_response
                for phrase in (
                    "can't guarantee",
                    "cannot guarantee",
                    "can't promise",
                    "cannot promise",
                    "depends on",
                )
            )
        )

        status = (
            "pass"
            if overlap >= 0.20 or directly_addresses_guarantee
            else "review_required"
        )

    return {
        "status": status,
        "overlap": round(overlap, 3),
        "lexical_overlap": round(overlap, 3),
        "matched_tokens": sorted(matched_tokens),
    }


def _check_safety(response: str) -> list[str]:
    """Return unsupported claims that a refund has been completed."""
    text = response.lower()
    violations: list[str] = []

    patterns = [
        r"\brefund\s+(?:has\s+been\s+)?"
        r"(?:approved|processed|issued|completed)\b",
        r"\b(?:approved|processed|issued|completed)\s+"
        r"(?:your\s+)?refund\b",
        r"\byour\s+refund\s+(?:is|was|has\s+been)\s+"
        r"(?:approved|processed|issued|completed)\b",
    ]

    negation_pattern = re.compile(
        r"\b(?:no|not|never|hasn't|hasnt|haven't|havent|"
        r"cannot|can't|unable to|has not|have not)\b",
        re.IGNORECASE,
    )

    for pattern in patterns:
        for match in re.finditer(pattern, text):
            preceding = text[max(0, match.start() - 60):match.start()]

            # Ignore explicit denials such as:
            # "No refund has been processed."
            if negation_pattern.search(preceding):
                continue

            claim = match.group(0)
            if claim not in violations:
                violations.append(claim)

    return violations


def _check_groundedness(
    response: str,
    evidence: str | list[str] | dict[str, Any] | None,
    grounding_phrases: list[str] | None = None,
) -> dict[str, Any]:
    """Check configured response phrases against supplied evidence."""

    phrases = grounding_phrases or []

    if isinstance(evidence, dict):
        evidence_text = evidence.get("evidence")
        # Preserve compatibility with the older nested dictionary format.
        if not phrases:
            phrases = evidence.get("grounding_phrases", [])
    else:
        evidence_text = evidence

    if not evidence_text:
        return {
            "status": "not_assessed",
            "checked_phrases": [],
            "unsupported_phrases": [],
        }

    if isinstance(evidence_text, list):
        evidence_text = " ".join(str(item) for item in evidence_text)

    response_lower = response.lower()
    evidence_lower = str(evidence_text).lower()

    checked_phrases = [
        str(phrase)
        for phrase in phrases
        if str(phrase).lower() in response_lower
    ]

    unsupported_phrases = [
        phrase
        for phrase in checked_phrases
        if phrase.lower() not in evidence_lower
    ]

    if unsupported_phrases:
        status = "fail"
    elif checked_phrases:
        status = "pass"
    else:
        status = "not_assessed"

    return {
        "status": status,
        "checked_phrases": checked_phrases,
        "unsupported_phrases": unsupported_phrases,
    }



def _check_verified_order_facts(
    message: str,
    response: str,
    evidence: str | list[str] | dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Check known demo-order facts and skip unknown orders."""
    known_orders = {
        "ORD1002": {
            "product": "Mechanical Keyboard",
            "status": "delayed",
            "expected_delivery": "2026-10-10",
        }
    }

    order_ids = set(
        match.upper()
        for match in re.findall(
            r"\bORD\d+\b",
            f"{message}\n{response}",
            flags=re.IGNORECASE,
        )
    )

    if not order_ids:
        return {"status": "not_assessed", "violations": []}

    # If supplied evidence provides authoritative details, use it.
    if isinstance(evidence, dict):
        evidence_text = evidence.get("evidence", "")
        if isinstance(evidence_text, list):
            evidence_text = " ".join(str(item) for item in evidence_text)
        evidence_text = str(evidence_text)
    elif isinstance(evidence, list):
        evidence_text = " ".join(str(item) for item in evidence)
    else:
        evidence_text = str(evidence or "")

    response_lower = response.lower()
    violations: list[str] = []
    assessed_any = False

    for order_id in sorted(order_ids):
        expected = known_orders.get(order_id)

        if expected is None:
            # Unknown order facts cannot be verified from the demo database.
            continue

        assessed_any = True

        # Product consistency.
        conflicting_products = [
            "wireless headphones",
            "smartphone",
            "laptop",
            "running shoes",
        ]

        for product in conflicting_products:
            if product in response_lower:
                violations.append(
                    f"{order_id}: unexpected product mentioned: {product}"
                )

        # Order-status consistency.
        status_aliases = {
            "delivered": "delivered",
            "shipped": "shipped",
            "processing": "processing",
            "cancelled": "cancelled",
            "canceled": "cancelled",
            "delayed": "delayed",
            "pending": "pending",
        }

        mentioned_statuses = [
            (alias, normalized)
            for alias, normalized in status_aliases.items()
            if re.search(rf"\b{re.escape(alias)}\b", response_lower)
        ]

        if mentioned_statuses:
            mentioned, normalized = mentioned_statuses[0]
            if normalized != expected["status"]:
                violations.append(
                    f"{order_id}: status mismatch; expected "
                    f"{expected['status']}, but response mentioned {mentioned}"
                )

        # Delivery-date consistency.
        response_dates = re.findall(
            r"\b\d{4}-\d{2}-\d{2}\b",
            response,
        )

        for response_date in response_dates:
            if response_date != expected["expected_delivery"]:
                violations.append(
                    f"{order_id}: unexpected date {response_date}; "
                    f"expected {expected['expected_delivery']}"
                )

    if violations:
        status = "fail"
    elif assessed_any:
        status = "pass"
    elif evidence_text:
        # We have evidence, but the evaluator has no built-in record for
        # this order; don't pretend the fact was independently verified.
        status = "not_assessed"
    else:
        status = "not_assessed"

    return {
        "status": status,
        "violations": violations,
    }


def evaluate_case(
    case: dict[str, Any],
    response: str | None = None,
) -> dict[str, Any]:
    """Evaluate one response against required and forbidden phrases."""
    case_id = str(case.get("id", "UNKNOWN"))
    message = str(case.get("message", ""))
    category = str(case.get("category", "general"))
    description = str(case.get("description", ""))

    errors: list[str] = []
    missing_phrases: list[str] = []
    found_forbidden_phrases: list[str] = []

    if response is None:
        try:
            response = generate_support_response(message)
        except Exception as exc:
            error_message = (
                f"Response generation failed: {type(exc).__name__}: {exc}"
            )
            return {
                "id": case_id,
                "category": category,
                "description": description,
                "message": message,
                "response": "",
                "passed": False,
                "errors": [error_message],
                "missing_phrases": [],
                "found_forbidden_phrases": [],
                "evaluation_status": "FAIL",
                "review_reasons": ["Response generation failed"],
                "quality": {
                    "relevance": _check_relevance(message, ""),
                    "safety": {
                        "status": "not_assessed",
                        "flagged_claims": [],
                    },
                    "groundedness": {
                        "status": "not_assessed",
                        "checked_phrases": [],
                        "unsupported_phrases": [],
                    },
                    "verified_order_facts": {
                        "status": "not_assessed",
                        "violations": [],
                    },
                },
            }

    response = str(response)
    response_lower = response.lower()

    # Support both field names so older and newer datasets keep working.
    required_phrases = case.get(
        "required_phrases",
        case.get("expected_phrases", []),
    )
    forbidden_phrases = case.get("forbidden_phrases", [])

    missing_phrases = [
        str(phrase)
        for phrase in required_phrases
        if str(phrase).lower() not in response_lower
    ]

    found_forbidden_phrases = [
        str(phrase)
        for phrase in forbidden_phrases
        if str(phrase).lower() in response_lower
    ]

    if missing_phrases:
        errors.append("Missing required phrases")

    if found_forbidden_phrases:
        errors.append("Found forbidden phrases")

    relevance = _check_relevance(message, response)
    safety_violations = _check_safety(response)
    safety = {
        "status": "fail" if safety_violations else "pass",
        "flagged_claims": safety_violations,
    }

    groundedness = _check_groundedness(
    response,
    case.get("evidence"),
    case.get("grounding_phrases"),
)
    verified_order_facts = _check_verified_order_facts(
        message,
        response,
        case.get("evidence"),
    )

    
    review_reasons: list[str] = []

    if relevance["status"] == "review_required":
        review_reasons.append("Relevance requires review")

    if groundedness["status"] == "not_assessed":
        review_reasons.append("Groundedness could not be assessed")

    order_id_requested = bool(
        re.search(r"\bORD[A-Z0-9]+\b", message, re.IGNORECASE)
    )
    order_not_found = bool(
        re.search(
            r"(couldn't find|could not find|no matching order|order not found)",
            response,
            re.IGNORECASE,
        )
    )

    if (
        verified_order_facts["status"] == "not_assessed"
        and order_id_requested
        and not order_not_found
    ):
        review_reasons.append("Order facts could not be verified")

    # The overall test result reflects the test's explicit phrase assertions.
    # Quality heuristics are reported separately rather than silently changing
    # existing dataset pass rates.
    passed = not errors

    return {
        "id": case_id,
        "category": category,
        "description": description,
        "message": message,
        "response": response,
        "passed": passed,
        "errors": errors,
        "missing_phrases": missing_phrases,
        "found_forbidden_phrases": found_forbidden_phrases,
        "evaluation_status": "PASS" if passed else "FAIL",
        "review_reasons": review_reasons,
        "quality": {
            "relevance": relevance,
            "safety": safety,
            "groundedness": groundedness,
            "verified_order_facts": verified_order_facts,
        },
    }


def evaluate_dataset(
    dataset_path: str | Path = DEFAULT_DATASET,
) -> dict[str, Any]:
    """Evaluate the dataset and return aggregate metrics."""
    cases = load_test_cases(dataset_path)
    results = [evaluate_case(case) for case in cases]

    total = len(results)
    passed = sum(result["passed"] for result in results)
    failed = total - passed

    review_required = sum(
        bool(result["review_reasons"])
        for result in results
    )

    pass_rate = round((passed / total) * 100, 2) if total else 0.0

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": pass_rate,
        "review_required": review_required,
        "results": results,
    }



def evaluate_dataset(
    dataset_path: str | Path = DEFAULT_DATASET,
) -> dict[str, Any]:
    """Evaluate the dataset and return functional and quality metrics."""
    cases = load_test_cases(dataset_path)
    results = [evaluate_case(case) for case in cases]

    total = len(results)
    passed = sum(result["passed"] for result in results)
    failed = total - passed

    review_required = sum(
        bool(result.get("review_reasons"))
        for result in results
    )

    pass_rate = round((passed / total) * 100, 2) if total else 0.0

    def quality_status_count(check_name: str, status: str) -> int:
        """Count results with a specific quality-check status."""
        return sum(
            result.get("quality", {})
            .get(check_name, {})
            .get("status") == status
            for result in results
        )

    def assessed_rate(check_name: str) -> float | None:
        """Calculate pass rate among assessed checks only."""
        check_passed = quality_status_count(check_name, "pass")
        check_failed = quality_status_count(check_name, "fail")
        assessed = check_passed + check_failed

        if not assessed:
            return None

        return round((check_passed / assessed) * 100, 2)

    safety_violations = sum(
        bool(
            result.get("quality", {})
            .get("safety", {})
            .get("flagged_claims")
        )
        for result in results
    )

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": pass_rate,
        "review_required": review_required,
        "quality_metrics": {
            "relevance": {
                "passed": quality_status_count("relevance", "pass"),
                "failed": quality_status_count("relevance", "fail"),
                "review_required": quality_status_count(
                    "relevance", "review_required"
                ),
                "not_assessed": quality_status_count(
                    "relevance", "not_assessed"
                ),
                "pass_rate": assessed_rate("relevance"),
            },
            "groundedness": {
                "passed": quality_status_count("groundedness", "pass"),
                "failed": quality_status_count("groundedness", "fail"),
                "not_assessed": quality_status_count(
                    "groundedness", "not_assessed"
                ),
                "pass_rate": assessed_rate("groundedness"),
            },
            "safety": {
                "passed": quality_status_count("safety", "pass"),
                "failed": quality_status_count("safety", "fail"),
                "not_assessed": quality_status_count(
                    "safety", "not_assessed"
                ),
                "violation_count": safety_violations,
                "violation_rate": (
                    round((safety_violations / total) * 100, 2)
                    if total else 0.0
                ),
            },
            "verified_order_facts": {
                "passed": quality_status_count(
                    "verified_order_facts", "pass"
                ),
                "failed": quality_status_count(
                    "verified_order_facts", "fail"
                ),
                "not_assessed": quality_status_count(
                    "verified_order_facts", "not_assessed"
                ),
                "pass_rate": assessed_rate("verified_order_facts"),
            },
        },
        "results": results,
    }
