"""Validate Foundry portal-tracking manifests for direct-model agents."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
APPS_README = REPO_ROOT / "apps" / "README.md"
FOUNDRY_SURFACE_REGISTRY = REPO_ROOT / "apps" / "foundry-surfaces.yaml"
AGENT_ROW_RE = re.compile(r"^\| `([^`]+)` \| Agent service \| ([^|]+) \|$")

EXPECTED_HOSTED_SURFACE_AGENTS = {
    "crm-support-assistance",
    "ecommerce-cart-intelligence",
    "ecommerce-catalog-search",
    "ecommerce-checkout-support",
    "ecommerce-order-status",
    "ecommerce-product-detail-enrichment",
    "inventory-health-check",
    "logistics-eta-computation",
    "logistics-returns-support",
    "truth-hitl",
}
EXPECTED_CUSTOM_SURFACE_AGENTS = {
    "crm-campaign-intelligence",
    "crm-profile-aggregation",
    "crm-segmentation-personalization",
    "inventory-alerts-triggers",
    "inventory-jit-replenishment",
    "inventory-reservation-validation",
    "logistics-carrier-selection",
    "logistics-route-issue-detection",
    "product-management-acp-transformation",
    "product-management-assortment-optimization",
    "product-management-consistency-validation",
    "product-management-normalization-classification",
    "search-enrichment-agent",
    "truth-enrichment",
    "truth-export",
    "truth-ingestion",
}

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
FORBIDDEN_TRACKING_MANIFEST_TOKENS = (
    "hosted_main.py",
    "entrypoint.sh",
    "second runtime",
)
HOSTED_SURFACE_MANIFEST_NAMES = ("agent.hosted.yaml", "agent.manifest.yaml")
BASE_DIRECT_MODEL_PROTOCOLS = {"fastapi-rest": "1.0.0", "mcp": "1.0.0"}
REQUIRED_HOSTED_ENV_VARS = {
    "HPH_AGENT_ID_FAST",
    "HPH_AGENT_ID_RICH",
    "PROJECT_ENDPOINT",
    "PROJECT_NAME",
    "MODEL_DEPLOYMENT_NAME_FAST",
    "MODEL_DEPLOYMENT_NAME_RICH",
    "HOLIDAY_PEAK_FOUNDRY_HOSTED",
    "UVICORN_PORT",
}
REQUIRED_HOSTED_DEPENDENCY = "agent-framework-foundry-hosting==1.0.0a260507"
REQUIRED_HOSTED_DEPENDENCY_NAME = "agent-framework-foundry-hosting"
REQUIRED_HOSTED_DEPENDENCY_SPECIFIER = "==1.0.0a260507"
FORBIDDEN_HOSTED_ENV_PREFIXES = ("FOUNDRY_", "AGENT_")


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


def _surface_registry() -> dict[str, object]:
    return _load_yaml(FOUNDRY_SURFACE_REGISTRY)


def _surface_agents(surface_name: str) -> set[str]:
    registry = _surface_registry()
    surfaces = registry["surfaces"]
    assert isinstance(surfaces, dict)
    surface = surfaces[surface_name]
    assert isinstance(surface, dict)
    agents = surface["agents"]
    assert isinstance(agents, list)
    return {str(agent) for agent in agents}


def test_apps_readme_declares_twenty_six_active_agents() -> None:
    assert len(_agent_services()) == 26


def test_foundry_surface_registry_matches_two_track_policy() -> None:
    registry = _surface_registry()
    policy = registry["policy"]
    assert isinstance(policy, dict)
    assert policy["productRuntime"] == "aks"
    assert policy["productTrafficPath"] == "APIM -> AGC -> AKS"
    assert policy["hostedManifest"] == "agent.hosted.yaml"
    assert policy["customMetadataPath"] == ".foundry/agent-metadata.yaml"

    hosted_agents = _surface_agents("hosted")
    custom_agents = _surface_agents("custom")

    assert hosted_agents == EXPECTED_HOSTED_SURFACE_AGENTS
    assert custom_agents == EXPECTED_CUSTOM_SURFACE_AGENTS
    assert hosted_agents.isdisjoint(custom_agents)
    assert hosted_agents | custom_agents == set(_agent_services())


@pytest.mark.parametrize("service", sorted(EXPECTED_HOSTED_SURFACE_AGENTS))
def test_hosted_surface_agents_have_foundry_hosted_manifest(service: str) -> None:
    app_dir = REPO_ROOT / "apps" / service
    manifest_path = app_dir / "agent.hosted.yaml"

    assert manifest_path.is_file()
    manifest_text = manifest_path.read_text(encoding="utf-8")
    assert manifest_text.isascii()
    for token in FORBIDDEN_TRACKING_MANIFEST_TOKENS:
        assert token not in manifest_text

    manifest = _load_yaml(manifest_path)
    assert manifest["name"] == service

    metadata = manifest["metadata"]
    assert isinstance(metadata, dict)
    surface = metadata["surface"]
    assert isinstance(surface, dict)
    assert surface["type"] == "hosted"
    assert surface["classification"] == "Hosted Agent"
    assert surface["audience"] == "public-human-facing"
    assert surface["productRuntime"] == "aks"
    assert surface["productTrafficPath"] == "APIM -> AGC -> AKS"
    assert surface["replacesProductRuntime"] is False

    template = manifest["template"]
    assert isinstance(template, dict)
    assert template["kind"] == "hosted"
    assert ".main:app" in template["startupCommand"]
    assert "--port 8088" in template["startupCommand"]
    protocols = {entry["protocol"]: entry["version"] for entry in template["protocols"]}
    assert protocols["responses"] == "1.0.0"

    env_vars = {entry["name"]: str(entry["value"]) for entry in template["environment_variables"]}
    assert REQUIRED_HOSTED_ENV_VARS <= env_vars.keys()
    assert env_vars["HOLIDAY_PEAK_FOUNDRY_HOSTED"] == "1"
    assert env_vars["UVICORN_PORT"] == "8088"
    for name in env_vars:
        assert not name.startswith(FORBIDDEN_HOSTED_ENV_PREFIXES)


@pytest.mark.parametrize("service", sorted(EXPECTED_HOSTED_SURFACE_AGENTS))
def test_hosted_surface_agents_include_responses_hosting_dependency(service: str) -> None:
    app_dir = REPO_ROOT / "apps" / service / "src"
    pyproject_path = app_dir / "pyproject.toml"
    requirements_path = app_dir / "requirements.txt"
    lock_path = app_dir / "uv.lock"

    assert pyproject_path.is_file()
    assert requirements_path.is_file()
    assert lock_path.is_file()
    assert REQUIRED_HOSTED_DEPENDENCY in pyproject_path.read_text(encoding="utf-8")
    assert REQUIRED_HOSTED_DEPENDENCY in requirements_path.read_text(encoding="utf-8")
    lock_text = lock_path.read_text(encoding="utf-8")
    assert f'name = "{REQUIRED_HOSTED_DEPENDENCY_NAME}"' in lock_text
    assert (
        f'{{ name = "{REQUIRED_HOSTED_DEPENDENCY_NAME}", '
        f'specifier = "{REQUIRED_HOSTED_DEPENDENCY_SPECIFIER}" }}'
    ) in lock_text


@pytest.mark.parametrize("service", sorted(EXPECTED_CUSTOM_SURFACE_AGENTS))
def test_custom_surface_agents_proxy_existing_aks_apim_endpoint(service: str) -> None:
    app_dir = REPO_ROOT / "apps" / service
    for manifest_name in HOSTED_SURFACE_MANIFEST_NAMES:
        assert not (app_dir / manifest_name).exists()

    metadata = _load_yaml(app_dir / ".foundry" / "agent-metadata.yaml")
    surface = metadata["surface"]
    assert isinstance(surface, dict)
    assert surface["type"] == "custom"
    assert surface["classification"] == "Custom Agent"
    assert surface["audience"] == "non-public-internal"
    assert surface["productRuntime"] == "aks"
    assert surface["productTrafficPath"] == "APIM -> AGC -> AKS"
    assert surface["foundryManagedCompute"] is False
    proxy = surface["proxy"]
    assert isinstance(proxy, dict)
    assert proxy["target"] == "existing-aks-apim-endpoint"
    assert proxy["endpoint"] == f"${{APIM_BASE_URL}}/agents/{service}"


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
    for token in FORBIDDEN_TRACKING_MANIFEST_TOKENS:
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


def test_inventory_health_check_tracking_manifest_stays_direct_model() -> None:
    app_dir = REPO_ROOT / "apps" / "inventory-health-check"
    agent_manifest = _load_yaml(app_dir / "agent.yaml")

    metadata = agent_manifest["metadata"]
    assert isinstance(metadata, dict)
    assert metadata["trackingOnly"] is True

    template = agent_manifest["template"]
    assert isinstance(template, dict)
    assert template["kind"] == "direct-model"


def test_inventory_health_check_hosted_surface_is_portal_only_when_present() -> None:
    app_dir = REPO_ROOT / "apps" / "inventory-health-check"
    manifest_paths = [
        app_dir / manifest_name
        for manifest_name in HOSTED_SURFACE_MANIFEST_NAMES
        if (app_dir / manifest_name).exists()
    ]
    if not manifest_paths:
        pytest.skip("No Foundry-hosted portal/evaluation surface manifest present yet")

    for manifest_path in manifest_paths:
        manifest = _load_yaml(manifest_path)
        metadata = manifest.get("metadata")
        assert isinstance(metadata, dict)
        surface = metadata.get("surface")
        assert isinstance(surface, dict)
        assert surface.get("type") == "hosted"
        assert surface.get("productRuntime") == "aks"
        assert surface.get("replacesProductRuntime") is False

        template = manifest.get("template")
        assert isinstance(template, dict)
        assert template.get("kind") == "hosted"
        protocols = {entry["protocol"]: entry["version"] for entry in template["protocols"]}
        assert protocols["responses"] == "1.0.0"

        manifest_text = manifest_path.read_text(encoding="utf-8")
        assert "hosted_main.py" not in manifest_text
        assert "replacement product" not in manifest_text.lower()
