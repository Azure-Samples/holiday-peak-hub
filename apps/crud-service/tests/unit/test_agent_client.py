"""Unit tests for agent client resilience."""

import crud_service.integrations.agent_client as agent_client_module
import httpx
import pytest
from circuitbreaker import CircuitBreakerMonitor
from holiday_peak_lib.utils import clear_correlation_id, set_correlation_id

AgentClient = agent_client_module.AgentClient


@pytest.fixture(autouse=True)
def reset_circuit_breakers() -> None:
    """Reset global circuit breaker state to keep tests order-independent."""
    for circuit_breaker in CircuitBreakerMonitor.get_circuits():
        circuit_breaker.reset()


class DummyResponse:
    """Simple response stub for httpx.AsyncClient."""

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class DummyClient:
    """AsyncClient stub returning a fixed response."""

    def __init__(self, *args, **kwargs):
        self._payload = kwargs.pop("payload", {"ok": True})

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def post(self, *args, **kwargs):
        self.last_headers = kwargs.get("headers", {})
        return DummyResponse(self._payload)


class TimeoutClient:
    """AsyncClient stub that raises a timeout."""

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def post(self, *args, **kwargs):
        raise httpx.TimeoutException("timeout")


@pytest.mark.asyncio
async def test_call_endpoint_success(monkeypatch):
    """Agent client returns response payload on success."""
    monkeypatch.setattr(agent_client_module.httpx, "AsyncClient", DummyClient)
    client = AgentClient()
    result = await client.call_endpoint("http://agent", "/invoke", {"sku": "A"})
    assert result == {"ok": True}


@pytest.mark.asyncio
async def test_call_endpoint_includes_correlation_header(monkeypatch):
    """Agent calls include x-correlation-id when request context has one."""
    captured: dict = {}

    class CapturingClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, *args, **kwargs):
            captured["headers"] = kwargs.get("headers", {})
            return DummyResponse({"ok": True})

    monkeypatch.setattr(agent_client_module.httpx, "AsyncClient", CapturingClient)

    set_correlation_id("corr-xyz")
    try:
        client = AgentClient()
        result = await client.call_endpoint("http://agent", "/invoke", {"sku": "A"})
    finally:
        clear_correlation_id()

    assert result == {"ok": True}
    assert captured["headers"]["x-correlation-id"] == "corr-xyz"


@pytest.mark.asyncio
async def test_call_endpoint_fallback(monkeypatch):
    """Agent client returns fallback on timeout."""
    monkeypatch.setattr(agent_client_module.httpx, "AsyncClient", TimeoutClient)
    client = AgentClient()
    fallback = {"status": "timeout"}
    result = await client.call_endpoint("http://agent", "/invoke", {"sku": "A"}, fallback)
    assert result == fallback


@pytest.mark.asyncio
async def test_calculate_dynamic_pricing(monkeypatch):
    """Dynamic pricing extracts active amount when provided."""

    async def fake_call_endpoint(*args, **kwargs):
        return {"pricing": [{"active": {"amount": 12.5}}]}

    monkeypatch.setattr(agent_client_module.settings, "checkout_support_agent_url", "http://agent")
    monkeypatch.setattr(AgentClient, "call_endpoint", fake_call_endpoint)

    client = AgentClient()
    price = await client.calculate_dynamic_pricing("SKU-1")
    assert price == 12.5


@pytest.mark.asyncio
async def test_get_inventory_status_parses_context(monkeypatch):
    """Inventory status parses availability from inventory context."""

    async def fake_call_endpoint(*args, **kwargs):
        return {"inventory_context": {"item": {"sku": "SKU-1", "available": 0}}}

    monkeypatch.setattr(agent_client_module.settings, "inventory_health_agent_url", "http://agent")
    monkeypatch.setattr(AgentClient, "call_endpoint", fake_call_endpoint)

    client = AgentClient()
    status = await client.get_inventory_status("SKU-1")
    assert status["available"] is False
    assert status["quantity"] == 0
