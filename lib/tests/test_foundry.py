"""Tests for Azure AI Foundry integration."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from azure.core.exceptions import HttpResponseError
from holiday_peak_lib.agents.foundry import (
    FoundryAgentConfig,
    FoundryInvoker,
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
        assert config.runtime_agent_id == "agent-123"
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
        assert config.runtime_agent_id == "agent-456"

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
        """Test different stream flag values."""
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
        monkeypatch.setenv("FOUNDRY_AGENT_ID", "agent-123")

        # Test "1"
        monkeypatch.setenv("FOUNDRY_STREAM", "1")
        assert FoundryAgentConfig.from_env().stream is True

        # Test "yes"
        monkeypatch.setenv("FOUNDRY_STREAM", "yes")
        assert FoundryAgentConfig.from_env().stream is True

        # Test "false"
        monkeypatch.setenv("FOUNDRY_STREAM", "false")
        assert FoundryAgentConfig.from_env().stream is False


@pytest.mark.asyncio
class TestFoundryInvoker:
    """Tests for FoundryInvoker."""

    @patch("holiday_peak_lib.agents.foundry._ensure_agents_client")
    async def test_invoke_non_streaming(self, mock_ensure_agents_client):
        """Test non-streaming invocation."""
        config = FoundryAgentConfig(
            endpoint=TEST_PROJECT_ENDPOINT,
            agent_id="agent-123",
            agent_name="catalog-fast",
            stream=False,
        )

        # Create mock runtime client structure
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        mock_client_instance.threads = MagicMock()
        mock_client_instance.messages = MagicMock()
        mock_client_instance.runs = MagicMock()

        mock_client_instance.threads.create = AsyncMock(
            return_value=SimpleNamespace(id="thread-123")
        )
        mock_client_instance.messages.create = AsyncMock(return_value=SimpleNamespace(id="msg-1"))
        mock_client_instance.messages.get_last_message_text_by_role = AsyncMock(
            return_value=SimpleNamespace(text=SimpleNamespace(value="ok"))
        )
        mock_client_instance.runs.create_and_process = AsyncMock(
            return_value=SimpleNamespace(
                id="run-123",
                status="completed",
                usage={"total_tokens": 10},
            )
        )
        mock_ensure_agents_client.return_value = mock_client_instance

        # Test invocation
        invoker = FoundryInvoker(config)
        result = await invoker(messages="Test query")

        assert result["thread_id"] == "thread-123"
        assert result["conversation_id"] == "thread-123"
        assert result["run_id"] == "run-123"
        assert result["response_id"] == "run-123"
        assert not result["stream"]
        assert "telemetry" in result
        assert result["telemetry"]["endpoint"] == TEST_PROJECT_ENDPOINT
        assert result["telemetry"]["api_version"] == "v2"
        mock_client_instance.runs.create_and_process.assert_called_once()

    @patch("holiday_peak_lib.agents.foundry._ensure_agents_client")
    async def test_invoke_with_existing_conversation(self, mock_ensure_agents_client):
        """Test invocation with an existing conversation id (thread id)."""
        config = FoundryAgentConfig(
            endpoint=TEST_PROJECT_ENDPOINT,
            agent_id="agent-123",
            agent_name="catalog-fast",
            stream=True,
        )

        # Create mock runtime client structure
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        mock_client_instance.threads = MagicMock()
        mock_client_instance.messages = MagicMock()
        mock_client_instance.runs = MagicMock()

        mock_client_instance.threads.create = AsyncMock()
        mock_client_instance.messages.create = AsyncMock(return_value=SimpleNamespace(id="msg-2"))
        mock_client_instance.messages.get_last_message_text_by_role = AsyncMock(return_value=None)
        mock_client_instance.runs.create_and_process = AsyncMock(
            return_value=SimpleNamespace(id="run-456", status="completed", usage={})
        )
        mock_ensure_agents_client.return_value = mock_client_instance

        # Test invocation
        invoker = FoundryInvoker(config)
        result = await invoker(
            messages=[{"role": "user", "content": "Test"}],
            conversation_id="conv-existing",
        )

        assert result["conversation_id"] == "conv-existing"
        assert result["response_id"] == "run-456"
        assert result["stream"] is False
        mock_client_instance.threads.create.assert_not_called()
        mock_client_instance.runs.create_and_process.assert_called_once()


class TestBuildFoundryModelTarget:
    """Tests for build_foundry_model_target function."""

    def test_build_model_target_basic(self):
        """Test building a basic foundry model target."""
        config = FoundryAgentConfig(
            endpoint=TEST_PROJECT_ENDPOINT,
            agent_id="agent-123",
            deployment_name="gpt-4",
        )

        target = build_foundry_model_target(config)

        assert target.name == "agent-123"
        assert target.model == "gpt-4"
        assert target.stream is False
        assert isinstance(target.invoker, FoundryInvoker)

    def test_build_model_target_with_streaming(self):
        """Test building a streaming model target."""
        config = FoundryAgentConfig(
            endpoint=TEST_PROJECT_ENDPOINT, agent_id="agent-456", stream=True
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
        config = FoundryAgentConfig(endpoint=TEST_PROJECT_ENDPOINT, agent_id="agent-123:1")
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
