"""Quality drift detection for continuous agent evaluation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .eval_runner import EvaluationRunResult
from .models import DriftReport, EvalBaseline, EvalConfig, EvalSeverity

_CRITICAL_DEFICIT = 0.25


class DriftDetector:
    """Compare evaluation metrics with configured thresholds and baselines.

    Pattern: Observer — callers can treat the emitted `DriftReport` as the
    signal that downstream observers (self-healing, CI, monitoring) react to.
    """

    def __init__(self, config: EvalConfig) -> None:
        self.config = config
        self._failure_counts: dict[str, int] = {}
        self._last_signal_at: dict[str, datetime] = {}

    def detect(
        self,
        result: EvaluationRunResult,
        *,
        baseline: EvalBaseline | None = None,
        run_name: str = "default",
    ) -> DriftReport | None:
        """Return a drift report when a run breaches configured guardrails."""

        current_metrics = _float_metrics(result.metrics)
        baseline_metrics = baseline.metrics if baseline is not None else {}
        breached_thresholds, drift_metrics = self._find_breaches(
            current_metrics=current_metrics,
            baseline_metrics=baseline_metrics,
        )

        if not breached_thresholds:
            self._failure_counts[self.config.agent_name] = 0
            return None

        failure_count = self._failure_counts.get(self.config.agent_name, 0) + 1
        self._failure_counts[self.config.agent_name] = failure_count
        if failure_count < self.config.consecutive_failure_window:
            return None
        if self._is_rate_limited():
            return None

        severity = (
            EvalSeverity.CRITICAL
            if any(abs(value) >= _CRITICAL_DEFICIT for value in drift_metrics.values())
            else EvalSeverity.WARNING
        )
        report = DriftReport(
            agent_name=self.config.agent_name,
            run_name=run_name,
            severity=severity,
            breached_thresholds=breached_thresholds,
            drift_metrics=drift_metrics,
            current_metrics=current_metrics,
            baseline_metrics=baseline_metrics,
            consecutive_failures=failure_count,
        )
        self._last_signal_at[self.config.agent_name] = datetime.now(timezone.utc)
        return report

    def _find_breaches(
        self,
        *,
        current_metrics: dict[str, float],
        baseline_metrics: dict[str, float],
    ) -> tuple[list[str], dict[str, float]]:
        breaches: list[str] = []
        drift_metrics: dict[str, float] = {}

        for metric_name, threshold in self.config.thresholds.items():
            current = current_metrics.get(metric_name)
            if current is None:
                continue
            if current < threshold:
                breaches.append(metric_name)
                drift_metrics[metric_name] = current - threshold

        for metric_name, baseline_value in baseline_metrics.items():
            current = current_metrics.get(metric_name)
            if current is None or baseline_value <= 0:
                continue
            if current < baseline_value:
                baseline_key = f"{metric_name}:baseline"
                if baseline_key not in breaches:
                    breaches.append(baseline_key)
                drift_metrics[baseline_key] = current - baseline_value

        return breaches, drift_metrics

    def _is_rate_limited(self) -> bool:
        if self.config.rate_limit_hours <= 0:
            return False
        last_signal = self._last_signal_at.get(self.config.agent_name)
        if last_signal is None:
            return False
        window = timedelta(hours=self.config.rate_limit_hours)
        return datetime.now(timezone.utc) - last_signal < window


def _float_metrics(metrics: dict[str, Any]) -> dict[str, float]:
    """Coerce numeric metrics to floats.

    # No GoF pattern applies — simple data normalization utility.
    """

    normalized: dict[str, float] = {}
    for key, value in metrics.items():
        try:
            normalized[key] = float(value)
        except (TypeError, ValueError):
            continue
    return normalized
