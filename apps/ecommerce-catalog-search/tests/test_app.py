from unittest.mock import AsyncMock, patch

import pytest
from ecommerce_catalog_search.ai_search import AISearchIndexStatus, AISearchSeedResult
from ecommerce_catalog_search.main import create_app
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def clear_ai_search_environment(monkeypatch):
    monkeypatch.delenv("AI_SEARCH_ENDPOINT", raising=False)
    monkeypatch.delenv("AI_SEARCH_INDEX", raising=False)
    monkeypatch.delenv("AI_SEARCH_VECTOR_INDEX", raising=False)
    monkeypatch.delenv("EVENTHUB_CONNECTION_STRING", raising=False)
    monkeypatch.delenv("EVENT_HUB_CONNECTION_STRING", raising=False)
    monkeypatch.delenv("EVENT_HUB_NAMESPACE", raising=False)
    monkeypatch.delenv("EVENTHUB_NAMESPACE", raising=False)


def test_health():
    with TestClient(create_app()) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["service"] == "ecommerce-catalog-search"


def test_invoke_returns_service():
    with TestClient(create_app()) as client:
        response = client.post("/invoke", json={"query": "", "limit": 1})
        assert response.status_code == 200
        assert response.json()["service"] == "ecommerce-catalog-search"


def test_agent_activity_endpoints():
    with TestClient(create_app()) as client:
        invoke_response = client.post("/invoke", json={"query": "running shoes", "limit": 3})
        assert invoke_response.status_code == 200

        traces_response = client.get("/agent/traces")
        assert traces_response.status_code == 200
        assert "traces" in traces_response.json()

        metrics_response = client.get("/agent/metrics")
        assert metrics_response.status_code == 200
        assert metrics_response.json()["service"] == "ecommerce-catalog-search"
        assert metrics_response.json()["enabled"] is False

        evaluation_response = client.get("/agent/evaluation/latest")
        assert evaluation_response.status_code == 200
        assert "latest" in evaluation_response.json()
        assert evaluation_response.json()["latest"] is None


def test_ready_returns_503_when_strict_mode_ai_search_not_ready(monkeypatch):
    monkeypatch.setenv("PROJECT_ENDPOINT", "https://test.endpoint.com")
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
        with TestClient(create_app()) as client:
            response = client.get("/ready")

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["service"] == "ecommerce-catalog-search"
    assert detail["catalog_ai_search"]["strict_mode"] is True
    assert detail["catalog_ai_search"]["ready"] is False
    assert detail["catalog_ai_search"]["reason"] == "ai_search_not_configured"


def test_startup_attempts_seed_when_index_empty(monkeypatch):
    monkeypatch.setenv("CATALOG_SEARCH_SEED_MAX_ATTEMPTS", "1")
    monkeypatch.setenv("CATALOG_SEARCH_SEED_BATCH_SIZE", "3")

    status_sequence = [
        AISearchIndexStatus(
            configured=True,
            reachable=True,
            non_empty=False,
            reason="ai_search_index_empty",
        ),
        AISearchIndexStatus(
            configured=True,
            reachable=True,
            non_empty=True,
            reason=None,
        ),
    ]

    with (
        patch(
            "ecommerce_catalog_search.main.get_catalog_index_status",
            new=AsyncMock(side_effect=status_sequence),
        ) as mock_status,
        patch(
            "ecommerce_catalog_search.main.seed_catalog_index_from_crud",
            new=AsyncMock(
                return_value=AISearchSeedResult(
                    attempted=True,
                    success=True,
                    attempt_count=1,
                    seeded_documents=3,
                    reason=None,
                )
            ),
        ) as mock_seed,
    ):
        with TestClient(create_app()):
            pass

    mock_seed.assert_awaited_once_with(max_attempts=1, batch_size=3)
    assert mock_status.await_count == 2
