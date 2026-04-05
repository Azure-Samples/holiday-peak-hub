"""Tests for app_factory_components.foundry_lifecycle."""

from unittest.mock import AsyncMock

import pytest
from holiday_peak_lib.agents.base_agent import AgentDependencies, BaseRetailAgent
from holiday_peak_lib.agents.foundry import FoundryAgentConfig
from holiday_peak_lib.app_factory_components.foundry_lifecycle import (
    FoundryLifecycleManager,
    auto_ensure_on_startup_enabled,
    build_foundry_config,
    strict_foundry_mode_enabled,
)


class _Agent(BaseRetailAgent):
    async def handle(self, request: dict) -> dict:
        return request


def test_build_foundry_config_from_env(monkeypatch):
    monkeypatch.setenv("PROJECT_ENDPOINT", "https://example.test")
    monkeypatch.setenv("FOUNDRY_AGENT_ID_FAST", "agent-fast")
    monkeypatch.setenv("MODEL_DEPLOYMENT_NAME_FAST", "gpt-fast")

    cfg = build_foundry_config("FOUNDRY_AGENT_ID_FAST", "MODEL_DEPLOYMENT_NAME_FAST")
    assert cfg is not None
    assert cfg.endpoint == "https://example.test"
    assert cfg.agent_id == "agent-fast"
    assert cfg.deployment_name == "gpt-fast"


def test_foundry_mode_flags(monkeypatch):
    monkeypatch.setenv("FOUNDRY_STRICT_ENFORCEMENT", "true")
    assert strict_foundry_mode_enabled() is True

    monkeypatch.setenv("FOUNDRY_AUTO_ENSURE_ON_STARTUP", "true")
    assert auto_ensure_on_startup_enabled(strict_foundry_mode=True) is True


@pytest.mark.asyncio
async def test_ensure_role_wires_model_target():
    agent = _Agent(config=AgentDependencies())
    cfg = FoundryAgentConfig(
        endpoint="https://example.test",
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
    assert agent.slm == "target-fast"


@pytest.mark.asyncio
async def test_ensure_role_skips_wiring_when_id_remains_pending():
    agent = _Agent(config=AgentDependencies())
    cfg = FoundryAgentConfig(
        endpoint="https://example.test",
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
    assert agent.slm is None
