"""Unit tests for the Adobe Experience Platform (AEP) connector.

Tests cover:
- Authentication: token acquisition, caching, refresh, error handling
- Data mapping: XDM profiles → CustomerData, audiences → SegmentData
- Connector methods: get_customer, get_customer_by_email, get_customer_segments,
  get_purchase_history, update_customer, track_event, list_audiences,
  get_profile_preview, health
- Pagination support
- Error handling: 401, 429, network errors
"""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from holiday_peak_lib.connectors.crm_loyalty.adobe_aep.auth import (
    AdobeImsAuth,
    AdobeImsToken,
)
from holiday_peak_lib.connectors.crm_loyalty.adobe_aep.connector import (
    AdobeAEPConnector,
    _AEPHttpAdapter,
)
from holiday_peak_lib.connectors.crm_loyalty.adobe_aep.mappings import (
    audience_to_segment,
    export_record_to_order,
    xdm_to_customer,
)
from holiday_peak_lib.integrations.contracts import (
    CustomerData,
    OrderData,
    SegmentData,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

XDM_PROFILE: dict[str, Any] = {
    "entity": {
        "_id": "profile-123",
        "identities": [{"id": "ecid-abc", "namespace": {"code": "ECID"}}],
        "person": {"name": {"firstName": "Jane", "lastName": "Doe"}},
        "personalEmail": {"address": "jane.doe@example.com"},
        "mobilePhone": {"number": "+1-555-0100"},
        "segmentMembership": {
            "ups": {
                "seg-1": {"segmentID": {"_id": "seg-1"}, "status": "realized"},
                "seg-2": {"segmentID": {"_id": "seg-2"}, "status": "exited"},
            }
        },
        "loyalty": {"tier": "Gold", "lifetimeValue": 1250.0},
        "preferences": {"currency": "USD"},
        "consents": {"marketing": {"email": {"val": "y"}}},
        "timeSeriesEvents": [{"timestamp": "2024-01-15T10:00:00Z"}],
    }
}

AEP_AUDIENCE: dict[str, Any] = {
    "id": "aud-001",
    "name": "High-Value Customers",
    "description": "Customers with LTV > 500",
    "expression": {"type": "PQL", "format": "pql/text", "value": "ltv > 500"},
    "totalProfiles": 42000,
}

EXPORT_RECORD: dict[str, Any] = {
    "_id": "evt-999",
    "timestamp": "2024-03-01T08:00:00Z",
    "endUserIDs": {
        "_experience": {
            "aaid": {"id": "cust-456"},
        }
    },
    "commerce": {
        "order": {
            "purchaseID": "order-789",
            "priceTotal": 199.99,
            "currencyCode": "USD",
        },
        "purchases": {"value": "completed"},
    },
    "productListItems": [
        {"SKU": "SKU-001", "name": "Widget", "quantity": 2, "priceTotal": 99.99},
    ],
}


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------


class TestAdobeImsToken:
    def test_valid_token_not_yet_expired(self):
        token = AdobeImsToken(access_token="tok", expires_at=time.monotonic() + 300)
        assert token.is_valid() is True

    def test_expired_token_returns_false(self):
        token = AdobeImsToken(access_token="tok", expires_at=time.monotonic() - 1)
        assert token.is_valid() is False

    def test_token_within_buffer_returns_false(self):
        # expires in 30 seconds – within the 60-second safety buffer
        token = AdobeImsToken(access_token="tok", expires_at=time.monotonic() + 30)
        assert token.is_valid() is False


class TestAdobeImsAuth:
    @pytest.mark.asyncio
    async def test_fetch_token_success(self):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "access_token": "new-token",
            "expires_in": 3600,
        }

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            auth = AdobeImsAuth(
                client_id="cid",
                client_secret="csec",
                org_id="org@AdobeOrg",
            )
            token = await auth.get_token()

        assert token == "new-token"

    @pytest.mark.asyncio
    async def test_cached_token_returned_without_http_call(self):
        auth = AdobeImsAuth(client_id="cid", client_secret="csec", org_id="org")
        auth._cached = AdobeImsToken(
            access_token="cached-token", expires_at=time.monotonic() + 3600
        )

        with patch("httpx.AsyncClient") as mock_client_cls:
            token = await auth.get_token()
            mock_client_cls.assert_not_called()

        assert token == "cached-token"

    @pytest.mark.asyncio
    async def test_expired_token_triggers_refresh(self):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "access_token": "refreshed",
            "expires_in": 3600,
        }

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            auth = AdobeImsAuth(client_id="cid", client_secret="csec", org_id="org")
            auth._cached = AdobeImsToken(access_token="old", expires_at=time.monotonic() - 1)
            token = await auth.get_token()

        assert token == "refreshed"

    @pytest.mark.asyncio
    async def test_http_error_propagates(self):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(
                side_effect=httpx.HTTPStatusError("401", request=MagicMock(), response=MagicMock())
            )
            mock_client_cls.return_value = mock_client

            auth = AdobeImsAuth(client_id="cid", client_secret="csec", org_id="org")
            with pytest.raises(httpx.HTTPStatusError):
                await auth.get_token()

    def test_invalidate_clears_cache(self):
        auth = AdobeImsAuth(client_id="cid", client_secret="csec", org_id="org")
        auth._cached = AdobeImsToken(access_token="tok", expires_at=time.monotonic() + 3600)
        auth.invalidate()
        assert auth._cached is None


# ---------------------------------------------------------------------------
# Mapping tests
# ---------------------------------------------------------------------------


class TestXdmToCustomer:
    def test_basic_mapping(self):
        customer = xdm_to_customer(XDM_PROFILE)
        assert customer.customer_id == "ecid-abc"
        assert customer.first_name == "Jane"
        assert customer.last_name == "Doe"
        assert customer.email == "jane.doe@example.com"
        assert customer.phone == "+1-555-0100"
        assert "seg-1" in customer.segments
        assert "seg-2" not in customer.segments
        assert customer.loyalty_tier == "Gold"
        assert customer.lifetime_value == 1250.0
        assert customer.preferences == {"currency": "USD"}
        assert customer.last_activity is not None

    def test_missing_fields_produce_none(self):
        customer = xdm_to_customer({"entity": {"_id": "x"}})
        # _id falls back to customer_id when identities list is absent
        assert customer.customer_id == "x"
        assert customer.email is None
        assert customer.first_name is None
        assert customer.segments == []

    def test_returns_customer_data_instance(self):
        result = xdm_to_customer(XDM_PROFILE)
        assert isinstance(result, CustomerData)


class TestAudienceToSegment:
    def test_basic_mapping(self):
        segment = audience_to_segment(AEP_AUDIENCE)
        assert segment.segment_id == "aud-001"
        assert segment.name == "High-Value Customers"
        assert segment.description == "Customers with LTV > 500"
        assert segment.member_count == 42000
        assert segment.criteria["type"] == "PQL"

    def test_missing_optional_fields(self):
        segment = audience_to_segment({"id": "x", "name": "Test"})
        assert segment.description is None
        assert segment.member_count is None
        assert segment.criteria == {}

    def test_returns_segment_data_instance(self):
        result = audience_to_segment(AEP_AUDIENCE)
        assert isinstance(result, SegmentData)


class TestExportRecordToOrder:
    def test_basic_mapping(self):
        order = export_record_to_order(EXPORT_RECORD)
        assert order.order_id == "order-789"
        assert order.customer_id == "cust-456"
        assert order.status == "completed"
        assert order.total == 199.99
        assert order.currency == "USD"
        assert len(order.items) == 1
        assert order.items[0]["sku"] == "SKU-001"
        assert order.created_at is not None

    def test_returns_order_data_instance(self):
        result = export_record_to_order(EXPORT_RECORD)
        assert isinstance(result, OrderData)

    def test_empty_record(self):
        order = export_record_to_order({})
        assert order.order_id == ""
        assert order.total == 0.0
        assert order.items == []


# ---------------------------------------------------------------------------
# Connector tests (with mocked HTTP)
# ---------------------------------------------------------------------------


def _make_connector(fetch_return: Any = None, upsert_return: Any = None) -> AdobeAEPConnector:
    """Build a connector whose underlying HTTP adapter is fully mocked."""
    connector = AdobeAEPConnector(
        base_url="https://platform.adobe.io",
        org_id="test-org@AdobeOrg",
        sandbox="dev",
        inlet_id="inlet-123",
    )
    mock_http = AsyncMock(spec=_AEPHttpAdapter)
    mock_http.fetch = AsyncMock(return_value=[fetch_return or {}])
    mock_http.upsert = AsyncMock(return_value=upsert_return or {})
    connector._http = mock_http
    return connector


class TestAdobeAEPConnectorGetCustomer:
    @pytest.mark.asyncio
    async def test_returns_customer_data(self):
        connector = _make_connector(fetch_return={"entities": [XDM_PROFILE["entity"]]})
        result = await connector.get_customer("ecid-abc")
        assert isinstance(result, CustomerData)
        assert result.email == "jane.doe@example.com"

    @pytest.mark.asyncio
    async def test_returns_none_on_empty_entities(self):
        connector = _make_connector(fetch_return={"entities": []})
        result = await connector.get_customer("unknown")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_adapter_error(self):
        from holiday_peak_lib.adapters.base import AdapterError

        connector = _make_connector()
        connector._http.fetch = AsyncMock(side_effect=AdapterError("err"))
        result = await connector.get_customer("x")
        assert result is None


class TestAdobeAEPConnectorGetCustomerByEmail:
    @pytest.mark.asyncio
    async def test_returns_customer_by_email(self):
        connector = _make_connector(fetch_return={"entities": [XDM_PROFILE["entity"]]})
        result = await connector.get_customer_by_email("jane.doe@example.com")
        assert result is not None
        assert result.email == "jane.doe@example.com"


class TestAdobeAEPConnectorGetCustomerSegments:
    @pytest.mark.asyncio
    async def test_returns_matched_segments(self):
        # Profile has seg-1 as realized
        connector = _make_connector(fetch_return={"entities": [XDM_PROFILE["entity"]]})
        # list_audiences returns both segments
        connector._http.fetch = AsyncMock(
            side_effect=[
                # First call: get_customer
                [{"entities": [XDM_PROFILE["entity"]]}],
                # Second call: list_audiences
                [{"children": [AEP_AUDIENCE, {"id": "seg-2", "name": "Low-Value"}]}],
            ]
        )
        # Patch get_customer to return a known customer with segment seg-1
        from holiday_peak_lib.connectors.crm_loyalty.adobe_aep import connector as mod

        customer = xdm_to_customer(XDM_PROFILE)
        connector.get_customer = AsyncMock(return_value=customer)
        connector.list_audiences = AsyncMock(
            return_value=[
                SegmentData(segment_id="seg-1", name="High-Value"),
                SegmentData(segment_id="seg-2", name="Low-Value"),
            ]
        )
        results = await connector.get_customer_segments("ecid-abc")
        assert len(results) == 1
        assert results[0].segment_id == "seg-1"

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_profile(self):
        connector = _make_connector()
        connector.get_customer = AsyncMock(return_value=None)
        results = await connector.get_customer_segments("unknown")
        assert results == []


class TestAdobeAEPConnectorGetPurchaseHistory:
    @pytest.mark.asyncio
    async def test_returns_orders(self):
        connector = _make_connector(upsert_return={"records": [EXPORT_RECORD]})
        orders = await connector.get_purchase_history("cust-456")
        assert len(orders) == 1
        assert orders[0].order_id == "order-789"

    @pytest.mark.asyncio
    async def test_returns_empty_on_error(self):
        from holiday_peak_lib.adapters.base import AdapterError

        connector = _make_connector()
        connector._http.upsert = AsyncMock(side_effect=AdapterError("err"))
        orders = await connector.get_purchase_history("cust-x")
        assert orders == []


class TestAdobeAEPConnectorListAudiences:
    @pytest.mark.asyncio
    async def test_returns_segments(self):
        connector = _make_connector(fetch_return={"children": [AEP_AUDIENCE]})
        segments = await connector.list_audiences()
        assert len(segments) == 1
        assert segments[0].segment_id == "aud-001"

    @pytest.mark.asyncio
    async def test_pagination_params_forwarded(self):
        connector = _make_connector(fetch_return={"children": []})
        await connector.list_audiences(limit=10, start=50)
        connector._http.fetch.assert_called_once()
        call_kwargs = connector._http.fetch.call_args[0][0]
        assert call_kwargs["limit"] == 10
        assert call_kwargs["start"] == 50

    @pytest.mark.asyncio
    async def test_returns_empty_on_error(self):
        from holiday_peak_lib.adapters.base import AdapterError

        connector = _make_connector()
        connector._http.fetch = AsyncMock(side_effect=AdapterError("err"))
        result = await connector.list_audiences()
        assert result == []


class TestAdobeAEPConnectorGetProfilePreview:
    @pytest.mark.asyncio
    async def test_returns_customers(self):
        connector = _make_connector(fetch_return={"entities": [XDM_PROFILE["entity"]]})
        profiles = await connector.get_profile_preview()
        assert len(profiles) == 1
        assert isinstance(profiles[0], CustomerData)

    @pytest.mark.asyncio
    async def test_returns_empty_on_error(self):
        from holiday_peak_lib.adapters.base import AdapterError

        connector = _make_connector()
        connector._http.fetch = AsyncMock(side_effect=AdapterError("err"))
        result = await connector.get_profile_preview()
        assert result == []


class TestAdobeAEPConnectorHealth:
    @pytest.mark.asyncio
    async def test_healthy_response(self):
        connector = _make_connector(fetch_return={"entities": []})
        status = await connector.health()
        assert status["ok"] is True
        assert status["connector"] == "adobe_aep"

    @pytest.mark.asyncio
    async def test_unhealthy_response(self):
        from holiday_peak_lib.adapters.base import AdapterError

        connector = _make_connector()
        connector._http.fetch = AsyncMock(side_effect=AdapterError("connectivity issue"))
        status = await connector.health()
        assert status["ok"] is False
        assert "error" in status


class TestAdobeAEPConnectorTrackEvent:
    @pytest.mark.asyncio
    async def test_track_event_calls_upsert(self):
        connector = _make_connector(upsert_return={})
        await connector.track_event(
            "cust-1",
            "productView",
            {"timestamp": "2024-01-01T00:00:00Z", "datasetId": "ds-001"},
        )
        connector._http.upsert.assert_called_once()
        payload = connector._http.upsert.call_args[0][0]
        assert "collection" in payload.get("_path", "")


class TestAdobeAEPConnectorUpdateCustomer:
    @pytest.mark.asyncio
    async def test_update_customer_returns_updated(self):
        customer = xdm_to_customer(XDM_PROFILE)
        connector = _make_connector(upsert_return={})
        connector.get_customer = AsyncMock(return_value=customer)
        result = await connector.update_customer(
            "ecid-abc",
            {"loyalty": {"tier": "Platinum"}, "datasetId": "ds-001"},
        )
        assert result.customer_id == customer.customer_id

    @pytest.mark.asyncio
    async def test_update_raises_when_profile_missing(self):
        from holiday_peak_lib.adapters.base import AdapterError

        connector = _make_connector(upsert_return={})
        connector.get_customer = AsyncMock(return_value=None)
        with pytest.raises(AdapterError, match="not found after update"):
            await connector.update_customer(
                "ghost",
                {"loyalty": {"tier": "Bronze"}, "datasetId": "ds-001"},
            )


# ---------------------------------------------------------------------------
# HTTP adapter error mapping tests
# ---------------------------------------------------------------------------


class TestAEPHttpAdapterErrors:
    def _make_http(self) -> _AEPHttpAdapter:
        auth = MagicMock()
        auth._client_id = "cid"
        return _AEPHttpAdapter(
            base_url="https://platform.adobe.io",
            auth=auth,
            org_id="org@AdobeOrg",
            sandbox="dev",
        )

    def test_401_raises_adapter_error(self):
        from holiday_peak_lib.adapters.base import AdapterError

        adapter = self._make_http()
        response = MagicMock(spec=httpx.Response)
        response.status_code = 401
        with pytest.raises(AdapterError, match="authentication failed"):
            adapter._raise_for_status(response)

    def test_429_raises_adapter_error(self):
        from holiday_peak_lib.adapters.base import AdapterError

        adapter = self._make_http()
        response = MagicMock(spec=httpx.Response)
        response.status_code = 429
        with pytest.raises(AdapterError, match="rate limit"):
            adapter._raise_for_status(response)

    def test_500_raises_adapter_error(self):
        from holiday_peak_lib.adapters.base import AdapterError

        adapter = self._make_http()
        request = httpx.Request("GET", "https://example.com")
        response = httpx.Response(500, request=request)
        with pytest.raises(AdapterError, match="AEP API error 500"):
            adapter._raise_for_status(response)
