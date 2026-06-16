"""Claim-map export and validation helpers for ASB bundles."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .asb_models import ASBRunManifest
from .catalog_topology import TopologyGraph
from .cost_model import CostModelConfig

EXPECTED_ARTIFACTS = (
    "bundle.json",
    "manifest.json",
    "dataset-manifest.json",
    "model-manifest.json",
    "cost-provenance.json",
    "catalog-topology.json",
    "topology-metrics.csv",
    "grid-search.csv",
    "holdout.csv",
    "pareto.csv",
    "qlst-scalar.csv",
    "qlst-multivariate.csv",
    "falsification.csv",
    "claim-map.yaml",
)


def export_claim_map(bundle_dir: Path | str) -> dict[str, Any]:
    """Write and return the ASB claim map for generated artifacts."""

    target_dir = Path(bundle_dir)
    payload = {
        "schema_version": "1",
        "workload": "holiday-peak-hub-asb-v1",
        "claims": [
            {
                "id": "C1-COST-BOUNDARY-PRODUCTION-LIKE",
                "status": "supported",
                "artifacts": ["cost-provenance.json", "grid-search.csv"],
                "statement": "The production-like setup space has finite coordinate bounds and a declared cost function.",
            },
            {
                "id": "C3-PRODUCTION-LIKE-TOPOLOGY",
                "status": "supported",
                "artifacts": ["catalog-topology.json", "topology-metrics.csv"],
                "statement": "The API and agent topology is extracted from Holiday Peak Hub repository surfaces.",
            },
            {
                "id": "C7-PRODUCTION-LIKE-WORKLOAD",
                "status": "supported",
                "artifacts": [
                    "bundle.json",
                    "grid-search.csv",
                    "holdout.csv",
                    "qlst-multivariate.csv",
                    "falsification.csv",
                ],
                "statement": "The ASB protocol runs on a public-safe Holiday Peak Hub retail workload bundle.",
            },
        ],
    }
    (target_dir / "claim-map.yaml").write_text(
        yaml.safe_dump(payload, sort_keys=False), encoding="utf-8"
    )
    return payload


def write_bundle_manifests(
    *,
    bundle_dir: Path | str,
    scenario_dir: Path | str,
    request_count: int,
    setup_count: int,
    graph: TopologyGraph,
    cost_config: CostModelConfig,
) -> ASBRunManifest:
    """Write dataset, model, and run manifests for a generated ASB bundle."""

    target_dir = Path(bundle_dir)
    scenario_path = Path(scenario_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    dataset_manifest = {
        "schema_version": "1",
        "source": str(scenario_path),
        "policy": "public-safe synthetic retail requests; no customer data",
        "request_count": request_count,
        "datasets": sorted(path.name for path in (scenario_path / "datasets").glob("*.jsonl")),
    }
    model_manifest = {
        "schema_version": "1",
        "execution": "local-deterministic",
        "models": [],
        "note": "No hosted model inference is required for the reproducible ASB bundle.",
    }
    (target_dir / "dataset-manifest.json").write_text(
        json.dumps(dataset_manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (target_dir / "model-manifest.json").write_text(
        json.dumps(model_manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    hashes = _hash_existing_artifacts(target_dir)
    artifact_map = {
        artifact: artifact for artifact in EXPECTED_ARTIFACTS if (target_dir / artifact).exists()
    }
    manifest = ASBRunManifest(
        workload="holiday-peak-hub-asb-v1",
        issue="1153",
        generated_at=datetime.now(timezone.utc).isoformat(),
        source=str(scenario_path),
        data_policy="public-safe synthetic retail requests",
        cost_model_mode=cost_config.mode,
        request_count=request_count,
        setup_count=setup_count,
        topology_node_count=int(graph.metrics()["node_count"]),
        topology_edge_count=int(graph.metrics()["edge_count"]),
        artifacts=artifact_map,
        hashes=hashes,
    )
    (target_dir / "manifest.json").write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return manifest


def validate_bundle(bundle_dir: Path | str) -> dict[str, Any]:
    """Validate that a generated ASB bundle contains expected artifacts."""

    target_dir = Path(bundle_dir)
    missing = [artifact for artifact in EXPECTED_ARTIFACTS if not (target_dir / artifact).exists()]
    empty = [
        artifact
        for artifact in EXPECTED_ARTIFACTS
        if (target_dir / artifact).exists() and (target_dir / artifact).stat().st_size == 0
    ]
    manifest_path = target_dir / "manifest.json"
    manifest_valid = False
    if manifest_path.exists() and manifest_path.stat().st_size > 0:
        ASBRunManifest.model_validate(json.loads(manifest_path.read_text(encoding="utf-8")))
        manifest_valid = True
    return {
        "passes": not missing and not empty and manifest_valid,
        "missing": missing,
        "empty": empty,
        "manifest_valid": manifest_valid,
    }


def refresh_manifest_hashes(bundle_dir: Path | str) -> None:
    """Refresh manifest hashes after all artifacts have been written."""

    target_dir = Path(bundle_dir)
    manifest_path = target_dir / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["artifacts"] = {
        artifact: artifact for artifact in EXPECTED_ARTIFACTS if (target_dir / artifact).exists()
    }
    payload["hashes"] = _hash_existing_artifacts(target_dir)
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _hash_existing_artifacts(bundle_dir: Path) -> dict[str, str]:
    return {
        artifact: _sha256(bundle_dir / artifact)
        for artifact in EXPECTED_ARTIFACTS
        if artifact != "manifest.json" and (bundle_dir / artifact).exists()
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as artifact_file:
        for chunk in iter(lambda: artifact_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
