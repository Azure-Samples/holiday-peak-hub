"""Tests for app_factory module."""

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from holiday_peak_lib.agents.base_agent import BaseRetailAgent
from holiday_peak_lib.agents.memory.cold import ColdMemory
from holiday_peak_lib.agents.memory.hot import HotMemory
from holiday_peak_lib.agents.memory.warm import WarmMemory
from holiday_peak_lib.app_factory import build_service_app


class SampleServiceAgent(BaseRetailAgent):
    """Test agent for app factory."""

    async def handle(self, request: dict) -> dict:
        return {"status": "ok", "data": request}


@pytest.fixture
def mock_hot_memory(mock_redis_client, monkeypatch):
    """Mock hot memory."""
    memory = HotMemory("redis://localhost:6379")
    monkeypatch.setattr(memory, "client", mock_redis_client)
    return memory


@pytest.fixture
def mock_warm_memory(mock_cosmos_client, monkeypatch):
    """Mock warm memory."""
    memory = WarmMemory(
        account_uri="https://test.documents.azure.com",
        database="test",
        container="test",
    )
    monkeypatch.setattr(memory, "client", mock_cosmos_client)
    return memory


@pytest.fixture
def mock_cold_memory(mock_blob_client, monkeypatch):
    """Mock cold memory."""
    memory = ColdMemory(
        account_url="https://test.blob.core.windows.net", container_name="test"
    )
    monkeypatch.setattr(memory, "client", mock_blob_client)
    return memory


class TestBuildServiceApp:
    """Test build_service_app function."""

    def test_build_minimal_app(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        """Test building app with minimal configuration."""
        # Mock the foundry config builder
        monkeypatch.setenv("PROJECT_ENDPOINT", "https://test.endpoint.com")
        monkeypatch.setenv("FOUNDRY_AGENT_ID_FAST", "agent-fast-123")
        monkeypatch.setenv("MODEL_DEPLOYMENT_NAME_FAST", "gpt-4o-mini")

        app = build_service_app(
            service_name="test-service",
            agent_class=SampleServiceAgent,
            hot_memory=mock_hot_memory,
            warm_memory=mock_warm_memory,
            cold_memory=mock_cold_memory,
        )

        assert isinstance(app, FastAPI)
        assert app.title == "test-service"

    def test_build_app_with_custom_config(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory
    ):
        """Test building app with custom Foundry config."""
        from holiday_peak_lib.agents.foundry import FoundryAgentConfig

        async def mock_invoker(**kwargs):
            return {"response": "test"}

        slm_config = FoundryAgentConfig(
            endpoint="https://test.endpoint.com",
            agent_id="slm-agent-123",
            deployment_name="gpt-4o-mini",
        )

        with patch(
            "holiday_peak_lib.agents.foundry.build_foundry_model_target"
        ) as mock_build:
            from holiday_peak_lib.agents.base_agent import ModelTarget

            mock_build.return_value = ModelTarget(
                name="slm", model="gpt-4o-mini", invoker=mock_invoker
            )

            app = build_service_app(
                service_name="test-service",
                agent_class=SampleServiceAgent,
                hot_memory=mock_hot_memory,
                warm_memory=mock_warm_memory,
                cold_memory=mock_cold_memory,
                slm_config=slm_config,
            )

            assert isinstance(app, FastAPI)

    def test_app_health_endpoint(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        """Test health endpoint."""
        monkeypatch.setenv("PROJECT_ENDPOINT", "https://test.endpoint.com")
        monkeypatch.setenv("FOUNDRY_AGENT_ID_FAST", "agent-123")

        app = build_service_app(
            service_name="test-service",
            agent_class=SampleServiceAgent,
            hot_memory=mock_hot_memory,
            warm_memory=mock_warm_memory,
            cold_memory=mock_cold_memory,
        )

        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["service"] == "test-service"

    @pytest.mark.asyncio
    async def test_app_invoke_endpoint(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        """Test invoke endpoint."""
        monkeypatch.setenv("PROJECT_ENDPOINT", "https://test.endpoint.com")
        monkeypatch.setenv("FOUNDRY_AGENT_ID_FAST", "agent-123")

        app = build_service_app(
            service_name="test-service",
            agent_class=SampleServiceAgent,
            hot_memory=mock_hot_memory,
            warm_memory=mock_warm_memory,
            cold_memory=mock_cold_memory,
        )

        client = TestClient(app)
        response = client.post("/invoke", json={"query": "test"})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_app_with_mcp_setup(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        """Test app with MCP setup callback."""
        monkeypatch.setenv("PROJECT_ENDPOINT", "https://test.endpoint.com")
        monkeypatch.setenv("FOUNDRY_AGENT_ID_FAST", "agent-123")

        setup_called = {"value": False}

        def mcp_setup_callback(mcp_server, agent):
            setup_called["value"] = True
            assert mcp_server is not None
            assert isinstance(agent, SampleServiceAgent)

        app = build_service_app(
            service_name="test-service",
            agent_class=SampleServiceAgent,
            hot_memory=mock_hot_memory,
            warm_memory=mock_warm_memory,
            cold_memory=mock_cold_memory,
            mcp_setup=mcp_setup_callback,
        )

        assert isinstance(app, FastAPI)
        assert setup_called["value"] is True

    def test_app_routes_registered(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        """Test that required routes are registered."""
        monkeypatch.setenv("PROJECT_ENDPOINT", "https://test.endpoint.com")
        monkeypatch.setenv("FOUNDRY_AGENT_ID_FAST", "agent-123")

        app = build_service_app(
            service_name="test-service",
            agent_class=SampleServiceAgent,
            hot_memory=mock_hot_memory,
            warm_memory=mock_warm_memory,
            cold_memory=mock_cold_memory,
        )

        # Check routes exist
        routes = [route.path for route in app.routes]
        assert "/health" in routes
        assert "/invoke" in routes

    def test_build_foundry_config_from_env(self, monkeypatch):
        """Test building Foundry config from environment."""
        monkeypatch.setenv("PROJECT_ENDPOINT", "https://test.endpoint.com")
        monkeypatch.setenv("FOUNDRY_AGENT_ID_FAST", "agent-fast-123")
        monkeypatch.setenv("MODEL_DEPLOYMENT_NAME_FAST", "gpt-4o-mini")
        monkeypatch.setenv("FOUNDRY_AGENT_ID_RICH", "agent-rich-456")
        monkeypatch.setenv("MODEL_DEPLOYMENT_NAME_RICH", "gpt-4o")

        from holiday_peak_lib.app_factory import _build_foundry_config

        slm_config = _build_foundry_config(
            "FOUNDRY_AGENT_ID_FAST", "MODEL_DEPLOYMENT_NAME_FAST"
        )
        llm_config = _build_foundry_config(
            "FOUNDRY_AGENT_ID_RICH", "MODEL_DEPLOYMENT_NAME_RICH"
        )

        assert slm_config is not None
        assert slm_config.endpoint == "https://test.endpoint.com"
        assert slm_config.agent_id == "agent-fast-123"
        assert llm_config.agent_id == "agent-rich-456"

    def test_build_foundry_config_missing_env(self, monkeypatch):
        """Test building Foundry config with missing environment vars."""
        monkeypatch.delenv("PROJECT_ENDPOINT", raising=False)
        monkeypatch.delenv("FOUNDRY_ENDPOINT", raising=False)

        from holiday_peak_lib.app_factory import _build_foundry_config

        config = _build_foundry_config(
            "FOUNDRY_AGENT_ID_FAST", "MODEL_DEPLOYMENT_NAME_FAST"
        )

        assert config is None

    def test_build_foundry_config_with_streaming(self, monkeypatch):
        """Test building Foundry config with streaming enabled."""
        monkeypatch.setenv("PROJECT_ENDPOINT", "https://test.endpoint.com")
        monkeypatch.setenv("FOUNDRY_AGENT_ID_FAST", "agent-123")
        monkeypatch.setenv("FOUNDRY_STREAM", "true")

        from holiday_peak_lib.app_factory import _build_foundry_config

        config = _build_foundry_config(
            "FOUNDRY_AGENT_ID_FAST", "MODEL_DEPLOYMENT_NAME_FAST"
        )

        assert config is not None
        assert config.stream is True


class TestAppFactoryIntegration:
    """Test app factory integration scenarios."""

    def test_complete_service_setup(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        """Test complete service setup."""
        monkeypatch.setenv("PROJECT_ENDPOINT", "https://test.endpoint.com")
        monkeypatch.setenv("FOUNDRY_AGENT_ID_FAST", "agent-fast")
        monkeypatch.setenv("FOUNDRY_AGENT_ID_RICH", "agent-rich")

        app = build_service_app(
            service_name="complete-service",
            agent_class=SampleServiceAgent,
            hot_memory=mock_hot_memory,
            warm_memory=mock_warm_memory,
            cold_memory=mock_cold_memory,
        )

        client = TestClient(app)

        # Test health
        health_response = client.get("/health")
        assert health_response.status_code == 200

        # Test invoke
        invoke_response = client.post("/invoke", json={"test": "data"})
        assert invoke_response.status_code == 200

    def test_app_with_different_agent_classes(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        """Test building apps with different agent classes."""
        monkeypatch.setenv("PROJECT_ENDPOINT", "https://test.endpoint.com")
        monkeypatch.setenv("FOUNDRY_AGENT_ID_FAST", "agent-123")

        class CustomAgent(BaseRetailAgent):
            async def handle(self, request):
                return {"custom": True}

        app = build_service_app(
            service_name="custom-service",
            agent_class=CustomAgent,
            hot_memory=mock_hot_memory,
            warm_memory=mock_warm_memory,
            cold_memory=mock_cold_memory,
        )

        assert isinstance(app, FastAPI)
        client = TestClient(app)
        response = client.post("/invoke", json={"test": "data"})
        assert response.json()["custom"] is True
