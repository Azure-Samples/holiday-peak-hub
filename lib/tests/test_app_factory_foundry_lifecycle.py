"""Tests for app_factory_components.foundry_lifecycle."""

from typing import Any

from holiday_peak_lib.agents.base_agent import AgentDependencies, BaseRetailAgent, ModelTarget
from holiday_peak_lib.agents.foundry import FoundryAgentConfig
from holiday_peak_lib.app_factory_components.foundry_lifecycle import (
    DEFAULT_FOUNDRY_MODELS,
    build_foundry_config,
    build_foundry_readiness_snapshot,
    strict_foundry_mode_enabled,
)

TEST_PROJECT_NAME = "catalog-search"
TEST_PROJECT_ENDPOINT = f"https://example.services.ai.azure.com/api/projects/{TEST_PROJECT_NAME}"
TEST_RESOURCE_ENDPOINT = "https://example.cognitiveservices.azure.com"


class _Agent(BaseRetailAgent):
    async def handle(self, request: dict) -> dict:
        return request


async def _mock_invoker(**_kwargs: Any) -> dict[str, str]:
    return {"content": "ok"}


def _target(name: str, *, provider: str = "maf-direct") -> ModelTarget:
    return ModelTarget(
        name=name,
        model=f"{name}-model",
        invoker=_mock_invoker,
        provider=provider,
    )


def test_default_foundry_models_remain_documented() -> None:
    assert DEFAULT_FOUNDRY_MODELS == {"fast": "gpt-5-nano", "rich": "gpt-5"}


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
    assert cfg.deployment_name == "gpt-fast"
    assert cfg.runtime_agent_id is None


def test_build_foundry_config_does_not_default_missing_deployment(monkeypatch):
    monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
    monkeypatch.delenv("MODEL_DEPLOYMENT_NAME_FAST", raising=False)

    cfg = build_foundry_config("FOUNDRY_AGENT_ID_FAST", "MODEL_DEPLOYMENT_NAME_FAST")

    assert cfg is not None
    assert cfg.agent_id == "fast-pending"
    assert cfg.deployment_name is None


def test_build_foundry_config_name_only_stays_metadata(monkeypatch):
    monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
    monkeypatch.delenv("FOUNDRY_AGENT_ID_FAST", raising=False)
    monkeypatch.setenv("FOUNDRY_AGENT_NAME_FAST", "svc-fast")
    monkeypatch.setenv("MODEL_DEPLOYMENT_NAME_FAST", "gpt-fast")

    cfg = build_foundry_config("FOUNDRY_AGENT_ID_FAST", "MODEL_DEPLOYMENT_NAME_FAST")

    assert cfg is not None
    assert cfg.agent_id == "fast-pending"
    assert cfg.agent_name == "svc-fast"
    assert cfg.runtime_agent_id is None


def test_build_foundry_config_prefers_hph_agent_id_over_foundry_agent_id(monkeypatch):
    """``HPH_AGENT_ID_FAST`` wins over ``FOUNDRY_AGENT_ID_FAST``.

    Foundry V3 hosted-agents reserves the ``FOUNDRY_*`` / ``AGENT_*``
    env-var namespaces (per container-image-spec), so hosted manifests
    must map the logical agent ID through the non-reserved ``HPH_``
    prefix. The legacy ``FOUNDRY_AGENT_ID_*`` name remains the AKS
    contract and acts as a back-compat fallback.
    """
    monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
    monkeypatch.setenv("PROJECT_NAME", TEST_PROJECT_NAME)
    monkeypatch.setenv("HPH_AGENT_ID_FAST", "hosted-fast-id")
    monkeypatch.setenv("FOUNDRY_AGENT_ID_FAST", "legacy-fast-id")
    monkeypatch.setenv("MODEL_DEPLOYMENT_NAME_FAST", "gpt-fast")

    cfg = build_foundry_config("FOUNDRY_AGENT_ID_FAST", "MODEL_DEPLOYMENT_NAME_FAST")

    assert cfg is not None
    assert cfg.agent_id == "hosted-fast-id"


def test_build_foundry_config_hph_agent_name_takes_precedence(monkeypatch):
    """``HPH_AGENT_NAME_RICH`` wins over ``FOUNDRY_AGENT_NAME_RICH``."""
    monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
    monkeypatch.setenv("HPH_AGENT_NAME_RICH", "hosted-rich-name")
    monkeypatch.setenv("FOUNDRY_AGENT_NAME_RICH", "legacy-rich-name")

    cfg = build_foundry_config("FOUNDRY_AGENT_ID_RICH", "MODEL_DEPLOYMENT_NAME_RICH")

    assert cfg is not None
    assert cfg.agent_name == "hosted-rich-name"


def test_strict_foundry_mode_flag(monkeypatch):
    monkeypatch.setenv("FOUNDRY_STRICT_ENFORCEMENT", "true")
    assert strict_foundry_mode_enabled() is True


def test_build_foundry_readiness_snapshot_ready_with_bound_direct_targets():
    agent = _Agent(config=AgentDependencies())
    agent.slm = _target("fast")
    agent.llm = _target("rich")
    slm_cfg = FoundryAgentConfig(
        endpoint=TEST_PROJECT_ENDPOINT,
        deployment_name="gpt-fast",
    )
    llm_cfg = FoundryAgentConfig(
        endpoint=TEST_PROJECT_ENDPOINT,
        deployment_name="gpt-rich",
    )

    snapshot = build_foundry_readiness_snapshot(
        agent=agent,
        slm_config=slm_cfg,
        llm_config=llm_cfg,
        require_foundry_readiness=True,
        strict_foundry_mode=True,
    )

    assert snapshot.ready is True
    assert snapshot.bound_roles == ("fast", "rich")
    assert snapshot.unbound_roles == ()
    assert snapshot.runtime_resolution_required is False
    assert snapshot.agent_targets_bound is True


def test_build_foundry_readiness_snapshot_requires_maf_direct_provider():
    agent = _Agent(config=AgentDependencies())
    agent.slm = _target("fast", provider="foundry")
    slm_cfg = FoundryAgentConfig(
        endpoint=TEST_PROJECT_ENDPOINT,
        deployment_name="gpt-fast",
    )

    snapshot = build_foundry_readiness_snapshot(
        agent=agent,
        slm_config=slm_cfg,
        llm_config=None,
        require_foundry_readiness=True,
        strict_foundry_mode=True,
    )

    assert snapshot.ready is False
    assert snapshot.bound_roles == ()
    assert snapshot.unbound_roles == ("fast",)
    assert snapshot.runtime_resolution_required is True


def test_build_foundry_readiness_snapshot_requires_deployment_name_when_enforced():
    agent = _Agent(config=AgentDependencies())
    agent.slm = _target("fast")
    slm_cfg = FoundryAgentConfig(endpoint=TEST_PROJECT_ENDPOINT)

    snapshot = build_foundry_readiness_snapshot(
        agent=agent,
        slm_config=slm_cfg,
        llm_config=None,
        require_foundry_readiness=True,
        strict_foundry_mode=False,
    )

    assert snapshot.ready is False
    assert snapshot.unbound_roles == ("fast",)
    assert snapshot.runtime_resolution_required is True


def test_readiness_payload_includes_direct_and_compat_role_names():
    agent = _Agent(config=AgentDependencies())
    agent.slm = _target("fast")
    slm_cfg = FoundryAgentConfig(
        endpoint=TEST_PROJECT_ENDPOINT,
        deployment_name="gpt-fast",
    )

    payload = build_foundry_readiness_snapshot(
        agent=agent,
        slm_config=slm_cfg,
        llm_config=None,
        require_foundry_readiness=False,
        strict_foundry_mode=False,
    ).to_payload()

    assert payload["bound_roles"] == ["fast"]
    assert payload["unbound_roles"] == []
    assert payload["resolved_roles"] == ["fast"]
    assert payload["unresolved_roles"] == []
