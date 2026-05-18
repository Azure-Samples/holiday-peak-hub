"""Validate Foundry portal-tracking manifests for direct-model agents."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
APPS_README = REPO_ROOT / "apps" / "README.md"
AGENT_ROW_RE = re.compile(r"^\| `([^`]+)` \| Agent service \| ([^|]+) \|$")

REQUIRED_AGENT_ENV_VARS = {
    "PROJECT_ENDPOINT",
    "PROJECT_NAME",
    "MODEL_DEPLOYMENT_NAME_FAST",
    "MODEL_DEPLOYMENT_NAME_RICH",
    "FOUNDRY_AGENT_NAME_FAST",
    "FOUNDRY_AGENT_NAME_RICH",
    "REDIS_HOST",
    "REDIS_URL",
    "COSMOS_ACCOUNT_URI",
    "COSMOS_DATABASE",
    "COSMOS_CONTAINER",
    "BLOB_ACCOUNT_URL",
    "BLOB_CONTAINER",
    "EVENT_HUB_NAMESPACE",
    "KEY_VAULT_URI",
    "APPLICATIONINSIGHTS_CONNECTION_STRING",
}
REQUIRED_EVALUATION_SUITE_TAGS = {
    "tier": "smoke",
    "purpose": "portal-tracking",
    "stage": "seed",
}
FORBIDDEN_DUAL_RUNTIME_TOKENS = (
    "hosted_main.py",
    "agent.hosted.yaml",
    "template.kind: hosted",
    "AIProjectClient.agents.create_version",
    "entrypoint.sh",
    "8088",
    "second runtime",
)
BASE_DIRECT_MODEL_PROTOCOLS = {"fastapi-rest": "1.0.0", "mcp": "1.0.0"}


# No GoF pattern applies: this is a deterministic metadata contract test.
def _agent_services() -> dict[str, str]:
    agents: dict[str, str] = {}
    for line in APPS_README.read_text(encoding="utf-8").splitlines():
        match = AGENT_ROW_RE.match(line)
        if match:
            agents[match.group(1)] = match.group(2).strip()
    return agents


def _load_yaml(path: Path) -> dict[str, object]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"{path} must contain a YAML mapping"
    return data


def test_apps_readme_declares_twenty_six_active_agents() -> None:
    assert len(_agent_services()) == 26


@pytest.mark.parametrize("service,purpose", sorted(_agent_services().items()))
def test_direct_model_agent_has_foundry_portal_tracking_manifests(
    service: str, purpose: str
) -> None:
    app_dir = REPO_ROOT / "apps" / service
    agent_manifest_path = app_dir / "agent.yaml"
    metadata_path = app_dir / ".foundry" / "agent-metadata.yaml"

    assert agent_manifest_path.is_file()
    assert metadata_path.is_file()

    agent_text = agent_manifest_path.read_text(encoding="utf-8")
    metadata_text = metadata_path.read_text(encoding="utf-8")
    assert agent_text.isascii()
    assert metadata_text.isascii()
    assert "priority:" not in metadata_text
    for token in FORBIDDEN_DUAL_RUNTIME_TOKENS:
        assert token not in agent_text
        assert token not in metadata_text

    agent_manifest = _load_yaml(agent_manifest_path)
    assert agent_manifest["name"] == service
    assert purpose in str(agent_manifest["description"])

    metadata = agent_manifest["metadata"]
    assert isinstance(metadata, dict)
    assert metadata["trackingOnly"] is True
    assert metadata["runtime"] == "fastapi-direct-model"
    assert "Foundry Portal Tracking" in metadata["tags"]
    assert "Direct Model" in metadata["tags"]

    template = agent_manifest["template"]
    assert isinstance(template, dict)
    assert template["kind"] == "direct-model"
    protocols = {entry["protocol"]: entry["version"] for entry in template["protocols"]}
    assert BASE_DIRECT_MODEL_PROTOCOLS.items() <= protocols.items()
    if service == "inventory-health-check":
        assert protocols["responses"] == "1.0.0"
    else:
        assert protocols == BASE_DIRECT_MODEL_PROTOCOLS

    env_vars = {entry["name"]: entry["value"] for entry in template["environment_variables"]}
    assert REQUIRED_AGENT_ENV_VARS <= env_vars.keys()
    for name in REQUIRED_AGENT_ENV_VARS:
        assert env_vars[name] == f"${{{name}}}"

    foundry_metadata = _load_yaml(metadata_path)
    assert "testCases" not in foundry_metadata
    assert foundry_metadata["defaultEnvironment"] == "dev"

    environments = foundry_metadata["environments"]
    assert isinstance(environments, dict)
    dev_environment = environments["dev"]
    assert isinstance(dev_environment, dict)
    assert "testCases" not in dev_environment
    assert dev_environment["projectEndpoint"] == "${PROJECT_ENDPOINT}"
    assert dev_environment["agentName"] == service
    assert dev_environment["azureContainerRegistry"] == "${AZURE_CONTAINER_REGISTRY}"

    observability = dev_environment["observability"]
    assert observability["applicationInsightsConnectionString"] == (
        "${APPLICATIONINSIGHTS_CONNECTION_STRING}"
    )

    evaluation_suites = dev_environment["evaluationSuites"]
    assert isinstance(evaluation_suites, list)
    assert evaluation_suites
    for evaluation_suite in evaluation_suites:
        assert isinstance(evaluation_suite, dict)
        assert "priority" not in evaluation_suite
        tags = evaluation_suite["tags"]
        assert isinstance(tags, dict)
        assert REQUIRED_EVALUATION_SUITE_TAGS.items() <= tags.items()


def test_inventory_health_check_has_no_foundry_managed_hosted_manifest() -> None:
    app_dir = REPO_ROOT / "apps" / "inventory-health-check"
    assert not (app_dir / "agent.hosted.yaml").exists()
    assert not (app_dir / "agent.manifest.yaml").exists()

    agent_text = (app_dir / "agent.yaml").read_text(encoding="utf-8")
    assert "kind: hosted" not in agent_text
    assert "AIProjectClient.agents.create_version" not in agent_text
