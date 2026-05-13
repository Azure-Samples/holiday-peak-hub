"""Tests for the Foundry hosted-agent deploy helper.

The tests avoid the ``azure-ai-projects`` / ``azure-identity`` SDKs by
injecting a stub ``project_client`` and stubbing
``_build_definition`` so the helper exercises its own polling and
result-shaping logic in isolation.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from holiday_peak_lib.foundry_hosting import deploy as deploy_module
from holiday_peak_lib.foundry_hosting.manifest import HostedAgentManifest, load_manifest

CANONICAL_YAML = """\
name: sample-hosted-agent
description: deploy-test
template:
  name: sample-hosted-agent
  kind: hosted
  protocols:
    - protocol: responses
      version: "1.0.0"
  environment_variables:
    - name: LITERAL_VAR
      value: literal-value
container:
  cpu: "1"
  memory: 2Gi
resources:
  - kind: model
    id: gpt-5-nano
    name: AZURE_AI_MODEL_DEPLOYMENT_NAME
"""


@pytest.fixture(autouse=True)
def _stub_build_definition(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub the SDK-specific definition builder so tests don't need azure-ai-projects."""

    def _fake_build(
        manifest: HostedAgentManifest,
        *,
        image: str,
        cpu: str,
        memory: str,
        environment_variables: dict[str, str],
    ) -> dict[str, Any]:
        return {
            "kind": manifest.template.kind,
            "image": image,
            "cpu": cpu,
            "memory": memory,
            "environment_variables": environment_variables,
            "protocols": [
                {"protocol": p.protocol, "version": p.version} for p in manifest.template.protocols
            ],
        }

    monkeypatch.setattr(deploy_module, "_build_definition", _fake_build)


@pytest.fixture()
def manifest(tmp_path: Path) -> HostedAgentManifest:
    p = tmp_path / "agent.yaml"
    p.write_text(CANONICAL_YAML, encoding="utf-8")
    return load_manifest(p)


class _FakeAgentsClient:
    """In-memory stand-in for ``client.agents`` with deterministic polling."""

    def __init__(
        self,
        *,
        initial_status: str = "creating",
        terminal_status: str = "active",
        polls_until_terminal: int = 2,
        endpoint_url: str = "https://example/agents/sample-hosted-agent/endpoint",
    ) -> None:
        self.initial_status = initial_status
        self.terminal_status = terminal_status
        self.polls_until_terminal = polls_until_terminal
        self.endpoint_url = endpoint_url
        self.create_calls: list[dict[str, Any]] = []
        self.get_calls: list[tuple[str, str | None]] = []
        self._poll_count = 0

    def create_version(self, *, agent_name: str, definition: Any) -> SimpleNamespace:
        self.create_calls.append({"agent_name": agent_name, "definition": definition})
        return SimpleNamespace(
            name=agent_name,
            version="v1",
            status=self.initial_status,
            endpoint_url=None,
        )

    def get_version(self, agent_name: str, version: str | None = None) -> SimpleNamespace:
        self.get_calls.append((agent_name, version))
        self._poll_count += 1
        if self._poll_count >= self.polls_until_terminal:
            return SimpleNamespace(
                name=agent_name,
                version=version,
                status=self.terminal_status,
                endpoint_url=self.endpoint_url,
            )
        return SimpleNamespace(
            name=agent_name,
            version=version,
            status="provisioning",
            endpoint_url=None,
        )


class _FakeProjectClient:
    def __init__(self, agents: _FakeAgentsClient) -> None:
        self.agents = agents


def test_deploy_succeeds_after_polling(
    monkeypatch: pytest.MonkeyPatch, manifest: HostedAgentManifest
) -> None:
    monkeypatch.setattr(deploy_module.time, "sleep", lambda _s: None)
    agents = _FakeAgentsClient(polls_until_terminal=2, terminal_status="active")
    client = _FakeProjectClient(agents)

    result = deploy_module.deploy_hosted_agent_version(
        manifest,
        image_uri="acr.example.io/sample:latest",
        project_endpoint="https://example/api/projects/sample",
        project_client=client,
        poll_interval_seconds=0.0,
    )

    assert result.succeeded
    assert result.status == "active"
    assert result.version == "v1"
    assert result.endpoint_url == agents.endpoint_url
    assert agents.create_calls[0]["agent_name"] == "sample-hosted-agent"
    assert agents.create_calls[0]["definition"]["image"] == "acr.example.io/sample:latest"
    # Polled at least once before reaching terminal status.
    assert result.polling_attempts >= 1


def test_deploy_raises_on_failed_status(
    monkeypatch: pytest.MonkeyPatch, manifest: HostedAgentManifest
) -> None:
    monkeypatch.setattr(deploy_module.time, "sleep", lambda _s: None)
    agents = _FakeAgentsClient(polls_until_terminal=1, terminal_status="failed")
    client = _FakeProjectClient(agents)

    with pytest.raises(RuntimeError, match="failed"):
        deploy_module.deploy_hosted_agent_version(
            manifest,
            image_uri="acr.example.io/sample:latest",
            project_endpoint="https://example/api/projects/sample",
            project_client=client,
            poll_interval_seconds=0.0,
        )


def test_deploy_requires_image_when_manifest_has_none(
    manifest: HostedAgentManifest,
) -> None:
    with pytest.raises(ValueError, match="image_uri"):
        deploy_module.deploy_hosted_agent_version(
            manifest,
            image_uri=None,
            project_endpoint="https://example/api/projects/sample",
            project_client=_FakeProjectClient(_FakeAgentsClient()),
        )


def test_deploy_no_poll_returns_initial_status(manifest: HostedAgentManifest) -> None:
    agents = _FakeAgentsClient(initial_status="active")
    client = _FakeProjectClient(agents)

    result = deploy_module.deploy_hosted_agent_version(
        manifest,
        image_uri="acr.example.io/sample:latest",
        project_endpoint="https://example/api/projects/sample",
        project_client=client,
        poll=False,
    )
    assert result.status == "active"
    assert agents.get_calls == []  # never polled


def test_deploy_times_out_when_status_never_terminal(
    monkeypatch: pytest.MonkeyPatch, manifest: HostedAgentManifest
) -> None:
    monkeypatch.setattr(deploy_module.time, "sleep", lambda _s: None)
    # Drive ``time.monotonic`` forward fast enough that the polling loop
    # exceeds the configured timeout immediately.
    clock = iter([0.0, 0.1, 100.0, 200.0])
    monkeypatch.setattr(deploy_module.time, "monotonic", lambda: next(clock))

    agents = _FakeAgentsClient(polls_until_terminal=999, terminal_status="active")
    client = _FakeProjectClient(agents)

    with pytest.raises(TimeoutError):
        deploy_module.deploy_hosted_agent_version(
            manifest,
            image_uri="acr.example.io/sample:latest",
            project_endpoint="https://example/api/projects/sample",
            project_client=client,
            poll_interval_seconds=0.0,
            poll_timeout_seconds=1.0,
        )


def test_deploy_applies_environment_overrides(
    monkeypatch: pytest.MonkeyPatch, manifest: HostedAgentManifest
) -> None:
    monkeypatch.setattr(deploy_module.time, "sleep", lambda _s: None)
    agents = _FakeAgentsClient(polls_until_terminal=1, terminal_status="active")
    client = _FakeProjectClient(agents)

    deploy_module.deploy_hosted_agent_version(
        manifest,
        image_uri="acr.example.io/sample:latest",
        project_endpoint="https://example/api/projects/sample",
        project_client=client,
        environment_overrides={"EXTRA": "override-value", "LITERAL_VAR": "replaced"},
        poll_interval_seconds=0.0,
    )

    env = agents.create_calls[0]["definition"]["environment_variables"]
    assert env["EXTRA"] == "override-value"
    assert env["LITERAL_VAR"] == "replaced"


def test_deploy_raises_on_deleted_status(
    monkeypatch: pytest.MonkeyPatch, manifest: HostedAgentManifest
) -> None:
    """``deleted`` is a failure terminal status for create_version per docs."""
    monkeypatch.setattr(deploy_module.time, "sleep", lambda _s: None)
    agents = _FakeAgentsClient(polls_until_terminal=1, terminal_status="deleted")
    client = _FakeProjectClient(agents)

    with pytest.raises(RuntimeError, match="deleted"):
        deploy_module.deploy_hosted_agent_version(
            manifest,
            image_uri="acr.example.io/sample:latest",
            project_endpoint="https://example/api/projects/sample",
            project_client=client,
            poll_interval_seconds=0.0,
        )


def test_build_project_client_passes_allow_preview(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``allow_preview=True`` is mandatory for the hosted-agent V3 surface."""
    captured: dict[str, Any] = {}

    class _FakeAIProjectClient:
        # pylint: disable=too-few-public-methods
        def __init__(self, *, endpoint: str, credential: Any, **kwargs: Any) -> None:
            captured["endpoint"] = endpoint
            captured["credential"] = credential
            captured["kwargs"] = kwargs
            self.agents = SimpleNamespace()

    fake_module = SimpleNamespace(AIProjectClient=_FakeAIProjectClient)
    monkeypatch.setitem(__import__("sys").modules, "azure.ai.projects", fake_module)

    sentinel_credential = object()
    client = deploy_module._build_project_client(  # pylint: disable=protected-access
        project_endpoint="https://example.services.ai.azure.com/api/projects/p",
        credential=sentinel_credential,
    )

    assert isinstance(client, _FakeAIProjectClient)
    assert captured["endpoint"] == "https://example.services.ai.azure.com/api/projects/p"
    assert captured["credential"] is sentinel_credential
    assert captured["kwargs"].get("allow_preview") is True


def test_normalize_status_handles_enum_value() -> None:
    """``_normalize_status`` prefers ``.value`` on Enum-like objects.

    The Foundry SDK deserialises ``"status": "failed"`` into an
    ``AgentVersionStatus`` Enum whose ``str()`` returns
    ``"AgentVersionStatus.FAILED"``. The poll loop must still recognise
    that as the terminal ``failed`` status.
    """

    class _FakeStatus:
        value = "failed"

        def __str__(self) -> str:
            return "AgentVersionStatus.FAILED"

    assert (
        deploy_module._normalize_status(_FakeStatus())  # pylint: disable=protected-access
        == "failed"
    )


def test_normalize_status_strips_dotted_enum_repr() -> None:
    """Fallback: when ``.value`` is missing, drop the ``Enum.`` prefix."""

    class _StringlyEnum:
        def __str__(self) -> str:
            return "AgentVersionStatus.ACTIVE"

    assert (
        deploy_module._normalize_status(_StringlyEnum())  # pylint: disable=protected-access
        == "active"
    )


def test_normalize_status_plain_string() -> None:
    """Plain string statuses are lower-cased and returned unchanged."""
    assert deploy_module._normalize_status("Active") == "active"  # pylint: disable=protected-access
    assert deploy_module._normalize_status(None) == "unknown"  # pylint: disable=protected-access
