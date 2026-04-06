"""Tests for CRUD main composition and optional connector wiring."""

from types import SimpleNamespace

import crud_service.main as main
import pytest


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
