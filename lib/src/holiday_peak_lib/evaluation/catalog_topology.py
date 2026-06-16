"""Extract production-like agent/API topology for ASB bundles."""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class TopologyGraph:
    """Agent/API graph extracted from Holiday Peak Hub metadata."""

    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]

    def metrics(self) -> dict[str, float]:
        """Return simple graph metrics used by ASB cost and topology claims."""

        out_degree: dict[str, int] = {}
        for edge in self.edges:
            source = str(edge["source"])
            out_degree[source] = out_degree.get(source, 0) + 1
        agent_nodes = [node for node in self.nodes if node.get("kind") == "agent"]
        hosted_nodes = [node for node in agent_nodes if node.get("surface") == "hosted"]
        custom_nodes = [node for node in agent_nodes if node.get("surface") == "custom"]
        average_out_degree = sum(out_degree.values()) / max(len(out_degree), 1)
        return {
            "node_count": float(len(self.nodes)),
            "edge_count": float(len(self.edges)),
            "agent_count": float(len(agent_nodes)),
            "hosted_agent_count": float(len(hosted_nodes)),
            "custom_agent_count": float(len(custom_nodes)),
            "average_out_degree": float(average_out_degree),
        }

    def model_dump(self) -> dict[str, Any]:
        """Return a JSON-friendly graph payload."""

        return {"nodes": self.nodes, "edges": self.edges, "metrics": self.metrics()}


def extract_topology(repo_root: Path | str) -> TopologyGraph:
    """Extract the Holiday Peak Hub agent/API topology from repository files."""

    root = Path(repo_root).resolve()
    surface_payload = _load_surface_catalog(root / "apps" / "foundry-surfaces.yaml")
    nodes: list[dict[str, Any]] = [
        {"id": "apim", "kind": "gateway", "label": "Azure API Management"},
        {"id": "agc", "kind": "gateway", "label": "Application Gateway for Containers"},
        {"id": "aks", "kind": "runtime", "label": "Azure Kubernetes Service"},
        {"id": "crud-service", "kind": "service", "label": "CRUD Service"},
    ]
    edges: list[dict[str, Any]] = [
        {"source": "apim", "target": "agc", "kind": "traffic-path"},
        {"source": "agc", "target": "aks", "kind": "traffic-path"},
        {"source": "aks", "target": "crud-service", "kind": "hosts"},
    ]

    for surface_name, surface_data in _surface_sections(surface_payload).items():
        for agent_name in surface_data.get("agents", []) or []:
            nodes.append(
                {
                    "id": str(agent_name),
                    "kind": "agent",
                    "surface": surface_name,
                    "classification": surface_data.get("classification"),
                    "audience": surface_data.get("audience"),
                }
            )
            edges.append({"source": "aks", "target": str(agent_name), "kind": "hosts"})
            edges.append({"source": "apim", "target": str(agent_name), "kind": "agent-route"})

    agent_client_path = (
        root / "apps" / "crud-service" / "src" / "crud_service" / "integrations" / "agent_client.py"
    )
    for target_agent in _extract_agent_client_targets(agent_client_path):
        edges.append({"source": "crud-service", "target": target_agent, "kind": "agent-client"})

    return TopologyGraph(nodes=_dedupe_nodes(nodes), edges=_dedupe_edges(edges))


def write_topology_artifacts(graph: TopologyGraph, output_dir: Path | str) -> None:
    """Write topology JSON and CSV metrics artifacts."""

    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "catalog-topology.json").write_text(
        json.dumps(graph.model_dump(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    metrics = graph.metrics()
    metric_lines = ["metric,value"] + [f"{key},{value}" for key, value in metrics.items()]
    (target_dir / "topology-metrics.csv").write_text(
        "\n".join(metric_lines) + "\n",
        encoding="utf-8",
    )


def _load_surface_catalog(path: Path) -> dict[str, Any]:
    raw_payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw_payload, dict):
        raise ValueError(f"Surface catalog must be a mapping: {path}")
    return raw_payload


def _surface_sections(surface_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    sections = surface_payload.get("surfaces", {})
    if not isinstance(sections, dict):
        raise ValueError("surfaces must be a mapping")
    return {str(key): dict(value or {}) for key, value in sections.items()}


def _extract_agent_client_targets(agent_client_path: Path) -> list[str]:
    """Extract service names passed to AgentClient._resolve_agent_url."""

    if not agent_client_path.exists():
        return []
    tree = ast.parse(agent_client_path.read_text(encoding="utf-8"))
    targets: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "_resolve_agent_url" or len(node.args) < 2:
            continue
        target_arg = node.args[1]
        if isinstance(target_arg, ast.Constant) and isinstance(target_arg.value, str):
            targets.append(target_arg.value)
    return sorted(set(targets))


def _dedupe_nodes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for node in nodes:
        node_id = str(node["id"])
        if node_id in seen:
            continue
        seen.add(node_id)
        deduped.append(node)
    return deduped


def _dedupe_edges(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for edge in edges:
        key = (str(edge["source"]), str(edge["target"]), str(edge["kind"]))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(edge)
    return deduped
