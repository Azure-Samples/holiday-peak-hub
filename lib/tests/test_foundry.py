"""Tests for Azure AI Foundry integration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from azure.core.exceptions import HttpResponseError
from holiday_peak_lib.agents.foundry import (
    FoundryAgentConfig,
    FoundryAgentInvoker,
    _ensure_client,
    build_foundry_model_target,
    ensure_foundry_agent,
)

TEST_PROJECT_NAME = "test-project"
TEST_PROJECT_ENDPOINT = f"https://test.services.ai.azure.com/api/projects/{TEST_PROJECT_NAME}"
TEST_RESOURCE_ENDPOINT = "https://test.cognitiveservices.azure.com"
ALTERNATE_PROJECT_NAME = "alternate-project"
ALTERNATE_PROJECT_ENDPOINT = (
    f"https://alternate.services.ai.azure.com/api/projects/{ALTERNATE_PROJECT_NAME}"
)
ALTERNATE_RESOURCE_ENDPOINT = "https://alternate.cognitiveservices.azure.com"


class TestFoundryAgentConfig:
    """Tests for FoundryAgentConfig."""

    def test_from_env_with_all_vars(self, monkeypatch):
        """Test config creation from environment variables."""
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_RESOURCE_ENDPOINT)
        monkeypatch.setenv("PROJECT_NAME", TEST_PROJECT_NAME)
        monkeypatch.setenv("FOUNDRY_AGENT_ID", "agent-123")
        monkeypatch.setenv("MODEL_DEPLOYMENT_NAME", "gpt-4")
        monkeypatch.setenv("FOUNDRY_STREAM", "true")

        config = FoundryAgentConfig.from_env()

        assert config.endpoint == TEST_PROJECT_ENDPOINT
        assert config.project_name == TEST_PROJECT_NAME
        assert config.agent_id == "agent-123"
        assert config.runtime_agent_id is None
        assert config.deployment_name == "gpt-4"
        assert config.stream is True

    def test_from_env_with_alternate_vars(self, monkeypatch):
        """Test config creation using alternate env var names."""
        monkeypatch.delenv("PROJECT_ENDPOINT", raising=False)
        monkeypatch.delenv("PROJECT_NAME", raising=False)
        monkeypatch.delenv("FOUNDRY_AGENT_ID", raising=False)
        monkeypatch.setenv("FOUNDRY_ENDPOINT", ALTERNATE_RESOURCE_ENDPOINT)
        monkeypatch.setenv("FOUNDRY_PROJECT_NAME", ALTERNATE_PROJECT_NAME)
        monkeypatch.setenv("AGENT_ID", "agent-456")

        config = FoundryAgentConfig.from_env()

        assert config.endpoint == ALTERNATE_PROJECT_ENDPOINT
        assert config.project_name == ALTERNATE_PROJECT_NAME
        assert config.agent_id == "agent-456"
        assert config.runtime_agent_id is None

    def test_from_env_with_name_only_stays_unresolved_for_runtime(self, monkeypatch):
        """Test name-only config remains lookup-capable but unbound for runtime."""
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
        monkeypatch.delenv("FOUNDRY_AGENT_ID", raising=False)
        monkeypatch.delenv("AGENT_ID", raising=False)
        monkeypatch.setenv("FOUNDRY_AGENT_NAME", "catalog-fast")

        config = FoundryAgentConfig.from_env()

        assert config.agent_id == "pending"
        assert config.agent_name == "catalog-fast"
        assert config.runtime_agent_id is None

    def test_name_like_agent_id_without_agent_name_stays_unresolved(self):
        """agent_id that looks like a name should NOT auto-promote to resolved."""
        config = FoundryAgentConfig(
            endpoint=TEST_PROJECT_ENDPOINT,
            agent_id="ecommerce-catalog-search-fast",
        )
        assert config.resolved_agent_id is None
        assert config.runtime_agent_id is None

    def test_resolved_agent_id_only_from_explicit_constructor_arg(self):
        """Explicitly passed resolved_agent_id is preserved when valid."""
        config = FoundryAgentConfig(
            endpoint=TEST_PROJECT_ENDPOINT,
            agent_id="pending",
            agent_name="catalog-fast",
            resolved_agent_id="asst_real123",
        )
        assert config.resolved_agent_id == "asst_real123"
        assert config.runtime_agent_id == "asst_real123"

    def test_from_env_extracts_project_name_from_project_endpoint(self, monkeypatch):
        """Test project-scoped endpoints remain valid without a separate project name."""
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
        monkeypatch.delenv("PROJECT_NAME", raising=False)
        monkeypatch.setenv("FOUNDRY_AGENT_ID", "agent-123")

        config = FoundryAgentConfig.from_env()

        assert config.endpoint == TEST_PROJECT_ENDPOINT
        assert config.project_name == TEST_PROJECT_NAME

    def test_from_env_rejects_mismatched_project_name(self, monkeypatch):
        """Test mismatch between endpoint path and project name fails fast."""
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
        monkeypatch.setenv("PROJECT_NAME", "other-project")
        monkeypatch.setenv("FOUNDRY_AGENT_ID", "agent-123")

        with pytest.raises(ValueError, match="must match the project encoded"):
            FoundryAgentConfig.from_env()

    def test_from_env_rejects_unscoped_endpoint_without_project_name(self, monkeypatch):
        """Test account endpoints require a project name for derivation."""
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_RESOURCE_ENDPOINT)
        monkeypatch.delenv("PROJECT_NAME", raising=False)
        monkeypatch.setenv("FOUNDRY_AGENT_ID", "agent-123")

        with pytest.raises(ValueError, match="PROJECT_NAME/FOUNDRY_PROJECT_NAME is required"):
            FoundryAgentConfig.from_env()

    def test_from_env_missing_endpoint(self, monkeypatch):
        """Test error when endpoint is missing."""
        monkeypatch.setenv("FOUNDRY_AGENT_ID", "agent-123")
        monkeypatch.delenv("PROJECT_ENDPOINT", raising=False)
        monkeypatch.delenv("FOUNDRY_ENDPOINT", raising=False)

        with pytest.raises(ValueError, match="PROJECT_ENDPOINT/FOUNDRY_ENDPOINT"):
            FoundryAgentConfig.from_env()

    def test_from_env_missing_agent_id(self, monkeypatch):
        """Test error when agent ID is missing."""
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
        monkeypatch.delenv("FOUNDRY_AGENT_ID", raising=False)
        monkeypatch.delenv("FOUNDRY_AGENT_NAME", raising=False)
        monkeypatch.delenv("AGENT_ID", raising=False)

        with pytest.raises(ValueError, match="FOUNDRY_AGENT_ID or FOUNDRY_AGENT_NAME"):
            FoundryAgentConfig.from_env()

    def test_stream_flag_variants(self, monkeypatch):
        """Test different stream flag values — streaming is on by default."""
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
        monkeypatch.setenv("FOUNDRY_AGENT_ID", "agent-123")

        # Test "1" → True
        monkeypatch.setenv("FOUNDRY_STREAM", "1")
        assert FoundryAgentConfig.from_env().stream is True

        # Test "yes" → True
        monkeypatch.setenv("FOUNDRY_STREAM", "yes")
        assert FoundryAgentConfig.from_env().stream is True

        # Test "true" → True
        monkeypatch.setenv("FOUNDRY_STREAM", "true")
        assert FoundryAgentConfig.from_env().stream is True

        # Test "false" → False (explicit opt-out)
        monkeypatch.setenv("FOUNDRY_STREAM", "false")
        assert FoundryAgentConfig.from_env().stream is False

        # Test "0" → False (explicit opt-out)
        monkeypatch.setenv("FOUNDRY_STREAM", "0")
        assert FoundryAgentConfig.from_env().stream is False

        # Test "no" → False (explicit opt-out)
        monkeypatch.setenv("FOUNDRY_STREAM", "no")
        assert FoundryAgentConfig.from_env().stream is False

        # Test default (unset) → True (streaming-first)
        monkeypatch.delenv("FOUNDRY_STREAM", raising=False)
        assert FoundryAgentConfig.from_env().stream is True


class TestBuildFoundryModelTarget:
    """Tests for build_foundry_model_target function."""

    def test_build_model_target_basic(self):
        """Test building a basic foundry model target."""
        config = FoundryAgentConfig(
            endpoint=TEST_PROJECT_ENDPOINT,
            agent_id="agent-123",
            deployment_name="gpt-4",
            resolved_agent_id="agent-123",
        )

        target = build_foundry_model_target(config)

        assert target.name == "agent-123"
        assert target.model == "gpt-4"
        assert target.stream is True  # streaming-first default
        assert isinstance(target.invoker, FoundryAgentInvoker)

    def test_build_model_target_with_streaming(self):
        """Test building a streaming model target."""
        config = FoundryAgentConfig(
            endpoint=TEST_PROJECT_ENDPOINT,
            agent_id="agent-456",
            stream=True,
            resolved_agent_id="agent-456",
        )

        target = build_foundry_model_target(config)

        assert target.name == "agent-456"
        assert target.model == "agent-456"  # Falls back to agent_id when no deployment
        assert target.stream is True

    def test_build_model_target_requires_resolved_runtime_id(self):
        """Test name-only or pending configs cannot bind as live runtime targets."""
        config = FoundryAgentConfig(
            endpoint=TEST_PROJECT_ENDPOINT,
            agent_id="pending",
            agent_name="catalog-fast",
        )

        with pytest.raises(ValueError, match="resolved agent id"):
            build_foundry_model_target(config)


@pytest.mark.asyncio
class TestFoundryAgentInvokerMessages:
    """Tests for FoundryAgentInvoker message normalization."""

    @patch("holiday_peak_lib.agents.foundry.MAFMessage")
    @patch("holiday_peak_lib.agents.foundry.FoundryAgent")
    async def test_dict_content_serialized_to_json(self, mock_foundry_agent_cls, mock_message_cls):
        """Dict message content is JSON-serialized before passing to MAF."""
        mock_agent_instance = AsyncMock()
        mock_agent_instance.run = AsyncMock(return_value=MagicMock(text="ok"))
        mock_foundry_agent_cls.return_value = mock_agent_instance

        config = FoundryAgentConfig(
            endpoint=TEST_PROJECT_ENDPOINT,
            agent_id="test-agent",
            agent_name="test-agent",
            deployment_name="gpt-5-nano",
            resolved_agent_id="test-agent",
        )
        invoker = FoundryAgentInvoker(config)

        await invoker(
            messages=[
                {"role": "user", "content": {"query": "sweater", "results": []}},
            ],
            model="gpt-5-nano",
        )

        # The MAFMessage constructor should receive a JSON string, not a dict
        call_args = mock_message_cls.call_args
        contents = call_args.kwargs.get("contents") or call_args[1].get(
            "contents", call_args[0][1] if len(call_args[0]) > 1 else None
        )
        assert contents is not None
        assert isinstance(contents[0], str)
        assert '"query"' in contents[0]

    @patch("holiday_peak_lib.agents.foundry.MAFMessage")
    @patch("holiday_peak_lib.agents.foundry.FoundryAgent")
    async def test_string_content_passed_directly(self, mock_foundry_agent_cls, mock_message_cls):
        """String message content is passed through unchanged."""
        mock_agent_instance = AsyncMock()
        mock_agent_instance.run = AsyncMock(return_value=MagicMock(text="ok"))
        mock_foundry_agent_cls.return_value = mock_agent_instance

        config = FoundryAgentConfig(
            endpoint=TEST_PROJECT_ENDPOINT,
            agent_id="test-agent",
            agent_name="test-agent",
            deployment_name="gpt-5-nano",
            resolved_agent_id="test-agent",
        )
        invoker = FoundryAgentInvoker(config)

        await invoker(
            messages=[{"role": "user", "content": "hello world"}],
            model="gpt-5-nano",
        )

        call_args = mock_message_cls.call_args
        contents = call_args.kwargs.get("contents") or call_args[1].get(
            "contents", call_args[0][1] if len(call_args[0]) > 1 else None
        )
        assert contents is not None
        assert contents[0] == "hello world"


@pytest.mark.asyncio
class TestFoundryAgentInvokerSession:
    """Tests for AgentSession handling in FoundryAgentInvoker."""

    @patch("holiday_peak_lib.agents.foundry.FoundryAgent")
    async def test_session_id_creates_agent_session(self, mock_foundry_agent_cls):
        """When session_id is provided, an AgentSession is passed to agent.run()."""
        mock_agent = AsyncMock()
        response_mock = MagicMock(text="response text")
        response_mock.session = None
        mock_agent.run = AsyncMock(return_value=response_mock)
        mock_foundry_agent_cls.return_value = mock_agent

        config = FoundryAgentConfig(
            endpoint=TEST_PROJECT_ENDPOINT,
            agent_id="test-agent",
            agent_name="test-agent",
            deployment_name="gpt-5-nano",
            resolved_agent_id="test-agent",
        )
        invoker = FoundryAgentInvoker(config)

        await invoker(
            messages=[{"role": "user", "content": "hello"}],
            model="gpt-5-nano",
            session_id="page-session-abc",
        )

        run_call = mock_agent.run
        assert run_call.called
        call_kwargs = run_call.call_args.kwargs
        assert "session" in call_kwargs
        session = call_kwargs["session"]
        assert session.session_id == "page-session-abc"

    @patch("holiday_peak_lib.agents.foundry.FoundryAgent")
    async def test_session_state_restores_from_dict(self, mock_foundry_agent_cls):
        """When _foundry_session_state dict is provided, AgentSession.from_dict is used."""
        mock_agent = AsyncMock()
        response_mock = MagicMock(text="ok")
        response_mock.session = None
        mock_agent.run = AsyncMock(return_value=response_mock)
        mock_foundry_agent_cls.return_value = mock_agent

        config = FoundryAgentConfig(
            endpoint=TEST_PROJECT_ENDPOINT,
            agent_id="test-agent",
            agent_name="test-agent",
            deployment_name="gpt-5-nano",
            resolved_agent_id="test-agent",
        )
        invoker = FoundryAgentInvoker(config)

        session_state = {
            "type": "session",
            "session_id": "page-session-abc",
            "service_session_id": "foundry-thread-xyz",
            "state": {},
        }
        await invoker(
            messages=[{"role": "user", "content": "follow-up"}],
            model="gpt-5-nano",
            session_id="page-session-abc",
            _foundry_session_state=session_state,
        )

        call_kwargs = mock_agent.run.call_args.kwargs
        session = call_kwargs["session"]
        assert session.session_id == "page-session-abc"
        serialized = session.to_dict()
        assert serialized["service_session_id"] == "foundry-thread-xyz"

    @patch("holiday_peak_lib.agents.foundry.FoundryAgent")
    async def test_no_session_when_no_session_id(self, mock_foundry_agent_cls):
        """When no session_id is provided, session kwarg is not passed."""
        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock(text="ok"))
        mock_foundry_agent_cls.return_value = mock_agent

        config = FoundryAgentConfig(
            endpoint=TEST_PROJECT_ENDPOINT,
            agent_id="test-agent",
            agent_name="test-agent",
            deployment_name="gpt-5-nano",
            resolved_agent_id="test-agent",
        )
        invoker = FoundryAgentInvoker(config)

        await invoker(
            messages=[{"role": "user", "content": "hello"}],
            model="gpt-5-nano",
        )

        call_kwargs = mock_agent.run.call_args.kwargs
        assert "session" not in call_kwargs

    @patch("holiday_peak_lib.agents.foundry.FoundryAgent")
    async def test_response_includes_session_state(self, mock_foundry_agent_cls):
        """Response includes _foundry_session_state when session is used."""
        mock_agent = AsyncMock()
        resp_session_mock = MagicMock()
        resp_session_mock.to_dict.return_value = {
            "type": "session",
            "session_id": "page-abc",
            "service_session_id": "foundry-thread-new",
            "state": {},
        }
        response_mock = MagicMock(text="answer")
        response_mock.session = resp_session_mock
        mock_agent.run = AsyncMock(return_value=response_mock)
        mock_foundry_agent_cls.return_value = mock_agent

        config = FoundryAgentConfig(
            endpoint=TEST_PROJECT_ENDPOINT,
            agent_id="test-agent",
            agent_name="test-agent",
            deployment_name="gpt-5-nano",
            resolved_agent_id="test-agent",
        )
        invoker = FoundryAgentInvoker(config)

        result = await invoker(
            messages=[{"role": "user", "content": "hello"}],
            model="gpt-5-nano",
            session_id="page-abc",
        )

        assert "_foundry_session_state" in result
        assert result["_foundry_session_state"]["service_session_id"] == "foundry-thread-new"


@pytest.mark.asyncio
class TestEnsureFoundryAgent:
    """Tests for ensure_foundry_agent helper."""

    @patch("holiday_peak_lib.agents.foundry.AIProjectClient")
    @patch("holiday_peak_lib.agents.foundry.DefaultAzureCredential")
    async def test_ensure_client_derives_project_endpoint(
        self, mock_credential_cls, mock_client_cls
    ):
        """Test ensure path always uses the normalized project endpoint."""
        credential = MagicMock()
        mock_credential_cls.return_value = credential
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        config = FoundryAgentConfig(
            endpoint=TEST_RESOURCE_ENDPOINT,
            project_name=TEST_PROJECT_NAME,
            agent_id="agent-123",
        )

        result = _ensure_client(config)

        assert result is mock_client
        mock_client_cls.assert_called_once_with(
            endpoint=TEST_PROJECT_ENDPOINT,
            credential=credential,
        )

    async def test_ensure_agent_exists_by_id(self):
        config = FoundryAgentConfig(
            endpoint=TEST_PROJECT_ENDPOINT,
            agent_id="agent-123:1",
            resolved_agent_id="agent-123:1",
        )
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_agents = MagicMock()
        mock_agents.create_version = AsyncMock()
        mock_agents.list = AsyncMock(return_value=[{"id": "agent-123:1", "name": "svc-fast"}])
        mock_client.agents = mock_agents

        with patch("holiday_peak_lib.agents.foundry._ensure_client", return_value=mock_client):
            result = await ensure_foundry_agent(config)

        assert result["status"] == "exists"
        assert result["agent_id"] == "agent-123:1"
        assert result["created"] is False

    async def test_ensure_agent_found_by_name(self):
        config = FoundryAgentConfig(
            endpoint=TEST_PROJECT_ENDPOINT,
            agent_id="pending",
            agent_name="svc-fast",
        )
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_agents = MagicMock()
        mock_agents.create_version = AsyncMock()
        mock_agents.list = AsyncMock(return_value=[{"id": "agent-999", "name": "svc-fast"}])
        mock_client.agents = mock_agents

        with patch("holiday_peak_lib.agents.foundry._ensure_client", return_value=mock_client):
            result = await ensure_foundry_agent(config)

        assert result["status"] == "found_by_name"
        assert result["agent_id"] == "agent-999"
        assert result["created"] is False

    async def test_ensure_agent_creates_when_missing(self):
        config = FoundryAgentConfig(endpoint=TEST_PROJECT_ENDPOINT, agent_id="missing-id")
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_agents = MagicMock()
        mock_agents.create_version = AsyncMock(
            return_value={"id": "svc-fast:1", "name": "svc-fast"}
        )
        mock_agents.list = AsyncMock(return_value=[])
        mock_client.agents = mock_agents

        with patch("holiday_peak_lib.agents.foundry._ensure_client", return_value=mock_client):
            result = await ensure_foundry_agent(
                config,
                agent_name="svc-fast",
                instructions="Use Foundry instructions",
                create_if_missing=True,
                model="gpt-4o-mini",
            )

        assert result["status"] == "created"
        assert result["agent_id"] == "svc-fast:1"
        assert result["created"] is True

    async def test_ensure_agent_creates_when_list_fails(self):
        config = FoundryAgentConfig(
            endpoint=TEST_PROJECT_ENDPOINT,
            agent_id="missing-id",
            deployment_name="gpt-4o-mini",
        )
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_agents = MagicMock()
        mock_agents.create_version = AsyncMock(
            return_value={"id": "svc-fast:2", "name": "svc-fast"}
        )
        mock_agents.list = AsyncMock(side_effect=RuntimeError("service invocation"))
        mock_client.agents = mock_agents

        with patch("holiday_peak_lib.agents.foundry._ensure_client", return_value=mock_client):
            result = await ensure_foundry_agent(
                config,
                agent_name="svc-fast",
                create_if_missing=True,
            )

        assert result["status"] == "created"
        assert result["agent_id"] == "svc-fast:2"

    async def test_ensure_agent_returns_missing_model_when_create_requested(self):
        config = FoundryAgentConfig(endpoint=TEST_PROJECT_ENDPOINT, agent_id="missing-id")
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_agents = MagicMock()
        mock_agents.create_version = AsyncMock()
        mock_agents.list = AsyncMock(return_value=[])
        mock_client.agents = mock_agents

        with patch("holiday_peak_lib.agents.foundry._ensure_client", return_value=mock_client):
            result = await ensure_foundry_agent(
                config,
                agent_name="svc-fast",
                create_if_missing=True,
            )

        assert result["status"] == "missing_model"
        assert result["created"] is False

    async def test_ensure_agent_returns_create_failed_on_service_invocation(self):
        config = FoundryAgentConfig(
            endpoint=TEST_PROJECT_ENDPOINT,
            agent_id="missing-id",
            deployment_name="gpt-4o-mini",
        )
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_agents = MagicMock()
        mock_agents.create_version = AsyncMock(
            side_effect=HttpResponseError(
                message="(UserError.ServiceInvocationException) Encounter exception while calling dependency services"
            )
        )
        mock_agents.list = AsyncMock(return_value=[])
        mock_client.agents = mock_agents

        with patch("holiday_peak_lib.agents.foundry._ensure_client", return_value=mock_client):
            result = await ensure_foundry_agent(
                config,
                agent_name="svc-fast",
                create_if_missing=True,
            )

        assert result["status"] == "agents_service_unavailable"
        assert result["created"] is False
        assert result["error_code"] == "UserError.ServiceInvocationException"

    async def test_ensure_agent_returns_agents_unavailable_on_list(self):
        config = FoundryAgentConfig(endpoint=TEST_PROJECT_ENDPOINT, agent_id="missing-id")
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_agents = MagicMock()
        mock_agents.create_version = AsyncMock()
        mock_agents.list = AsyncMock(
            side_effect=HttpResponseError(
                message="(UserError.ServiceInvocationException) Encounter exception while calling dependency services"
            )
        )
        mock_client.agents = mock_agents

        with patch("holiday_peak_lib.agents.foundry._ensure_client", return_value=mock_client):
            result = await ensure_foundry_agent(
                config,
                agent_name="svc-fast",
                create_if_missing=True,
                model="gpt-4o-mini",
            )

        assert result["status"] == "agents_service_unavailable"
        assert result["created"] is False
