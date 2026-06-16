"""Tests for ASB production-like evaluation support."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from holiday_peak_lib.evaluation import (
    build_cost_source,
    evaluate_setup_surface,
    extract_topology,
    load_cost_model,
    load_requests,
    load_setup_grid,
    validate_bundle,
    validate_compact_bounds,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIO_DIR = REPO_ROOT / "tests" / "evaluation" / "asb_v1"


def test_cost_model_defines_compact_setup_region() -> None:
    config = load_cost_model(SCENARIO_DIR / "cost-model.yaml")

    result = validate_compact_bounds(config)

    assert result["passes"] is True
    assert result["coordinate_count"] == 6


def test_topology_extraction_uses_surface_catalog_and_agent_client() -> None:
    graph = extract_topology(REPO_ROOT)
    metrics = graph.metrics()
    edge_targets = {edge["target"] for edge in graph.edges if edge["kind"] == "agent-client"}

    assert metrics["agent_count"] == 26.0
    assert metrics["hosted_agent_count"] == 10.0
    assert "ecommerce-catalog-search" in edge_targets
    assert "inventory-health-check" in edge_targets


def test_setup_surface_selects_one_candidate() -> None:
    graph = extract_topology(REPO_ROOT)
    requests = load_requests(SCENARIO_DIR / "datasets")
    setups = load_setup_grid(SCENARIO_DIR / "setup-grid.yaml")
    cost_config = load_cost_model(SCENARIO_DIR / "cost-model.yaml")
    source = build_cost_source(
        cost_config,
        request_count=len(requests),
        topology_fanout=graph.metrics()["average_out_degree"],
    )

    rows = evaluate_setup_surface(setups, requests, graph, cost_config, source)

    assert len(rows) == 3
    assert sum(1 for row in rows if row.selected) == 1
    assert all(row.risk >= 0 for row in rows)


def test_runner_generates_valid_bundle(tmp_path: Path) -> None:
    output_dir = tmp_path / "bundle"
    runner = REPO_ROOT / "scripts" / "evaluation" / "run_agentic_setup_benchmark.py"

    completed = subprocess.run(
        [
            sys.executable,
            str(runner),
            "--scenario",
            str(SCENARIO_DIR),
            "--output-dir",
            str(output_dir),
            "--repo-root",
            str(REPO_ROOT),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Generated ASB bundle" in completed.stdout
    assert validate_bundle(output_dir)["passes"] is True
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["request_count"] == 9
    assert manifest["setup_count"] == 3
