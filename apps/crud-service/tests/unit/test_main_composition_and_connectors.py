"""Tests for CRUD main composition and optional connector wiring."""

import asyncio
import json
import sys
from types import SimpleNamespace

import crud_service.main as main
import crud_service.routes.health as health_routes
import pytest
from fastapi.testclient import TestClient
from holiday_peak_lib.utils.event_hub import (
    CRITICAL_SAGA_PUBLISH_PROFILE,
    EventPublishError,
    MessagingFailureCategory,
    PublishFailureEnvelope,
)


def test_route_groups_keep_expected_api_surfaces() -> None:
    paths = {route.path for route in main.app.routes}
    expected_paths = {
        "/health",
        "/api/products",
        "/api/orders/{order_id}",
        "/api/truth/attributes/{entity_id}",
        "/acp/checkout/sessions",
    }
    for path in expected_paths:
        assert path in paths
    assert any(path.startswith("/api/staff/tickets") for path in paths)


def test_create_connector_registry_returns_none_when_import_fails(monkeypatch) -> None:
    def _raise_import(_module_name: str):
        raise ImportError("missing optional connector package")

    monkeypatch.setattr(main, "import_module", _raise_import)

    assert main.create_connector_registry() is None


def test_create_connector_registry_returns_instance_when_available(monkeypatch) -> None:
    class FakeConnectorRegistry:
        pass

    fake_module = SimpleNamespace(ConnectorRegistry=FakeConnectorRegistry)
    monkeypatch.setattr(main, "import_module", lambda _module_name: fake_module)

    registry = main.create_connector_registry()

    assert isinstance(registry, FakeConnectorRegistry)


class _NoOpAsyncComponent:
    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None


def _patch_lifespan_dependencies(monkeypatch) -> None:
    def _noop_telemetry(_connection_string: str | None) -> None:
        return None

    async def _noop_initialize_pool() -> None:
        return None

    async def _noop_close_pool() -> None:
        return None

    monkeypatch.setattr(main, "configure_optional_telemetry", _noop_telemetry)
    monkeypatch.setattr(main, "get_event_publisher", _NoOpAsyncComponent)
    monkeypatch.setattr(main, "get_connector_sync_consumer", _NoOpAsyncComponent)
    monkeypatch.setattr(main.BaseRepository, "initialize_pool", _noop_initialize_pool)
    monkeypatch.setattr(main.BaseRepository, "close_pool", _noop_close_pool)


@pytest.mark.asyncio
async def test_lifespan_loads_redis_password_from_key_vault(monkeypatch) -> None:
    _patch_lifespan_dependencies(monkeypatch)

    original_redis_password = main.settings.redis_password
    original_postgres_auth_mode = main.settings.postgres_auth_mode
    original_redis_secret_name = main.settings.redis_password_secret_name
    main.settings.redis_password = None
    main.settings.postgres_auth_mode = "entra"
    main.settings.redis_password_secret_name = "redis-primary-key"

    async def _fake_get_secret(secret_name: str) -> str:
        if secret_name == "redis-primary-key":
            return "redis-secret-value"
        raise AssertionError("Unexpected secret request")

    monkeypatch.setattr(main, "get_key_vault_secret", _fake_get_secret)

    app_state = SimpleNamespace(state=SimpleNamespace())
    try:
        async with main.lifespan(app_state):
            assert main.settings.redis_password == "redis-secret-value"
    finally:
        main.settings.redis_password = original_redis_password
        main.settings.postgres_auth_mode = original_postgres_auth_mode
        main.settings.redis_password_secret_name = original_redis_secret_name


@pytest.mark.asyncio
async def test_lifespan_continues_when_redis_secret_retrieval_fails(monkeypatch) -> None:
    _patch_lifespan_dependencies(monkeypatch)

    original_redis_password = main.settings.redis_password
    original_postgres_auth_mode = main.settings.postgres_auth_mode
    original_redis_secret_name = main.settings.redis_password_secret_name
    main.settings.redis_password = None
    main.settings.postgres_auth_mode = "entra"
    main.settings.redis_password_secret_name = "redis-primary-key"

    async def _failing_get_secret(secret_name: str) -> str:
        if secret_name == "redis-primary-key":
            raise RuntimeError("Key Vault unavailable")
        raise AssertionError("Unexpected secret request")

    monkeypatch.setattr(main, "get_key_vault_secret", _failing_get_secret)

    app_state = SimpleNamespace(state=SimpleNamespace())
    try:
        async with main.lifespan(app_state):
            assert main.settings.redis_password is None
    finally:
        main.settings.redis_password = original_redis_password
        main.settings.postgres_auth_mode = original_postgres_auth_mode
        main.settings.redis_password_secret_name = original_redis_secret_name


@pytest.mark.asyncio
async def test_lifespan_records_postgres_pool_startup_timeout_for_ready(
    monkeypatch,
) -> None:
    _patch_lifespan_dependencies(monkeypatch)
    monkeypatch.setattr(main.settings, "postgres_auth_mode", "entra")
    monkeypatch.setattr(main.settings, "redis_password", "redis-secret-value")
    monkeypatch.setattr(main.settings, "postgres_pool_startup_timeout_seconds", 0.01)

    async def _hanging_initialize_pool() -> None:
        await asyncio.Event().wait()

    async def _unhealthy_pool() -> tuple[str, str]:
        return "unhealthy", "pool unavailable"

    async def _healthy_redis(_request) -> tuple[str, str]:
        return "healthy", "ping ok"

    async def _unconfigured_cosmos() -> tuple[str, str]:
        return "unconfigured", "COSMOS_ACCOUNT_URI not set"

    monkeypatch.setattr(main.BaseRepository, "initialize_pool", _hanging_initialize_pool)
    monkeypatch.setattr(main.BaseRepository, "check_pool_health", _unhealthy_pool)
    monkeypatch.setattr(health_routes, "_check_redis", _healthy_redis)
    monkeypatch.setattr(health_routes, "_check_cosmos", _unconfigured_cosmos)

    async with main.lifespan(main.app):
        assert "TimeoutError" in main.app.state.db_pool_init_error
        assert "PostgreSQL pool initialization exceeded" in main.app.state.db_pool_init_error

        response = TestClient(main.app).get("/ready")
        payload = response.json()

        assert response.status_code == 503
        assert payload["checks"]["postgres"]["status"] == "unhealthy"
        assert "PostgreSQL pool initialization exceeded" in payload["checks"]["postgres"]["detail"]


@pytest.mark.asyncio
async def test_lifespan_records_redis_secret_timeout_and_ready_reports_redis(
    monkeypatch,
) -> None:
    _patch_lifespan_dependencies(monkeypatch)
    monkeypatch.setattr(main.settings, "postgres_auth_mode", "entra")
    monkeypatch.setattr(main.settings, "redis_password", None)
    monkeypatch.setattr(main.settings, "redis_password_secret_name", "redis-primary-key")
    monkeypatch.setattr(main.settings, "key_vault_secret_startup_timeout_seconds", 0.01)

    async def _hanging_get_secret(secret_name: str) -> str:
        if secret_name == "redis-primary-key":
            await asyncio.Event().wait()
        raise AssertionError("Unexpected secret request")

    class _FakeRedisClient:
        async def ping(self) -> None:
            raise RuntimeError("NOAUTH Authentication required")

        async def aclose(self) -> None:
            return None

    class _FakeRedis:
        @staticmethod
        def from_url(_url: str, socket_timeout: float):
            assert socket_timeout == 2
            return _FakeRedisClient()

    async def _healthy_pool() -> tuple[str, str]:
        return "healthy", "query ok"

    async def _unconfigured_cosmos() -> tuple[str, str]:
        return "unconfigured", "COSMOS_ACCOUNT_URI not set"

    monkeypatch.setattr(main, "get_key_vault_secret", _hanging_get_secret)
    monkeypatch.setattr(main.BaseRepository, "check_pool_health", _healthy_pool)
    monkeypatch.setattr(health_routes, "_check_cosmos", _unconfigured_cosmos)
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

    async with main.lifespan(main.app):
        assert main.settings.redis_password is None
        assert "TimeoutError" in main.app.state.redis_secret_init_error
        assert "Redis password secret retrieval exceeded" in main.app.state.redis_secret_init_error

        response = TestClient(main.app).get("/ready")
        payload = response.json()

        assert response.status_code == 503
        assert payload["checks"]["redis"]["status"] == "unhealthy"
        assert "Redis password secret retrieval exceeded" in payload["checks"]["redis"]["detail"]
        assert "NOAUTH Authentication required" in payload["checks"]["redis"]["detail"]


@pytest.mark.asyncio
async def test_event_publish_error_handler_preserves_publish_status_code() -> None:
    error = EventPublishError(
        PublishFailureEnvelope(
            service_name="crud-service",
            topic="order-events",
            operation="publish",
            error_type="TimeoutError",
            error_message="event hub unavailable",
            category=MessagingFailureCategory.TRANSIENT,
            status_code=503,
            profile=CRITICAL_SAGA_PUBLISH_PROFILE,
            event_type="OrderCreated",
        ),
        incident_id="incident-123",
    )

    response = await main.event_publish_error_handler(None, error)
    payload = json.loads(response.body.decode("utf-8"))

    assert response.status_code == 503
    assert payload == {
        "detail": "Event publish failed",
        "type": "EventPublishError",
        "topic": "order-events",
        "event_type": "OrderCreated",
        "category": "transient",
        "profile": "critical_saga",
        "incident_id": "incident-123",
    }
