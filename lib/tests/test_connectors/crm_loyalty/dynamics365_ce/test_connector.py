"""Tests for the Dynamics 365 Customer Engagement connector."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from holiday_peak_lib.connectors.crm_loyalty.dynamics365_ce.auth import (
    AzureADTokenProvider,
    _TokenCache,
)
from holiday_peak_lib.connectors.crm_loyalty.dynamics365_ce.connector import (
    Dynamics365CEConnector,
)
from holiday_peak_lib.connectors.crm_loyalty.dynamics365_ce.mappings import (
    _parse_dt,
    map_contact_to_customer,
    map_marketinglist_to_segment,
    map_salesorder_to_order,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE_URL = "https://testorg.crm.dynamics.com"


def _mock_credential(token: str = "test-token", expires_on: float = 9999999999.0):
    """Build a synchronous mock azure-identity credential."""
    token_obj = MagicMock()
    token_obj.token = token
    token_obj.expires_on = expires_on
    cred = MagicMock()
    cred.get_token = MagicMock(return_value=token_obj)
    return cred


def _make_connector(**kwargs) -> Dynamics365CEConnector:
    credential = _mock_credential()
    return Dynamics365CEConnector(
        base_url=_BASE_URL,
        credential=credential,
        timeout=5.0,
        retries=0,
        **kwargs,
    )


def _json_response(data: Any, status: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status,
        content=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
    )


# ---------------------------------------------------------------------------
# _TokenCache tests
# ---------------------------------------------------------------------------


class TestTokenCache:
    def test_empty_cache_returns_none(self):
        cache = _TokenCache()
        assert cache.get() is None

    def test_set_and_get(self):
        cache = _TokenCache()
        cache.set("abc", 3600)
        assert cache.get() == "abc"

    def test_expired_token_returns_none(self):
        cache = _TokenCache()
        cache.set("abc", -10)  # Already expired (TTL negative → expires immediately)
        assert cache.get() is None

    def test_clear_invalidates_token(self):
        cache = _TokenCache()
        cache.set("abc", 3600)
        cache.clear()
        assert cache.get() is None


# ---------------------------------------------------------------------------
# AzureADTokenProvider tests
# ---------------------------------------------------------------------------


class TestAzureADTokenProvider:
    @pytest.mark.asyncio
    async def test_get_token_calls_credential(self):
        cred = _mock_credential(token="my-token")
        provider = AzureADTokenProvider(resource_url=_BASE_URL, credential=cred)
        token = await provider.get_token()
        assert token == "my-token"
        cred.get_token.assert_called_once()

    @pytest.mark.asyncio
    async def test_token_is_cached(self):
        cred = _mock_credential(token="cached-token")
        provider = AzureADTokenProvider(resource_url=_BASE_URL, credential=cred)
        t1 = await provider.get_token()
        t2 = await provider.get_token()
        assert t1 == t2 == "cached-token"
        # credential.get_token should be called only once
        assert cred.get_token.call_count == 1

    @pytest.mark.asyncio
    async def test_invalidate_forces_refresh(self):
        cred = _mock_credential(token="fresh-token")
        provider = AzureADTokenProvider(resource_url=_BASE_URL, credential=cred)
        await provider.get_token()
        provider.invalidate()
        await provider.get_token()
        assert cred.get_token.call_count == 2


# ---------------------------------------------------------------------------
# Mappings tests
# ---------------------------------------------------------------------------


class TestParseDt:
    def test_parses_iso_z(self):
        dt = _parse_dt("2024-06-01T12:00:00Z")
        assert dt is not None
        assert dt.year == 2024
        assert dt.tzinfo is not None

    def test_none_returns_none(self):
        assert _parse_dt(None) is None

    def test_datetime_passthrough(self):
        dt = datetime(2024, 1, 1)
        result = _parse_dt(dt)
        assert result is not None
        assert result.tzinfo == timezone.utc


class TestMapContactToCustomer:
    def test_basic_mapping(self):
        contact = {
            "contactid": "c-1",
            "emailaddress1": "ada@example.com",
            "firstname": "Ada",
            "lastname": "Lovelace",
            "telephone1": "555-0100",
        }
        data = map_contact_to_customer(contact)
        assert data.customer_id == "c-1"
        assert data.email == "ada@example.com"
        assert data.first_name == "Ada"
        assert data.last_name == "Lovelace"
        assert data.phone == "555-0100"

    def test_optional_fields_default_none(self):
        data = map_contact_to_customer({"contactid": "c-2"})
        assert data.email is None
        assert data.loyalty_tier is None

    def test_empty_segments_list(self):
        data = map_contact_to_customer({"contactid": "c-3"})
        assert data.segments == []


class TestMapSalesorderToOrder:
    def test_basic_mapping(self):
        order = {
            "salesorderid": "o-1",
            "customerid": "c-1",
            "statecode": 0,
            "totalamount": 199.99,
            "transactioncurrencyid": "USD",
            "createdon": "2024-06-01T10:00:00Z",
        }
        data = map_salesorder_to_order(order)
        assert data.order_id == "o-1"
        assert data.total == 199.99
        assert data.status == "open"
        assert data.currency == "USD"

    def test_status_mapping_won(self):
        data = map_salesorder_to_order({"salesorderid": "o-2", "statecode": 1, "totalamount": 0})
        assert data.status == "won"

    def test_customer_id_from_dict(self):
        order = {
            "salesorderid": "o-3",
            "customerid": {"contactid": "c-99"},
            "statecode": 0,
            "totalamount": 0,
        }
        data = map_salesorder_to_order(order)
        assert data.customer_id == "c-99"


class TestMapMarketinglistToSegment:
    def test_basic_mapping(self):
        lst = {
            "listid": "s-1",
            "listname": "VIP",
            "description": "High value",
            "membercount": 10,
        }
        data = map_marketinglist_to_segment(lst)
        assert data.segment_id == "s-1"
        assert data.name == "VIP"
        assert data.member_count == 10

    def test_criteria_from_query(self):
        lst = {"listid": "s-2", "listname": "Test", "query": "revenue > 5000"}
        data = map_marketinglist_to_segment(lst)
        assert data.criteria == {"query": "revenue > 5000"}

    def test_no_query_empty_criteria(self):
        lst = {"listid": "s-3", "listname": "Empty"}
        data = map_marketinglist_to_segment(lst)
        assert data.criteria == {}


# ---------------------------------------------------------------------------
# Connector constructor tests
# ---------------------------------------------------------------------------


class TestConnectorInit:
    def test_raises_without_base_url(self):
        with pytest.raises(ValueError, match="D365_CE_BASE_URL"):
            Dynamics365CEConnector(credential=_mock_credential())

    def test_api_base_is_set(self):
        c = _make_connector()
        assert c._api_base == f"{_BASE_URL}/api/data/v9.2/"

    def test_custom_api_version(self):
        c = _make_connector(api_version="9.1")
        assert "v9.1" in c._api_base

    def test_base_url_env_var(self, monkeypatch):
        monkeypatch.setenv("D365_CE_BASE_URL", _BASE_URL)
        c = Dynamics365CEConnector(credential=_mock_credential())
        assert c._base_url == _BASE_URL


# ---------------------------------------------------------------------------
# Connector CRM methods (mocked HTTP)
# ---------------------------------------------------------------------------


@pytest.fixture
def connector() -> Dynamics365CEConnector:
    return _make_connector()


class TestGetCustomer:
    @pytest.mark.asyncio
    async def test_returns_customer_data(self, connector):
        contact_payload = {
            "contactid": "c-1",
            "emailaddress1": "test@example.com",
            "firstname": "Test",
        }
        mock_transport = httpx.MockTransport(lambda req: _json_response(contact_payload))
        connector._http_client = httpx.AsyncClient(transport=mock_transport)
        result = await connector.get_customer("c-1")
        assert result is not None
        assert result.customer_id == "c-1"
        assert result.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_returns_none_for_404(self, connector):
        mock_transport = httpx.MockTransport(lambda req: httpx.Response(404, content=b"{}"))
        connector._http_client = httpx.AsyncClient(transport=mock_transport)
        result = await connector.get_customer("nonexistent")
        assert result is None


class TestGetCustomerByEmail:
    @pytest.mark.asyncio
    async def test_finds_by_email(self, connector):
        payload = {"value": [{"contactid": "c-2", "emailaddress1": "found@example.com"}]}
        mock_transport = httpx.MockTransport(lambda req: _json_response(payload))
        connector._http_client = httpx.AsyncClient(transport=mock_transport)
        result = await connector.get_customer_by_email("found@example.com")
        assert result is not None
        assert result.customer_id == "c-2"

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, connector):
        payload = {"value": []}
        mock_transport = httpx.MockTransport(lambda req: _json_response(payload))
        connector._http_client = httpx.AsyncClient(transport=mock_transport)
        result = await connector.get_customer_by_email("unknown@example.com")
        assert result is None


class TestGetCustomerSegments:
    @pytest.mark.asyncio
    async def test_returns_segments(self, connector):
        payload = {
            "value": [
                {"listid": "s-1", "listname": "VIP", "membercount": 5},
            ]
        }
        mock_transport = httpx.MockTransport(lambda req: _json_response(payload))
        connector._http_client = httpx.AsyncClient(transport=mock_transport)
        segments = await connector.get_customer_segments("c-1")
        assert len(segments) == 1
        assert segments[0].segment_id == "s-1"

    @pytest.mark.asyncio
    async def test_empty_segments(self, connector):
        payload = {"value": []}
        mock_transport = httpx.MockTransport(lambda req: _json_response(payload))
        connector._http_client = httpx.AsyncClient(transport=mock_transport)
        segments = await connector.get_customer_segments("c-1")
        assert segments == []


class TestGetPurchaseHistory:
    @pytest.mark.asyncio
    async def test_returns_orders(self, connector):
        payload = {
            "value": [
                {
                    "salesorderid": "o-1",
                    "statecode": 1,
                    "totalamount": 50.0,
                    "transactioncurrencyid": "USD",
                }
            ]
        }
        mock_transport = httpx.MockTransport(lambda req: _json_response(payload))
        connector._http_client = httpx.AsyncClient(transport=mock_transport)
        orders = await connector.get_purchase_history("c-1")
        assert len(orders) == 1
        assert orders[0].order_id == "o-1"

    @pytest.mark.asyncio
    async def test_with_since_filter(self, connector):
        payload = {"value": []}
        captured_params: list[str] = []

        def handler(req: httpx.Request) -> httpx.Response:
            captured_params.append(str(req.url))
            return _json_response(payload)

        mock_transport = httpx.MockTransport(handler)
        connector._http_client = httpx.AsyncClient(transport=mock_transport)
        since = datetime(2024, 1, 1, tzinfo=timezone.utc)
        await connector.get_purchase_history("c-1", since=since)
        assert captured_params
        assert "createdon" in captured_params[0]


class TestUpdateCustomer:
    @pytest.mark.asyncio
    async def test_patch_and_return(self, connector):
        contact_payload = {"contactid": "c-1", "emailaddress1": "new@example.com"}
        call_count = 0

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if req.method == "PATCH":
                return httpx.Response(204, content=b"")
            return _json_response(contact_payload)

        mock_transport = httpx.MockTransport(handler)
        connector._http_client = httpx.AsyncClient(transport=mock_transport)
        result = await connector.update_customer("c-1", {"emailaddress1": "new@example.com"})
        assert result.customer_id == "c-1"


class TestTrackEvent:
    @pytest.mark.asyncio
    async def test_posts_event(self, connector):
        posted: list[bytes] = []

        def handler(req: httpx.Request) -> httpx.Response:
            posted.append(req.content)
            return httpx.Response(204, content=b"")

        mock_transport = httpx.MockTransport(handler)
        connector._http_client = httpx.AsyncClient(transport=mock_transport)
        await connector.track_event("c-1", "page_view", {"page": "/home"})
        assert posted

    @pytest.mark.asyncio
    async def test_silently_ignores_error(self, connector):
        def handler(req: httpx.Request) -> httpx.Response:
            return httpx.Response(404, content=b'{"error":"not found"}')

        mock_transport = httpx.MockTransport(handler)
        connector._http_client = httpx.AsyncClient(transport=mock_transport)
        # Should not raise
        await connector.track_event("c-1", "page_view", {})


class TestHealth:
    @pytest.mark.asyncio
    async def test_healthy_when_metadata_200(self, connector):
        mock_transport = httpx.MockTransport(lambda req: httpx.Response(200, content=b"<edmx/>"))
        with patch.object(httpx, "AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=httpx.Response(200, content=b"<edmx/>"))
            mock_client_cls.return_value = mock_client
            connector._http_client = httpx.AsyncClient(transport=mock_transport)
            result = await connector.health()
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_unhealthy_on_exception(self, connector):
        with patch.object(httpx, "AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("down"))
            mock_client_cls.return_value = mock_client
            result = await connector.health()
        assert result["ok"] is False


class TestBaseAdapterIntegration:
    """Verify that BaseAdapter resilience hooks work through the connector."""

    @pytest.mark.asyncio
    async def test_fetch_impl_returns_list(self, connector):
        payload = {"value": [{"contactid": "c-x"}]}
        mock_transport = httpx.MockTransport(lambda req: _json_response(payload))
        connector._http_client = httpx.AsyncClient(transport=mock_transport)
        result = list(await connector._fetch_impl({"_entity": "contacts"}))
        assert result == [{"contactid": "c-x"}]

    @pytest.mark.asyncio
    async def test_upsert_impl_patch(self, connector):
        def handler(req: httpx.Request) -> httpx.Response:
            if req.method == "PATCH":
                return httpx.Response(204, content=b"")
            return _json_response({"contactid": "c-1"})

        mock_transport = httpx.MockTransport(handler)
        connector._http_client = httpx.AsyncClient(transport=mock_transport)
        result = await connector._upsert_impl(
            {"_entity": "contacts", "_id": "c-1", "firstname": "X"}
        )
        assert result == {"id": "c-1"}

    @pytest.mark.asyncio
    async def test_delete_impl(self, connector):
        mock_transport = httpx.MockTransport(lambda req: httpx.Response(204, content=b""))
        connector._http_client = httpx.AsyncClient(transport=mock_transport)
        result = await connector._delete_impl("contacts(c-1)")
        assert result is True
