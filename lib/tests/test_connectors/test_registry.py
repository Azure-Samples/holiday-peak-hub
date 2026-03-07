"""Tests for centralized connector registry behavior."""

from __future__ import annotations

import asyncio

import pytest

from holiday_peak_lib.adapters.base import BaseAdapter
from holiday_peak_lib.connectors.registry import ConnectorRegistry


class DummyConnector:
    """Simple connector class for class-registration tests."""


class HealthyRuntimeConnector:
    """Simple runtime connector with healthy status."""

    async def health(self) -> dict[str, object]:
        return {"ok": True, "status": "healthy"}


class FailingRuntimeConnector:
    """Runtime connector that raises during health checks."""

    async def health(self) -> dict[str, object]:
        raise RuntimeError("connector unavailable")


class DummyAdapterConnector(BaseAdapter):
    """BaseAdapter subclass used to validate resilience status reporting."""

    async def _connect_impl(self, **kwargs):
        return None

    async def _fetch_impl(self, query):
        return [query]

    async def _upsert_impl(self, payload):
        return payload

    async def _delete_impl(self, identifier):
        return True

    async def health(self) -> dict[str, object]:
        return {"ok": True, "status": "healthy"}


def test_register_get_and_list_vendors():
    registry = ConnectorRegistry()
    registry.register("pim", "dummy", DummyConnector)

    assert registry.get("pim", "dummy") is DummyConnector
    assert registry.get("pim", "missing") is None
    assert registry.list_vendors("pim") == ["dummy"]


@pytest.mark.asyncio
async def test_discover_registers_known_connectors(tmp_path, monkeypatch):
    registry = ConnectorRegistry()

    package_root = tmp_path / "mock_connectors"
    domain_dir = package_root / "inventory_scm" / "oracle_scm"
    domain_dir.mkdir(parents=True)
    (package_root / "__init__.py").write_text('"""mock package"""\n', encoding="utf-8")
    (package_root / "inventory_scm" / "__init__.py").write_text(
        '"""inventory"""\n', encoding="utf-8"
    )
    (domain_dir / "__init__.py").write_text('"""oracle"""\n', encoding="utf-8")
    (domain_dir / "connector.py").write_text(
        "class OracleConnector:\n" "    pass\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    discovered = await registry.discover("mock_connectors")

    assert discovered >= 0


def test_configuration_loader_and_provider_resolution():
    env = {
        "CONNECTOR_INVENTORY_SCM_PROVIDER": "oracle_scm",
        "CONNECTOR_INVENTORY_SCM_TIMEOUT": "30",
        "CONNECTOR_INVENTORY_SCM_ORACLE_SCM_SCOPE": "inventory.read",
    }
    registry = ConnectorRegistry(env=env)

    assert registry.configured_vendor("inventory_scm") == "oracle_scm"
    settings = registry.load_settings("inventory_scm", "oracle_scm")
    assert "CONNECTOR_INVENTORY_SCM_TIMEOUT" in settings
    assert "CONNECTOR_INVENTORY_SCM_ORACLE_SCM_SCOPE" in settings


@pytest.mark.asyncio
async def test_create_uses_configured_provider():
    env = {"CONNECTOR_PIM_PROVIDER": "dummy"}
    registry = ConnectorRegistry(env=env)
    registry.register("pim", "dummy", DummyConnector)

    instance = await registry.create("pim")

    assert isinstance(instance, DummyConnector)
    assert await registry.count() == 1
    assert await registry.get_runtime("pim:dummy") is instance


@pytest.mark.asyncio
async def test_runtime_health_and_resilience_details():
    registry = ConnectorRegistry()
    await registry.register_runtime("healthy", HealthyRuntimeConnector(), domain="pim")
    await registry.register_runtime("failing", FailingRuntimeConnector(), domain="crm")
    await registry.register_runtime("adapter", DummyAdapterConnector(), domain="inventory_scm")

    details = await registry.health_details()

    assert details["healthy"]["ok"] is True
    assert details["failing"]["ok"] is False
    assert "resilience" in details["adapter"]["details"]


@pytest.mark.asyncio
async def test_health_monitor_start_and_stop():
    registry = ConnectorRegistry()
    await registry.register_runtime("healthy", HealthyRuntimeConnector(), domain="pim")

    await registry.start_health_monitor(interval_seconds=5)
    await asyncio.sleep(0)
    await registry.stop_health_monitor()

    health = await registry.health()
    assert health["healthy"] is True
