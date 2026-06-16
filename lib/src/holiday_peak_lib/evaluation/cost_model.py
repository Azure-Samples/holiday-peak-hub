"""ASB cost function helpers for production-like setup boundaries."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import yaml

from .asb_models import ASBCoordinate, CostModelConfig, SetupPoint


class CostSource(Protocol):
    """Strategy interface for setup-cost estimation."""

    def estimate(self, setup: SetupPoint) -> dict[str, float]:
        """Estimate raw component values for a setup point."""


@dataclass(frozen=True)
class SyntheticCostSource:
    """Deterministic synthetic cost strategy for public-safe ASB bundles."""

    request_count: int
    topology_fanout: float

    def estimate(self, setup: SetupPoint) -> dict[str, float]:
        """Estimate synthetic production-like cost components."""

        request_scale = max(self.request_count, 1)
        return {
            "input_tokens": float(setup.token_budget * request_scale),
            "tool_calls": float(setup.tool_budget * request_scale * max(self.topology_fanout, 1.0)),
            "memory_ops": float(setup.memory_policy * request_scale * 2),
            "search_ops": float(setup.retrieval_depth * request_scale),
            "latency_ms": float(
                120
                + setup.token_budget * 0.08
                + setup.tool_budget * 45
                + setup.retrieval_depth * 18
                + setup.memory_policy * 12
                + setup.topology_policy * 28
                + setup.hitl_policy * 250
            ),
            "human_review_minutes": float(setup.hitl_policy * request_scale * 0.75),
        }


@dataclass(frozen=True)
class TelemetryCostSource:
    """Telemetry-derived cost strategy for future production runs."""

    component_values: dict[str, float]

    def estimate(self, _setup: SetupPoint) -> dict[str, float]:
        """Return externally supplied telemetry component values."""

        return dict(self.component_values)


def load_cost_model(path: Path | str) -> CostModelConfig:
    """Load an ASB cost model from YAML."""

    model_path = Path(path)
    raw_payload = yaml.safe_load(model_path.read_text(encoding="utf-8"))
    if not isinstance(raw_payload, dict):
        raise ValueError(f"Cost model must be a mapping: {model_path}")
    return CostModelConfig.model_validate(raw_payload)


def build_cost_source(
    config: CostModelConfig,
    *,
    request_count: int,
    topology_fanout: float,
    telemetry_values: dict[str, float] | None = None,
) -> CostSource:
    """Create a cost-source strategy for the configured mode."""

    if config.mode == "telemetry-derived":
        return TelemetryCostSource(telemetry_values or {})
    return SyntheticCostSource(request_count=request_count, topology_fanout=topology_fanout)


def evaluate_cost(config: CostModelConfig, source: CostSource, setup: SetupPoint) -> float:
    """Evaluate normalized ASB cost Phi for one setup point."""

    raw_values = source.estimate(setup)
    total = 0.0
    for component in config.components:
        raw_value = raw_values.get(component.name, 0.0)
        total += component.weight * (raw_value / component.baseline)
    return total


def validate_compact_bounds(config: CostModelConfig) -> dict[str, object]:
    """Check that the cost model defines finite coordinate boundaries."""

    coordinates = {bound.coordinate for bound in config.coordinate_bounds}
    missing = sorted(set(ASBCoordinate) - coordinates)
    invalid = [
        bound.coordinate.value
        for bound in config.coordinate_bounds
        if bound.minimum < 0 or bound.minimum > bound.maximum
    ]
    return {
        "passes": not missing and not invalid,
        "missing_coordinates": [coordinate.value for coordinate in missing],
        "invalid_bounds": invalid,
        "coordinate_count": len(config.coordinate_bounds),
    }


def write_cost_provenance(config: CostModelConfig, output_path: Path | str) -> None:
    """Write cost model provenance and theorem-boundary assumptions."""

    payload = {
        "schema_version": config.schema_version,
        "mode": config.mode,
        "currency": config.currency,
        "components": [component.model_dump(mode="json") for component in config.components],
        "coordinate_bounds": [bound.model_dump(mode="json") for bound in config.coordinate_bounds],
        "assumptions": config.assumptions,
        "assumption_check": validate_compact_bounds(config),
    }
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
