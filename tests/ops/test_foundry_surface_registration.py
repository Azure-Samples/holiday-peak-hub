"""Validate Foundry surface registration planning."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "ops" / "register_foundry_surfaces.py"


def _load_registration_module():
    spec = importlib.util.spec_from_file_location("register_foundry_surfaces", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _inputs(module, **overrides):
    defaults = {
        "mode": "plan",
        "environment": "dev",
        "registry_path": REPO_ROOT / "apps" / "foundry-surfaces.yaml",
        "project_endpoint": "https://example.services.ai.azure.com/api/projects/hph-dev",
        "project_name": "hph-dev",
        "acr_login_server": None,
        "image_tag": None,
        "image_map_file": None,
        "apim_base_url": "https://apim.example.test",
        "services": (),
        "output": None,
        "model_deployment_fast": "gpt-5-nano",
        "model_deployment_rich": "gpt-5",
        "allow_unresolved": False,
    }
    defaults.update(overrides)
    return module.RegistrationInputs(**defaults)


@pytest.fixture(name="registration")
def registration_fixture():
    return _load_registration_module()


@pytest.fixture(name="_hosted_runtime_env")
def hosted_runtime_env_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    values = {
        "REDIS_HOST": "redis.example.test",
        "REDIS_URL": "rediss://redis.example.test:6380",
        "COSMOS_ACCOUNT_URI": "https://cosmos.example.test/",
        "COSMOS_DATABASE": "holiday-peak",
        "COSMOS_CONTAINER": "agent-memory",
        "BLOB_ACCOUNT_URL": "https://blob.example.test/",
        "BLOB_CONTAINER": "cold-memory",
        "EVENT_HUB_NAMESPACE": "hph-eventhub.servicebus.windows.net",
        "KEY_VAULT_URI": "https://hph-kv.vault.azure.net/",
        "APPLICATIONINSIGHTS_CONNECTION_STRING": "InstrumentationKey=00000000-0000-0000-0000-000000000000",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)


def test_hosted_surface_plan_materializes_foundry_hosted_definition(
    registration, _hosted_runtime_env, tmp_path: Path
) -> None:
    image_map_path = tmp_path / "images.json"
    image_ref = "hphdevacr.azurecr.io/inventory-health-check@sha256:abc123"
    image_map_path.write_text(
        json.dumps({"inventory-health-check": image_ref}), encoding="utf-8"
    )
    inputs = _inputs(
        registration,
        services=("inventory-health-check",),
        image_map_file=image_map_path,
    )

    plan = registration.build_registration_plan(inputs)

    assert plan["counts"] == {"hosted": 1, "custom": 0, "total": 1}
    operation = plan["operations"][0]
    assert operation["service"] == "inventory-health-check"
    assert operation["surface"] == "hosted"
    assert operation["applySupported"] is True
    assert operation["agentEndpoint"].endswith(
        "/agents/inventory-health-check/endpoint/protocols/openai/v1/responses"
    )
    definition = operation["agentDefinition"]
    assert definition["kind"] == "hosted"
    assert definition["image"] == image_ref
    assert definition["cpu"] == "0.5"
    assert definition["memory"] == "1Gi"
    assert definition["container_protocol_versions"] == [
        {"protocol": "responses", "version": "1.0.0"}
    ]
    env_vars = definition["environment_variables"]
    assert env_vars["HOLIDAY_PEAK_FOUNDRY_HOSTED"] == "1"
    assert env_vars["UVICORN_PORT"] == "8088"
    assert env_vars["PROJECT_ENDPOINT"] == inputs.project_endpoint
    assert env_vars["HPH_AGENT_ID_FAST"] == "inventory-health-check-fast"
    assert env_vars["MODEL_DEPLOYMENT_NAME_RICH"] == "gpt-5"
    assert all(not name.startswith(("FOUNDRY_", "AGENT_")) for name in env_vars)
    assert operation["unresolvedVariables"] == []
    assert operation["metadata"]["hphDefinitionSha256"] == operation["definitionSha256"]


def test_custom_surface_plan_stays_proxy_metadata_only(registration) -> None:
    inputs = _inputs(registration, services=("crm-campaign-intelligence",))

    plan = registration.build_registration_plan(inputs)

    assert plan["counts"] == {"hosted": 0, "custom": 1, "total": 1}
    operation = plan["operations"][0]
    assert operation["service"] == "crm-campaign-intelligence"
    assert operation["surface"] == "custom"
    assert operation["action"] == "validate_custom_proxy_metadata"
    assert operation["applySupported"] is False
    assert "agentDefinition" not in operation
    proxy = operation["customProxyDefinition"]
    assert proxy["kind"] == "custom-proxy"
    assert proxy["endpoint"] == "https://apim.example.test/agents/crm-campaign-intelligence"
    assert proxy["productRuntime"] == "aks"
    assert proxy["productTrafficPath"] == "APIM -> AGC -> AKS"
    assert proxy["foundryManagedCompute"] is False


def test_hosted_surface_requires_image_source(registration, _hosted_runtime_env) -> None:
    inputs = _inputs(registration, services=("inventory-health-check",))

    with pytest.raises(registration.SurfaceRegistrationError, match="Hosted surfaces require"):
        registration.build_registration_plan(inputs)


def test_acr_and_tag_can_materialize_hosted_image_ref(
    registration, _hosted_runtime_env
) -> None:
    inputs = _inputs(
        registration,
        services=("inventory-health-check",),
        acr_login_server="hphdevacr.azurecr.io",
        image_tag="commit-123",
    )

    plan = registration.build_registration_plan(inputs)

    definition = plan["operations"][0]["agentDefinition"]
    assert definition["image"] == "hphdevacr.azurecr.io/inventory-health-check:commit-123"


def test_apply_mode_rejects_unresolved_values(registration, monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "REDIS_HOST",
        "COSMOS_ACCOUNT_URI",
        "COSMOS_DATABASE",
        "COSMOS_CONTAINER",
        "BLOB_ACCOUNT_URL",
        "BLOB_CONTAINER",
        "EVENT_HUB_NAMESPACE",
        "KEY_VAULT_URI",
        "APPLICATIONINSIGHTS_CONNECTION_STRING",
    ):
        monkeypatch.delenv(key, raising=False)
    inputs = _inputs(
        registration,
        mode="apply",
        services=("inventory-health-check",),
        acr_login_server="hphdevacr.azurecr.io",
        image_tag="commit-123",
    )

    with pytest.raises(registration.SurfaceRegistrationError, match="Unresolved required values"):
        registration.build_registration_plan(inputs)