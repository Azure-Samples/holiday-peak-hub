"""Evaluation runner wrapper with optional Azure AI Evaluation integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class EvaluationRunResult:
    """Normalized output for evaluation execution."""

    status: str
    backend: str
    metrics: dict[str, Any]
    details: dict[str, Any]


def run_evaluation(
    dataset: list[dict[str, Any]],
    evaluator: Callable[[list[dict[str, Any]]], dict[str, Any]],
    *,
    run_name: str = "default",
) -> EvaluationRunResult:
    """Run evaluation with graceful fallback when Azure SDK is unavailable."""

    try:
        from azure.ai.evaluation import evaluate  # type: ignore[import-not-found]

        azure_result = evaluate(data=dataset, evaluators={"custom": evaluator}, run_name=run_name)
        metrics = dict(getattr(azure_result, "metrics", {}) or {})
        details = {
            "run_name": run_name,
            "result": str(azure_result),
        }
        return EvaluationRunResult(
            status="ok",
            backend="azure-ai-evaluation",
            metrics=metrics,
            details=details,
        )
    except ImportError:
        fallback_metrics = evaluator(dataset)
        return EvaluationRunResult(
            status="ok",
            backend="local-fallback",
            metrics=fallback_metrics,
            details={
                "run_name": run_name,
                "reason": "azure-ai-evaluation-sdk-unavailable",
            },
        )
    except Exception as exc:  # pylint: disable=broad-except
        fallback_metrics = evaluator(dataset)
        return EvaluationRunResult(
            status="degraded",
            backend="local-fallback",
            metrics=fallback_metrics,
            details={
                "run_name": run_name,
                "reason": str(exc),
            },
        )
