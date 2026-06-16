"""Generate the Holiday Peak Hub ASB v1 production-like bundle."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LIB_SRC = REPO_ROOT / "lib" / "src"
if str(LIB_SRC) not in sys.path:
    sys.path.insert(0, str(LIB_SRC))

from holiday_peak_lib.evaluation import (  # noqa: E402
    build_cost_source,
    evaluate_setup_surface,
    export_claim_map,
    extract_topology,
    load_cost_model,
    load_requests,
    load_setup_grid,
    refresh_manifest_hashes,
    write_cost_provenance,
    write_quadratic_support,
    write_setup_artifacts,
    write_topology_artifacts,
)
from holiday_peak_lib.evaluation.claim_map import write_bundle_manifests  # noqa: E402
from holiday_peak_lib.evaluation.falsification import write_falsification  # noqa: E402


def parse_args() -> argparse.Namespace:
    """Parse ASB runner command-line options."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", required=True, help="ASB scenario directory")
    parser.add_argument("--output-dir", required=True, help="Generated bundle output directory")
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="Repository root")
    return parser.parse_args()


def main() -> int:
    """Run the ASB generation pipeline."""

    args = parse_args()
    scenario_dir = Path(args.scenario).resolve()
    output_dir = Path(args.output_dir).resolve()
    repo_root = Path(args.repo_root).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    graph = extract_topology(repo_root)
    requests = load_requests(scenario_dir / "datasets")
    setups = load_setup_grid(scenario_dir / "setup-grid.yaml")
    cost_config = load_cost_model(scenario_dir / "cost-model.yaml")
    cost_source = build_cost_source(
        cost_config,
        request_count=len(requests),
        topology_fanout=graph.metrics()["average_out_degree"],
    )
    rows = evaluate_setup_surface(setups, requests, graph, cost_config, cost_source)

    write_topology_artifacts(graph, output_dir)
    write_cost_provenance(cost_config, output_dir / "cost-provenance.json")
    write_setup_artifacts(rows, output_dir)
    write_quadratic_support(output_dir / "grid-search.csv", output_dir)
    write_falsification(
        output_dir / "grid-search.csv",
        scenario_dir / "falsification-matrix.yaml",
        output_dir,
    )
    export_claim_map(output_dir)
    write_bundle_manifests(
        bundle_dir=output_dir,
        scenario_dir=scenario_dir,
        request_count=len(requests),
        setup_count=len(setups),
        graph=graph,
        cost_config=cost_config,
    )
    refresh_manifest_hashes(output_dir)
    print(f"Generated ASB bundle at {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
