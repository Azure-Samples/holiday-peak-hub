"""Unit tests for the Braze Customer Engagement connector.

All external HTTP calls are intercepted with ``httpx.MockTransport`` so
tests are fully offline.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import httpx
import pytest

from holiday_peak_lib.adapters.base import AdapterError
from holiday_peak_lib.connectors.crm_loyalty.braze.auth import BrazeAuth
from holiday_peak_lib.connectors.crm_loyalty.braze.connector import BrazeConnector
from holiday_peak_lib.connectors.crm_loyalty.braze.mappings import (
    map_braze_purchase_to_order,
    map_braze_segment_to_segment,
    map_braze_user_to_customer,
)
from holiday_peak_lib.integrations.contracts import CustomerData, OrderData, SegmentData

# ---------------------------------------------------------------------------
# Shared fixtures & helpers
# ---------------------------------------------------------------------------

_USER_PAYLOAD = {
    "external_id": "user-1",
    "email": "ada@example.com",
    "first_name": "Ada",
    "last_name": "Lovelace",
    "phone": "+15550001234",
    "email_subscribe": "opted_in",
    "push_subscribe": "subscribed",
    "custom_attributes": {"tier": "gold", "lifetime_value": "199.99"},
    "purchases": [
        {
            "product_id": "sku-42",
            "currency": "USD",
            "price": 49.99,
            "time": "2024-06-15T10:00:00Z",
            "quantity": 2,
        }
    ],
    "last_used_app": {"time": "2024-07-01T08:00:00Z"},
}

_SEGMENT_PAYLOAD = {
    "id": "seg-1",
    "name": "Holiday Shoppers",
    "analytics_tracking_enabled": True,
    "size": 5000,
}

_CAMPAIGN_PAYLOAD = {
    "id": "camp-1",
    "name": "Summer Sale",
    "is_archived": False,
}


def _make_transport(routes: dict[str, object]):
    """Build an ``httpx.MockTransport`` from a dict of path -> response body."""

    def handler(request: httpx.Request) -> httpx.Response:
        key = f"{request.method} {request.url.path}"
        body = routes.get(key)
        if body is None:
            return httpx.Response(404, json={"error": "not found"})
        return httpx.Response(200, json=body)

    return httpx.MockTransport(handler)


def _make_connector(routes: dict[str, object], **kwargs) -> BrazeConnector:
    return BrazeConnector(
        api_key="test-api-key",
        transport=_make_transport(routes),
        retries=0,
        timeout=5.0,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# BrazeAuth tests
# ---------------------------------------------------------------------------


class TestBrazeAuth:
    def test_headers_contain_bearer_token(self):
        auth = BrazeAuth(api_key="my-secret-key")
        assert auth.headers["Authorization"] == "Bearer my-secret-key"
        assert auth.headers["Content-Type"] == "application/json"

    def test_missing_api_key_raises(self, monkeypatch):
        monkeypatch.delenv("BRAZE_API_KEY", raising=False)
        with pytest.raises(ValueError, match="BRAZE_API_KEY"):
            BrazeAuth(api_key=None)

    def test_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("BRAZE_API_KEY", "env-key")
        auth = BrazeAuth()
        assert auth.headers["Authorization"] == "Bearer env-key"


# ---------------------------------------------------------------------------
# Mapping tests
# ---------------------------------------------------------------------------


class TestMappings:
    def test_map_user_canonical_fields(self):
        customer = map_braze_user_to_customer(_USER_PAYLOAD)
        assert isinstance(customer, CustomerData)
        assert customer.customer_id == "user-1"
        assert customer.email == "ada@example.com"
        assert customer.first_name == "Ada"
        assert customer.last_name == "Lovelace"
        assert customer.phone == "+15550001234"

    def test_map_user_loyalty_tier(self):
        customer = map_braze_user_to_customer(_USER_PAYLOAD)
        assert customer.loyalty_tier == "gold"

    def test_map_user_lifetime_value(self):
        customer = map_braze_user_to_customer(_USER_PAYLOAD)
        assert customer.lifetime_value == pytest.approx(199.99)

    def test_map_user_consent(self):
        customer = map_braze_user_to_customer(_USER_PAYLOAD)
        assert customer.consent["email_subscribe"] == "opted_in"
        assert customer.consent["push_subscribe"] == "subscribed"

    def test_map_user_last_activity(self):
        customer = map_braze_user_to_customer(_USER_PAYLOAD)
        assert customer.last_activity is not None
        assert customer.last_activity.year == 2024

    def test_map_user_missing_optional_fields(self):
        raw = {"external_id": "u2"}
        customer = map_braze_user_to_customer(raw)
        assert customer.customer_id == "u2"
        assert customer.email is None
        assert customer.loyalty_tier is None
        assert customer.lifetime_value is None

    def test_map_purchase_to_order(self):
        purchase = _USER_PAYLOAD["purchases"][0]
        order = map_braze_purchase_to_order(purchase)
        assert isinstance(order, OrderData)
        assert order.order_id == "sku-42_2024-06-15T10:00:00Z"
        assert order.total == pytest.approx(99.98)
        assert order.currency == "USD"
        assert order.status == "completed"
        assert order.created_at is not None

    def test_map_segment(self):
        seg = map_braze_segment_to_segment(_SEGMENT_PAYLOAD)
        assert isinstance(seg, SegmentData)
        assert seg.segment_id == "seg-1"
        assert seg.name == "Holiday Shoppers"
        assert seg.member_count == 5000
        assert seg.criteria["analytics_tracking_enabled"] is True


# ---------------------------------------------------------------------------
# Connector – authentication & error handling
# ---------------------------------------------------------------------------


class TestBrazeConnectorAuth:
    @pytest.mark.asyncio
    async def test_auth_header_sent(self):
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"users": []})

        connector = BrazeConnector(
            api_key="secret-key",
            transport=httpx.MockTransport(handler),
            retries=0,
        )
        await connector.get_customer("any-id")
        assert captured[0].headers["Authorization"] == "Bearer secret-key"

    @pytest.mark.asyncio
    async def test_401_raises_adapter_error(self):
        transport = httpx.MockTransport(lambda r: httpx.Response(401, json={}))
        connector = BrazeConnector(api_key="bad-key", transport=transport, retries=0)
        with pytest.raises(AdapterError, match="authentication failed"):
            await connector.get_customer("u1")

    @pytest.mark.asyncio
    async def test_429_raises_adapter_error(self):
        transport = httpx.MockTransport(lambda r: httpx.Response(429, json={}))
        connector = BrazeConnector(api_key="key", transport=transport, retries=0)
        with pytest.raises(AdapterError, match="rate limit"):
            await connector.get_customer("u1")

    @pytest.mark.asyncio
    async def test_500_raises_adapter_error(self):
        transport = httpx.MockTransport(lambda r: httpx.Response(500, json={}))
        connector = BrazeConnector(api_key="key", transport=transport, retries=0)
        with pytest.raises(AdapterError, match="500"):
            await connector.get_customer("u1")


# ---------------------------------------------------------------------------
# Connector – get_customer
# ---------------------------------------------------------------------------


class TestGetCustomer:
    @pytest.mark.asyncio
    async def test_get_customer_found(self):
        connector = _make_connector({"POST /users/export/ids": {"users": [_USER_PAYLOAD]}})
        customer = await connector.get_customer("user-1")
        assert customer is not None
        assert customer.customer_id == "user-1"
        assert customer.email == "ada@example.com"

    @pytest.mark.asyncio
    async def test_get_customer_not_found(self):
        connector = _make_connector({"POST /users/export/ids": {"users": []}})
        customer = await connector.get_customer("unknown")
        assert customer is None

    @pytest.mark.asyncio
    async def test_get_customer_by_email(self):
        connector = _make_connector({"POST /users/export/ids": {"users": [_USER_PAYLOAD]}})
        customer = await connector.get_customer_by_email("ada@example.com")
        assert customer is not None
        assert customer.email == "ada@example.com"


# ---------------------------------------------------------------------------
# Connector – get_customer_segments
# ---------------------------------------------------------------------------


class TestGetCustomerSegments:
    @pytest.mark.asyncio
    async def test_segments_returned(self):
        connector = _make_connector(
            {
                "POST /users/export/ids": {"users": [_USER_PAYLOAD]},
                "GET /segments/list": {"segments": [_SEGMENT_PAYLOAD]},
            }
        )
        segments = await connector.get_customer_segments("user-1")
        assert isinstance(segments, list)
        assert all(isinstance(s, SegmentData) for s in segments)

    @pytest.mark.asyncio
    async def test_segments_empty_when_customer_missing(self):
        connector = _make_connector(
            {
                "POST /users/export/ids": {"users": []},
                "GET /segments/list": {"segments": [_SEGMENT_PAYLOAD]},
            }
        )
        segments = await connector.get_customer_segments("ghost")
        assert segments == []


# ---------------------------------------------------------------------------
# Connector – get_purchase_history
# ---------------------------------------------------------------------------


class TestGetPurchaseHistory:
    @pytest.mark.asyncio
    async def test_purchase_history_returned(self):
        connector = _make_connector({"POST /users/export/ids": {"users": [_USER_PAYLOAD]}})
        orders = await connector.get_purchase_history("user-1")
        assert len(orders) == 1
        assert orders[0].total == pytest.approx(99.98)

    @pytest.mark.asyncio
    async def test_purchase_history_empty_user(self):
        connector = _make_connector({"POST /users/export/ids": {"users": []}})
        orders = await connector.get_purchase_history("ghost")
        assert orders == []

    @pytest.mark.asyncio
    async def test_purchase_history_since_filter(self):
        connector = _make_connector({"POST /users/export/ids": {"users": [_USER_PAYLOAD]}})
        since = datetime(2025, 1, 1, tzinfo=timezone.utc)
        orders = await connector.get_purchase_history("user-1", since=since)
        # The only purchase is from 2024, so it should be filtered out
        assert orders == []


# ---------------------------------------------------------------------------
# Connector – track_event
# ---------------------------------------------------------------------------


class TestTrackEvent:
    @pytest.mark.asyncio
    async def test_track_event_posts_correctly(self):
        payloads: list[bytes] = []

        def handler(request: httpx.Request) -> httpx.Response:
            payloads.append(request.content)
            return httpx.Response(201, json={"message": "success"})

        connector = BrazeConnector(
            api_key="key",
            transport=httpx.MockTransport(handler),
            retries=0,
        )
        await connector.track_event("user-1", "add_to_cart", {"sku": "sku-42", "qty": 1})
        body = json.loads(payloads[0])
        events = body.get("events", [])
        assert len(events) == 1
        assert events[0]["name"] == "add_to_cart"
        assert events[0]["external_id"] == "user-1"
        assert events[0]["properties"]["sku"] == "sku-42"


# ---------------------------------------------------------------------------
# Connector – update_customer
# ---------------------------------------------------------------------------


class TestUpdateCustomer:
    @pytest.mark.asyncio
    async def test_update_customer(self):
        call_count = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            call_count["n"] += 1
            # First call is the track; second is the re-fetch via export/ids
            return httpx.Response(200, json={"users": [_USER_PAYLOAD], "message": "success"})

        connector = BrazeConnector(
            api_key="key",
            transport=httpx.MockTransport(handler),
            retries=0,
        )
        customer = await connector.update_customer("user-1", {"custom_attribute_x": "y"})
        assert customer.customer_id == "user-1"

    @pytest.mark.asyncio
    async def test_update_customer_not_found_after_update(self):
        responses = iter(
            [
                httpx.Response(200, json={"message": "success"}),
                httpx.Response(200, json={"users": []}),
            ]
        )

        connector = BrazeConnector(
            api_key="key",
            transport=httpx.MockTransport(lambda r: next(responses)),
            retries=0,
        )
        with pytest.raises(AdapterError, match="not found after update"):
            await connector.update_customer("ghost", {})


# ---------------------------------------------------------------------------
# Connector – list_campaigns / send_message
# ---------------------------------------------------------------------------


class TestCampaigns:
    @pytest.mark.asyncio
    async def test_list_campaigns(self):
        connector = _make_connector({"GET /campaigns/list": {"campaigns": [_CAMPAIGN_PAYLOAD]}})
        campaigns = await connector.list_campaigns()
        assert len(campaigns) == 1
        assert campaigns[0]["id"] == "camp-1"

    @pytest.mark.asyncio
    async def test_list_campaigns_pagination(self):
        pages_requested: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            pages_requested.append(request.url.params.get("page", "0"))
            return httpx.Response(200, json={"campaigns": []})

        connector = BrazeConnector(
            api_key="key",
            transport=httpx.MockTransport(handler),
            retries=0,
        )
        await connector.list_campaigns(page=2)
        assert pages_requested[-1] == "2"

    @pytest.mark.asyncio
    async def test_send_message(self):
        connector = _make_connector(
            {"POST /messages/send": {"dispatch_id": "disp-1", "message": "success"}}
        )
        result = await connector.send_message(
            campaign_id="camp-1",
            recipients=[{"external_user_id": "user-1"}],
        )
        assert result["dispatch_id"] == "disp-1"


# ---------------------------------------------------------------------------
# Connector – segment list
# ---------------------------------------------------------------------------


class TestSegmentList:
    @pytest.mark.asyncio
    async def test_list_segments_pagination(self):
        pages_requested: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            pages_requested.append(request.url.params.get("page", "0"))
            return httpx.Response(200, json={"segments": []})

        connector = BrazeConnector(
            api_key="key",
            transport=httpx.MockTransport(handler),
            retries=0,
        )
        # Trigger via the low-level helper used by get_customer_segments
        await connector._list_segments(page=3)
        assert pages_requested[-1] == "3"


# ---------------------------------------------------------------------------
# Connector – health check
# ---------------------------------------------------------------------------


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_health_ok(self):
        connector = _make_connector({"GET /segments/list": {"segments": []}})
        result = await connector.health()
        assert result["ok"] is True
        assert result["connector"] == "braze"

    @pytest.mark.asyncio
    async def test_health_failure(self):
        transport = httpx.MockTransport(lambda r: httpx.Response(500, json={}))
        connector = BrazeConnector(api_key="key", transport=transport, retries=0)
        result = await connector.health()
        assert result["ok"] is False
        assert "error" in result


# ---------------------------------------------------------------------------
# Connector – BaseAdapter hooks (unsupported operations)
# ---------------------------------------------------------------------------


class TestBaseAdapterHooks:
    @pytest.mark.asyncio
    async def test_fetch_unknown_op_raises(self):
        connector = BrazeConnector(api_key="key", retries=0)
        with pytest.raises(AdapterError, match="Unknown Braze fetch operation"):
            await connector._fetch_impl({"_op": "unsupported"})

    @pytest.mark.asyncio
    async def test_upsert_unknown_op_raises(self):
        connector = BrazeConnector(api_key="key", retries=0)
        with pytest.raises(AdapterError, match="Unknown Braze upsert operation"):
            await connector._upsert_impl({"_op": "unsupported"})

    @pytest.mark.asyncio
    async def test_delete_raises(self):
        connector = BrazeConnector(api_key="key", retries=0)
        with pytest.raises(AdapterError, match="Delete is not supported"):
            await connector._delete_impl("any-id")
