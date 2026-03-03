"""Unit tests for SalesforceCRMConnector."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from holiday_peak_lib.adapters.base import AdapterError
from holiday_peak_lib.connectors.crm_loyalty.salesforce.auth import (
    SalesforceAuth,
    _TokenEntry,
)
from holiday_peak_lib.connectors.crm_loyalty.salesforce.connector import (
    SalesforceCRMConnector,
)

_INSTANCE_URL = "https://myorg.salesforce.com"
_ACCESS_TOKEN = "test_access_token"
_TOKEN_ENTRY = _TokenEntry(
    access_token=_ACCESS_TOKEN,
    instance_url=_INSTANCE_URL,
    expires_at=float("inf"),
)

_CONTACT_RECORD = {
    "Id": "003xx000004TmiKAAS",
    "Email": "jane@example.com",
    "FirstName": "Jane",
    "LastName": "Doe",
    "Phone": "+1-555-0100",
    "loyalty_tier__c": "Gold",
    "Segments__c": "VIP",
    "HasOptedOutOfEmail": False,
    "HasOptedOutOfFax": False,
    "LastActivityDate": None,
    "npo02__TotalOppAmount__c": 500.0,
}

_ORDER_RECORD = {
    "Id": "801xx000003GXAiAAO",
    "AccountId": "003xx000004TmiKAAS",
    "Status": "Activated",
    "TotalAmount": 99.99,
    "CurrencyIsoCode": "USD",
    "CreatedDate": "2024-11-01T00:00:00Z",
    "LastModifiedDate": "2024-11-02T00:00:00Z",
}

_CAMPAIGN_RECORD = {
    "Id": "701xx000004TmiKAAS",
    "Name": "Holiday VIP",
    "Description": "Top Q4 spenders",
    "Type": "Email",
    "Status": "Active",
    "StartDate": "2024-11-01",
    "EndDate": "2024-12-31",
    "NumberOfContacts": 200,
}


def _make_connector(http_client=None) -> SalesforceCRMConnector:
    """Return a connector with a pre-authenticated stub auth."""
    auth = MagicMock(spec=SalesforceAuth)
    auth.get_token = AsyncMock(return_value=_TOKEN_ENTRY)
    auth.invalidate = MagicMock()
    connector = SalesforceCRMConnector(auth=auth, http_client=http_client)
    return connector


def _mock_response(body: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = body
    resp.content = json.dumps(body).encode()
    resp.raise_for_status = MagicMock()
    return resp


def _soql_response(records: list, done: bool = True) -> dict:
    return {
        "totalSize": len(records),
        "done": done,
        "records": records,
    }


class TestSalesforceCRMConnectorInit:
    def test_default_api_version(self):
        connector = _make_connector()
        assert connector._api_version == "v59.0"

    def test_custom_api_version(self):
        auth = MagicMock(spec=SalesforceAuth)
        auth.get_token = AsyncMock(return_value=_TOKEN_ENTRY)
        connector = SalesforceCRMConnector(auth=auth, api_version="v58.0")
        assert connector._api_version == "v58.0"

    def test_api_version_from_env(self, monkeypatch):
        monkeypatch.setenv("SALESFORCE_API_VERSION", "v57.0")
        auth = MagicMock(spec=SalesforceAuth)
        auth.get_token = AsyncMock(return_value=_TOKEN_ENTRY)
        connector = SalesforceCRMConnector(auth=auth)
        assert connector._api_version == "v57.0"


class TestSalesforceCRMConnectorGetCustomer:
    @pytest.mark.asyncio
    async def test_returns_customer_data(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_mock_response(_soql_response([_CONTACT_RECORD])))
        connector = _make_connector(http_client=mock_client)
        result = await connector.get_customer("003xx000004TmiKAAS")

        assert result is not None
        assert result.customer_id == "003xx000004TmiKAAS"
        assert result.email == "jane@example.com"
        assert result.loyalty_tier == "Gold"

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_mock_response(_soql_response([])))
        connector = _make_connector(http_client=mock_client)
        result = await connector.get_customer("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_raises_on_auth_failure(self):
        mock_response = _mock_response({}, status_code=401)
        mock_response.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        connector = _make_connector(http_client=mock_client)

        with pytest.raises(AdapterError, match="authentication failed"):
            await connector.get_customer("003xx")

    @pytest.mark.asyncio
    async def test_raises_on_rate_limit(self):
        mock_response = _mock_response({}, status_code=429)
        mock_response.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        connector = _make_connector(http_client=mock_client)

        with pytest.raises(AdapterError, match="rate limit"):
            await connector.get_customer("003xx")

    @pytest.mark.asyncio
    async def test_raises_without_http_client(self):
        connector = _make_connector(http_client=None)
        with pytest.raises(AdapterError, match="HTTP client not initialised"):
            await connector.get_customer("003xx")


class TestSalesforceCRMConnectorGetCustomerByEmail:
    @pytest.mark.asyncio
    async def test_returns_customer_by_email(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_mock_response(_soql_response([_CONTACT_RECORD])))
        connector = _make_connector(http_client=mock_client)
        result = await connector.get_customer_by_email("jane@example.com")

        assert result is not None
        assert result.email == "jane@example.com"

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_mock_response(_soql_response([])))
        connector = _make_connector(http_client=mock_client)
        result = await connector.get_customer_by_email("unknown@example.com")
        assert result is None


class TestSalesforceCRMConnectorGetCustomerSegments:
    @pytest.mark.asyncio
    async def test_returns_segments(self):
        campaign_member_record = {
            "CampaignId": _CAMPAIGN_RECORD["Id"],
            "Campaign": _CAMPAIGN_RECORD,
        }
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            return_value=_mock_response(_soql_response([campaign_member_record]))
        )
        connector = _make_connector(http_client=mock_client)
        segments = await connector.get_customer_segments("003xx000004TmiKAAS")

        assert len(segments) == 1
        assert segments[0].name == "Holiday VIP"
        assert segments[0].member_count == 200

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_campaigns(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_mock_response(_soql_response([])))
        connector = _make_connector(http_client=mock_client)
        segments = await connector.get_customer_segments("003xx")
        assert segments == []

    @pytest.mark.asyncio
    async def test_skips_records_without_campaign(self):
        member_no_campaign = {"CampaignId": "701MIN", "Campaign": None}
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            return_value=_mock_response(_soql_response([member_no_campaign]))
        )
        connector = _make_connector(http_client=mock_client)
        segments = await connector.get_customer_segments("003xx")
        assert segments == []


class TestSalesforceCRMConnectorGetPurchaseHistory:
    @pytest.mark.asyncio
    async def test_returns_order_list(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_mock_response(_soql_response([_ORDER_RECORD])))
        connector = _make_connector(http_client=mock_client)
        orders = await connector.get_purchase_history("003xx000004TmiKAAS")

        assert len(orders) == 1
        assert orders[0].order_id == "801xx000003GXAiAAO"
        assert orders[0].status == "Activated"

    @pytest.mark.asyncio
    async def test_includes_since_filter_in_query(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_mock_response(_soql_response([])))
        connector = _make_connector(http_client=mock_client)
        since = datetime(2024, 10, 1, tzinfo=timezone.utc)
        await connector.get_purchase_history("003xx", since=since)

        call_args = mock_client.get.call_args
        query = call_args.kwargs.get("params", {}).get("q", "")
        assert "CreatedDate" in query


class TestSalesforceCRMConnectorUpdateCustomer:
    @pytest.mark.asyncio
    async def test_updates_and_returns_refreshed_customer(self):
        patched_record = {**_CONTACT_RECORD, "loyalty_tier__c": "Platinum"}
        mock_client = AsyncMock()
        mock_patch_resp = MagicMock()
        mock_patch_resp.status_code = 204
        mock_patch_resp.raise_for_status = MagicMock()
        mock_client.patch = AsyncMock(return_value=mock_patch_resp)
        mock_client.get = AsyncMock(return_value=_mock_response(_soql_response([patched_record])))
        connector = _make_connector(http_client=mock_client)
        updated = await connector.update_customer(
            "003xx000004TmiKAAS", {"loyalty_tier__c": "Platinum"}
        )
        assert updated.loyalty_tier == "Platinum"

    @pytest.mark.asyncio
    async def test_raises_if_record_not_found_after_update(self):
        mock_client = AsyncMock()
        mock_patch_resp = MagicMock()
        mock_patch_resp.status_code = 204
        mock_patch_resp.raise_for_status = MagicMock()
        mock_client.patch = AsyncMock(return_value=mock_patch_resp)
        mock_client.get = AsyncMock(return_value=_mock_response(_soql_response([])))
        connector = _make_connector(http_client=mock_client)

        with pytest.raises(AdapterError, match="not found after update"):
            await connector.update_customer("003xx", {})


class TestSalesforceCRMConnectorTrackEvent:
    @pytest.mark.asyncio
    async def test_posts_platform_event(self):
        mock_client = AsyncMock()
        post_resp = _mock_response({"id": "evt001", "success": True})
        mock_client.post = AsyncMock(return_value=post_resp)
        connector = _make_connector(http_client=mock_client)

        await connector.track_event("003xx", "page_view", {"page": "/home"})

        mock_client.post.assert_called_once()
        call_kwargs = mock_client.post.call_args.kwargs
        assert "Retail_Engagement__e" in mock_client.post.call_args.args[0]
        body = call_kwargs["json"]
        assert body["Customer_Id__c"] == "003xx"
        assert body["Event_Type__c"] == "page_view"


class TestSalesforceCRMConnectorHealth:
    @pytest.mark.asyncio
    async def test_returns_ok_on_success(self):
        limits_resp = MagicMock()
        limits_resp.status_code = 200
        limits_resp.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=limits_resp)
        connector = _make_connector(http_client=mock_client)
        result = await connector.health()
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_returns_not_ok_on_error(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("network error"))
        connector = _make_connector(http_client=mock_client)
        result = await connector.health()
        assert result["ok"] is False
        assert "network error" in result["error"]

    @pytest.mark.asyncio
    async def test_returns_not_ok_without_client(self):
        connector = _make_connector(http_client=None)
        result = await connector.health()
        assert result["ok"] is False


class TestSalesforceCRMConnectorContextManager:
    @pytest.mark.asyncio
    async def test_context_manager_opens_and_closes_client(self):
        auth = MagicMock(spec=SalesforceAuth)
        auth.get_token = AsyncMock(return_value=_TOKEN_ENTRY)
        connector = SalesforceCRMConnector(auth=auth)

        async with connector:
            assert connector._http_client is not None

        assert connector._http_client is None


class TestSalesforceCRMConnectorPagination:
    @pytest.mark.asyncio
    async def test_follows_next_records_url(self):
        first_page = {
            "totalSize": 2,
            "done": False,
            "records": [_CONTACT_RECORD],
            "nextRecordsUrl": "/services/data/v59.0/query/01gxx001",
        }
        second_page = {
            "totalSize": 2,
            "done": True,
            "records": [{**_CONTACT_RECORD, "Id": "003xx000004SecondAAA"}],
        }
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=[
                _mock_response(first_page),
                _mock_response(second_page),
            ]
        )
        connector = _make_connector(http_client=mock_client)
        result = await connector.get_customer("003xx000004TmiKAAS")

        # get_customer takes the first record, but pagination is exercised
        assert mock_client.get.call_count == 2
