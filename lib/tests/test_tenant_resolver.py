"""Tests for tenant context and connector resolver."""

from __future__ import annotations

import json

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from holiday_peak_lib.connectors.registry import ConnectorRegistry
from holiday_peak_lib.connectors.tenant_config import TenantConfigStore
from holiday_peak_lib.connectors.tenant_resolver import (
    TenantConnectorResolver,
    TenantContextMiddleware,
    TenantResolver,
    get_current_tenant_context,
)


async def _receive_empty() -> dict:
    return {
        "type": "http.request",
        "body": b"",
        "more_body": False,
    }


@pytest.mark.asyncio
async def test_tenant_resolver_prefers_header_then_query():
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"tenant_id=query-tenant",
        "headers": [(b"x-tenant-id", b"header-tenant"), (b"x-request-id", b"req-1")],
    }
    request = Request(scope, receive=_receive_empty)

    resolver = TenantResolver()
    context = await resolver.resolve(request)

    assert context.tenant_id == "header-tenant"
    assert context.source == "header"
    assert context.request_id == "req-1"


@pytest.mark.asyncio
async def test_tenant_resolver_supports_custom_plugin():
    async def custom(_: Request):
        return "custom-tenant"

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [],
    }
    request = Request(scope, receive=_receive_empty)

    resolver = TenantResolver(custom_resolver=custom)
    context = await resolver.resolve(request)

    assert context.tenant_id == "custom-tenant"
    assert context.source == "custom"


def test_tenant_context_middleware_propagates_state():
    app = FastAPI()
    app.add_middleware(TenantContextMiddleware, tenant_resolver=TenantResolver())

    @app.get("/check")
    async def check(request: Request):
        state_context = request.state.tenant_context
        current_context = get_current_tenant_context()
        return {
            "state_tenant": state_context.tenant_id,
            "current_tenant": current_context.tenant_id if current_context else None,
        }

    with TestClient(app) as client:
        response = client.get("/check", headers={"x-tenant-id": "acme"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["state_tenant"] == "acme"
    assert payload["current_tenant"] == "acme"


def test_tenant_context_middleware_returns_400_for_missing_tenant():
    app = FastAPI()
    app.add_middleware(TenantContextMiddleware, tenant_resolver=TenantResolver())

    @app.get("/check")
    async def check(_: Request):
        return {"ok": True}

    with TestClient(app) as client:
        response = client.get("/check")

    assert response.status_code == 400
    assert "Unable to resolve tenant context" in response.json()["detail"]


@pytest.mark.asyncio
async def test_tenant_connector_resolver_caches_connectors(tmp_path):
    config = {
        "connectors": {
            "inventory_scm": {
                "vendor": "sap_s4hana",
                "settings": {"endpoint": "https://sap.example/api"},
            }
        }
    }
    (tmp_path / "tenant-acme.yaml").write_text(json.dumps(config), encoding="utf-8")

    class DummyConnector:
        def __init__(self, endpoint: str):
            self.endpoint = endpoint

    registry = ConnectorRegistry(env={})
    registry.register("inventory_scm", "sap_s4hana", DummyConnector)

    config_store = TenantConfigStore(config_dir=tmp_path, env={})
    resolver = TenantConnectorResolver(registry=registry, config_store=config_store)

    first = await resolver.get_connector("acme", "inventory_scm")
    second = await resolver.get_connector("acme", "inventory_scm")

    assert first is second
    assert isinstance(first, DummyConnector)
    assert first.endpoint == "https://sap.example/api"

    registrations = await registry.list_registrations()
    assert len(registrations) == 1


@pytest.mark.asyncio
async def test_get_connector_from_request_uses_tenant_context(tmp_path):
    config = {
        "connectors": {
            "inventory_scm": {
                "vendor": "sap_s4hana",
                "settings": {"endpoint": "https://sap.example/api"},
            }
        }
    }
    (tmp_path / "tenant-acme.yaml").write_text(json.dumps(config), encoding="utf-8")

    class DummyConnector:
        def __init__(self, endpoint: str):
            self.endpoint = endpoint

    registry = ConnectorRegistry(env={})
    registry.register("inventory_scm", "sap_s4hana", DummyConnector)

    config_store = TenantConfigStore(config_dir=tmp_path, env={})
    resolver = TenantConnectorResolver(
        registry=registry,
        config_store=config_store,
        tenant_resolver=TenantResolver(),
    )

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [(b"x-tenant-id", b"acme")],
    }
    request = Request(scope, receive=_receive_empty)

    connector = await resolver.get_connector_from_request(request, "inventory_scm")

    assert isinstance(connector, DummyConnector)
    assert connector.endpoint == "https://sap.example/api"
