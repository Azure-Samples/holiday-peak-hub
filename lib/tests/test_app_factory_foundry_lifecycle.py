"""Tests for app_factory_components.foundry_lifecycle."""

from unittest.mock import AsyncMock

import pytest
from holiday_peak_lib.agents.base_agent import AgentDependencies, BaseRetailAgent
from holiday_peak_lib.agents.foundry import FoundryAgentConfig
from holiday_peak_lib.app_factory_components.foundry_lifecycle import (
    FoundryLifecycleManager,
    auto_ensure_on_startup_enabled,
    build_foundry_config,
    build_foundry_readiness_snapshot,
    first_foundry_error_state,
    strict_foundry_mode_enabled,
)

TEST_PROJECT_NAME = "catalog-search"
TEST_PROJECT_ENDPOINT = f"https://example.services.ai.azure.com/api/projects/{TEST_PROJECT_NAME}"
TEST_RESOURCE_ENDPOINT = "https://example.cognitiveservices.azure.com"


class _Agent(BaseRetailAgent):
    async def handle(self, request: dict) -> dict:
        return request


def test_build_foundry_config_from_env(monkeypatch):
    monkeypatch.setenv("PROJECT_ENDPOINT", TEST_RESOURCE_ENDPOINT)
    monkeypatch.setenv("PROJECT_NAME", TEST_PROJECT_NAME)
    monkeypatch.setenv("FOUNDRY_AGENT_ID_FAST", "agent-fast")
    monkeypatch.setenv("MODEL_DEPLOYMENT_NAME_FAST", "gpt-fast")

    cfg = build_foundry_config("FOUNDRY_AGENT_ID_FAST", "MODEL_DEPLOYMENT_NAME_FAST")
    assert cfg is not None
    assert cfg.endpoint == TEST_PROJECT_ENDPOINT
    assert cfg.project_name == TEST_PROJECT_NAME
    assert cfg.agent_id == "agent-fast"
    assert cfg.runtime_agent_id == "agent-fast"
    assert cfg.deployment_name == "gpt-fast"


def test_build_foundry_config_name_only_stays_unresolved(monkeypatch):
    monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
    monkeypatch.delenv("FOUNDRY_AGENT_ID_FAST", raising=False)
    monkeypatch.setenv("FOUNDRY_AGENT_NAME_FAST", "svc-fast")

    cfg = build_foundry_config("FOUNDRY_AGENT_ID_FAST", "MODEL_DEPLOYMENT_NAME_FAST")

    assert cfg is not None
    assert cfg.agent_id == "fast-pending"
    assert cfg.agent_name == "svc-fast"
    assert cfg.runtime_agent_id is None


def test_foundry_mode_flags(monkeypatch):
    monkeypatch.setenv("FOUNDRY_STRICT_ENFORCEMENT", "true")
    assert strict_foundry_mode_enabled() is True

    monkeypatch.setenv("FOUNDRY_AUTO_ENSURE_ON_STARTUP", "true")
    assert auto_ensure_on_startup_enabled(strict_foundry_mode=True) is True


def test_build_foundry_readiness_snapshot_requires_all_configured_roles():
    agent = _Agent(config=AgentDependencies())
    agent.slm = "target-fast"

    slm_cfg = FoundryAgentConfig(
        endpoint=TEST_PROJECT_ENDPOINT,
        agent_id="agent-fast",
        deployment_name="gpt-fast",
    )
    llm_cfg = FoundryAgentConfig(
        endpoint=TEST_PROJECT_ENDPOINT,
        agent_id="rich-pending",
        agent_name="svc-rich",
        deployment_name="gpt-rich",
        resolved_agent_id=None,
    )

    snapshot = build_foundry_readiness_snapshot(
        agent=agent,
        slm_config=slm_cfg,
        llm_config=llm_cfg,
        require_foundry_readiness=True,
        strict_foundry_mode=True,
        auto_ensure_on_startup=False,
        last_error=None,
    )

    assert snapshot.ready is False
    assert snapshot.configured_roles == ("fast", "rich")
    assert snapshot.resolved_roles == ("fast",)
    assert snapshot.unresolved_roles == ("rich",)
    assert snapshot.runtime_resolution_required is True


def test_first_foundry_error_state_returns_role_context():
    error_state = first_foundry_error_state(
        {
            "fast": {
                "status": "agents_service_unavailable",
                "agent_id": None,
                "agent_name": "svc-fast",
                "created": False,
                "error_code": "UserError.ServiceInvocationException",
                "detail": "Foundry backend unavailable",
            }
        },
        configured_roles=("fast", "rich"),
    )

    assert error_state is not None
    assert error_state["role"] == "fast"
    assert error_state["status"] == "agents_service_unavailable"
    assert error_state["error_code"] == "UserError.ServiceInvocationException"
    assert error_state["detail"] == "Foundry backend unavailable"


@pytest.mark.asyncio
async def test_ensure_role_wires_model_target():
    agent = _Agent(config=AgentDependencies())
    cfg = FoundryAgentConfig(
        endpoint=TEST_PROJECT_ENDPOINT,
        agent_id="pending",
        deployment_name="gpt-fast",
    )
    ensure_fn = AsyncMock(
        return_value={
            "status": "exists",
            "agent_id": "agent-fast",
            "agent_name": "svc-fast",
            "created": False,
        }
    )

    manager = FoundryLifecycleManager(
        service_name="svc",
        agent=agent,
        slm_config=cfg,
        llm_config=None,
        ensure_foundry_agent_fn=ensure_fn,
        build_foundry_model_target_fn=lambda _: "target-fast",
    )

    result = await manager.ensure_role(
        selected_role="fast",
        config=cfg,
        instructions="instruction",
        create_if_missing=True,
    )

    assert result["agent_id"] == "agent-fast"
    assert cfg.runtime_agent_id == "agent-fast"
    assert agent.slm == "target-fast"


@pytest.mark.asyncio
async def test_ensure_role_skips_wiring_when_id_remains_pending():
    agent = _Agent(config=AgentDependencies())
    cfg = FoundryAgentConfig(
        endpoint=TEST_PROJECT_ENDPOINT,
        agent_id="fast-pending",
        deployment_name="gpt-fast",
    )
    ensure_fn = AsyncMock(
        return_value={
            "status": "missing",
            "agent_id": None,
            "agent_name": "svc-fast",
            "created": False,
        }
    )

    manager = FoundryLifecycleManager(
        service_name="svc",
        agent=agent,
        slm_config=cfg,
        llm_config=None,
        ensure_foundry_agent_fn=ensure_fn,
        build_foundry_model_target_fn=lambda _: "target-fast",
    )

    result = await manager.ensure_role(
        selected_role="fast",
        config=cfg,
        instructions="instruction",
        create_if_missing=True,
    )

    assert result["status"] == "missing"
    assert cfg.runtime_agent_id is None
    assert agent.slm is None
