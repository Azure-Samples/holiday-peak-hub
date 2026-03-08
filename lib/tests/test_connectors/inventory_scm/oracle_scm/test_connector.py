"""Tests for OracleSCMConnector."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from holiday_peak_lib.adapters.base import AdapterError
from holiday_peak_lib.connectors.inventory_scm.oracle_scm.auth import (
    OracleSCMAuth,
    OracleSCMAuthError,
)
from holiday_peak_lib.connectors.inventory_scm.oracle_scm.connector import OracleSCMConnector

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_auth(token: str = "test-token") -> OracleSCMAuth:
    """Return an OracleSCMAuth stub that always returns *token*."""
    auth = MagicMock(spec=OracleSCMAuth)
    auth.get_token = AsyncMock(return_value=token)
    auth.invalidate = MagicMock()
    return auth


def _oracle_response(items: list, has_more: bool = False) -> MagicMock:
    """Build a mocked httpx.Response for Oracle onHandQuantities pagination."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 200
    resp.json.return_value = {"items": items, "hasMore": has_more}
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def connector():
    return OracleSCMConnector(
        base_url="https://oracle.example.com",
        auth=_make_auth(),
        retries=0,
        cache_ttl=0,
    )


@pytest.fixture
def sample_item():
    return {
        "ItemNumber": "ITEM-001",
        "OrganizationCode": "M1",
        "PrimaryOnHandQuantity": 75.0,
        "ReservedQuantity": 5.0,
        "PrimaryUOMCode": "EA",
    }


# ---------------------------------------------------------------------------
# Connectivity
# ---------------------------------------------------------------------------


class TestOracleSCMConnectorConnect:
    @pytest.mark.asyncio
    async def test_connect_calls_get_token(self, connector):
        await connector._connect_impl()
        connector._auth.get_token.assert_awaited_once()


# ---------------------------------------------------------------------------
# get_on_hand_quantity
# ---------------------------------------------------------------------------


class TestGetOnHandQuantity:
    @pytest.mark.asyncio
    async def test_returns_inventory_data_list(self, connector, sample_item):
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = MagicMock()
            mock_client.get = AsyncMock(return_value=_oracle_response([sample_item]))
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await connector.get_on_hand_quantity("ITEM-001", "M1")

        assert len(result) == 1
        assert result[0].item_number == "ITEM-001"
        assert result[0].on_hand_quantity == 75.0

    @pytest.mark.asyncio
    async def test_empty_response_returns_empty_list(self, connector):
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = MagicMock()
            mock_client.get = AsyncMock(return_value=_oracle_response([]))
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await connector.get_on_hand_quantity("ITEM-999")

        assert result == []

    @pytest.mark.asyncio
    async def test_filter_params_include_item_and_org(self, connector, sample_item):
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = MagicMock()
            mock_client.get = AsyncMock(return_value=_oracle_response([sample_item]))
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            await connector.get_on_hand_quantity("ITEM-001", "M1")

        call_kwargs = mock_client.get.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params", {})
        q_filter = params.get("q", "")
        assert "ITEM-001" in q_filter
        assert "M1" in q_filter


# ---------------------------------------------------------------------------
# list_on_hand_quantities
# ---------------------------------------------------------------------------


class TestListOnHandQuantities:
    @pytest.mark.asyncio
    async def test_returns_multiple_records(self, connector):
        items = [
            {"ItemNumber": "A", "OrganizationCode": "M1", "PrimaryOnHandQuantity": 10},
            {"ItemNumber": "B", "OrganizationCode": "M1", "PrimaryOnHandQuantity": 20},
        ]
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = MagicMock()
            mock_client.get = AsyncMock(return_value=_oracle_response(items))
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await connector.list_on_hand_quantities(organization_code="M1")

        assert len(result) == 2
        item_numbers = {r.item_number for r in result}
        assert item_numbers == {"A", "B"}


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


class TestPagination:
    @pytest.mark.asyncio
    async def test_paginates_until_has_more_false(self, connector):
        page1 = [{"ItemNumber": f"ITEM-{i}", "OrganizationCode": "M1"} for i in range(3)]
        page2 = [{"ItemNumber": f"ITEM-{i}", "OrganizationCode": "M1"} for i in range(3, 5)]

        responses = [
            _oracle_response(page1, has_more=True),
            _oracle_response(page2, has_more=False),
        ]

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = MagicMock()
            mock_client.get = AsyncMock(side_effect=responses)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await connector.list_on_hand_quantities()

        assert len(result) == 5
        assert mock_client.get.await_count == 2


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_missing_base_url_raises_adapter_error(self):
        connector = OracleSCMConnector(base_url="", auth=_make_auth(), retries=0, cache_ttl=0)
        with pytest.raises(AdapterError):
            await connector.get_on_hand_quantity("ITEM-001")

    @pytest.mark.asyncio
    async def test_http_401_retries_with_fresh_token(self, connector, sample_item):
        auth_error_resp = MagicMock(spec=httpx.Response)
        auth_error_resp.status_code = 401
        auth_error_resp.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("401", request=MagicMock(), response=auth_error_resp)
        )

        success_resp = _oracle_response([sample_item])

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = MagicMock()
            # First call returns 401 (raises on raise_for_status), second returns success
            mock_client.get = AsyncMock(side_effect=[auth_error_resp, success_resp])
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await connector.get_on_hand_quantity("ITEM-001")

        connector._auth.invalidate.assert_called()
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_http_500_raises_adapter_error(self, connector):
        error_resp = MagicMock(spec=httpx.Response)
        error_resp.status_code = 500
        error_resp.text = "Internal Server Error"
        http_err = httpx.HTTPStatusError("500", request=MagicMock(), response=error_resp)
        error_resp.raise_for_status = MagicMock(side_effect=http_err)

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = MagicMock()
            mock_client.get = AsyncMock(return_value=error_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(AdapterError):
                await connector.get_on_hand_quantity("ITEM-001")

    @pytest.mark.asyncio
    async def test_network_error_raises_adapter_error(self, connector):
        req_error = httpx.RequestError("Connection refused", request=MagicMock())

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = MagicMock()
            mock_client.get = AsyncMock(side_effect=req_error)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(AdapterError):
                await connector.get_on_hand_quantity("ITEM-001")

    @pytest.mark.asyncio
    async def test_unknown_resource_raises_adapter_error(self, connector):
        with pytest.raises(AdapterError, match="Unknown Oracle SCM resource"):
            await connector._fetch_impl({"resource": "unsupported"})

    @pytest.mark.asyncio
    async def test_upsert_raises_not_implemented(self, connector):
        with pytest.raises(NotImplementedError):
            await connector._upsert_impl({})

    @pytest.mark.asyncio
    async def test_delete_raises_not_implemented(self, connector):
        with pytest.raises(NotImplementedError):
            await connector._delete_impl("id")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_health_ok_when_token_succeeds(self, connector):
        result = await connector.health()
        assert result["status"] == "ok"
        assert result["connector"] == "oracle_scm"

    @pytest.mark.asyncio
    async def test_health_error_when_auth_fails(self):
        auth = MagicMock(spec=OracleSCMAuth)
        auth.get_token = AsyncMock(side_effect=OracleSCMAuthError("bad credentials"))
        connector = OracleSCMConnector(
            base_url="https://oracle.example.com",
            auth=auth,
            retries=0,
            cache_ttl=0,
        )
        result = await connector.health()
        assert result["status"] == "error"
        assert "bad credentials" in result["detail"]


# ---------------------------------------------------------------------------
# URL and filter building
# ---------------------------------------------------------------------------


class TestInternals:
    def test_resource_url(self, connector):
        url = connector._resource_url("onHandQuantities")
        assert url == (
            "https://oracle.example.com/fscmRestApi/resources/11.13.18.05/onHandQuantities"
        )

    def test_build_filter_with_item_and_org(self, connector):
        q = connector._build_filter("ITEM-001", "M1", {})
        assert "ItemNumber='ITEM-001'" in q
        assert "OrganizationCode='M1'" in q

    def test_build_filter_none_when_no_criteria(self, connector):
        q = connector._build_filter(None, None, {})
        assert q is None

    def test_build_filter_with_extra(self, connector):
        q = connector._build_filter(None, None, {"SubinventoryCode": "FGS"})
        assert "SubinventoryCode='FGS'" in q
