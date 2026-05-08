"""Evaluation runners with optional Azure AI Evaluation integration."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any, Callable

from .dataset_loader import DatasetLoader
from .foundry_evaluators import (
    EvaluationBackendUnavailable,
    EvaluatorStrategy,
    LocalEvaluatorStrategy,
    select_evaluator_strategy,
)
from .models import EvalCase, EvalConfig


@dataclass(frozen=True)
class EvaluationRunResult:
    """Normalized output for evaluation execution."""

    status: str
    backend: str
    metrics: dict[str, Any]
    details: dict[str, Any]

    def model_dump(self) -> dict[str, Any]:
        """Return a JSON-friendly representation for API responses."""

        return asdict(self)


@dataclass(frozen=True)
class _EvaluationExecution:
    status: str
    backend: str
    metrics: dict[str, Any]
    details: dict[str, Any]


class BaseEvaluationRunner(ABC):
    """Template Method base class for evaluation execution."""

    async def run(self, *, run_name: str = "default") -> EvaluationRunResult:
        """Run the evaluation lifecycle from load to normalized result."""

        cases = await self.load_dataset()
        strategy = self.select_evaluator_strategy()
        execution = await self.execute(strategy=strategy, cases=cases, run_name=run_name)
        return self.collect_results(execution=execution, run_name=run_name, cases=cases)

    @abstractmethod
    async def load_dataset(self) -> list[EvalCase]:
        """Load evaluation input cases."""

    @abstractmethod
    def select_evaluator_strategy(self) -> EvaluatorStrategy:
        """Select an evaluator backend strategy."""

    @abstractmethod
    async def execute(
        self,
        *,
        strategy: EvaluatorStrategy,
        cases: list[EvalCase],
        run_name: str,
    ) -> _EvaluationExecution:
        """Execute the selected evaluator backend."""

    def collect_results(
        self,
        *,
        execution: _EvaluationExecution,
        run_name: str,
        cases: list[EvalCase],
    ) -> EvaluationRunResult:
        """Normalize execution output.

        # No GoF pattern applies — final data normalization step in the
        Template Method pipeline.
        """

        details = dict(execution.details)
        details.setdefault("run_name", run_name)
        details.setdefault("case_count", len(cases))
        return EvaluationRunResult(
            status=execution.status,
            backend=execution.backend,
            metrics=execution.metrics,
            details=details,
        )


class ConfiguredEvaluationRunner(BaseEvaluationRunner):
    """Evaluation runner backed by `.foundry/eval-config.yaml`."""

    def __init__(
        self,
        *,
        loader: DatasetLoader,
        config: EvalConfig | None = None,
        prefer_foundry: bool = True,
    ) -> None:
        self.loader = loader
        self.config = config or loader.load_config()
        self.prefer_foundry = prefer_foundry

    @classmethod
    def from_foundry_root(
        cls,
        foundry_root: str,
        *,
        prefer_foundry: bool = True,
    ) -> "ConfiguredEvaluationRunner":
        """Build a configured runner from a `.foundry` directory."""

        loader = DatasetLoader(foundry_root)
        return cls(loader=loader, prefer_foundry=prefer_foundry)

    async def load_dataset(self) -> list[EvalCase]:
        return self.loader.load_cases(self.config)

    def select_evaluator_strategy(self) -> EvaluatorStrategy:
        return select_evaluator_strategy(
            evaluators=self.config.evaluators,
            prefer_foundry=self.prefer_foundry,
        )

    async def execute(
        self,
        *,
        strategy: EvaluatorStrategy,
        cases: list[EvalCase],
        run_name: str,
    ) -> _EvaluationExecution:
        try:
            metrics = await strategy.evaluate(cases, run_name=run_name)
            return _EvaluationExecution(
                status="ok",
                backend=strategy.backend_name,
                metrics=metrics,
                details={"run_name": run_name, "agent_name": self.config.agent_name},
            )
        except EvaluationBackendUnavailable as exc:
            fallback = LocalEvaluatorStrategy(self.config.evaluators)
            metrics = await fallback.evaluate(cases, run_name=run_name)
            return _EvaluationExecution(
                status="ok",
                backend=fallback.backend_name,
                metrics=metrics,
                details={
                    "run_name": run_name,
                    "agent_name": self.config.agent_name,
                    "reason": str(exc),
                },
            )
        except Exception as exc:  # pylint: disable=broad-except
            fallback = LocalEvaluatorStrategy(self.config.evaluators)
            metrics = await fallback.evaluate(cases, run_name=run_name)
            return _EvaluationExecution(
                status="degraded",
                backend=fallback.backend_name,
                metrics=metrics,
                details={
                    "run_name": run_name,
                    "agent_name": self.config.agent_name,
                    "reason": str(exc),
                },
            )


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
