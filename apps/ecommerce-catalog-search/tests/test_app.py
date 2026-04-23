import importlib
from unittest.mock import AsyncMock, patch

import pytest
from ecommerce_catalog_search.ai_search import AISearchIndexStatus
from fastapi.testclient import TestClient

TEST_PROJECT_ENDPOINT = "https://test.services.ai.azure.com/api/projects/test-project"

pytestmark = pytest.mark.usefixtures("mock_foundry_readiness")


@pytest.fixture(autouse=True)
def clear_ai_search_environment(monkeypatch):
    for env_name in (
        "PROJECT_ENDPOINT",
        "FOUNDRY_ENDPOINT",
        "PROJECT_NAME",
        "FOUNDRY_PROJECT_NAME",
        "FOUNDRY_AGENT_ID_FAST",
        "FOUNDRY_AGENT_NAME_FAST",
        "MODEL_DEPLOYMENT_NAME_FAST",
        "FOUNDRY_AGENT_ID_RICH",
        "FOUNDRY_AGENT_NAME_RICH",
        "MODEL_DEPLOYMENT_NAME_RICH",
        "FOUNDRY_STREAM",
    ):
        monkeypatch.delenv(env_name, raising=False)

    monkeypatch.setenv("FOUNDRY_AUTO_ENSURE_ON_STARTUP", "false")
    monkeypatch.setenv("FOUNDRY_STRICT_ENFORCEMENT", "false")
    monkeypatch.delenv("AI_SEARCH_ENDPOINT", raising=False)
    monkeypatch.delenv("AI_SEARCH_INDEX", raising=False)
    monkeypatch.delenv("AI_SEARCH_VECTOR_INDEX", raising=False)
    monkeypatch.delenv("EVENTHUB_CONNECTION_STRING", raising=False)
    monkeypatch.delenv("EVENT_HUB_CONNECTION_STRING", raising=False)
    monkeypatch.delenv("EVENTHUB_NAMESPACE", raising=False)
    monkeypatch.setenv("EVENT_HUB_NAMESPACE", "test-retail.servicebus.windows.net")


def _create_app():
    main = importlib.import_module("ecommerce_catalog_search.main")
    return main.create_app()


def test_health():
    with TestClient(_create_app()) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["service"] == "ecommerce-catalog-search"


def test_invoke_returns_service():
    with TestClient(_create_app()) as client:
        response = client.post("/invoke", json={"query": "", "limit": 1})
        assert response.status_code == 200
        assert response.json()["service"] == "ecommerce-catalog-search"


def test_agent_activity_endpoints():
    with TestClient(_create_app()) as client:
        invoke_response = client.post("/invoke", json={"query": "running shoes", "limit": 3})
        assert invoke_response.status_code == 200

        traces_response = client.get("/agent/traces")
        assert traces_response.status_code == 200
        assert "traces" in traces_response.json()
        assert len(traces_response.json()["traces"]) >= 1

        metrics_response = client.get("/agent/metrics")
        assert metrics_response.status_code == 200
        assert metrics_response.json()["service"] == "ecommerce-catalog-search"
        assert metrics_response.json()["enabled"] is True

        evaluation_response = client.get("/agent/evaluation/latest")
        assert evaluation_response.status_code == 200
        assert "latest" in evaluation_response.json()


def test_ready_returns_503_when_strict_mode_ai_search_not_ready(monkeypatch):
    monkeypatch.setenv("PROJECT_ENDPOINT", TEST_PROJECT_ENDPOINT)
    monkeypatch.setenv("FOUNDRY_AGENT_ID_FAST", "agent-fast-123")
    monkeypatch.setenv("CATALOG_SEARCH_REQUIRE_AI_SEARCH", "true")

    with patch(
        "ecommerce_catalog_search.main.get_catalog_index_status",
        new=AsyncMock(
            return_value=AISearchIndexStatus(
                configured=False,
                reachable=False,
                non_empty=False,
                reason="ai_search_not_configured",
            )
        ),
    ):
        with TestClient(_create_app()) as client:
            response = client.get("/ready")

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["service"] == "ecommerce-catalog-search"
    assert detail["catalog_ai_search"]["strict_mode"] is True
    assert detail["catalog_ai_search"]["ready"] is False
    assert detail["catalog_ai_search"]["reason"] == "ai_search_not_configured"
