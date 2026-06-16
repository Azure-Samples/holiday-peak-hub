"""Data contracts for Agentic Setup Benchmark production-workload bundles."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ASBCoordinate(StrEnum):
    """Supported setup coordinates for ASB v1."""

    RETRIEVAL_DEPTH = "retrieval_depth"
    MEMORY_POLICY = "memory_policy"
    TOOL_BUDGET = "tool_budget"
    TOKEN_BUDGET = "token_budget"
    TOPOLOGY_POLICY = "topology_policy"
    HITL_POLICY = "hitl_policy"


class CostComponent(BaseModel):
    """One normalized cost component used by the ASB cost function."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    unit: str
    weight: float = Field(ge=0)
    baseline: float = Field(gt=0)
    source: str

    @field_validator("name", "unit", "source")
    @classmethod
    def _require_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be empty")
        return normalized


class CoordinateBound(BaseModel):
    """Bound for one production setup coordinate."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    coordinate: ASBCoordinate
    minimum: float
    maximum: float
    unit: str
    rationale: str

    @field_validator("unit", "rationale")
    @classmethod
    def _require_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be empty")
        return normalized

    @field_validator("maximum")
    @classmethod
    def _require_finite_maximum(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("maximum must be positive")
        return value


class CostModelConfig(BaseModel):
    """ASB cost model loaded from scenario configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1"] = "1"
    mode: Literal["synthetic-default", "telemetry-derived"] = "synthetic-default"
    currency: str = "USD"
    components: list[CostComponent]
    coordinate_bounds: list[CoordinateBound]
    assumptions: list[str] = Field(default_factory=list)

    @field_validator("components")
    @classmethod
    def _require_components(cls, value: list[CostComponent]) -> list[CostComponent]:
        if not value:
            raise ValueError("at least one cost component is required")
        return value

    @field_validator("coordinate_bounds")
    @classmethod
    def _require_bounds(cls, value: list[CoordinateBound]) -> list[CoordinateBound]:
        if not value:
            raise ValueError("at least one coordinate bound is required")
        for bound in value:
            if bound.minimum > bound.maximum:
                raise ValueError(f"minimum exceeds maximum for {bound.coordinate}")
        return value


class SetupPoint(BaseModel):
    """One setup candidate evaluated by the ASB protocol."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    setup_id: str
    retrieval_depth: int = Field(ge=0)
    memory_policy: int = Field(ge=0)
    tool_budget: int = Field(ge=0)
    token_budget: int = Field(ge=1)
    topology_policy: int = Field(ge=0)
    hitl_policy: int = Field(ge=0)

    @field_validator("setup_id")
    @classmethod
    def _require_setup_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("setup_id must not be empty")
        return normalized

    def coordinate_value(self, coordinate: ASBCoordinate) -> float:
        """Return a coordinate value by ASB coordinate enum."""

        return float(getattr(self, coordinate.value))


class ScenarioRequest(BaseModel):
    """Public-safe retail request used by ASB local runs."""

    model_config = ConfigDict(frozen=True, extra="allow")

    request_id: str
    domain: str
    query: str
    expected_behavior: str
    expected_agents: list[str] = Field(default_factory=list)
    complexity: Literal["low", "medium", "high"] = "medium"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("request_id", "domain", "query", "expected_behavior")
    @classmethod
    def _require_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be empty")
        return normalized


class ASBRunManifest(BaseModel):
    """Manifest for a generated ASB bundle."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1"] = "1"
    workload: str
    issue: str
    generated_at: str
    source: str
    data_policy: str
    cost_model_mode: str
    request_count: int = Field(ge=0)
    setup_count: int = Field(ge=0)
    topology_node_count: int = Field(ge=0)
    topology_edge_count: int = Field(ge=0)
    artifacts: dict[str, str]
    hashes: dict[str, str]
