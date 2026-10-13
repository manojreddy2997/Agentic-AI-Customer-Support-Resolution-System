"""Command-line runner for ResolveAI automated evaluation."""

import argparse
import json
from pathlib import Path

from app.evaluation.evaluator import DEFAULT_DATASET, evaluate_dataset


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate ResolveAI customer-support responses."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
        help="Path to the evaluation JSON dataset.",
    )
    parser.add_argument(
        "--show-responses",
        action="store_true",
        help="Display each generated response.",
    )
    args = parser.parse_args()

    try:
        report = evaluate_dataset(args.dataset)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Evaluation could not start: {exc}")
        return 2

    print("\n" + "=" * 58)
    print("             RESOLVEAI EVALUATION REPORT")
    print("=" * 58)
    print(f"Total test cases : {report['total']}")
    print(f"Passed           : {report['passed']}")
    print(f"Failed           : {report['failed']}")
    print(f"Pass rate        : {report['pass_rate']:.2f}%")
    print("-" * 58)

    for result in report["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"[{status}] {result['id']} | {result['category']}")

        if result["description"]:
            print(f"       {result['description']}")

        for error in result["errors"]:
            print(f"       Issue: {error}")

        if args.show_responses:
            print("       Response:")
            print("       " + (result["response"] or "(empty response)").replace(
                "\n", "\n       "
            ))

        print()

    print("=" * 58)

    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
