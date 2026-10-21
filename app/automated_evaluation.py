
"""Run pytest and save a machine-readable evaluation report."""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = PROJECT_ROOT / "automated_evaluation_report.json"


def main():
    started_at = datetime.now(timezone.utc).isoformat()

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    output = (result.stdout + "\n" + result.stderr).strip()

    summary_lines = [
        line.strip()
        for line in output.splitlines()
        if " passed" in line
        or " failed" in line
        or " error" in line
        or " no tests ran" in line
    ]

    report = {
        "timestamp": started_at,
        "command": ["python", "-m", "pytest", "-q"],
        "exit_code": result.returncode,
        "passed": result.returncode == 0,
        "summary": summary_lines[-1] if summary_lines else "No summary found",
        "details": output,
        "note": (
            "This report records the actual pytest run. "
            "Passing tests do not guarantee every scenario is covered."
        ),
    }

    REPORT_PATH.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("Evaluation summary:")
    print(json.dumps({
        "passed": report["passed"],
        "summary": report["summary"],
        "report_path": str(REPORT_PATH),
    }, indent=2))

    if result.returncode != 0:
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
