
"""Simple metrics for evaluating an AI agent."""

from dataclasses import dataclass, asdict
import json


@dataclass
class AgentMetrics:
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    safety_violations: int = 0
    total_latency_ms: float = 0.0

    def record(self, success: bool, latency_ms: float,
               safety_violation: bool = False):
        self.total_requests += 1
        self.total_latency_ms += max(0.0, latency_ms)

        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1

        if safety_violation:
            self.safety_violations += 1

    def report(self) -> dict:
        total = self.total_requests

        return {
            **asdict(self),
            "success_rate_percent": round(
                self.successful_requests / total * 100, 2
            ) if total else 0.0,
            "failure_rate_percent": round(
                self.failed_requests / total * 100, 2
            ) if total else 0.0,
            "safety_violation_rate_percent": round(
                self.safety_violations / total * 100, 2
            ) if total else 0.0,
            "average_latency_ms": round(
                self.total_latency_ms / total, 2
            ) if total else 0.0,
        }


if __name__ == "__main__":
    metrics = AgentMetrics()

    metrics.record(success=True, latency_ms=250)
    metrics.record(success=True, latency_ms=400)
    metrics.record(success=False, latency_ms=1200)

    print(json.dumps(metrics.report(), indent=2))
