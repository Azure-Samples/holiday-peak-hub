"""Unit tests for health routes."""

import sys
from types import SimpleNamespace

import crud_service.routes.health as health_routes
from crud_service.main import app
from crud_service.repositories.base import BaseRepository
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_readiness_check_returns_valid_shape():
    """Test readiness check endpoint returns expected shape.

    In the unit-test environment the external dependencies (Redis, Cosmos DB)
    are not configured, so the check may report 'unconfigured' or 'degraded'.
    We only assert the response structure here.
    """
    response = client.get("/ready")
    data = response.json()
    assert "status" in data
    assert "service" in data
    assert "checks" in data
    assert "postgres" in data["checks"]
    assert "redis" in data["checks"]
    assert "cosmos" in data["checks"]
    assert data["service"] == "crud-service"


def test_readiness_with_connector_registry():
    """Readiness includes connector registry health when available."""

    class StubRegistry:
        async def health(self):
            return {"inventory_scm:oracle_scm": True, "crm_loyalty:salesforce": False}

    original_registry = getattr(app.state, "connector_registry", None)
    app.state.connector_registry = StubRegistry()
    try:
        response = client.get("/ready")
        assert response.status_code == 503
        payload = response.json()
        assert payload["status"] == "degraded"
        assert payload["checks"]["connectors"]["detail"]["registered"] == 2
        assert payload["checks"]["connectors"]["detail"]["unhealthy"] == ["crm_loyalty:salesforce"]
    finally:
        if original_registry is None:
            delattr(app.state, "connector_registry")
        else:
            app.state.connector_registry = original_registry


def test_readiness_degraded_when_postgres_pool_unhealthy_and_init_failed(monkeypatch):
    """Readiness should return 503 when postgres pool is unhealthy and startup init failed."""

    async def _unhealthy_pool():
        return "unhealthy", "timeout"

    monkeypatch.setattr(BaseRepository, "check_pool_health", _unhealthy_pool)

    original_error = getattr(app.state, "db_pool_init_error", None)
    app.state.db_pool_init_error = "RuntimeError: pool init failed"
    try:
        response = client.get("/ready")
        assert response.status_code == 503
        payload = response.json()
        assert payload["status"] == "degraded"
        assert payload["checks"]["postgres"]["status"] == "unhealthy"
        assert "pool init failed" in payload["checks"]["postgres"]["detail"]
    finally:
        app.state.db_pool_init_error = original_error


def test_readiness_recovers_when_postgres_pool_is_healthy(monkeypatch):
    """Readiness should recover and clear stale startup init error when pool becomes healthy."""

    async def _healthy_pool():
        return "healthy", "query ok"

    monkeypatch.setattr(BaseRepository, "check_pool_health", _healthy_pool)

    original_error = getattr(app.state, "db_pool_init_error", None)
    app.state.db_pool_init_error = "RuntimeError: pool init failed"
    try:
        response = client.get("/ready")
        assert response.status_code in (200, 503)
        payload = response.json()
        assert payload["checks"]["postgres"]["status"] == "healthy"
        assert getattr(app.state, "db_pool_init_error", None) is None
    finally:
        app.state.db_pool_init_error = original_error


def test_readiness_uses_configured_authenticated_redis_url(monkeypatch):
    captured: dict[str, object] = {}

    class _FakeRedisClient:
        async def ping(self):
            return True

        async def aclose(self):
            return None

    class _FakeRedis:
        @staticmethod
        def from_url(url: str, socket_timeout: float):
            captured["url"] = url
            captured["socket_timeout"] = socket_timeout
            return _FakeRedisClient()

    monkeypatch.setattr(
        health_routes,
        "get_settings",
        lambda: SimpleNamespace(redis_url="rediss://:encoded%40secret@cache:6380/0"),
    )

    monkeypatch.setitem(
        sys.modules,
        "redis",
        SimpleNamespace(asyncio=SimpleNamespace(Redis=_FakeRedis)),
    )
    monkeypatch.setitem(
        sys.modules,
        "redis.asyncio",
        SimpleNamespace(Redis=_FakeRedis),
    )

    async def _healthy_pool():
        return "healthy", "query ok"

    async def _unconfigured_cosmos():
        return "unconfigured", "COSMOS_ACCOUNT_URI not set"

    monkeypatch.setattr(BaseRepository, "check_pool_health", _healthy_pool)
    monkeypatch.setattr(health_routes, "_check_cosmos", _unconfigured_cosmos)

    response = client.get("/ready")
    payload = response.json()

    assert payload["checks"]["redis"]["status"] == "healthy"
    assert captured["url"] == "rediss://:encoded%40secret@cache:6380/0"
    assert captured["socket_timeout"] == 2
