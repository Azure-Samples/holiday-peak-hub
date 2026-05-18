"""Tests for the Foundry hosted-agent deploy helper.

The tests avoid the ``azure-ai-projects`` / ``azure-identity`` SDKs by
injecting a stub ``project_client`` and stubbing
``_build_definition`` so the helper exercises its own polling and
result-shaping logic in isolation.
"""

from __future__ import annotations

import collections.abc
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


# ---------------------------------------------------------------------------
# _resolve_latest_version: hardening against stale create_version responses.
#
# Root cause: the Azure AI Projects preview SDK has been observed to return
# create_version responses whose .version / .status reflect the *previous*
# version, not the one just created. The deploy helper must re-resolve the
# real latest version before reporting success/failure.
# ---------------------------------------------------------------------------


class _StaleCreateAgentsClient:
    """Fake agents client where ``create_version`` lies about the new version.

    Mirrors the preview-SDK bug seen against ``inventory-health-check``:
    create_version returns ``v2 failed`` (stale) even though the platform
    has just created ``v3`` and is provisioning it.
    """

    def __init__(
        self,
        *,
        list_versions_payload: list[Any] | None = None,
        get_agent_payload: Any | None = None,
        get_version_status_sequence: list[str] | None = None,
        endpoint_url: str = "https://example/agents/sample-hosted-agent/endpoint",
    ) -> None:
        self.list_versions_payload = list_versions_payload
        self.get_agent_payload = get_agent_payload
        self.get_version_status_sequence = list(get_version_status_sequence or ["active"])
        self.endpoint_url = endpoint_url
        self.create_calls: list[dict[str, Any]] = []
        self.list_calls: list[dict[str, Any]] = []
        self.get_agent_calls: list[dict[str, Any]] = []
        self.get_version_calls: list[tuple[str, str | None]] = []

    def create_version(self, *, agent_name: str, definition: Any) -> SimpleNamespace:
        self.create_calls.append({"agent_name": agent_name, "definition": definition})
        # Stale: SDK bug - reports the previous (failed) version.
        return SimpleNamespace(
            name=agent_name,
            version="v2",
            status="failed",
            endpoint_url=None,
        )

    # Only attached when the test wants to exercise this path:
    def _enable_list_versions(self) -> None:
        def _list(*, agent_name: str) -> list[Any]:
            self.list_calls.append({"agent_name": agent_name})
            return self.list_versions_payload or []

        self.list_versions = _list  # type: ignore[attr-defined]

    def _enable_get_agent(self) -> None:
        def _get(*, agent_name: str) -> Any:
            self.get_agent_calls.append({"agent_name": agent_name})
            return self.get_agent_payload

        self.get_agent = _get  # type: ignore[attr-defined]

    def get_version(self, *, agent_name: str, version: str | None) -> SimpleNamespace:
        self.get_version_calls.append((agent_name, version))
        if self.get_version_status_sequence:
            status = self.get_version_status_sequence.pop(0)
        else:
            status = "active"
        return SimpleNamespace(
            name=agent_name,
            version=version,
            status=status,
            endpoint_url=self.endpoint_url if status == "active" else None,
        )


def test_resolve_latest_version_prefers_list_versions_over_stale_create_response(
    monkeypatch: pytest.MonkeyPatch, manifest: HostedAgentManifest, caplog: pytest.LogCaptureFixture
) -> None:
    """When ``list_versions`` exists, deploy must trust it over the stale create_response."""
    monkeypatch.setattr(deploy_module.time, "sleep", lambda _s: None)
    agents = _StaleCreateAgentsClient(
        list_versions_payload=[
            SimpleNamespace(version="v1", status="active"),
            SimpleNamespace(version="v2", status="failed"),
            SimpleNamespace(version="v3", status="creating"),
        ],
        # First poll resolves v3 -> active.
        get_version_status_sequence=["active"],
    )
    agents._enable_list_versions()  # pylint: disable=protected-access
    client = _FakeProjectClient(agents)

    with caplog.at_level("INFO", logger=deploy_module.logger.name):
        result = deploy_module.deploy_hosted_agent_version(
            manifest,
            image_uri="acr.example.io/sample:latest",
            project_endpoint="https://example/api/projects/sample",
            project_client=client,
            poll_interval_seconds=0.0,
        )

    # The fix: deploy ignored the create_response's stale "v2 failed" and
    # resolved v3 from list_versions, then polled v3 to active.
    assert result.version == "v3"
    assert result.status == "active"
    assert result.succeeded
    assert result.endpoint_url == agents.endpoint_url
    assert agents.list_calls == [{"agent_name": "sample-hosted-agent"}]
    # Poll loop targeted the resolved version, not the reported one.
    assert agents.get_version_calls and agents.get_version_calls[0][1] == "v3"
    # Structured log line exposes the divergence (reported v2, resolved v3).
    resolve_logs = [
        rec for rec in caplog.records if "foundry_hosted_agent_resolved_version" in rec.getMessage()
    ]
    assert resolve_logs, "expected foundry_hosted_agent_resolved_version log line"
    msg = resolve_logs[-1].getMessage()
    assert "reported=v2" in msg
    assert "resolved=v3" in msg
    assert "path=list_versions" in msg


def test_resolve_latest_version_falls_back_to_get_agent_when_list_versions_missing(
    monkeypatch: pytest.MonkeyPatch, manifest: HostedAgentManifest, caplog: pytest.LogCaptureFixture
) -> None:
    """No ``list_versions`` attribute: deploy uses ``get_agent`` + ``get_version``."""
    monkeypatch.setattr(deploy_module.time, "sleep", lambda _s: None)
    agents = _StaleCreateAgentsClient(
        get_agent_payload=SimpleNamespace(name="sample-hosted-agent", latest_version="v3"),
        get_version_status_sequence=["active"],
    )
    agents._enable_get_agent()  # pylint: disable=protected-access
    # Intentionally no list_versions attribute.
    assert not hasattr(agents, "list_versions")
    client = _FakeProjectClient(agents)

    with caplog.at_level("INFO", logger=deploy_module.logger.name):
        result = deploy_module.deploy_hosted_agent_version(
            manifest,
            image_uri="acr.example.io/sample:latest",
            project_endpoint="https://example/api/projects/sample",
            project_client=client,
            poll_interval_seconds=0.0,
        )

    assert result.version == "v3"
    assert result.status == "active"
    assert result.succeeded
    assert agents.get_agent_calls == [{"agent_name": "sample-hosted-agent"}]
    # get_version called once during resolve (returns active, no poll needed).
    assert agents.get_version_calls and agents.get_version_calls[0] == (
        "sample-hosted-agent",
        "v3",
    )
    resolve_logs = [
        rec for rec in caplog.records if "foundry_hosted_agent_resolved_version" in rec.getMessage()
    ]
    assert resolve_logs
    msg = resolve_logs[-1].getMessage()
    assert "reported=v2" in msg
    assert "resolved=v3" in msg
    assert "path=get_agent" in msg


def test_resolve_latest_version_uses_create_response_when_both_fallbacks_unavailable(
    monkeypatch: pytest.MonkeyPatch, manifest: HostedAgentManifest, caplog: pytest.LogCaptureFixture
) -> None:
    """Older SDK (no ``list_versions`` and no ``get_agent``): preserve back-compat."""
    monkeypatch.setattr(deploy_module.time, "sleep", lambda _s: None)

    class _LegacyAgents:
        # pylint: disable=too-few-public-methods
        def __init__(self) -> None:
            self.create_calls: list[dict[str, Any]] = []

        def create_version(self, *, agent_name: str, definition: Any) -> SimpleNamespace:
            self.create_calls.append({"agent_name": agent_name, "definition": definition})
            return SimpleNamespace(
                name=agent_name,
                version="v3",
                status="active",
                endpoint_url="https://example/agents/sample-hosted-agent/endpoint",
            )

        def get_version(self, *, agent_name: str, version: str | None) -> SimpleNamespace:
            raise AssertionError("get_version must not be called: status is terminal")

    agents = _LegacyAgents()
    assert not hasattr(agents, "list_versions")
    assert not hasattr(agents, "get_agent")
    client = _FakeProjectClient(agents)

    with caplog.at_level("INFO", logger=deploy_module.logger.name):
        result = deploy_module.deploy_hosted_agent_version(
            manifest,
            image_uri="acr.example.io/sample:latest",
            project_endpoint="https://example/api/projects/sample",
            project_client=client,
            poll_interval_seconds=0.0,
        )

    # Back-compat: deploy still uses what create_response surfaced.
    assert result.version == "v3"
    assert result.status == "active"
    assert result.succeeded
    resolve_logs = [
        rec for rec in caplog.records if "foundry_hosted_agent_resolved_version" in rec.getMessage()
    ]
    assert resolve_logs
    msg = resolve_logs[-1].getMessage()
    assert "reported=v3" in msg
    assert "resolved=v3" in msg
    assert "path=create_response" in msg


def test_resolve_latest_version_handles_list_versions_positional_signature(
    monkeypatch: pytest.MonkeyPatch, manifest: HostedAgentManifest
) -> None:
    """Some preview SDK builds expose ``list_versions`` positional-only."""
    monkeypatch.setattr(deploy_module.time, "sleep", lambda _s: None)

    class _PositionalAgents:
        # pylint: disable=too-few-public-methods
        def __init__(self) -> None:
            self.list_calls: list[str] = []

        def create_version(self, *, agent_name: str, definition: Any) -> SimpleNamespace:
            return SimpleNamespace(version="v2", status="failed", endpoint_url=None)

        def list_versions(self, agent_name: str) -> list[Any]:  # positional only
            self.list_calls.append(agent_name)
            return [
                SimpleNamespace(version="v1", status="active"),
                SimpleNamespace(version="v3", status="active"),
            ]

        def get_version(self, *, agent_name: str, version: str | None) -> SimpleNamespace:
            return SimpleNamespace(
                name=agent_name, version=version, status="active", endpoint_url=None
            )

    agents = _PositionalAgents()
    client = _FakeProjectClient(agents)

    result = deploy_module.deploy_hosted_agent_version(
        manifest,
        image_uri="acr.example.io/sample:latest",
        project_endpoint="https://example/api/projects/sample",
        project_client=client,
        poll_interval_seconds=0.0,
    )

    assert result.version == "v3"
    assert result.status == "active"
    assert agents.list_calls == ["sample-hosted-agent"]


def test_resolve_latest_version_falls_through_when_list_versions_raises(
    monkeypatch: pytest.MonkeyPatch, manifest: HostedAgentManifest
) -> None:
    """If ``list_versions`` exists but raises, fall through to ``get_agent``."""
    monkeypatch.setattr(deploy_module.time, "sleep", lambda _s: None)

    class _ErrorThenAgent:
        # pylint: disable=too-few-public-methods
        def __init__(self) -> None:
            self.get_agent_called = False

        def create_version(self, *, agent_name: str, definition: Any) -> SimpleNamespace:
            return SimpleNamespace(version="v2", status="failed", endpoint_url=None)

        def list_versions(self, *, agent_name: str) -> list[Any]:
            raise RuntimeError("preview SDK transient failure")

        def get_agent(self, *, agent_name: str) -> Any:
            self.get_agent_called = True
            return SimpleNamespace(name=agent_name, latest_version="v3")

        def get_version(self, *, agent_name: str, version: str | None) -> SimpleNamespace:
            return SimpleNamespace(
                name=agent_name, version=version, status="active", endpoint_url=None
            )

    agents = _ErrorThenAgent()
    client = _FakeProjectClient(agents)

    result = deploy_module.deploy_hosted_agent_version(
        manifest,
        image_uri="acr.example.io/sample:latest",
        project_endpoint="https://example/api/projects/sample",
        project_client=client,
        poll_interval_seconds=0.0,
    )

    assert agents.get_agent_called
    assert result.version == "v3"
    assert result.status == "active"


def test_pick_latest_version_picks_highest_numeric_label() -> None:
    """``_pick_latest_version`` selects by numeric value, not list order."""
    versions = [
        SimpleNamespace(version="v10"),
        SimpleNamespace(version="v2"),
        SimpleNamespace(version="v9"),
    ]
    obj, label = deploy_module._pick_latest_version(versions)  # pylint: disable=protected-access
    assert label == "v10"
    assert obj is versions[0]


def test_pick_latest_version_tolerates_non_numeric_labels() -> None:
    """Non-numeric labels are kept only as a last-resort candidate."""
    versions = [
        SimpleNamespace(version="rc-alpha"),
        SimpleNamespace(version="v3"),
    ]
    obj, label = deploy_module._pick_latest_version(versions)  # pylint: disable=protected-access
    assert label == "v3"
    assert obj is versions[1]


def test_parse_version_number_variants() -> None:
    parse = deploy_module._parse_version_number  # pylint: disable=protected-access
    assert parse("v3") == 3
    assert parse("3") == 3
    assert parse("3.1.0") == 3
    assert parse("rc-1") is None


# ---------------------------------------------------------------------------
# _extract: read fields from MutableMapping-style SDK models.
#
# Root cause: ``azure.ai.projects.models.AgentVersionDetails`` (returned by
# ``client.agents.get_version`` in azure-ai-projects 2.0.1) is a
# ``collections.abc.MutableMapping`` subclass but is NOT a ``dict`` and does
# NOT expose its fields via ``getattr``. Without the Mapping branch the poll
# loop logged ``status=unknown`` for ~164s on real Azure deployments and
# timed out instead of failing fast when the platform reported ``failed``.
# ---------------------------------------------------------------------------


class _FakeAgentVersionDetails(collections.abc.MutableMapping):
    """``MutableMapping`` stand-in for the live SDK ``AgentVersionDetails``.

    Mirrors the verified shape from azure-ai-projects 2.0.1:

    * ``getattr(obj, "status", None) is None``
    * ``isinstance(obj, dict) is False``
    * ``isinstance(obj, collections.abc.Mapping) is True``
    * ``obj["status"]`` returns the value.
    """

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = dict(data)

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value

    def __delitem__(self, key: str) -> None:
        del self._data[key]

    def __iter__(self) -> Any:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)


def test_extract_reads_mapping_style_models() -> None:
    """``_extract`` must read fields from ``MutableMapping``-style SDK models.

    The live SDK shape (``AgentVersionDetails``) does not expose fields via
    ``getattr`` and is not a ``dict``. Without the ``Mapping`` branch
    ``_extract`` returns ``None`` and the poll loop normalises status to
    ``"unknown"``, masking real terminal states like ``failed``.
    """
    obj = _FakeAgentVersionDetails(
        {"status": "failed", "endpoint_url": "https://example/agents/x/endpoint"}
    )

    # Sanity: confirm the fake mirrors the live SDK shape.
    assert getattr(obj, "status", None) is None
    assert not isinstance(obj, dict)
    assert isinstance(obj, collections.abc.Mapping)

    extract = deploy_module._extract  # pylint: disable=protected-access
    assert extract(obj, "status") == "failed"
    assert extract(obj, "status", "provisioning_state") == "failed"
    assert extract(obj, "endpoint_url", "endpoint") == "https://example/agents/x/endpoint"
    assert extract(obj, "missing", "also_missing") is None
    # None obj remains a None passthrough.
    assert extract(None, "status") is None


def test_deploy_succeeds_with_mapping_style_get_version(
    monkeypatch: pytest.MonkeyPatch, manifest: HostedAgentManifest
) -> None:
    """End-to-end: ``get_version`` returns a ``MutableMapping`` (not a ``dict``).

    ``azure-ai-projects 2.0.1``'s ``client.agents.get_version`` returns an
    ``AgentVersionDetails`` model that is a ``MutableMapping`` subclass and
    does not expose ``status`` as an attribute. The poll loop must reach
    the terminal ``active`` status through the ``Mapping`` branch of
    ``_extract`` rather than treating every response as ``unknown``.
    """
    monkeypatch.setattr(deploy_module.time, "sleep", lambda _s: None)

    class _MappingAgentsClient:
        # pylint: disable=too-few-public-methods
        def __init__(self) -> None:
            self.create_calls: list[dict[str, Any]] = []
            self.get_calls: list[tuple[str, str | None]] = []
            self._poll_count = 0

        def create_version(self, *, agent_name: str, definition: Any) -> _FakeAgentVersionDetails:
            self.create_calls.append({"agent_name": agent_name, "definition": definition})
            # create_response is itself Mapping-style to mirror the live SDK.
            return _FakeAgentVersionDetails(
                {
                    "name": agent_name,
                    "version": "v1",
                    "status": "creating",
                    "endpoint_url": None,
                }
            )

        def get_version(self, *, agent_name: str, version: str | None) -> _FakeAgentVersionDetails:
            self.get_calls.append((agent_name, version))
            self._poll_count += 1
            if self._poll_count >= 2:
                return _FakeAgentVersionDetails(
                    {
                        "name": agent_name,
                        "version": version,
                        "status": "active",
                        "endpoint_url": ("https://example/agents/sample-hosted-agent/endpoint"),
                    }
                )
            return _FakeAgentVersionDetails(
                {
                    "name": agent_name,
                    "version": version,
                    "status": "provisioning",
                    "endpoint_url": None,
                }
            )

    agents = _MappingAgentsClient()
    client = _FakeProjectClient(agents)

    result = deploy_module.deploy_hosted_agent_version(
        manifest,
        image_uri="acr.example.io/sample:latest",
        project_endpoint="https://example/api/projects/sample",
        project_client=client,
        poll_interval_seconds=0.0,
    )

    # Without the Mapping branch result.status would be ``"unknown"`` and
    # the poll loop would time out instead of recognising ``active``.
    assert result.status == "active"
    assert result.succeeded
    assert result.version == "v1"
    assert result.endpoint_url == "https://example/agents/sample-hosted-agent/endpoint"
    assert agents.create_calls[0]["agent_name"] == "sample-hosted-agent"
    assert agents.get_calls and agents.get_calls[0][1] == "v1"
    assert result.polling_attempts >= 1


# ---------------------------------------------------------------------------
# Foundry User auto-grant (issue #1107).
#
# The per-version managed identity minted by ``create_version`` does not
# automatically receive the ``Foundry User`` role on the project scope, so
# every Playground / Responses invocation fails 401 on the storage POST.
# These tests cover the helpers + integration that consolidate the manual
# ``az role assignment create`` runbook step into the deploy code path.
# ---------------------------------------------------------------------------


class _AgentsWithIdentity(_FakeAgentsClient):
    """``_FakeAgentsClient`` that returns ``instance_identity.principal_id``."""

    def __init__(self, *, principal_id: str | None = "principal-abc", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._principal_id = principal_id

    def _decorate(self, ns: SimpleNamespace) -> SimpleNamespace:
        if self._principal_id is None:
            return ns
        ns.instance_identity = SimpleNamespace(principal_id=self._principal_id)
        return ns

    def create_version(self, *, agent_name: str, definition: Any) -> SimpleNamespace:
        return self._decorate(super().create_version(agent_name=agent_name, definition=definition))

    def get_version(self, agent_name: str, version: str | None = None) -> SimpleNamespace:
        return self._decorate(super().get_version(agent_name, version))


def test_extract_principal_id_from_instance_identity() -> None:
    """Default shape: ``version_obj.instance_identity.principal_id``."""
    obj = SimpleNamespace(instance_identity=SimpleNamespace(principal_id="abc-123"))
    assert deploy_module._extract_principal_id(obj) == "abc-123"  # pylint: disable=protected-access


def test_extract_principal_id_from_managed_identity_alias() -> None:
    """Older preview alias: ``managed_identity.principal_id``."""
    obj = SimpleNamespace(managed_identity=SimpleNamespace(principal_id="xyz-789"))
    assert deploy_module._extract_principal_id(obj) == "xyz-789"  # pylint: disable=protected-access


def test_extract_principal_id_from_mapping() -> None:
    """SDK 2.x MutableMapping models expose fields via ``__getitem__``."""

    class _Mapping(collections.abc.Mapping):  # pylint: disable=too-few-public-methods
        def __init__(self, data: dict[str, Any]) -> None:
            self._data = data

        def __getitem__(self, key: str) -> Any:
            return self._data[key]

        def __iter__(self):  # pragma: no cover - iteration not exercised
            return iter(self._data)

        def __len__(self) -> int:  # pragma: no cover - len not exercised
            return len(self._data)

    obj = _Mapping({"instance_identity": _Mapping({"principal_id": "from-mapping"})})
    assert (
        deploy_module._extract_principal_id(obj) == "from-mapping"
    )  # pylint: disable=protected-access


def test_extract_principal_id_returns_none_when_missing() -> None:
    obj = SimpleNamespace(name="agent", status="active")
    assert deploy_module._extract_principal_id(obj) is None  # pylint: disable=protected-access


def test_derive_project_scope_uses_resolver() -> None:
    """``scope_resolver`` is the test seam for the az lookup."""
    resolved = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/account-foo"
    scope = deploy_module._derive_project_scope_from_endpoint(  # pylint: disable=protected-access
        "https://account-foo.services.ai.azure.com/api/projects/proj-bar",
        scope_resolver=lambda _name: resolved,
    )
    assert scope == f"{resolved}/projects/proj-bar"


def test_derive_project_scope_rejects_malformed_endpoint() -> None:
    with pytest.raises(ValueError, match="Unexpected"):
        deploy_module._derive_project_scope_from_endpoint(  # pylint: disable=protected-access
            "https://example.com/not-a-foundry-endpoint",
            scope_resolver=lambda _: "ignored",
        )


def test_derive_project_scope_raises_when_resolver_returns_none() -> None:
    with pytest.raises(RuntimeError, match="ARM resource id"):
        deploy_module._derive_project_scope_from_endpoint(  # pylint: disable=protected-access
            "https://account-foo.services.ai.azure.com/api/projects/proj-bar",
            scope_resolver=lambda _name: None,
        )


def test_resolve_azure_cli_executable_prefers_windows_cmd(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Windows Azure CLI installs commonly expose ``az.cmd`` on PATH."""
    calls: list[str] = []
    az_cmd = "C:\\Program Files\\Microsoft SDKs\\Azure\\CLI2\\wbin\\az.cmd"

    def _fake_which(candidate: str) -> str | None:
        calls.append(candidate)
        return az_cmd if candidate == "az.cmd" else None

    monkeypatch.setattr(deploy_module.sys, "platform", "win32")
    monkeypatch.setattr(deploy_module.shutil, "which", _fake_which)

    resolver = getattr(deploy_module, "_resolve_azure_cli_executable")
    assert resolver() == az_cmd
    assert calls == ["az.cmd"]


def test_resolve_azure_cli_executable_falls_back_to_windows_exe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The resolver checks Windows launcher names before the bare command."""
    calls: list[str] = []
    az_exe = "C:\\Program Files\\Microsoft SDKs\\Azure\\CLI2\\wbin\\az.exe"

    def _fake_which(candidate: str) -> str | None:
        calls.append(candidate)
        return az_exe if candidate == "az.exe" else None

    monkeypatch.setattr(deploy_module.sys, "platform", "win32")
    monkeypatch.setattr(deploy_module.shutil, "which", _fake_which)

    resolver = getattr(deploy_module, "_resolve_azure_cli_executable")
    assert resolver() == az_exe
    assert calls == ["az.cmd", "az.exe"]


def test_resolve_azure_cli_executable_uses_bare_command_off_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def _fake_which(candidate: str) -> str | None:
        calls.append(candidate)
        return "/usr/bin/az" if candidate == "az" else None

    monkeypatch.setattr(deploy_module.sys, "platform", "linux")
    monkeypatch.setattr(deploy_module.shutil, "which", _fake_which)

    resolver = getattr(deploy_module, "_resolve_azure_cli_executable")
    assert resolver() == "/usr/bin/az"
    assert calls == ["az"]


def test_resolve_azure_cli_executable_raises_actionable_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(deploy_module.sys, "platform", "win32")
    monkeypatch.setattr(deploy_module.shutil, "which", lambda _candidate: None)

    resolver = getattr(deploy_module, "_resolve_azure_cli_executable")
    with pytest.raises(RuntimeError, match="Azure CLI executable not found"):
        resolver()


def test_resolve_ai_account_resource_id_via_az_uses_resolved_cli(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeProc:  # pylint: disable=too-few-public-methods
        def __init__(self) -> None:
            self.returncode = 0
            self.stdout = "/subscriptions/sub/resourceGroups/rg/providers/accounts/account-foo\n"
            self.stderr = ""

    captured: dict[str, Any] = {}
    az_cmd = "C:\\Program Files\\Microsoft SDKs\\Azure\\CLI2\\wbin\\az.cmd"

    def _fake_run(cmd: list[str], **_kw: Any) -> _FakeProc:
        captured["cmd"] = cmd
        return _FakeProc()

    monkeypatch.setattr(deploy_module, "_resolve_azure_cli_executable", lambda: az_cmd)
    monkeypatch.setattr(deploy_module.subprocess, "run", _fake_run)

    result = (
        deploy_module._resolve_ai_account_resource_id_via_az(  # pylint: disable=protected-access
            "account-foo"
        )
    )

    assert result == "/subscriptions/sub/resourceGroups/rg/providers/accounts/account-foo"
    assert captured["cmd"][0] == az_cmd
    assert captured["cmd"][1:3] == ["resource", "list"]


def test_deploy_auto_grants_foundry_user_after_active(
    monkeypatch: pytest.MonkeyPatch, manifest: HostedAgentManifest
) -> None:
    """End-to-end: deploy reaches ``active`` -> role grant fires with right inputs."""
    monkeypatch.setattr(deploy_module.time, "sleep", lambda _s: None)
    agents = _AgentsWithIdentity(polls_until_terminal=1, terminal_status="active")
    client = _FakeProjectClient(agents)

    granter_calls: list[dict[str, Any]] = []

    def _fake_granter(*, principal_id: str, scope: str, role_name: str) -> dict[str, str]:
        granter_calls.append({"principal_id": principal_id, "scope": scope, "role_name": role_name})
        return {
            "id": "/scope/providers/Microsoft.Authorization/roleAssignments/aaa",
            "scope": scope,
        }

    result = deploy_module.deploy_hosted_agent_version(
        manifest,
        image_uri="acr.example.io/sample:latest",
        project_endpoint="https://account-foo.services.ai.azure.com/api/projects/proj-bar",
        project_client=client,
        poll_interval_seconds=0.0,
        scope_resolver=lambda _name: "/sub/rg/providers/Microsoft.CognitiveServices/accounts/account-foo",
        role_granter=_fake_granter,
    )

    assert result.status == "active"
    assert len(granter_calls) == 1
    assert granter_calls[0]["principal_id"] == "principal-abc"
    assert granter_calls[0]["role_name"] == "Foundry User"
    assert granter_calls[0]["scope"].endswith("/projects/proj-bar")
    grant_payload = result.extras["role_grant"]
    assert grant_payload["status"] == "granted"
    assert grant_payload["principal_id"] == "principal-abc"
    assert grant_payload["role_name"] == "Foundry User"


def test_deploy_skips_grant_when_auto_grant_disabled(
    monkeypatch: pytest.MonkeyPatch, manifest: HostedAgentManifest
) -> None:
    monkeypatch.setattr(deploy_module.time, "sleep", lambda _s: None)
    agents = _AgentsWithIdentity(polls_until_terminal=1, terminal_status="active")
    client = _FakeProjectClient(agents)

    granter_calls: list[Any] = []

    result = deploy_module.deploy_hosted_agent_version(
        manifest,
        image_uri="acr.example.io/sample:latest",
        project_endpoint="https://account-foo.services.ai.azure.com/api/projects/proj-bar",
        project_client=client,
        poll_interval_seconds=0.0,
        auto_grant_role=False,
        role_granter=lambda **kw: granter_calls.append(kw) or {},
        scope_resolver=lambda _n: "/should/not/be/called",
    )

    assert result.status == "active"
    assert granter_calls == []
    assert result.extras["role_grant"]["status"] == "skipped"


def test_deploy_records_already_exists_when_granter_returns_none(
    monkeypatch: pytest.MonkeyPatch, manifest: HostedAgentManifest
) -> None:
    monkeypatch.setattr(deploy_module.time, "sleep", lambda _s: None)
    agents = _AgentsWithIdentity(polls_until_terminal=1, terminal_status="active")
    client = _FakeProjectClient(agents)

    result = deploy_module.deploy_hosted_agent_version(
        manifest,
        image_uri="acr.example.io/sample:latest",
        project_endpoint="https://account-foo.services.ai.azure.com/api/projects/proj-bar",
        project_client=client,
        poll_interval_seconds=0.0,
        scope_resolver=lambda _n: "/sub/rg/providers/Microsoft.CognitiveServices/accounts/account-foo",
        role_granter=lambda **kw: None,  # idempotent: assignment already existed
    )

    assert result.status == "active"
    grant_payload = result.extras["role_grant"]
    assert grant_payload["status"] == "already_exists"
    assert grant_payload["principal_id"] == "principal-abc"


def test_deploy_surfaces_grant_failure_without_breaking_active(
    monkeypatch: pytest.MonkeyPatch, manifest: HostedAgentManifest
) -> None:
    """A failed role grant must NOT mask a successful version activation.

    The version is already ``active`` in Foundry; the operator can re-run
    the grant by hand or re-deploy. The recorded ``role_grant.status`` is
    ``failed`` so the failure is observable.
    """
    monkeypatch.setattr(deploy_module.time, "sleep", lambda _s: None)
    agents = _AgentsWithIdentity(polls_until_terminal=1, terminal_status="active")
    client = _FakeProjectClient(agents)

    def _broken_granter(**_kwargs: Any) -> None:
        raise RuntimeError("az failed: insufficient permissions")

    result = deploy_module.deploy_hosted_agent_version(
        manifest,
        image_uri="acr.example.io/sample:latest",
        project_endpoint="https://account-foo.services.ai.azure.com/api/projects/proj-bar",
        project_client=client,
        poll_interval_seconds=0.0,
        scope_resolver=lambda _n: "/sub/rg/providers/Microsoft.CognitiveServices/accounts/account-foo",
        role_granter=_broken_granter,
    )

    assert result.status == "active"
    assert result.succeeded
    grant_payload = result.extras["role_grant"]
    assert grant_payload["status"] == "failed"
    assert "insufficient permissions" in grant_payload["error"]


def test_deploy_captures_cli_resolution_failure_without_breaking_active(
    monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> None:
    """Missing Azure CLI is recorded as role-grant failure, not deploy failure."""
    monkeypatch.setattr(deploy_module.time, "sleep", lambda _s: None)
    test_manifest = request.getfixturevalue("manifest")
    agents = _AgentsWithIdentity(polls_until_terminal=1, terminal_status="active")
    client = _FakeProjectClient(agents)

    def _missing_cli() -> str:
        raise RuntimeError("Azure CLI executable not found")

    monkeypatch.setattr(deploy_module, "_resolve_azure_cli_executable", _missing_cli)

    result = deploy_module.deploy_hosted_agent_version(
        test_manifest,
        image_uri="acr.example.io/sample:latest",
        project_endpoint="https://account-foo.services.ai.azure.com/api/projects/proj-bar",
        project_client=client,
        poll_interval_seconds=0.0,
        project_scope=(
            "/subscriptions/sub-id/resourceGroups/my-rg/providers/"
            "Microsoft.CognitiveServices/accounts/account-foo/projects/proj-bar"
        ),
    )

    assert result.status == "active"
    assert result.succeeded
    grant_payload = result.extras["role_grant"]
    assert grant_payload["status"] == "failed"
    assert "Azure CLI executable not found" in grant_payload["error"]


def test_deploy_records_skipped_when_principal_id_missing(
    monkeypatch: pytest.MonkeyPatch, manifest: HostedAgentManifest
) -> None:
    """If the SDK doesn't surface a principal id, skip gracefully."""
    monkeypatch.setattr(deploy_module.time, "sleep", lambda _s: None)
    agents = _AgentsWithIdentity(
        polls_until_terminal=1, terminal_status="active", principal_id=None
    )
    client = _FakeProjectClient(agents)

    granter_calls: list[Any] = []

    result = deploy_module.deploy_hosted_agent_version(
        manifest,
        image_uri="acr.example.io/sample:latest",
        project_endpoint="https://account-foo.services.ai.azure.com/api/projects/proj-bar",
        project_client=client,
        poll_interval_seconds=0.0,
        role_granter=lambda **kw: granter_calls.append(kw) or {},
    )

    assert result.status == "active"
    assert granter_calls == []
    grant_payload = result.extras["role_grant"]
    assert grant_payload["status"] == "skipped"
    assert grant_payload["reason"] == "no_principal_id"


def test_deploy_uses_explicit_project_scope_override(
    monkeypatch: pytest.MonkeyPatch, manifest: HostedAgentManifest
) -> None:
    """``project_scope`` skips the resolver entirely."""
    monkeypatch.setattr(deploy_module.time, "sleep", lambda _s: None)
    agents = _AgentsWithIdentity(polls_until_terminal=1, terminal_status="active")
    client = _FakeProjectClient(agents)

    granter_calls: list[dict[str, Any]] = []
    explicit_scope = (
        "/subscriptions/sub-id/resourceGroups/my-rg/providers/"
        "Microsoft.CognitiveServices/accounts/account-foo/projects/proj-bar"
    )

    def _resolver(_name: str) -> str:
        raise AssertionError("scope_resolver must not run when project_scope is set")

    def _granter(*, principal_id: str, scope: str, role_name: str) -> dict[str, str]:
        granter_calls.append({"principal_id": principal_id, "scope": scope, "role_name": role_name})
        return {"id": "ra-id", "scope": scope}

    result = deploy_module.deploy_hosted_agent_version(
        manifest,
        image_uri="acr.example.io/sample:latest",
        project_endpoint="https://account-foo.services.ai.azure.com/api/projects/proj-bar",
        project_client=client,
        poll_interval_seconds=0.0,
        project_scope=explicit_scope,
        scope_resolver=_resolver,
        role_granter=_granter,
    )

    assert result.status == "active"
    assert granter_calls[0]["scope"] == explicit_scope
    assert result.extras["role_grant"]["scope"] == explicit_scope


def test_grant_role_via_az_treats_already_exists_as_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default granter: ``RoleAssignmentExists`` -> ``None`` (idempotent)."""

    class _FakeProc:  # pylint: disable=too-few-public-methods
        def __init__(self, *, returncode: int, stdout: str = "", stderr: str = "") -> None:
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def _fake_run(cmd: list[str], **_kw: Any) -> _FakeProc:
        assert cmd[:2] == ["az", "role"], cmd
        return _FakeProc(
            returncode=1,
            stderr="The role assignment already exists. (RoleAssignmentExists)",
        )

    monkeypatch.setattr(deploy_module, "_resolve_azure_cli_executable", lambda: "az")
    monkeypatch.setattr(deploy_module.subprocess, "run", _fake_run)
    result = deploy_module._grant_role_via_az(  # pylint: disable=protected-access
        principal_id="abc-123",
        scope="/scope",
        role_name="Foundry User",
    )
    assert result is None


def test_grant_role_via_az_raises_on_real_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeProc:  # pylint: disable=too-few-public-methods
        def __init__(self, *, returncode: int, stdout: str = "", stderr: str = "") -> None:
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    monkeypatch.setattr(deploy_module, "_resolve_azure_cli_executable", lambda: "az")
    monkeypatch.setattr(
        deploy_module.subprocess,
        "run",
        lambda *_a, **_kw: _FakeProc(
            returncode=2, stderr="AuthorizationFailed: principal not allowed"
        ),
    )

    with pytest.raises(RuntimeError, match="AuthorizationFailed"):
        deploy_module._grant_role_via_az(  # pylint: disable=protected-access
            principal_id="abc-123",
            scope="/scope",
            role_name="Foundry User",
        )


def test_grant_role_via_az_parses_assignment_id_on_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeProc:  # pylint: disable=too-few-public-methods
        def __init__(self, *, returncode: int, stdout: str = "", stderr: str = "") -> None:
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    payload = (
        '{"id": "/scope/providers/Microsoft.Authorization/roleAssignments/aaa",'
        ' "principalId": "abc-123"}'
    )
    captured: dict[str, Any] = {}
    az_cmd = "C:\\Program Files\\Microsoft SDKs\\Azure\\CLI2\\wbin\\az.cmd"

    def _fake_run(cmd: list[str], **_kw: Any) -> _FakeProc:
        captured["cmd"] = cmd
        return _FakeProc(returncode=0, stdout=payload)

    monkeypatch.setattr(deploy_module, "_resolve_azure_cli_executable", lambda: az_cmd)
    monkeypatch.setattr(deploy_module.subprocess, "run", _fake_run)

    result = deploy_module._grant_role_via_az(  # pylint: disable=protected-access
        principal_id="abc-123",
        scope="/scope",
        role_name="Foundry User",
    )
    assert result is not None
    assert result["id"].endswith("/aaa")
    assert result["principal_id"] == "abc-123"
    assert result["scope"] == "/scope"
    assert captured["cmd"][0] == az_cmd
    assert captured["cmd"][1:4] == ["role", "assignment", "create"]
