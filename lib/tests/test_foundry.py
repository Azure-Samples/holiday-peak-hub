"""Tests for Azure AI Foundry configuration helpers."""

import pytest
from holiday_peak_lib.agents.foundry import (
    FoundryAgentConfig,
    FoundryConfigurationError,
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
    """Tests for config loading and endpoint normalization."""

    def test_from_env_with_all_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_RESOURCE_ENDPOINT)
        monkeypatch.setenv("PROJECT_NAME", TEST_PROJECT_NAME)
        monkeypatch.setenv("FOUNDRY_AGENT_ID", "agent-123")
        monkeypatch.setenv("MODEL_DEPLOYMENT_NAME", "gpt-5-fast")

        config = FoundryAgentConfig.from_env()

        assert config.endpoint == TEST_PROJECT_ENDPOINT
        assert config.project_name == TEST_PROJECT_NAME
        assert config.agent_id == "agent-123"
        assert config.runtime_agent_id is None
        assert config.deployment_name == "gpt-5-fast"

    def test_from_env_with_alternate_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
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

    def test_from_env_allows_direct_model_config_without_agent_id(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
        monkeypatch.delenv("FOUNDRY_AGENT_ID", raising=False)
        monkeypatch.delenv("AGENT_ID", raising=False)
        monkeypatch.delenv("FOUNDRY_AGENT_NAME", raising=False)
        monkeypatch.setenv("MODEL_DEPLOYMENT_NAME", "gpt-5-fast")

        config = FoundryAgentConfig.from_env()

        assert config.agent_id == "pending"
        assert config.agent_name is None
        assert config.deployment_name == "gpt-5-fast"
        assert config.runtime_agent_id is None

    def test_from_env_extracts_project_name_from_project_endpoint(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
        monkeypatch.delenv("PROJECT_NAME", raising=False)

        config = FoundryAgentConfig.from_env()

        assert config.endpoint == TEST_PROJECT_ENDPOINT
        assert config.project_name == TEST_PROJECT_NAME

    def test_from_env_rejects_mismatched_project_name(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
        monkeypatch.setenv("PROJECT_NAME", "other-project")

        with pytest.raises(ValueError, match="must match the project encoded"):
            FoundryAgentConfig.from_env()

    def test_from_env_rejects_unscoped_endpoint_without_project_name(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_RESOURCE_ENDPOINT)
        monkeypatch.delenv("PROJECT_NAME", raising=False)
        monkeypatch.delenv("FOUNDRY_PROJECT_NAME", raising=False)

        with pytest.raises(ValueError, match="PROJECT_NAME/FOUNDRY_PROJECT_NAME is required"):
            FoundryAgentConfig.from_env()

    def test_from_env_missing_endpoint(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PROJECT_ENDPOINT", raising=False)
        monkeypatch.delenv("FOUNDRY_ENDPOINT", raising=False)

        with pytest.raises(ValueError, match="PROJECT_ENDPOINT/FOUNDRY_ENDPOINT"):
            FoundryAgentConfig.from_env()

    @pytest.mark.parametrize(
        "endpoint",
        [
            "http://test.services.ai.azure.com/api/projects/test-project",
            "https://test.example.com/api/projects/test-project",
            "https://test.services.ai.azure.com/api/projects/test-project?x=1",
            "https://test.services.ai.azure.com/not-a-project/test-project",
        ],
    )
    def test_invalid_endpoint_shapes_raise(self, endpoint: str) -> None:
        with pytest.raises(FoundryConfigurationError):
            FoundryAgentConfig(endpoint=endpoint, project_name=TEST_PROJECT_NAME)

    def test_resolved_agent_id_remains_compatibility_metadata(self) -> None:
        config = FoundryAgentConfig(
            endpoint=TEST_PROJECT_ENDPOINT,
            agent_id="pending",
            agent_name="catalog-fast",
            deployment_name="gpt-5-fast",
            resolved_agent_id="asst-real-123",
        )

        assert config.runtime_agent_id == "asst-real-123"
        assert config.deployment_name == "gpt-5-fast"

    def test_name_like_agent_id_does_not_auto_resolve(self) -> None:
        config = FoundryAgentConfig(
            endpoint=TEST_PROJECT_ENDPOINT,
            agent_id="ecommerce-catalog-search-fast",
            deployment_name="gpt-5-fast",
        )

        assert config.runtime_agent_id is None
