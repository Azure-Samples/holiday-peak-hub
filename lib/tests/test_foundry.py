"""Tests for Azure AI Foundry integration."""
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from holiday_peak_lib.agents.foundry import FoundryAgentConfig, build_foundry_model_target, FoundryInvoker


class TestFoundryAgentConfig:
    """Tests for FoundryAgentConfig."""

    def test_from_env_with_all_vars(self, monkeypatch):
        """Test config creation from environment variables."""
        monkeypatch.setenv("PROJECT_ENDPOINT", "https://test.openai.azure.com")
        monkeypatch.setenv("PROJECT_NAME", "test-project")
        monkeypatch.setenv("FOUNDRY_AGENT_ID", "agent-123")
        monkeypatch.setenv("MODEL_DEPLOYMENT_NAME", "gpt-4")
        monkeypatch.setenv("FOUNDRY_STREAM", "true")
        
        config = FoundryAgentConfig.from_env()
        
        assert config.endpoint == "https://test.openai.azure.com"
        assert config.project_name == "test-project"
        assert config.agent_id == "agent-123"
        assert config.deployment_name == "gpt-4"
        assert config.stream is True

    def test_from_env_with_alternate_vars(self, monkeypatch):
        """Test config creation using alternate env var names."""
        monkeypatch.setenv("FOUNDRY_ENDPOINT", "https://alternate.openai.azure.com")
        monkeypatch.setenv("FOUNDRY_PROJECT_NAME", "alternate-project")
        monkeypatch.setenv("AGENT_ID", "agent-456")
        
        config = FoundryAgentConfig.from_env()
        
        assert config.endpoint == "https://alternate.openai.azure.com"
        assert config.project_name == "alternate-project"
        assert config.agent_id == "agent-456"

    def test_from_env_missing_endpoint(self, monkeypatch):
        """Test error when endpoint is missing."""
        monkeypatch.setenv("FOUNDRY_AGENT_ID", "agent-123")
        monkeypatch.delenv("PROJECT_ENDPOINT", raising=False)
        monkeypatch.delenv("FOUNDRY_ENDPOINT", raising=False)
        
        with pytest.raises(ValueError, match="PROJECT_ENDPOINT/FOUNDRY_ENDPOINT"):
            FoundryAgentConfig.from_env()

    def test_from_env_missing_agent_id(self, monkeypatch):
        """Test error when agent ID is missing."""
        monkeypatch.setenv("PROJECT_ENDPOINT", "https://test.openai.azure.com")
        monkeypatch.delenv("FOUNDRY_AGENT_ID", raising=False)
        monkeypatch.delenv("AGENT_ID", raising=False)
        
        with pytest.raises(ValueError, match="FOUNDRY_AGENT_ID are required"):
            FoundryAgentConfig.from_env()

    def test_stream_flag_variants(self, monkeypatch):
        """Test different stream flag values."""
        monkeypatch.setenv("PROJECT_ENDPOINT", "https://test.openai.azure.com")
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

    @patch("holiday_peak_lib.agents.foundry.AIProjectClient")
    @patch("holiday_peak_lib.agents.foundry.DefaultAzureCredential")
    async def test_invoke_non_streaming(self, mock_cred, mock_client):
        """Test non-streaming invocation."""
        config = FoundryAgentConfig(
            endpoint="https://test.openai.azure.com",
            agent_id="agent-123",
            stream=False
        )
        
        mock_cred_instance = MagicMock()
        mock_cred.return_value = mock_cred_instance
        
        # Create mock client structure
        mock_client_instance = MagicMock()
        mock_agents_client = MagicMock()
        mock_threads_client = MagicMock()
        mock_messages_client = MagicMock()
        mock_runs_client = MagicMock()
        
        # Setup thread
        mock_thread = MagicMock()
        mock_thread.id = "thread-123"
        mock_threads_client.create = AsyncMock(return_value=mock_thread)
        
        # Setup message creation
        mock_messages_client.create = AsyncMock()
        
        # Setup run
        mock_run = MagicMock()
        mock_run.id = "run-123"
        mock_run.status = "completed"
        mock_runs_client.create_and_process = AsyncMock(return_value=mock_run)
        
        # Setup messages list
        mock_message = MagicMock()
        mock_message.to_dict = MagicMock(return_value={"role": "assistant", "content": "Test response"})
        mock_messages_client.list = AsyncMock(return_value=[mock_message])
        
        # Wire up the mocks
        mock_agents_client.threads = mock_threads_client
        mock_agents_client.messages = mock_messages_client
        mock_agents_client.runs = mock_runs_client
        mock_client_instance.agents = mock_agents_client
        mock_client.return_value = mock_client_instance
        
        # Test invocation
        invoker = FoundryInvoker(config)
        result = await invoker(messages="Test query")
        
        assert result["thread_id"] == "thread-123"
        assert result["run_id"] == "run-123"
        assert not result["stream"]
        assert "telemetry" in result
        mock_runs_client.create_and_process.assert_called_once()

    @patch("holiday_peak_lib.agents.foundry.AIProjectClient")
    @patch("holiday_peak_lib.agents.foundry.DefaultAzureCredential")
    async def test_invoke_streaming(self, mock_cred, mock_client):
        """Test streaming invocation."""
        config = FoundryAgentConfig(
            endpoint="https://test.openai.azure.com",
            agent_id="agent-123",
            stream=True
        )
        
        mock_cred_instance = MagicMock()
        mock_cred.return_value = mock_cred_instance
        
        # Create mock client structure
        mock_client_instance = MagicMock()
        mock_agents_client = MagicMock()
        mock_threads_client = MagicMock()
        mock_messages_client = MagicMock()
        mock_runs_client = MagicMock()
        
        # Setup thread
        mock_thread = MagicMock()
        mock_thread.id = "thread-456"
        mock_threads_client.create = AsyncMock(return_value=mock_thread)
        
        # Setup message creation
        mock_messages_client.create = AsyncMock()
        
        # Setup streaming
        async def mock_stream():
            # Simulate streaming events
            event_data_1 = MagicMock()
            event_data_1.text = "Hello "
            yield ("TEXT_DELTA", event_data_1, None)
            
            event_data_2 = MagicMock()
            event_data_2.text = "World"
            yield ("TEXT_DELTA", event_data_2, None)
            
            done_event = MagicMock()
            done_event.name = "DONE"
            yield (done_event, MagicMock(text=None), None)
        
        mock_runs_client.stream = AsyncMock(return_value=mock_stream())
        
        # Wire up the mocks
        mock_agents_client.threads = mock_threads_client
        mock_agents_client.messages = mock_messages_client
        mock_agents_client.runs = mock_runs_client
        mock_client_instance.agents = mock_agents_client
        mock_client.return_value = mock_client_instance
        
        # Test invocation
        invoker = FoundryInvoker(config)
        result = await invoker(messages=[{"role": "user", "content": "Test"}])
        
        assert result["thread_id"] == "thread-456"
        assert result["text"] == "Hello World"
        assert result["stream"] is True
        mock_runs_client.stream.assert_called_once()


class TestBuildFoundryModelTarget:
    """Tests for build_foundry_model_target function."""

    def test_build_model_target_basic(self):
        """Test building a basic foundry model target."""
        config = FoundryAgentConfig(
            endpoint="https://test.openai.azure.com",
            agent_id="agent-123",
            deployment_name="gpt-4"
        )
        
        target = build_foundry_model_target(config)
        
        assert target.name == "agent-123"
        assert target.model == "gpt-4"
        assert target.stream is False
        assert isinstance(target.invoker, FoundryInvoker)

    def test_build_model_target_with_streaming(self):
        """Test building a streaming model target."""
        config = FoundryAgentConfig(
            endpoint="https://test.openai.azure.com",
            agent_id="agent-456",
            stream=True
        )
        
        target = build_foundry_model_target(config)
        
        assert target.name == "agent-456"
        assert target.model == "agent-456"  # Falls back to agent_id when no deployment
        assert target.stream is True
