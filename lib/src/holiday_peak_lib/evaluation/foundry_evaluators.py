"""Evaluation strategy implementations for Foundry and local fallback scoring."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Iterable
from typing import Any, Protocol

from .models import EvalCase


class EvaluationBackendUnavailable(RuntimeError):
    """Raised when a requested evaluation backend cannot run."""


class EvaluatorStrategy(Protocol):
    """Structural interface for interchangeable evaluation backends.

    Pattern: Strategy — Foundry and local evaluators share a single behavior
    contract and can be selected at runtime.
    """

    backend_name: str

    async def evaluate(self, cases: list[EvalCase], *, run_name: str) -> dict[str, float]:
        """Evaluate cases and return normalized aggregate metrics."""


class LocalEvaluatorStrategy:
    """Deterministic local evaluator used when Foundry SDK access is unavailable."""

    backend_name = "local-fallback"

    def __init__(self, evaluators: Iterable[str] | None = None) -> None:
        self.evaluators = tuple(evaluators or ("dataset_readiness",))

    async def evaluate(self, cases: list[EvalCase], *, run_name: str) -> dict[str, float]:
        """Evaluate cases with deterministic completeness and overlap metrics."""

        del run_name
        return await asyncio.to_thread(self._evaluate_sync, cases)

    def _evaluate_sync(self, cases: list[EvalCase]) -> dict[str, float]:
        total = float(len(cases))
        if total == 0:
            return {"case_count": 0.0, "dataset_readiness": 0.0}

        response_count = sum(1 for case in cases if case.response)
        ground_truth_count = sum(1 for case in cases if case.ground_truth)
        behavior_count = sum(1 for case in cases if case.expected_behavior)

        metrics: dict[str, float] = {
            "case_count": total,
            "dataset_readiness": 1.0,
            "response_coverage": response_count / total,
            "ground_truth_coverage": ground_truth_count / total,
            "expected_behavior_coverage": behavior_count / total,
        }

        overlap_scores = [
            _token_overlap(case.response or "", case.expected_behavior)
            for case in cases
            if case.response
        ]
        if overlap_scores:
            overlap = sum(overlap_scores) / float(len(overlap_scores))
            for evaluator_name in self.evaluators:
                metrics.setdefault(evaluator_name, overlap)
        return metrics


class FoundryEvaluatorStrategy:
    """Azure AI Foundry evaluator gateway with normalized aggregate output."""

    backend_name = "azure-ai-evaluation"

    def __init__(self, evaluators: Iterable[str]) -> None:
        self.evaluators = tuple(evaluators)

    async def evaluate(self, cases: list[EvalCase], *, run_name: str) -> dict[str, float]:
        """Run Azure AI Evaluation when the optional SDK is importable."""

        return await asyncio.to_thread(self._evaluate_sync, cases, run_name)

    def _evaluate_sync(self, cases: list[EvalCase], run_name: str) -> dict[str, float]:
        try:
            from azure.ai.evaluation import evaluate  # type: ignore[import-not-found]
        except ImportError as exc:
            raise EvaluationBackendUnavailable("azure-ai-evaluation SDK is not installed") from exc

        data = [case.to_foundry_item() for case in cases]
        result = evaluate(
            data=data,
            evaluators={name: _score_expected_behavior for name in self.evaluators},
            run_name=run_name,
        )
        metrics = getattr(result, "metrics", None)
        if isinstance(metrics, dict):
            return _coerce_float_metrics(metrics)
        if isinstance(result, dict):
            return _coerce_float_metrics(result.get("metrics", result))
        return {"case_count": float(len(cases))}


def select_evaluator_strategy(
    *,
    evaluators: Iterable[str],
    prefer_foundry: bool = True,
) -> EvaluatorStrategy:
    """Choose the best available evaluator strategy."""

    if prefer_foundry:
        return FoundryEvaluatorStrategy(evaluators)
    return LocalEvaluatorStrategy(evaluators)


def _score_expected_behavior(*args: Any, **kwargs: Any) -> dict[str, float]:
    """Score one payload for SDKs that accept custom evaluator callables.

    # No GoF pattern applies — compatibility adapter for optional SDK callbacks.
    """

    payload: dict[str, Any] = {}
    if args and isinstance(args[0], dict):
        payload.update(args[0])
    payload.update(kwargs)
    response = str(payload.get("response") or payload.get("output") or "")
    expected = str(payload.get("expected_behavior") or payload.get("ground_truth") or "")
    return {"score": _token_overlap(response, expected)}


def _token_overlap(response: str, expected: str) -> float:
    response_tokens = _tokens(response)
    expected_tokens = _tokens(expected)
    if not expected_tokens:
        return 0.0
    return len(response_tokens & expected_tokens) / float(len(expected_tokens))


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", value.lower()) if len(token) > 2}


def _coerce_float_metrics(metrics: dict[Any, Any]) -> dict[str, float]:
    coerced: dict[str, float] = {}
    for key, value in metrics.items():
        try:
            coerced[str(key)] = float(value)
        except (TypeError, ValueError):
            continue
    return coerced
