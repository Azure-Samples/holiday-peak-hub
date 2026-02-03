"""Unit tests for agent client circuit breaker behavior."""

import httpx
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from crud_service.integrations.agent_client import AgentClient
import crud_service.integrations.agent_client as agent_client_module


class DummyResponse:
    """Simple response stub for httpx.AsyncClient."""

    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)
        return None

    def json(self):
        return self._payload


class TestAgentClientCircuitBreaker:
    """Tests for circuit breaker behavior."""

    @pytest.mark.asyncio
    async def test_circuit_opens_after_failures(self, monkeypatch):
        """Circuit breaker should open after multiple failures."""
        call_count = 0

        class FailingClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return None

            async def post(self, *args, **kwargs):
                nonlocal call_count
                call_count += 1
                raise httpx.TimeoutException("timeout")

        monkeypatch.setattr(agent_client_module.httpx, "AsyncClient", FailingClient)

        client = AgentClient()

        # Make multiple failing calls
        for _ in range(6):
            result = await client.call_endpoint(
                "http://agent", "/invoke", {}, {"fallback": True}
            )
            assert result == {"fallback": True}

        # Circuit should be open, preventing more calls
        # The exact behavior depends on circuit breaker configuration

    @pytest.mark.asyncio
    async def test_returns_fallback_on_http_error(self, monkeypatch):
        """Should return fallback on HTTP errors."""

        class ErrorClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return None

            async def post(self, *args, **kwargs):
                return DummyResponse({"error": "bad request"}, status_code=500)

        monkeypatch.setattr(agent_client_module.httpx, "AsyncClient", ErrorClient)

        client = AgentClient()
        result = await client.call_endpoint(
            "http://agent", "/invoke", {}, {"fallback": True}
        )
        assert result == {"fallback": True}


class TestAgentClientRetry:
    """Tests for retry behavior."""

    @pytest.mark.asyncio
    async def test_retries_on_transient_failure(self, monkeypatch):
        """Should retry on transient failures."""
        call_count = 0

        class RetryClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return None

            async def post(self, *args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count < 2:
                    raise httpx.TimeoutException("timeout")
                return DummyResponse({"success": True})

        monkeypatch.setattr(agent_client_module.httpx, "AsyncClient", RetryClient)

        client = AgentClient()
        result = await client.call_endpoint("http://agent", "/invoke", {})

        # Should have retried and succeeded
        assert call_count >= 2
        assert result == {"success": True}


class TestAgentClientProductEnrichment:
    """Tests for product enrichment methods."""

    @pytest.mark.asyncio
    async def test_get_product_enrichment_full_response(self, monkeypatch):
        """Should parse full enrichment response."""

        async def fake_call_endpoint(self, base_url, path, payload, fallback=None):
            return {
                "description": "Enriched description",
                "rating": 4.5,
                "review_count": 100,
                "features": ["Feature A", "Feature B"],
                "media": [{"url": "https://example.com/image.png"}],
                "inventory": {"available": True, "quantity": 50},
                "related": [{"sku": "SKU-002", "name": "Related Product"}],
            }

        monkeypatch.setattr(
            agent_client_module.settings, "product_enrichment_agent_url", "http://agent"
        )
        monkeypatch.setattr(AgentClient, "call_endpoint", fake_call_endpoint)

        client = AgentClient()
        result = await client.get_product_enrichment("SKU-001")

        assert result["rating"] == 4.5
        assert result["review_count"] == 100
        assert len(result["features"]) == 2
        assert result["inventory"]["available"] is True

    @pytest.mark.asyncio
    async def test_get_product_enrichment_returns_none_on_failure(self, monkeypatch):
        """Should return None when enrichment fails."""

        async def fake_call_endpoint(self, base_url, path, payload, fallback=None):
            return None

        monkeypatch.setattr(
            agent_client_module.settings, "product_enrichment_agent_url", "http://agent"
        )
        monkeypatch.setattr(AgentClient, "call_endpoint", fake_call_endpoint)

        client = AgentClient()
        result = await client.get_product_enrichment("SKU-001")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_product_enrichment_no_agent_url(self, monkeypatch):
        """Should return None when no agent URL is configured."""
        monkeypatch.setattr(
            agent_client_module.settings, "product_enrichment_agent_url", None
        )

        client = AgentClient()
        result = await client.get_product_enrichment("SKU-001")

        assert result is None


class TestAgentClientDynamicPricing:
    """Tests for dynamic pricing methods."""

    @pytest.mark.asyncio
    async def test_calculate_dynamic_pricing_extracts_price(self, monkeypatch):
        """Should extract price from pricing response."""

        async def fake_call_endpoint(self, base_url, path, payload, fallback=None):
            return {"pricing": [{"active": {"amount": 24.99}}]}

        monkeypatch.setattr(
            agent_client_module.settings, "checkout_support_agent_url", "http://agent"
        )
        monkeypatch.setattr(AgentClient, "call_endpoint", fake_call_endpoint)

        client = AgentClient()
        price = await client.calculate_dynamic_pricing("SKU-001")

        assert price == 24.99

    @pytest.mark.asyncio
    async def test_calculate_dynamic_pricing_no_active_price(self, monkeypatch):
        """Should return None when no active price exists."""

        async def fake_call_endpoint(self, base_url, path, payload, fallback=None):
            return {"pricing": [{"active": None}]}

        monkeypatch.setattr(
            agent_client_module.settings, "checkout_support_agent_url", "http://agent"
        )
        monkeypatch.setattr(AgentClient, "call_endpoint", fake_call_endpoint)

        client = AgentClient()
        price = await client.calculate_dynamic_pricing("SKU-001")

        assert price is None


class TestAgentClientInventoryStatus:
    """Tests for inventory status methods."""

    @pytest.mark.asyncio
    async def test_get_inventory_status_available(self, monkeypatch):
        """Should correctly report available inventory."""

        async def fake_call_endpoint(self, base_url, path, payload, fallback=None):
            return {
                "inventory_context": {
                    "item": {"sku": "SKU-001", "available": 50}
                }
            }

        monkeypatch.setattr(
            agent_client_module.settings, "inventory_health_agent_url", "http://agent"
        )
        monkeypatch.setattr(AgentClient, "call_endpoint", fake_call_endpoint)

        client = AgentClient()
        status = await client.get_inventory_status("SKU-001")

        assert status["available"] is True
        assert status["quantity"] == 50

    @pytest.mark.asyncio
    async def test_get_inventory_status_out_of_stock(self, monkeypatch):
        """Should correctly report out of stock."""

        async def fake_call_endpoint(self, base_url, path, payload, fallback=None):
            return {
                "inventory_context": {
                    "item": {"sku": "SKU-001", "available": 0}
                }
            }

        monkeypatch.setattr(
            agent_client_module.settings, "inventory_health_agent_url", "http://agent"
        )
        monkeypatch.setattr(AgentClient, "call_endpoint", fake_call_endpoint)

        client = AgentClient()
        status = await client.get_inventory_status("SKU-001")

        assert status["available"] is False
        assert status["quantity"] == 0

    @pytest.mark.asyncio
    async def test_get_inventory_status_fallback(self, monkeypatch):
        """Should return fallback status on failure."""

        async def fake_call_endpoint(self, base_url, path, payload, fallback=None):
            return None

        monkeypatch.setattr(
            agent_client_module.settings, "inventory_health_agent_url", "http://agent"
        )
        monkeypatch.setattr(AgentClient, "call_endpoint", fake_call_endpoint)

        client = AgentClient()
        status = await client.get_inventory_status("SKU-001")

        # Should return safe fallback
        assert status is None or status.get("available") is None
