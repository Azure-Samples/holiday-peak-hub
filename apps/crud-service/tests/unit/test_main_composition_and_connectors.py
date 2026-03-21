"""Tests for CRUD main composition and optional connector wiring."""

from types import SimpleNamespace

import crud_service.main as main


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
