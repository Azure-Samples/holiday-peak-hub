"""Unit tests for GenericRestPIMConnector."""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from holiday_peak_lib.integrations import (
    AssetData,
    GenericRestPIMConnector,
    PIMConnectionConfig,
    ProductData,
)
from holiday_peak_lib.integrations.pim_generic_rest import _TokenBucket


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(**overrides) -> PIMConnectionConfig:
    defaults = dict(
        base_url="https://pim.example.com",
        auth_type="bearer",
        auth_credentials={"token": "test-token"},
        product_endpoint="/api/products",
        asset_endpoint="/api/assets",
        category_endpoint="/api/categories",
        search_endpoint="/api/products/search",
        field_mapping={"pim_name": "title", "pim_desc": "description"},
        page_size=50,
        rate_limit_rps=100,
        max_retries=2,
        retry_backoff_base=0.01,
        timeout_seconds=5.0,
    )
    defaults.update(overrides)
    return PIMConnectionConfig(**defaults)


def _make_connector(**overrides) -> GenericRestPIMConnector:
    return GenericRestPIMConnector(_make_config(**overrides))


def _mock_response(status_code: int = 200, body: object = None) -> httpx.Response:
    content = json.dumps(body or {}).encode()
    response = httpx.Response(
        status_code,
        content=content,
        headers={"content-type": "application/json"},
        request=httpx.Request("GET", "https://pim.example.com/api/products"),
    )
    return response


# ---------------------------------------------------------------------------
# PIMConnectionConfig
# ---------------------------------------------------------------------------

class TestPIMConnectionConfig:
    def test_defaults(self):
        cfg = PIMConnectionConfig(
            base_url="https://pim.example.com",
            auth_credentials={"token": "x"},
        )
        assert cfg.product_endpoint == "/api/products"
        assert cfg.page_size == 100
        assert cfg.rate_limit_rps == 10
        assert cfg.auth_type == "bearer"

    def test_custom_fields(self):
        cfg = PIMConnectionConfig(
            base_url="https://pim.example.com",
            auth_type="basic",
            auth_credentials={"username": "u", "password": "p"},
            field_mapping={"name": "title"},
            page_size=25,
        )
        assert cfg.auth_type == "basic"
        assert cfg.field_mapping == {"name": "title"}
        assert cfg.page_size == 25


# ---------------------------------------------------------------------------
# Auth header building
# ---------------------------------------------------------------------------

class TestAuthHeaders:
    def test_bearer_auth(self):
        connector = _make_connector(auth_type="bearer", auth_credentials={"token": "abc"})
        headers = connector._build_auth_headers()
        assert headers["Authorization"] == "Bearer abc"

    def test_basic_auth(self):
        import base64
        connector = _make_connector(
            auth_type="basic",
            auth_credentials={"username": "user", "password": "pass"},
        )
        headers = connector._build_auth_headers()
        expected = base64.b64encode(b"user:pass").decode()
        assert headers["Authorization"] == f"Basic {expected}"

    def test_api_key_auth(self):
        connector = _make_connector(
            auth_type="api_key",
            auth_credentials={"header": "X-API-KEY", "key": "my-key"},
        )
        headers = connector._build_auth_headers()
        assert headers["X-API-KEY"] == "my-key"

    def test_api_key_auth_default_header(self):
        connector = _make_connector(
            auth_type="api_key",
            auth_credentials={"key": "my-key"},
        )
        headers = connector._build_auth_headers()
        assert headers["X-Api-Key"] == "my-key"

    def test_oauth2_auth(self):
        connector = _make_connector(
            auth_type="oauth2",
            auth_credentials={"access_token": "oauth-token"},
        )
        headers = connector._build_auth_headers()
        assert headers["Authorization"] == "Bearer oauth-token"

    def test_unknown_auth_type_returns_empty(self):
        connector = _make_connector(
            auth_type="magic",
            auth_credentials={},
        )
        headers = connector._build_auth_headers()
        assert headers == {}


# ---------------------------------------------------------------------------
# Token bucket
# ---------------------------------------------------------------------------

class TestTokenBucket:
    @pytest.mark.asyncio
    async def test_acquire_does_not_raise(self):
        bucket = _TokenBucket(rate=1000)
        await bucket.acquire()

    @pytest.mark.asyncio
    async def test_acquire_throttles(self):
        """Acquiring when bucket is empty should sleep (patched)."""
        bucket = _TokenBucket(rate=1)
        # Drain the bucket
        await bucket.acquire()
        # Next acquire should try to sleep; patch asyncio.sleep to verify
        with patch("holiday_peak_lib.integrations.pim_generic_rest.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await bucket.acquire()
            mock_sleep.assert_awaited()


# ---------------------------------------------------------------------------
# map_to_internal
# ---------------------------------------------------------------------------

class TestMapToInternal:
    def test_basic_mapping(self):
        connector = _make_connector(field_mapping={"pim_name": "title", "pim_desc": "description"})
        raw = {
            "sku": "SKU-001",
            "pim_name": "Awesome Widget",
            "pim_desc": "A great widget",
            "brand": "WidgetCo",
            "status": "active",
        }
        product = connector.map_to_internal(raw)
        assert product.sku == "SKU-001"
        assert product.title == "Awesome Widget"
        assert product.description == "A great widget"
        assert product.brand == "WidgetCo"

    def test_fallback_id_to_sku(self):
        connector = _make_connector(field_mapping={})
        raw = {"id": "42", "title": "Widget"}
        product = connector.map_to_internal(raw)
        assert product.sku == "42"

    def test_fallback_name_to_title(self):
        connector = _make_connector(field_mapping={})
        raw = {"sku": "SKU-002", "name": "My Product"}
        product = connector.map_to_internal(raw)
        assert product.title == "My Product"

    def test_category_path_from_string(self):
        connector = _make_connector(field_mapping={})
        raw = {"sku": "S", "title": "T", "category_path": "Electronics/Phones/Smartphones"}
        product = connector.map_to_internal(raw)
        assert product.category_path == ["Electronics", "Phones", "Smartphones"]

    def test_category_path_from_list(self):
        connector = _make_connector(field_mapping={})
        raw = {"sku": "S", "title": "T", "categories": ["A", "B"]}
        product = connector.map_to_internal(raw)
        assert product.category_path == ["A", "B"]

    def test_last_modified_parsing(self):
        connector = _make_connector(field_mapping={})
        raw = {"sku": "S", "title": "T", "last_modified": "2024-01-15T10:30:00"}
        product = connector.map_to_internal(raw)
        assert isinstance(product.last_modified, datetime)

    def test_updated_at_fallback(self):
        connector = _make_connector(field_mapping={})
        raw = {"sku": "S", "title": "T", "updated_at": "2024-01-15T10:30:00"}
        product = connector.map_to_internal(raw)
        assert isinstance(product.last_modified, datetime)

    def test_invalid_date_does_not_raise(self):
        connector = _make_connector(field_mapping={})
        raw = {"sku": "S", "title": "T", "last_modified": "not-a-date"}
        product = connector.map_to_internal(raw)
        assert product.last_modified is None

    def test_extra_fields_go_to_attributes(self):
        connector = _make_connector(field_mapping={})
        raw = {"sku": "S", "title": "T", "color": "red", "weight_kg": 1.2}
        product = connector.map_to_internal(raw)
        assert product.attributes["color"] == "red"
        assert product.attributes["weight_kg"] == 1.2


# ---------------------------------------------------------------------------
# get_product
# ---------------------------------------------------------------------------

class TestGetProduct:
    @pytest.mark.asyncio
    async def test_returns_product_on_200(self):
        connector = _make_connector()
        body = {"sku": "SKU-001", "title": "Widget", "status": "active"}
        with patch.object(connector, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_response(200, body)
            product = await connector.get_product("SKU-001")
        assert isinstance(product, ProductData)
        assert product.sku == "SKU-001"

    @pytest.mark.asyncio
    async def test_returns_none_on_404(self):
        connector = _make_connector()
        with patch.object(connector, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_response(404)
            product = await connector.get_product("MISSING")
        assert product is None

    @pytest.mark.asyncio
    async def test_returns_none_on_transport_error(self):
        connector = _make_connector()
        with patch.object(connector, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = httpx.RequestError("connection failed")
            product = await connector.get_product("SKU-001")
        assert product is None


# ---------------------------------------------------------------------------
# list_products
# ---------------------------------------------------------------------------

class TestListProducts:
    @pytest.mark.asyncio
    async def test_returns_list_from_items_key(self):
        connector = _make_connector()
        body = {"items": [{"sku": "A", "title": "A"}, {"sku": "B", "title": "B"}]}
        with patch.object(connector, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_response(200, body)
            products = await connector.list_products()
        assert len(products) == 2

    @pytest.mark.asyncio
    async def test_returns_list_from_array_response(self):
        connector = _make_connector()
        body = [{"sku": "A", "title": "A"}]
        with patch.object(connector, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_response(200, body)
            products = await connector.list_products()
        assert len(products) == 1

    @pytest.mark.asyncio
    async def test_returns_empty_on_transport_error(self):
        connector = _make_connector()
        with patch.object(connector, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = httpx.RequestError("fail")
            products = await connector.list_products()
        assert products == []

    @pytest.mark.asyncio
    async def test_passes_filters_as_params(self):
        connector = _make_connector()
        body = {"items": []}
        with patch.object(connector, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_response(200, body)
            await connector.list_products(category="Electronics", page=2)
        call_params = mock_req.call_args.kwargs["params"]
        assert call_params["category"] == "Electronics"
        assert call_params["page"] == 2


# ---------------------------------------------------------------------------
# search_products
# ---------------------------------------------------------------------------

class TestSearchProducts:
    @pytest.mark.asyncio
    async def test_search_returns_products(self):
        connector = _make_connector()
        body = [{"sku": "X", "title": "Xylophone"}]
        with patch.object(connector, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_response(200, body)
            results = await connector.search_products("Xylophone")
        assert len(results) == 1
        assert results[0].title == "Xylophone"

    @pytest.mark.asyncio
    async def test_search_empty_on_error(self):
        connector = _make_connector()
        with patch.object(connector, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = httpx.RequestError("fail")
            results = await connector.search_products("anything")
        assert results == []


# ---------------------------------------------------------------------------
# get_product_assets
# ---------------------------------------------------------------------------

class TestGetProductAssets:
    @pytest.mark.asyncio
    async def test_delegates_to_dam_connector(self):
        dam = AsyncMock()
        dam.get_assets_by_product = AsyncMock(
            return_value=[AssetData(id="a1", url="http://cdn/a.jpg", content_type="image/jpeg")]
        )
        connector = GenericRestPIMConnector(_make_config(), dam_connector=dam)
        assets = await connector.get_product_assets("SKU-001")
        assert len(assets) == 1
        dam.get_assets_by_product.assert_awaited_once_with("SKU-001")

    @pytest.mark.asyncio
    async def test_returns_assets_from_pim_when_no_dam(self):
        connector = _make_connector()
        body = [{"id": "img1", "url": "http://cdn/img.jpg", "content_type": "image/jpeg"}]
        with patch.object(connector, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_response(200, body)
            assets = await connector.get_product_assets("SKU-001")
        assert len(assets) == 1
        assert assets[0].id == "img1"

    @pytest.mark.asyncio
    async def test_returns_empty_on_404(self):
        connector = _make_connector()
        with patch.object(connector, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_response(404)
            assets = await connector.get_product_assets("SKU-001")
        assert assets == []

    @pytest.mark.asyncio
    async def test_returns_empty_on_error(self):
        connector = _make_connector()
        with patch.object(connector, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = httpx.RequestError("fail")
            assets = await connector.get_product_assets("SKU-001")
        assert assets == []


# ---------------------------------------------------------------------------
# get_categories
# ---------------------------------------------------------------------------

class TestGetCategories:
    @pytest.mark.asyncio
    async def test_returns_categories(self):
        connector = _make_connector()
        body = [{"id": "electronics", "name": "Electronics"}]
        with patch.object(connector, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_response(200, body)
            categories = await connector.get_categories()
        assert len(categories) == 1

    @pytest.mark.asyncio
    async def test_returns_empty_on_error(self):
        connector = _make_connector()
        with patch.object(connector, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = httpx.RequestError("fail")
            categories = await connector.get_categories()
        assert categories == []


# ---------------------------------------------------------------------------
# fetch_products
# ---------------------------------------------------------------------------

class TestFetchProducts:
    @pytest.mark.asyncio
    async def test_passes_custom_filters(self):
        connector = _make_connector()
        body = {"items": []}
        with patch.object(connector, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_response(200, body)
            await connector.fetch_products({"brand": "Nike", "status": "active"})
        call_params = mock_req.call_args.kwargs["params"]
        assert call_params["brand"] == "Nike"
        assert call_params["status"] == "active"

    @pytest.mark.asyncio
    async def test_returns_empty_on_error(self):
        connector = _make_connector()
        with patch.object(connector, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = httpx.RequestError("fail")
            result = await connector.fetch_products()
        assert result == []


# ---------------------------------------------------------------------------
# push_enrichment
# ---------------------------------------------------------------------------

class TestPushEnrichment:
    @pytest.mark.asyncio
    async def test_pushes_with_reverse_mapping(self):
        connector = _make_connector(field_mapping={"pim_name": "title"})
        product = ProductData(sku="SKU-001", title="Widget")
        body = {"sku": "SKU-001", "pim_name": "New Title"}
        with patch.object(connector, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_response(200, body)
            result = await connector.push_enrichment(product, {"title": "New Title"})
        call_json = mock_req.call_args.kwargs["json"]
        assert "pim_name" in call_json
        assert call_json["pim_name"] == "New Title"
        assert result["sku"] == "SKU-001"

    @pytest.mark.asyncio
    async def test_returns_error_dict_on_transport_error(self):
        connector = _make_connector()
        product = ProductData(sku="SKU-001", title="Widget")
        with patch.object(connector, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = httpx.RequestError("fail")
            result = await connector.push_enrichment(product, {"title": "x"})
        assert result["ok"] is False


# ---------------------------------------------------------------------------
# Retry logic
# ---------------------------------------------------------------------------

class TestRetryLogic:
    @pytest.mark.asyncio
    async def test_retries_on_429(self):
        connector = _make_connector(max_retries=2, retry_backoff_base=0.001)
        responses = [
            _mock_response(429),
            _mock_response(429),
            _mock_response(200, {"sku": "S", "title": "T"}),
        ]

        with patch.object(connector, "_bucket") as mock_bucket:
            mock_bucket.acquire = AsyncMock()
            with patch.object(connector, "_get_client", new_callable=AsyncMock) as mock_client:
                http_client = AsyncMock()
                http_client.request = AsyncMock(side_effect=lambda *a, **kw: responses.pop(0))
                mock_client.return_value = http_client
                # Reset responses list
                responses_inner = [
                    _mock_response(429),
                    _mock_response(429),
                    _mock_response(200, {"sku": "S", "title": "T"}),
                ]
                http_client.request.side_effect = lambda *a, **kw: responses_inner.pop(0)

                with patch("holiday_peak_lib.integrations.pim_generic_rest.asyncio.sleep", new_callable=AsyncMock):
                    response = await connector._request("GET", "/api/products")
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_raises_after_max_retries_on_transport_error(self):
        connector = _make_connector(max_retries=1, retry_backoff_base=0.001)
        with patch.object(connector, "_bucket") as mock_bucket:
            mock_bucket.acquire = AsyncMock()
            with patch.object(connector, "_get_client", new_callable=AsyncMock) as mock_client:
                http_client = AsyncMock()
                http_client.request = AsyncMock(side_effect=httpx.ConnectError("fail"))
                mock_client.return_value = http_client

                with patch("holiday_peak_lib.integrations.pim_generic_rest.asyncio.sleep", new_callable=AsyncMock):
                    with pytest.raises(httpx.RequestError):
                        await connector._request("GET", "/api/products")


# ---------------------------------------------------------------------------
# close / health
# ---------------------------------------------------------------------------

class TestLifecycle:
    @pytest.mark.asyncio
    async def test_close_is_idempotent_when_no_client(self):
        connector = _make_connector()
        await connector.close()  # should not raise

    @pytest.mark.asyncio
    async def test_health_ok(self):
        connector = _make_connector()
        with patch.object(connector, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_response(200, {"items": []})
            result = await connector.health()
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_health_not_ok_on_error(self):
        connector = _make_connector()
        with patch.object(connector, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = httpx.RequestError("fail")
            result = await connector.health()
        assert result["ok"] is False
