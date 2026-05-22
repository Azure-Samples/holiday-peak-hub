import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from holiday_peak_lib.agents.base_agent import BaseRetailAgent
from holiday_peak_lib.agents.memory.cold import ColdMemory
from holiday_peak_lib.agents.memory.hot import HotMemory
from holiday_peak_lib.agents.memory.warm import WarmMemory
from holiday_peak_lib.app_factory import build_service_app, create_standard_app
from holiday_peak_lib.config.settings import MemorySettings
from holiday_peak_lib.connectors.registry import ConnectorRegistry
from holiday_peak_lib.utils import EventHubSubscription

TEST_PROJECT_ENDPOINT = "https://test.services.ai.azure.com/api/projects/test-project"


class SampleServiceAgent(BaseRetailAgent):
    """Test agent for app factory."""

    async def handle(self, request: dict) -> dict:
        return {"status": "ok", "data": request}


@pytest.fixture(name="mock_hot_memory")
def fixture_mock_hot_memory(mock_redis_client, monkeypatch):
    """Mock hot memory."""
    memory = HotMemory("redis://localhost:6379")
    monkeypatch.setattr(memory, "client", mock_redis_client)
    return memory


@pytest.fixture(name="mock_warm_memory")
def fixture_mock_warm_memory(mock_cosmos_client, monkeypatch):
    """Mock warm memory."""
    memory = WarmMemory(
        account_uri="https://test.documents.azure.com",
        database="test",
        container="test",
    )
    monkeypatch.setattr(memory, "client", mock_cosmos_client)
    return memory


@pytest.fixture(name="mock_cold_memory")
def fixture_mock_cold_memory(mock_blob_client, monkeypatch):
    """Mock cold memory."""
    memory = ColdMemory(account_url="https://test.blob.core.windows.net", container_name="test")
    monkeypatch.setattr(memory, "client", mock_blob_client)
    return memory


def _clear_foundry_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "PROJECT_ENDPOINT",
        "FOUNDRY_ENDPOINT",
        "PROJECT_NAME",
        "FOUNDRY_PROJECT_NAME",
        "FOUNDRY_AGENT_ID_FAST",
        "FOUNDRY_AGENT_ID_RICH",
        "FOUNDRY_AGENT_NAME_FAST",
        "FOUNDRY_AGENT_NAME_RICH",
        "MODEL_DEPLOYMENT_NAME_FAST",
        "MODEL_DEPLOYMENT_NAME_RICH",
        "FOUNDRY_STRICT_ENFORCEMENT",
        "HOLIDAY_PEAK_DIRECT_MODEL",
        "AGENT_EVALUATION_FOUNDRY_ROOT",
    ):
        monkeypatch.delenv(key, raising=False)


def _clear_runtime_dependency_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "REDIS_URL",
        "REDIS_HOST",
        "REDIS_PASSWORD",
        "KEY_VAULT_URI",
        "COSMOS_ACCOUNT_URI",
        "COSMOS_DATABASE",
        "COSMOS_CONTAINER",
        "BLOB_ACCOUNT_URL",
        "BLOB_CONTAINER",
        "EVENT_HUB_NAMESPACE",
        "EVENT_HUB_CONNECTION_STRING",
        "HOLIDAY_PEAK_REDIS_SOCKET_TIMEOUT_SECONDS",
        "HOLIDAY_PEAK_REDIS_CONNECT_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(key, raising=False)


def _write_eval_fixture(service_root: Path) -> Path:
    foundry_root = service_root / ".foundry"
    dataset_dir = foundry_root / "datasets"
    dataset_dir.mkdir(parents=True)
    (foundry_root / "eval-config.yaml").write_text(
        "\n".join(
            [
                "schema_version: '1'",
                "agent_name: test-service",
                "evaluators:",
                "  - relevance",
                "dataset_path: datasets/seed.jsonl",
                "baseline_id: test-service:baseline",
            ]
        ),
        encoding="utf-8",
    )
    case = {
        "query": "find winter gloves",
        "expected_behavior": "return relevant winter glove products",
        "expected_model_tier": "slm",
    }
    (dataset_dir / "seed.jsonl").write_text(json.dumps(case), encoding="utf-8")
    return foundry_root


class TestCreateStandardAppRuntimeFlags:
    """Test create_standard_app dependency wiring controls."""

    def test_hot_memory_defaults_to_enabled_with_bounded_timeouts(self, monkeypatch):
        _clear_foundry_env(monkeypatch)
        _clear_runtime_dependency_env(monkeypatch)
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

        app = create_standard_app("test-service", SampleServiceAgent)

        hot_memory = app.state.agent.hot_memory
        assert isinstance(hot_memory, HotMemory)
        assert hot_memory.url == "redis://localhost:6379/0"
        assert hot_memory.socket_timeout == 1.0
        assert hot_memory.socket_connect_timeout == 1.0
        assert hot_memory.retry_on_timeout is False

    def test_eventhub_subscribers_default_to_enabled(self, monkeypatch):
        _clear_foundry_env(monkeypatch)
        _clear_runtime_dependency_env(monkeypatch)

        async def handler(_partition_context, _event):  # noqa: ANN001
            return None

        with patch(
            "holiday_peak_lib.app_factory.create_eventhub_lifespan",
            return_value=None,
        ) as create_lifespan:
            create_standard_app(
                "test-service",
                SampleServiceAgent,
                subscriptions=[EventHubSubscription("inventory-events", "test-group")],
                handlers={"inventory-events": handler},
            )

        create_lifespan.assert_called_once()


class TestBuildServiceApp:
    """Test build_service_app direct-model wiring and endpoints."""

    def test_build_minimal_app(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        _clear_foundry_env(monkeypatch)

        app = build_service_app(
            service_name="test-service",
            agent_class=SampleServiceAgent,
            hot_memory=mock_hot_memory,
            warm_memory=mock_warm_memory,
            cold_memory=mock_cold_memory,
        )

        assert isinstance(app, FastAPI)
        assert app.title == "test-service"
        assert app.state.agent.slm is None
        assert app.state.agent.llm is None

    def test_build_app_binds_direct_targets_when_deployments_configured(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        _clear_foundry_env(monkeypatch)
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
        monkeypatch.setenv("MODEL_DEPLOYMENT_NAME_FAST", "gpt-5-fast")
        monkeypatch.setenv("MODEL_DEPLOYMENT_NAME_RICH", "gpt-5-rich")

        app = build_service_app(
            service_name="test-service",
            agent_class=SampleServiceAgent,
            hot_memory=mock_hot_memory,
            warm_memory=mock_warm_memory,
            cold_memory=mock_cold_memory,
            use_direct_model=True,
        )

        agent = app.state.agent
        assert agent.slm is not None
        assert agent.llm is not None
        assert agent.slm.provider == "maf-direct"
        assert agent.llm.provider == "maf-direct"
        assert agent.slm.model == "gpt-5-fast"
        assert agent.llm.model == "gpt-5-rich"

    def test_ready_endpoint_returns_ok_when_required_and_direct_targets_bound(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        _clear_foundry_env(monkeypatch)
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
        monkeypatch.setenv("MODEL_DEPLOYMENT_NAME_FAST", "gpt-5-fast")
        monkeypatch.setenv("MODEL_DEPLOYMENT_NAME_RICH", "gpt-5-rich")
        monkeypatch.setenv("FOUNDRY_STRICT_ENFORCEMENT", "true")

        app = build_service_app(
            service_name="test-service",
            agent_class=SampleServiceAgent,
            hot_memory=mock_hot_memory,
            warm_memory=mock_warm_memory,
            cold_memory=mock_cold_memory,
            require_foundry_readiness=True,
        )

        response = TestClient(app).get("/ready")
        assert response.status_code == 200
        payload = response.json()
        assert payload["foundry_ready"] is True
        assert payload["foundry_required"] is True
        assert payload["foundry"]["bound_roles"] == ["fast", "rich"]
        assert payload["foundry"]["unbound_roles"] == []

    def test_ready_endpoint_returns_503_when_required_and_deployments_missing(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        _clear_foundry_env(monkeypatch)
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
        monkeypatch.setenv("FOUNDRY_STRICT_ENFORCEMENT", "true")

        app = build_service_app(
            service_name="test-service",
            agent_class=SampleServiceAgent,
            hot_memory=mock_hot_memory,
            warm_memory=mock_warm_memory,
            cold_memory=mock_cold_memory,
            require_foundry_readiness=True,
        )

        response = TestClient(app).get("/ready")
        assert response.status_code == 503
        detail = response.json()["detail"]
        assert "Direct-model targets are not ready" in detail["reason"]
        assert detail["foundry"]["configured_roles"] == ["fast", "rich"]
        assert detail["foundry"]["bound_roles"] == []
        assert detail["foundry"]["unbound_roles"] == ["fast", "rich"]

    def test_invoke_returns_503_when_required_and_direct_targets_unbound(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        _clear_foundry_env(monkeypatch)
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)

        app = build_service_app(
            service_name="test-service",
            agent_class=SampleServiceAgent,
            hot_memory=mock_hot_memory,
            warm_memory=mock_warm_memory,
            cold_memory=mock_cold_memory,
            require_foundry_readiness=True,
        )

        response = TestClient(app).post("/invoke", json={"query": "test"})
        assert response.status_code == 503
        assert "Direct-model targets are not ready" in response.json()["detail"]

    def test_ready_endpoint_returns_ok_when_foundry_missing_and_not_required(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        _clear_foundry_env(monkeypatch)

        app = build_service_app(
            service_name="test-service",
            agent_class=SampleServiceAgent,
            hot_memory=mock_hot_memory,
            warm_memory=mock_warm_memory,
            cold_memory=mock_cold_memory,
        )

        response = TestClient(app).get("/ready")
        assert response.status_code == 200
        payload = response.json()
        assert payload["foundry_ready"] is False
        assert payload["foundry_required"] is False

    def test_app_health_endpoint(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        _clear_foundry_env(monkeypatch)
        app = build_service_app(
            service_name="test-service",
            agent_class=SampleServiceAgent,
            hot_memory=mock_hot_memory,
            warm_memory=mock_warm_memory,
            cold_memory=mock_cold_memory,
        )

        response = TestClient(app).get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["service"] == "test-service"

    def test_app_health_endpoint_echoes_correlation_id(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        _clear_foundry_env(monkeypatch)
        app = build_service_app(
            service_name="test-service",
            agent_class=SampleServiceAgent,
            hot_memory=mock_hot_memory,
            warm_memory=mock_warm_memory,
            cold_memory=mock_cold_memory,
        )

        response = TestClient(app).get("/health", headers={"X-Correlation-ID": "corr-123"})

        assert response.status_code == 200
        assert response.headers.get("x-correlation-id") == "corr-123"

    def test_app_invoke_endpoint(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        _clear_foundry_env(monkeypatch)
        app = build_service_app(
            service_name="test-service",
            agent_class=SampleServiceAgent,
            hot_memory=mock_hot_memory,
            warm_memory=mock_warm_memory,
            cold_memory=mock_cold_memory,
        )

        response = TestClient(app).post("/invoke", json={"query": "test"})

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_app_with_mcp_setup(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        _clear_foundry_env(monkeypatch)
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
        _clear_foundry_env(monkeypatch)
        app = build_service_app(
            service_name="test-service",
            agent_class=SampleServiceAgent,
            hot_memory=mock_hot_memory,
            warm_memory=mock_warm_memory,
            cold_memory=mock_cold_memory,
        )

        routes = {route.path for route in app.routes}
        retired_route = "/foundry/agents/" + "ensure"
        assert "/health" in routes
        assert "/ready" in routes
        assert "/invoke" in routes
        assert "/invoke/stream" in routes
        assert "/integrations" in routes
        assert "/agent/evaluation/run" in routes
        assert "/agent/evaluation/history" in routes
        assert "/mcp/tool_descriptions" in routes
        assert retired_route not in routes

    def test_build_app_discovers_per_service_evaluation_config(
        self,
        mock_hot_memory,
        mock_warm_memory,
        mock_cold_memory,
        monkeypatch,
        tmp_path: Path,
    ):
        _clear_foundry_env(monkeypatch)
        _write_eval_fixture(tmp_path / "apps" / "test-service")
        monkeypatch.chdir(tmp_path)

        app = build_service_app(
            service_name="test-service",
            agent_class=SampleServiceAgent,
            hot_memory=mock_hot_memory,
            warm_memory=mock_warm_memory,
            cold_memory=mock_cold_memory,
        )

        assert app.state.evaluation_runner is not None
        assert app.state.evaluation_runner.config.agent_name == "test-service"

    def test_app_exposes_built_agent_on_state(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        _clear_foundry_env(monkeypatch)
        app = build_service_app(
            service_name="test-service",
            agent_class=SampleServiceAgent,
            hot_memory=mock_hot_memory,
            warm_memory=mock_warm_memory,
            cold_memory=mock_cold_memory,
        )

        assert isinstance(app.state.agent, SampleServiceAgent)

    @pytest.mark.asyncio
    async def test_app_wires_connector_registry(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        _clear_foundry_env(monkeypatch)
        registry = ConnectorRegistry()
        await registry.register_runtime("mock-pim", object(), domain="pim")

        app = build_service_app(
            service_name="test-service",
            agent_class=SampleServiceAgent,
            hot_memory=mock_hot_memory,
            warm_memory=mock_warm_memory,
            cold_memory=mock_cold_memory,
            connector_registry=registry,
        )

        assert app.state.connector_registry is registry
        client = TestClient(app)
        assert client.get("/health").json()["integrations_registered"] == 1
        assert client.get("/integrations").json()["domains"]["pim"] == ["mock-pim"]

    def test_build_foundry_config_from_env(self, monkeypatch):
        _clear_foundry_env(monkeypatch)
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
        monkeypatch.setenv("FOUNDRY_AGENT_ID_FAST", "agent-fast-123")
        monkeypatch.setenv("MODEL_DEPLOYMENT_NAME_FAST", "gpt-5-fast")
        monkeypatch.setenv("FOUNDRY_AGENT_ID_RICH", "agent-rich-456")
        monkeypatch.setenv("MODEL_DEPLOYMENT_NAME_RICH", "gpt-5-rich")

        from holiday_peak_lib.app_factory import _build_foundry_config

        slm_config = _build_foundry_config("FOUNDRY_AGENT_ID_FAST", "MODEL_DEPLOYMENT_NAME_FAST")
        llm_config = _build_foundry_config("FOUNDRY_AGENT_ID_RICH", "MODEL_DEPLOYMENT_NAME_RICH")

        assert slm_config is not None
        assert slm_config.endpoint == TEST_PROJECT_ENDPOINT
        assert slm_config.agent_id == "agent-fast-123"
        assert slm_config.deployment_name == "gpt-5-fast"
        assert llm_config is not None
        assert llm_config.agent_id == "agent-rich-456"
        assert llm_config.deployment_name == "gpt-5-rich"

    def test_build_foundry_config_missing_endpoint(self, monkeypatch):
        _clear_foundry_env(monkeypatch)
        from holiday_peak_lib.app_factory import _build_foundry_config

        config = _build_foundry_config("FOUNDRY_AGENT_ID_FAST", "MODEL_DEPLOYMENT_NAME_FAST")

        assert config is None

    def test_build_foundry_config_missing_deployment_stays_unbound(self, monkeypatch):
        _clear_foundry_env(monkeypatch)
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
        from holiday_peak_lib.app_factory import _build_foundry_config

        config = _build_foundry_config("FOUNDRY_AGENT_ID_FAST", "MODEL_DEPLOYMENT_NAME_FAST")

        assert config is not None
        assert config.agent_id == "fast-pending"
        assert config.deployment_name is None

    def test_app_upgrades_explicit_azure_redis_url_with_key_vault_secret(self, monkeypatch):
        _clear_foundry_env(monkeypatch)
        hot_memory = HotMemory("rediss://myredis.redis.cache.windows.net:6380/0")
        memory_settings = MemorySettings(
            _env_file=None,
            redis_url="rediss://myredis.redis.cache.windows.net:6380/0",
            key_vault_uri="https://test-kv.vault.azure.net/",
            redis_password_secret_name="redis-primary-key",
        )

        with patch(
            "holiday_peak_lib.app_factory._fetch_key_vault_secret",
            new=AsyncMock(return_value="s3cret"),
        ) as mock_fetch:
            app = build_service_app(
                service_name="test-service",
                agent_class=SampleServiceAgent,
                hot_memory=hot_memory,
                memory_settings=memory_settings,
            )

            with TestClient(app):
                pass

        assert hot_memory.url == "rediss://:s3cret@myredis.redis.cache.windows.net:6380/0"
        assert hot_memory.client is None
        mock_fetch.assert_awaited_once_with(
            "https://test-kv.vault.azure.net/",
            "redis-primary-key",
        )

    def test_app_detaches_authless_azure_redis_when_key_vault_secret_fails(self, monkeypatch):
        _clear_foundry_env(monkeypatch)
        hot_memory = HotMemory("rediss://myredis.redis.cache.windows.net:6380/0")
        memory_settings = MemorySettings(
            _env_file=None,
            redis_url="rediss://myredis.redis.cache.windows.net:6380/0",
            key_vault_uri="https://test-kv.vault.azure.net/",
            redis_password_secret_name="redis-primary-key",
        )

        with patch(
            "holiday_peak_lib.app_factory._fetch_key_vault_secret",
            new=AsyncMock(side_effect=PermissionError("rbac denied")),
        ) as mock_fetch:
            app = build_service_app(
                service_name="test-service",
                agent_class=SampleServiceAgent,
                hot_memory=hot_memory,
                memory_settings=memory_settings,
            )

            with TestClient(app):
                pass

        assert app.state.agent.hot_memory is None
        assert hot_memory.client is None
        mock_fetch.assert_awaited_once_with(
            "https://test-kv.vault.azure.net/",
            "redis-primary-key",
        )


class TestAzureTracingGuard:
    """Tests for the AZURE_TRACING_ENABLED env-var guard."""

    def test_guard_sets_env_when_no_appinsights_and_no_tracing_var(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        _clear_foundry_env(monkeypatch)
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
        monkeypatch.setenv("MODEL_DEPLOYMENT_NAME_FAST", "gpt-5-fast")
        monkeypatch.setenv("FOUNDRY_TRACING_ENABLED", "false")
        monkeypatch.delenv("APPLICATIONINSIGHTS_CONNECTION_STRING", raising=False)
        monkeypatch.delenv("APPINSIGHTS_CONNECTION_STRING", raising=False)
        monkeypatch.delenv("AZURE_TRACING_ENABLED", raising=False)

        build_service_app(
            service_name="guard-test",
            agent_class=SampleServiceAgent,
            hot_memory=mock_hot_memory,
            warm_memory=mock_warm_memory,
            cold_memory=mock_cold_memory,
        )

        assert os.environ.get("AZURE_TRACING_ENABLED") == "false"

    def test_guard_does_not_override_explicit_tracing_enabled(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        _clear_foundry_env(monkeypatch)
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
        monkeypatch.setenv("MODEL_DEPLOYMENT_NAME_FAST", "gpt-5-fast")
        monkeypatch.setenv("FOUNDRY_TRACING_ENABLED", "false")
        monkeypatch.delenv("APPLICATIONINSIGHTS_CONNECTION_STRING", raising=False)
        monkeypatch.delenv("APPINSIGHTS_CONNECTION_STRING", raising=False)
        monkeypatch.setenv("AZURE_TRACING_ENABLED", "true")

        build_service_app(
            service_name="guard-test-no-override",
            agent_class=SampleServiceAgent,
            hot_memory=mock_hot_memory,
            warm_memory=mock_warm_memory,
            cold_memory=mock_cold_memory,
        )

        assert os.environ.get("AZURE_TRACING_ENABLED") == "true"

    def test_guard_does_not_activate_when_appinsights_configured(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        import azure.monitor.opentelemetry as azure_monitor

        _clear_foundry_env(monkeypatch)
        monkeypatch.setattr(
            azure_monitor,
            "configure_azure_monitor",
            lambda **_kwargs: None,
        )
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
        monkeypatch.setenv("MODEL_DEPLOYMENT_NAME_FAST", "gpt-5-fast")
        monkeypatch.setenv("FOUNDRY_TRACING_ENABLED", "false")
        monkeypatch.setenv(
            "APPLICATIONINSIGHTS_CONNECTION_STRING",
            "InstrumentationKey=00000000-0000-0000-0000-000000000000",
        )
        monkeypatch.delenv("APPINSIGHTS_CONNECTION_STRING", raising=False)
        monkeypatch.delenv("AZURE_TRACING_ENABLED", raising=False)

        build_service_app(
            service_name="guard-test-appinsights",
            agent_class=SampleServiceAgent,
            hot_memory=mock_hot_memory,
            warm_memory=mock_warm_memory,
            cold_memory=mock_cold_memory,
        )

        assert os.environ.get("AZURE_TRACING_ENABLED") is None
