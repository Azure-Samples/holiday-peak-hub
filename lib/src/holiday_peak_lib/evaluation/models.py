"""Shared data contracts for agent evaluation and quality drift monitoring."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from holiday_peak_lib.self_healing.models import FailureSignal, SurfaceType
from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> datetime:
    """Return an aware UTC timestamp."""

    return datetime.now(timezone.utc)


class EvalSeverity(StrEnum):
    """Severity levels emitted by quality drift detection."""

    WARNING = "warning"
    CRITICAL = "critical"


class EvalModelTier(StrEnum):
    """Model routing tier expected for an evaluation case."""

    SLM = "slm"
    LLM = "llm"
    ANY = "any"


class EvalCase(BaseModel):
    """Single query/response record consumed by Foundry and local evaluators."""

    model_config = ConfigDict(frozen=True, extra="allow")

    id: str = Field(default_factory=lambda: str(uuid4()))
    query: str
    expected_behavior: str
    expected_model_tier: EvalModelTier = EvalModelTier.ANY
    response: str | None = None
    context: str | None = None
    ground_truth: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("query", "expected_behavior")
    @classmethod
    def _require_non_empty_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be empty")
        return normalized

    def to_foundry_item(self) -> dict[str, Any]:
        """Return JSON-serializable fields for Foundry JSONL evaluation input.

        Pattern: Adapter — converts the internal Pydantic contract to the
        external Foundry data item shape without leaking file-format details to
        callers.
        """

        return self.model_dump(mode="json", exclude_none=True)


class EvalConfig(BaseModel):
    """Per-agent evaluation configuration loaded from `.foundry/eval-config.yaml`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = "1"
    agent_name: str
    evaluators: list[str] = Field(default_factory=lambda: ["relevance"])
    dataset_path: str = "datasets/seed.jsonl"
    baseline_path: str | None = "results/baseline.json"
    thresholds: dict[str, float] = Field(default_factory=dict)
    model_targets: list[EvalModelTier] = Field(
        default_factory=lambda: [EvalModelTier.SLM, EvalModelTier.LLM]
    )
    foundry_project_endpoint: str | None = None
    foundry_agent_name: str | None = None
    foundry_model_deployment_name: str | None = None
    publish_events: bool = False
    consecutive_failure_window: int = 3
    rate_limit_hours: float = 24.0
    foundry_root: Path | None = None

    @field_validator("agent_name")
    @classmethod
    def _require_agent_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("agent_name must not be empty")
        return normalized

    @field_validator("evaluators")
    @classmethod
    def _require_evaluators(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value if item.strip()]
        if not normalized:
            raise ValueError("at least one evaluator is required")
        return normalized

    @field_validator("consecutive_failure_window")
    @classmethod
    def _require_positive_failure_window(cls, value: int) -> int:
        if value < 1:
            raise ValueError("consecutive_failure_window must be >= 1")
        return value

    @field_validator("rate_limit_hours")
    @classmethod
    def _require_non_negative_rate_limit(cls, value: float) -> float:
        if value < 0:
            raise ValueError("rate_limit_hours must be >= 0")
        return value


class EvalBaseline(BaseModel):
    """Stored quality baseline for one agent evaluation dataset."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    agent_name: str
    metrics: dict[str, float]
    dataset_version: str = "seed"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class DriftReport(BaseModel):
    """Quality drift report produced from a run and baseline comparison."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    agent_name: str
    run_name: str
    severity: EvalSeverity
    breached_thresholds: list[str]
    drift_metrics: dict[str, float]
    current_metrics: dict[str, float]
    baseline_metrics: dict[str, float] = Field(default_factory=dict)
    detected_at: datetime = Field(default_factory=utc_now)
    consecutive_failures: int = 1

    @property
    def is_critical(self) -> bool:
        """Return whether this drift report requires critical handling."""

        return self.severity == EvalSeverity.CRITICAL


class EvaluationDriftSignal(FailureSignal):
    """Self-healing-compatible signal for manual-only quality drift escalation."""

    surface: SurfaceType = SurfaceType.EVALUATION
    component: str = "evaluation"
    status_code: int | None = None
    error_type: str = "QualityDrift"
    error_message: str = "Agent evaluation quality drift detected"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_report(cls, report: DriftReport) -> "EvaluationDriftSignal":
        """Create a failure signal from a drift report.

        Pattern: Factory Method — centralizes conversion from evaluation-domain
        data to the self-healing incident input contract.
        """

        return cls(
            service_name=report.agent_name,
            metadata={
                "incident_class": "quality_drift",
                "severity": report.severity.value,
                "breached_thresholds": report.breached_thresholds,
                "drift_metrics": report.drift_metrics,
                "current_metrics": report.current_metrics,
                "baseline_metrics": report.baseline_metrics,
                "run_name": report.run_name,
                "detected_at": report.detected_at.isoformat(),
                "consecutive_failures": report.consecutive_failures,
            },
        )


class EvaluationResultEvent(BaseModel):
    """Event payload for the `agent-evaluation-results` topic."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1"] = "1"
    topic: Literal["agent-evaluation-results"] = "agent-evaluation-results"
    agent_name: str
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    run_name: str
    timestamp: datetime = Field(default_factory=utc_now)
    backend: str
    status: str
    metrics: dict[str, float]
    drift_detected: bool = False
    drift_report: DriftReport | None = None
    details: dict[str, Any] = Field(default_factory=dict)
