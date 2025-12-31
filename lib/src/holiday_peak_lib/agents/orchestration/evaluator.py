"""Evaluation hooks for latency and quality."""
from dataclasses import dataclass
from typing import Dict


@dataclass
class EvaluationResult:
    latency_ms: float
    success: bool
    notes: str = ""


class Evaluator:
    """Collects simple evaluation metrics."""

    def __init__(self) -> None:
        self.results: list[EvaluationResult] = []

    def record(self, latency_ms: float, success: bool, notes: str = "") -> EvaluationResult:
        result = EvaluationResult(latency_ms=latency_ms, success=success, notes=notes)
        self.results.append(result)
        return result

    def summary(self) -> Dict[str, float]:
        if not self.results:
            return {"count": 0, "avg_latency_ms": 0.0, "success_rate": 0.0}
        count = len(self.results)
        avg_latency = sum(r.latency_ms for r in self.results) / count
        success_rate = sum(1 for r in self.results if r.success) / count
        return {"count": count, "avg_latency_ms": avg_latency, "success_rate": success_rate}
