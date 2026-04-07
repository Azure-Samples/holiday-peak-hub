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
from holiday_peak_lib.connectors.registry import ConnectorRegistry

TEST_PROJECT_ENDPOINT = "https://test.services.ai.azure.com/api/projects/test-project"


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
    memory = ColdMemory(account_url="https://test.blob.core.windows.net", container_name="test")
    monkeypatch.setattr(memory, "client", mock_blob_client)
    return memory


class TestBuildServiceApp:
    """Test build_service_app function."""

    def test_build_minimal_app(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        """Test building app with minimal configuration."""
        # Mock the foundry config builder
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
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

    def test_build_app_skips_pending_foundry_runtime_targets(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        """Test unresolved Foundry runtime defs do not block fallback invoke paths."""

        class ModelAwareAgent(BaseRetailAgent):
            async def handle(self, request: dict) -> dict:
                return {"model_wired": bool(self.slm or self.llm)}

        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
        monkeypatch.delenv("FOUNDRY_AGENT_ID_FAST", raising=False)
        monkeypatch.delenv("FOUNDRY_AGENT_ID_RICH", raising=False)
        monkeypatch.delenv("FOUNDRY_AGENT_NAME_FAST", raising=False)
        monkeypatch.delenv("FOUNDRY_AGENT_NAME_RICH", raising=False)
        monkeypatch.setenv("FOUNDRY_AUTO_ENSURE_ON_STARTUP", "false")
        monkeypatch.setenv("FOUNDRY_STRICT_ENFORCEMENT", "true")

        app = build_service_app(
            service_name="test-service",
            agent_class=ModelAwareAgent,
            hot_memory=mock_hot_memory,
            warm_memory=mock_warm_memory,
            cold_memory=mock_cold_memory,
            require_foundry_readiness=True,
        )

        client = TestClient(app)
        with patch("holiday_peak_lib.app_factory.ensure_foundry_agent") as mock_ensure:
            mock_ensure.return_value = {
                "status": "missing",
                "agent_id": None,
                "agent_name": "test-service-fast",
                "created": False,
            }
            response = client.post("/invoke", json={"query": "test"})

        assert response.status_code == 200
        assert response.json()["model_wired"] is False

    def test_build_app_skips_name_only_foundry_runtime_targets(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        """Test name-only Foundry config remains unbound until ensure resolves an id."""

        class ModelAwareAgent(BaseRetailAgent):
            async def handle(self, request: dict) -> dict:
                return {"model_wired": bool(self.slm or self.llm)}

        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
        monkeypatch.delenv("FOUNDRY_AGENT_ID_FAST", raising=False)
        monkeypatch.delenv("FOUNDRY_AGENT_ID_RICH", raising=False)
        monkeypatch.setenv("FOUNDRY_AGENT_NAME_FAST", "catalog-fast")
        monkeypatch.delenv("FOUNDRY_AGENT_NAME_RICH", raising=False)
        monkeypatch.setenv("FOUNDRY_AUTO_ENSURE_ON_STARTUP", "false")

        app = build_service_app(
            service_name="test-service",
            agent_class=ModelAwareAgent,
            hot_memory=mock_hot_memory,
            warm_memory=mock_warm_memory,
            cold_memory=mock_cold_memory,
            require_foundry_readiness=True,
        )

        client = TestClient(app)
        response = client.post("/invoke", json={"query": "test"})

        assert response.status_code == 200
        assert response.json()["model_wired"] is False

    def test_invoke_auto_ensures_pending_foundry_runtime_targets(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        """Test invoke auto-ensures missing Foundry runtime ids before processing."""

        class RuntimeEnsureAgent(BaseRetailAgent):
            async def handle(self, request: dict) -> dict:
                return await self.invoke_model(
                    request=request,
                    messages=[{"role": "user", "content": str(request.get("query", ""))}],
                )

        async def _mock_invoker(**_kwargs):
            return {"response": "resolved"}

        from holiday_peak_lib.agents.base_agent import ModelTarget

        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
        monkeypatch.delenv("FOUNDRY_AGENT_ID_FAST", raising=False)
        monkeypatch.delenv("FOUNDRY_AGENT_ID_RICH", raising=False)
        monkeypatch.delenv("FOUNDRY_AGENT_NAME_FAST", raising=False)
        monkeypatch.delenv("FOUNDRY_AGENT_NAME_RICH", raising=False)
        monkeypatch.setenv("FOUNDRY_AUTO_ENSURE_ON_STARTUP", "false")

        with patch("holiday_peak_lib.app_factory.ensure_foundry_agent") as mock_ensure:
            mock_ensure.side_effect = [
                {
                    "status": "exists",
                    "agent_id": "agent-fast-123",
                    "agent_name": "test-service-fast",
                    "created": False,
                },
                {
                    "status": "exists",
                    "agent_id": "agent-rich-456",
                    "agent_name": "test-service-rich",
                    "created": False,
                },
            ]

            with patch("holiday_peak_lib.app_factory.build_foundry_model_target") as mock_target:
                mock_target.side_effect = [
                    ModelTarget(
                        name="slm",
                        model="gpt-5-nano",
                        invoker=_mock_invoker,
                        provider="foundry",
                    ),
                    ModelTarget(
                        name="llm",
                        model="gpt-5",
                        invoker=_mock_invoker,
                        provider="foundry",
                    ),
                ]

                app = build_service_app(
                    service_name="test-service",
                    agent_class=RuntimeEnsureAgent,
                    hot_memory=mock_hot_memory,
                    warm_memory=mock_warm_memory,
                    cold_memory=mock_cold_memory,
                )

                client = TestClient(app)
                response = client.post("/invoke", json={"query": "test"})

        assert response.status_code == 200
        assert response.json()["response"] == "resolved"
        assert mock_ensure.call_count == 2

    def test_build_app_with_custom_config(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory
    ):
        """Test building app with custom Foundry config."""
        from holiday_peak_lib.agents.foundry import FoundryAgentConfig

        async def mock_invoker(**kwargs):
            return {"response": "test"}

        slm_config = FoundryAgentConfig(
            endpoint=TEST_PROJECT_ENDPOINT,
            agent_id="slm-agent-123",
            deployment_name="gpt-4o-mini",
        )

        with patch("holiday_peak_lib.agents.foundry.build_foundry_model_target") as mock_build:
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
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
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

    def test_app_health_endpoint_echoes_correlation_id(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        """Test correlation ID is propagated to response headers."""
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
        monkeypatch.setenv("FOUNDRY_AGENT_ID_FAST", "agent-123")

        app = build_service_app(
            service_name="test-service",
            agent_class=SampleServiceAgent,
            hot_memory=mock_hot_memory,
            warm_memory=mock_warm_memory,
            cold_memory=mock_cold_memory,
        )

        client = TestClient(app)
        response = client.get("/health", headers={"X-Correlation-ID": "corr-123"})

        assert response.status_code == 200
        assert response.headers.get("x-correlation-id") == "corr-123"

    @pytest.mark.asyncio
    async def test_app_invoke_endpoint(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        """Test invoke endpoint."""
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
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
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
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
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
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
        assert "/ready" in routes
        assert "/invoke" in routes
        assert "/integrations" in routes
        assert "/foundry/agents/ensure" in routes

    def test_app_exposes_built_agent_on_state(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        """Test route handlers can reuse the exact built agent instance via app.state."""
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
        monkeypatch.setenv("FOUNDRY_AGENT_ID_FAST", "agent-123")

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
        """Test connector registry is attached to app state and used by endpoints."""
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
        monkeypatch.setenv("FOUNDRY_AGENT_ID_FAST", "agent-123")

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
        health_response = client.get("/health")
        assert health_response.status_code == 200
        assert health_response.json()["integrations_registered"] == 1

        integrations_response = client.get("/integrations")
        assert integrations_response.status_code == 200
        assert integrations_response.json()["domains"]["pim"] == ["mock-pim"]

    def test_foundry_ensure_endpoint(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        """Test service exposes endpoint to ensure/create Foundry agents."""
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
        monkeypatch.setenv("FOUNDRY_AGENT_ID_FAST", "agent-fast-123")
        monkeypatch.setenv("MODEL_DEPLOYMENT_NAME_FAST", "gpt-4o-mini")

        app = build_service_app(
            service_name="test-service",
            agent_class=SampleServiceAgent,
            hot_memory=mock_hot_memory,
            warm_memory=mock_warm_memory,
            cold_memory=mock_cold_memory,
        )
        client = TestClient(app)

        with patch("holiday_peak_lib.app_factory.ensure_foundry_agent") as mock_ensure:
            mock_ensure.return_value = {
                "status": "exists",
                "agent_id": "agent-fast-123",
                "agent_name": "test-service-fast",
                "created": False,
            }
            response = client.post(
                "/foundry/agents/ensure",
                json={"role": "fast", "create_if_missing": True},
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["service"] == "test-service"
        assert payload["results"]["fast"]["agent_id"] == "agent-fast-123"

    def test_foundry_ensure_uses_structured_default_instructions(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        """Test ensure endpoint passes structured defaults when request has no instructions."""
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
        monkeypatch.setenv("FOUNDRY_AGENT_ID_FAST", "agent-fast-123")

        app = build_service_app(
            service_name="test-service",
            agent_class=SampleServiceAgent,
            hot_memory=mock_hot_memory,
            warm_memory=mock_warm_memory,
            cold_memory=mock_cold_memory,
        )
        client = TestClient(app)

        with patch(
            "holiday_peak_lib.app_factory.load_service_prompt_instructions",
            return_value="## Identity and Role\nStructured prompt",
        ):
            with patch("holiday_peak_lib.app_factory.ensure_foundry_agent") as mock_ensure:
                mock_ensure.return_value = {
                    "status": "exists",
                    "agent_id": "agent-fast-123",
                    "agent_name": "test-service-fast",
                    "created": False,
                }
                response = client.post(
                    "/foundry/agents/ensure",
                    json={"role": "fast", "create_if_missing": True},
                )

        assert response.status_code == 200
        assert (
            mock_ensure.call_args.kwargs["instructions"]
            == "## Identity and Role\nStructured prompt"
        )

    def test_foundry_ensure_rejects_instruction_override_by_default(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        """Test request instruction override is blocked unless explicitly enabled."""
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
        monkeypatch.setenv("FOUNDRY_AGENT_ID_FAST", "agent-fast-123")
        monkeypatch.delenv("FOUNDRY_ALLOW_INSTRUCTION_OVERRIDE", raising=False)

        app = build_service_app(
            service_name="test-service",
            agent_class=SampleServiceAgent,
            hot_memory=mock_hot_memory,
            warm_memory=mock_warm_memory,
            cold_memory=mock_cold_memory,
        )
        client = TestClient(app)

        response = client.post(
            "/foundry/agents/ensure",
            json={
                "role": "fast",
                "create_if_missing": True,
                "instructions": {"fast": "## Identity and Role\nOverride prompt"},
            },
        )

        assert response.status_code == 403
        assert "Instruction overrides are disabled" in response.json()["detail"]

    def test_foundry_ensure_allows_instruction_override_when_enabled(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        """Test request instructions override defaults when explicitly enabled."""
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
        monkeypatch.setenv("FOUNDRY_AGENT_ID_FAST", "agent-fast-123")
        monkeypatch.setenv("FOUNDRY_ALLOW_INSTRUCTION_OVERRIDE", "true")

        app = build_service_app(
            service_name="test-service",
            agent_class=SampleServiceAgent,
            hot_memory=mock_hot_memory,
            warm_memory=mock_warm_memory,
            cold_memory=mock_cold_memory,
        )
        client = TestClient(app)

        with patch(
            "holiday_peak_lib.app_factory.load_service_prompt_instructions",
            return_value="## Identity and Role\nDefault prompt",
        ):
            with patch("holiday_peak_lib.app_factory.ensure_foundry_agent") as mock_ensure:
                mock_ensure.return_value = {
                    "status": "exists",
                    "agent_id": "agent-fast-123",
                    "agent_name": "test-service-fast",
                    "created": False,
                }
                response = client.post(
                    "/foundry/agents/ensure",
                    json={
                        "role": "fast",
                        "create_if_missing": True,
                        "instructions": {"fast": "## Identity and Role\nOverride prompt"},
                    },
                )

        assert response.status_code == 200
        assert (
            mock_ensure.call_args.kwargs["instructions"] == "## Identity and Role\nOverride prompt"
        )

    def test_ready_endpoint_returns_ok_when_not_strict(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        """Test /ready returns 200 when strict enforcement is not enabled."""
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
        monkeypatch.setenv("FOUNDRY_AGENT_ID_FAST", "agent-123")
        monkeypatch.delenv("FOUNDRY_STRICT_ENFORCEMENT", raising=False)

        app = build_service_app(
            service_name="test-service",
            agent_class=SampleServiceAgent,
            hot_memory=mock_hot_memory,
            warm_memory=mock_warm_memory,
            cold_memory=mock_cold_memory,
        )
        client = TestClient(app)
        response = client.get("/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["service"] == "test-service"
        assert data["foundry_ready"] is True
        assert data["foundry_required"] is False

    def test_ready_endpoint_returns_ok_when_foundry_missing_and_not_required(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        """Test /ready remains healthy when Foundry is not configured and not required."""
        monkeypatch.delenv("PROJECT_ENDPOINT", raising=False)
        monkeypatch.delenv("FOUNDRY_ENDPOINT", raising=False)
        monkeypatch.delenv("FOUNDRY_AGENT_ID_FAST", raising=False)
        monkeypatch.delenv("FOUNDRY_AGENT_ID_RICH", raising=False)
        monkeypatch.delenv("FOUNDRY_STRICT_ENFORCEMENT", raising=False)

        app = build_service_app(
            service_name="test-service",
            agent_class=SampleServiceAgent,
            hot_memory=mock_hot_memory,
            warm_memory=mock_warm_memory,
            cold_memory=mock_cold_memory,
        )
        client = TestClient(app)
        response = client.get("/ready")

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ready"
        assert payload["service"] == "test-service"
        assert payload["foundry_ready"] is False
        assert payload["foundry_required"] is False

    def test_ready_endpoint_returns_503_when_foundry_required_and_missing(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        """Test /ready fails when service explicitly requires Foundry readiness."""
        monkeypatch.delenv("PROJECT_ENDPOINT", raising=False)
        monkeypatch.delenv("FOUNDRY_ENDPOINT", raising=False)
        monkeypatch.delenv("FOUNDRY_AGENT_ID_FAST", raising=False)
        monkeypatch.delenv("FOUNDRY_AGENT_ID_RICH", raising=False)
        monkeypatch.delenv("FOUNDRY_STRICT_ENFORCEMENT", raising=False)

        app = build_service_app(
            service_name="test-service",
            agent_class=SampleServiceAgent,
            hot_memory=mock_hot_memory,
            warm_memory=mock_warm_memory,
            cold_memory=mock_cold_memory,
            require_foundry_readiness=True,
        )
        client = TestClient(app)
        response = client.get("/ready")

        assert response.status_code == 503
        detail = response.json()["detail"]
        assert detail["status"] == "not_ready"
        assert detail["service"] == "test-service"

    def test_ready_endpoint_returns_503_when_strict_and_not_ready(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        """Test /ready returns 503 when strict mode active and agents not ensured."""
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
        monkeypatch.delenv("FOUNDRY_AGENT_ID_FAST", raising=False)
        monkeypatch.delenv("FOUNDRY_AGENT_ID_RICH", raising=False)
        monkeypatch.setenv("FOUNDRY_STRICT_ENFORCEMENT", "true")
        # Disable auto-ensure so foundry_ready stays False
        monkeypatch.setenv("FOUNDRY_AUTO_ENSURE_ON_STARTUP", "false")

        app = build_service_app(
            service_name="test-service",
            agent_class=SampleServiceAgent,
            hot_memory=mock_hot_memory,
            warm_memory=mock_warm_memory,
            cold_memory=mock_cold_memory,
            require_foundry_readiness=True,
        )
        client = TestClient(app)
        response = client.get("/ready")

        assert response.status_code == 503
        detail = response.json()["detail"]
        assert detail["status"] == "not_ready"
        assert detail["service"] == "test-service"

    def test_ready_endpoint_returns_ok_after_ensure_in_strict_mode(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        """Test /ready flips to 200 after agents are ensured when readiness is required."""
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
        monkeypatch.delenv("FOUNDRY_AGENT_ID_FAST", raising=False)
        monkeypatch.delenv("FOUNDRY_AGENT_ID_RICH", raising=False)
        monkeypatch.setenv("FOUNDRY_STRICT_ENFORCEMENT", "true")
        monkeypatch.setenv("FOUNDRY_AUTO_ENSURE_ON_STARTUP", "false")

        app = build_service_app(
            service_name="test-service",
            agent_class=SampleServiceAgent,
            hot_memory=mock_hot_memory,
            warm_memory=mock_warm_memory,
            cold_memory=mock_cold_memory,
            require_foundry_readiness=True,
        )
        client = TestClient(app)

        # Before ensure: not ready
        assert client.get("/ready").status_code == 503

        # Ensure agents
        with patch("holiday_peak_lib.app_factory.ensure_foundry_agent") as mock_ensure:
            mock_ensure.return_value = {
                "status": "exists",
                "agent_id": "agent-123",
                "agent_name": "test-service-fast",
                "created": False,
            }
            ensure_resp = client.post(
                "/foundry/agents/ensure",
                json={"role": "fast", "create_if_missing": True},
            )
        assert ensure_resp.status_code == 200
        assert ensure_resp.json()["foundry_ready"] is True

        # After ensure: ready
        response = client.get("/ready")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"

    def test_strict_foundry_mode_auto_ensures_before_invoke(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        """Test strict mode auto-runs ensure during invoke before routing."""
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
        monkeypatch.delenv("FOUNDRY_AGENT_ID_FAST", raising=False)
        monkeypatch.delenv("FOUNDRY_AGENT_ID_RICH", raising=False)
        monkeypatch.setenv("FOUNDRY_STRICT_ENFORCEMENT", "true")

        app = build_service_app(
            service_name="test-service",
            agent_class=SampleServiceAgent,
            hot_memory=mock_hot_memory,
            warm_memory=mock_warm_memory,
            cold_memory=mock_cold_memory,
        )

        client = TestClient(app)
        with patch("holiday_peak_lib.app_factory.ensure_foundry_agent") as mock_ensure:
            mock_ensure.return_value = {
                "status": "exists",
                "agent_id": "agent-123",
                "agent_name": "test-service-fast",
                "created": False,
            }
            response = client.post("/invoke", json={"query": "test"})

        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert mock_ensure.call_count >= 1

    def test_build_foundry_config_from_env(self, monkeypatch):
        """Test building Foundry config from environment."""
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
        monkeypatch.setenv("FOUNDRY_AGENT_ID_FAST", "agent-fast-123")
        monkeypatch.setenv("MODEL_DEPLOYMENT_NAME_FAST", "gpt-4o-mini")
        monkeypatch.setenv("FOUNDRY_AGENT_ID_RICH", "agent-rich-456")
        monkeypatch.setenv("MODEL_DEPLOYMENT_NAME_RICH", "gpt-4o")

        from holiday_peak_lib.app_factory import _build_foundry_config

        slm_config = _build_foundry_config("FOUNDRY_AGENT_ID_FAST", "MODEL_DEPLOYMENT_NAME_FAST")
        llm_config = _build_foundry_config("FOUNDRY_AGENT_ID_RICH", "MODEL_DEPLOYMENT_NAME_RICH")

        assert slm_config is not None
        assert slm_config.endpoint == TEST_PROJECT_ENDPOINT
        assert slm_config.agent_id == "agent-fast-123"
        assert slm_config.runtime_agent_id == "agent-fast-123"
        assert llm_config.agent_id == "agent-rich-456"
        assert llm_config.runtime_agent_id == "agent-rich-456"

    def test_build_foundry_config_missing_env(self, monkeypatch):
        """Test building Foundry config with missing environment vars."""
        monkeypatch.delenv("PROJECT_ENDPOINT", raising=False)
        monkeypatch.delenv("FOUNDRY_ENDPOINT", raising=False)

        from holiday_peak_lib.app_factory import _build_foundry_config

        config = _build_foundry_config("FOUNDRY_AGENT_ID_FAST", "MODEL_DEPLOYMENT_NAME_FAST")

        assert config is None

    def test_build_foundry_config_with_streaming(self, monkeypatch):
        """Test building Foundry config with streaming enabled."""
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
        monkeypatch.setenv("FOUNDRY_AGENT_ID_FAST", "agent-123")
        monkeypatch.setenv("FOUNDRY_STREAM", "true")

        from holiday_peak_lib.app_factory import _build_foundry_config

        config = _build_foundry_config("FOUNDRY_AGENT_ID_FAST", "MODEL_DEPLOYMENT_NAME_FAST")

        assert config is not None
        assert config.stream is True

    def test_build_foundry_config_name_only_requires_later_resolution(self, monkeypatch):
        """Test role names stay available for ensure but unbound for runtime."""
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
        monkeypatch.delenv("FOUNDRY_AGENT_ID_FAST", raising=False)
        monkeypatch.setenv("FOUNDRY_AGENT_NAME_FAST", "catalog-fast")

        from holiday_peak_lib.app_factory import _build_foundry_config

        config = _build_foundry_config("FOUNDRY_AGENT_ID_FAST", "MODEL_DEPLOYMENT_NAME_FAST")

        assert config is not None
        assert config.agent_id == "fast-pending"
        assert config.agent_name == "catalog-fast"
        assert config.runtime_agent_id is None


class TestAppFactoryIntegration:
    """Test app factory integration scenarios."""

    def test_complete_service_setup(
        self, mock_hot_memory, mock_warm_memory, mock_cold_memory, monkeypatch
    ):
        """Test complete service setup."""
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
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
        monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
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
