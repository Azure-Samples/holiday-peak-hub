"""Generate ASB setup-surface artifacts for Holiday Peak Hub."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .asb_models import ScenarioRequest, SetupPoint
from .catalog_topology import TopologyGraph
from .cost_model import CostModelConfig, CostSource, evaluate_cost


@dataclass(frozen=True)
class SetupEvaluation:
    """Evaluation row for one setup point."""

    setup: SetupPoint
    benefit: float
    cost: float
    risk: float
    selected: bool = False

    def to_row(self) -> dict[str, Any]:
        """Convert the setup evaluation into a CSV row."""

        row = self.setup.model_dump(mode="json")
        row.update(
            {
                "benefit": round(self.benefit, 6),
                "cost": round(self.cost, 6),
                "risk": round(self.risk, 6),
                "selected": self.selected,
            }
        )
        return row


def load_setup_grid(path: Path | str) -> list[SetupPoint]:
    """Load setup points from YAML."""

    raw_payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw_payload, dict):
        raise ValueError("setup grid must be a mapping")
    points = raw_payload.get("setups", [])
    if not isinstance(points, list) or not points:
        raise ValueError("setup grid must contain at least one setup")
    return [SetupPoint.model_validate(point) for point in points]


def load_requests(dataset_dir: Path | str) -> list[ScenarioRequest]:
    """Load public-safe ASB request JSONL files."""

    requests: list[ScenarioRequest] = []
    for dataset_path in sorted(Path(dataset_dir).glob("*.jsonl")):
        with dataset_path.open("r", encoding="utf-8") as dataset_file:
            for line_number, raw_line in enumerate(dataset_file, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid JSONL at {dataset_path}:{line_number}: {exc.msg}"
                    ) from exc
                requests.append(ScenarioRequest.model_validate(payload))
    if not requests:
        raise ValueError(f"No ASB requests found in {dataset_dir}")
    return requests


def evaluate_setup_surface(
    setups: list[SetupPoint],
    requests: list[ScenarioRequest],
    graph: TopologyGraph,
    cost_config: CostModelConfig,
    cost_source: CostSource,
) -> list[SetupEvaluation]:
    """Evaluate setup candidates with a deterministic local ASB scoring model."""

    topology_metrics = graph.metrics()
    fanout = topology_metrics["average_out_degree"]
    complexity_bonus = _average_complexity(requests)
    rows: list[SetupEvaluation] = []
    for setup in setups:
        cost = evaluate_cost(cost_config, cost_source, setup)
        benefit = _estimate_benefit(setup, fanout=fanout, complexity_bonus=complexity_bonus)
        risk = max(0.0, 1.0 - benefit) + cost
        rows.append(SetupEvaluation(setup=setup, benefit=benefit, cost=cost, risk=risk))
    selected_id = min(rows, key=lambda row: row.risk).setup.setup_id
    return [
        SetupEvaluation(
            setup=row.setup,
            benefit=row.benefit,
            cost=row.cost,
            risk=row.risk,
            selected=row.setup.setup_id == selected_id,
        )
        for row in rows
    ]


def write_setup_artifacts(rows: list[SetupEvaluation], output_dir: Path | str) -> None:
    """Write grid-search, holdout, and pareto ASB artifacts."""

    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(target_dir / "grid-search.csv", [row.to_row() for row in rows])

    selected_rows = [row for row in rows if row.selected]
    _write_csv(target_dir / "holdout.csv", [row.to_row() for row in selected_rows])
    _write_csv(target_dir / "pareto.csv", [row.to_row() for row in _pareto_front(rows)])
    (target_dir / "bundle.json").write_text(
        json.dumps({"setups": [row.to_row() for row in rows]}, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _estimate_benefit(setup: SetupPoint, *, fanout: float, complexity_bonus: float) -> float:
    retrieval = min(setup.retrieval_depth / 8.0, 1.0) * 0.2
    memory = min(setup.memory_policy / 3.0, 1.0) * 0.16
    tools = min(setup.tool_budget / max(fanout * 2.0, 1.0), 1.0) * 0.2
    tokens = min(setup.token_budget / 8192.0, 1.0) * 0.18
    topology = min(setup.topology_policy / 3.0, 1.0) * 0.16
    hitl = min(setup.hitl_policy / 2.0, 1.0) * 0.1
    return min(0.98, 0.1 + retrieval + memory + tools + tokens + topology + hitl + complexity_bonus)


def _average_complexity(requests: list[ScenarioRequest]) -> float:
    values = {"low": 0.0, "medium": 0.03, "high": 0.06}
    return sum(values[request.complexity] for request in requests) / max(len(requests), 1)


def _pareto_front(rows: list[SetupEvaluation]) -> list[SetupEvaluation]:
    front: list[SetupEvaluation] = []
    for candidate in rows:
        dominated = any(
            other.cost <= candidate.cost
            and other.risk <= candidate.risk
            and (other.cost < candidate.cost or other.risk < candidate.risk)
            for other in rows
            if other is not candidate
        )
        if not dominated:
            front.append(candidate)
    return sorted(front, key=lambda row: (row.cost, row.risk))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
