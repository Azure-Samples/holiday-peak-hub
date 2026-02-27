"""Unit tests for newly added AgentClient methods."""

import pytest

import crud_service.integrations.agent_client as agent_client_module

AgentClient = agent_client_module.AgentClient


# ── Semantic Search ─────────────────────────────────────────────────


class TestSemanticSearch:
    """Tests for AgentClient.semantic_search."""

    @pytest.mark.asyncio
    async def test_returns_products_list(self, monkeypatch):
        """Should return product list from agent response."""

        async def fake_call(self, agent_url=None, endpoint=None, data=None, fallback_value=None):
            return {"products": [{"id": "p1", "name": "Widget"}]}

        monkeypatch.setattr(
            agent_client_module.settings, "catalog_search_agent_url", "http://agent"
        )
        monkeypatch.setattr(AgentClient, "call_endpoint", fake_call)

        client = AgentClient()
        result = await client.semantic_search("widget")
        assert result == [{"id": "p1", "name": "Widget"}]

    @pytest.mark.asyncio
    async def test_returns_results_key(self, monkeypatch):
        """Should also accept 'results' key."""

        async def fake_call(self, agent_url=None, endpoint=None, data=None, fallback_value=None):
            return {"results": [{"id": "p2"}]}

        monkeypatch.setattr(
            agent_client_module.settings, "catalog_search_agent_url", "http://agent"
        )
        monkeypatch.setattr(AgentClient, "call_endpoint", fake_call)

        client = AgentClient()
        result = await client.semantic_search("query")
        assert result == [{"id": "p2"}]

    @pytest.mark.asyncio
    async def test_returns_empty_on_none(self, monkeypatch):
        """Should return empty list when agent returns None."""

        async def fake_call(self, agent_url=None, endpoint=None, data=None, fallback_value=None):
            return None

        monkeypatch.setattr(
            agent_client_module.settings, "catalog_search_agent_url", "http://agent"
        )
        monkeypatch.setattr(AgentClient, "call_endpoint", fake_call)

        client = AgentClient()
        result = await client.semantic_search("query")
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_url(self, monkeypatch):
        """Should return empty list when no agent URL is configured."""
        monkeypatch.setattr(
            agent_client_module.settings, "catalog_search_agent_url", None
        )
        monkeypatch.setattr(
            agent_client_module.settings, "agent_apim_base_url", None
        )

        client = AgentClient()
        result = await client.semantic_search("query")
        assert result == []


# ── Order Status ────────────────────────────────────────────────────


class TestGetOrderStatus:
    """Tests for AgentClient.get_order_status."""

    @pytest.mark.asyncio
    async def test_returns_tracking_payload(self, monkeypatch):

        async def fake_call(self, agent_url=None, endpoint=None, data=None, fallback_value=None):
            return {"order_id": "o1", "status": "shipped", "tracking_url": "https://track.me"}

        monkeypatch.setattr(
            agent_client_module.settings, "order_status_agent_url", "http://agent"
        )
        monkeypatch.setattr(AgentClient, "call_endpoint", fake_call)

        client = AgentClient()
        result = await client.get_order_status("o1")
        assert result["status"] == "shipped"

    @pytest.mark.asyncio
    async def test_returns_none_on_failure(self, monkeypatch):

        async def fake_call(self, agent_url=None, endpoint=None, data=None, fallback_value=None):
            return None

        monkeypatch.setattr(
            agent_client_module.settings, "order_status_agent_url", "http://agent"
        )
        monkeypatch.setattr(AgentClient, "call_endpoint", fake_call)

        client = AgentClient()
        result = await client.get_order_status("o1")
        assert result is None


# ── Inventory Reservation ─────────────────────────────────────────


class TestValidateReservation:
    """Tests for AgentClient.validate_reservation."""

    @pytest.mark.asyncio
    async def test_returns_valid_reservation(self, monkeypatch):

        async def fake_call(self, agent_url=None, endpoint=None, data=None, fallback_value=None):
            return {"valid": True, "reserved_qty": 5}

        monkeypatch.setattr(
            agent_client_module.settings, "inventory_reservation_agent_url", "http://agent"
        )
        monkeypatch.setattr(AgentClient, "call_endpoint", fake_call)

        client = AgentClient()
        result = await client.validate_reservation("SKU-1", 5)
        assert result["valid"] is True

    @pytest.mark.asyncio
    async def test_returns_invalid_reservation(self, monkeypatch):

        async def fake_call(self, agent_url=None, endpoint=None, data=None, fallback_value=None):
            return {"valid": False, "reason": "Insufficient stock"}

        monkeypatch.setattr(
            agent_client_module.settings, "inventory_reservation_agent_url", "http://agent"
        )
        monkeypatch.setattr(AgentClient, "call_endpoint", fake_call)

        client = AgentClient()
        result = await client.validate_reservation("SKU-1", 100)
        assert result["valid"] is False

    @pytest.mark.asyncio
    async def test_returns_none_when_no_url(self, monkeypatch):
        monkeypatch.setattr(
            agent_client_module.settings, "inventory_reservation_agent_url", None
        )
        monkeypatch.setattr(
            agent_client_module.settings, "agent_apim_base_url", None
        )

        client = AgentClient()
        result = await client.validate_reservation("SKU-1", 1)
        assert result is None


# ── Logistics: Delivery ETA ─────────────────────────────────────────


class TestGetDeliveryEta:
    """Tests for AgentClient.get_delivery_eta."""

    @pytest.mark.asyncio
    async def test_returns_eta(self, monkeypatch):

        async def fake_call(self, agent_url=None, endpoint=None, data=None, fallback_value=None):
            return {"tracking_id": "t1", "eta": "2025-01-15T10:00:00Z"}

        monkeypatch.setattr(
            agent_client_module.settings, "logistics_eta_agent_url", "http://agent"
        )
        monkeypatch.setattr(AgentClient, "call_endpoint", fake_call)

        client = AgentClient()
        result = await client.get_delivery_eta("t1")
        assert result["eta"] == "2025-01-15T10:00:00Z"

    @pytest.mark.asyncio
    async def test_returns_none_on_failure(self, monkeypatch):

        async def fake_call(self, agent_url=None, endpoint=None, data=None, fallback_value=None):
            return None

        monkeypatch.setattr(
            agent_client_module.settings, "logistics_eta_agent_url", "http://agent"
        )
        monkeypatch.setattr(AgentClient, "call_endpoint", fake_call)

        client = AgentClient()
        result = await client.get_delivery_eta("t1")
        assert result is None


# ── Logistics: Carrier Recommendation ──────────────────────────────


class TestGetCarrierRecommendation:
    """Tests for AgentClient.get_carrier_recommendation."""

    @pytest.mark.asyncio
    async def test_returns_carrier(self, monkeypatch):

        async def fake_call(self, agent_url=None, endpoint=None, data=None, fallback_value=None):
            return {"carrier": "FedEx", "cost": 12.50}

        monkeypatch.setattr(
            agent_client_module.settings, "logistics_carrier_agent_url", "http://agent"
        )
        monkeypatch.setattr(AgentClient, "call_endpoint", fake_call)

        client = AgentClient()
        result = await client.get_carrier_recommendation("t1")
        assert result["carrier"] == "FedEx"


# ── Logistics: Return Plan ─────────────────────────────────────────


class TestGetReturnPlan:
    """Tests for AgentClient.get_return_plan."""

    @pytest.mark.asyncio
    async def test_returns_plan(self, monkeypatch):

        async def fake_call(self, agent_url=None, endpoint=None, data=None, fallback_value=None):
            return {"steps": ["Label", "Drop-off"], "cost": 0}

        monkeypatch.setattr(
            agent_client_module.settings, "logistics_returns_agent_url", "http://agent"
        )
        monkeypatch.setattr(AgentClient, "call_endpoint", fake_call)

        client = AgentClient()
        result = await client.get_return_plan("t1")
        assert len(result["steps"]) == 2


# ── CRM: Customer Profile ──────────────────────────────────────────


class TestGetCustomerProfile:
    """Tests for AgentClient.get_customer_profile."""

    @pytest.mark.asyncio
    async def test_returns_profile(self, monkeypatch):

        async def fake_call(self, agent_url=None, endpoint=None, data=None, fallback_value=None):
            return {"contact_id": "c1", "tier": "gold"}

        monkeypatch.setattr(
            agent_client_module.settings, "crm_profile_agent_url", "http://agent"
        )
        monkeypatch.setattr(AgentClient, "call_endpoint", fake_call)

        client = AgentClient()
        result = await client.get_customer_profile("c1")
        assert result["tier"] == "gold"

    @pytest.mark.asyncio
    async def test_returns_none_when_no_url(self, monkeypatch):
        monkeypatch.setattr(
            agent_client_module.settings, "crm_profile_agent_url", None
        )
        monkeypatch.setattr(
            agent_client_module.settings, "agent_apim_base_url", None
        )

        client = AgentClient()
        result = await client.get_customer_profile("c1")
        assert result is None


# ── CRM: Personalization ───────────────────────────────────────────


class TestGetPersonalization:
    """Tests for AgentClient.get_personalization."""

    @pytest.mark.asyncio
    async def test_returns_personalization(self, monkeypatch):

        async def fake_call(self, agent_url=None, endpoint=None, data=None, fallback_value=None):
            return {"segment": "vip", "offers": ["offer-1"]}

        monkeypatch.setattr(
            agent_client_module.settings, "crm_segmentation_agent_url", "http://agent"
        )
        monkeypatch.setattr(AgentClient, "call_endpoint", fake_call)

        client = AgentClient()
        result = await client.get_personalization("c1")
        assert result["segment"] == "vip"


# ── URL Resolution ──────────────────────────────────────────────────


class TestResolveAgentUrl:
    """Tests for AgentClient._resolve_agent_url with APIM fallback."""

    def test_explicit_url_takes_precedence(self, monkeypatch):
        monkeypatch.setattr(
            agent_client_module.settings, "agent_apim_base_url", "https://apim.example.com"
        )

        client = AgentClient()
        assert client._resolve_agent_url("http://explicit", "svc") == "http://explicit"

    def test_strips_trailing_slash_from_explicit(self, monkeypatch):
        monkeypatch.setattr(
            agent_client_module.settings, "agent_apim_base_url", None
        )

        client = AgentClient()
        assert client._resolve_agent_url("http://explicit/", "svc") == "http://explicit"

    def test_apim_fallback_when_explicit_is_none(self, monkeypatch):
        monkeypatch.setattr(
            agent_client_module.settings, "agent_apim_base_url", "https://apim.example.com"
        )

        client = AgentClient()
        url = client._resolve_agent_url(None, "my-agent-service")
        assert url == "https://apim.example.com/agents/my-agent-service"

    def test_returns_none_when_nothing_configured(self, monkeypatch):
        monkeypatch.setattr(
            agent_client_module.settings, "agent_apim_base_url", None
        )

        client = AgentClient()
        assert client._resolve_agent_url(None, "svc") is None
