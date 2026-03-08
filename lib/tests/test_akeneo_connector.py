"""Unit tests for the Akeneo PIM connector."""

from __future__ import annotations

import json

import httpx
import pytest
from holiday_peak_lib.adapters.base import AdapterError
from holiday_peak_lib.connectors.pim.akeneo.auth import AkeneoAuth
from holiday_peak_lib.connectors.pim.akeneo.connector import AkeneoConnector
from holiday_peak_lib.connectors.pim.akeneo.mappings import (
    _extract_value,
    map_asset,
    map_product,
)
from holiday_peak_lib.integrations.contracts import AssetData, ProductData

# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

_TOKEN_RESPONSE = {"access_token": "tok-123", "expires_in": 3600}

SAMPLE_PRODUCT: dict = {
    "identifier": "SKU-001",
    "family": "clothing",
    "categories": ["master", "shirts", "casual"],
    "enabled": True,
    "values": {
        "name": [{"locale": "en_US", "scope": None, "data": "Casual Shirt"}],
        "description": [{"locale": "en_US", "scope": None, "data": "A comfortable casual shirt."}],
        "short_description": [{"locale": "en_US", "scope": None, "data": "Casual shirt"}],
        "brand": [{"locale": None, "scope": None, "data": "Acme"}],
        "image": [{"locale": None, "scope": None, "data": "https://cdn.example.com/shirt.jpg"}],
        "color": [{"locale": None, "scope": None, "data": "blue"}],
    },
    "associations": {"UPSELL": {"products": ["SKU-002", "SKU-003"]}},
    "updated": "2024-01-15T10:00:00+00:00",
}

SAMPLE_ASSET: dict = {
    "code": "asset-001",
    "values": {
        "media": [
            {
                "locale": None,
                "scope": None,
                "data": {
                    "filePath": "a/b/asset.jpg",
                    "originalFilename": "product.jpg",
                },
            }
        ],
        "description": [{"locale": "en_US", "scope": None, "data": "Product image"}],
    },
}


def _oauth_then(api_handler):
    """Return a transport handler that responds to /api/oauth/v1/token first,
    then delegates to *api_handler* for all other requests."""

    def handler(request: httpx.Request) -> httpx.Response:
        if "/api/oauth/v1/token" in str(request.url):
            return httpx.Response(200, json=_TOKEN_RESPONSE)
        return api_handler(request)

    return handler


def _make_connector(transport: httpx.MockTransport) -> AkeneoConnector:
    return AkeneoConnector(
        base_url="https://akeneo.test",
        client_id="cid",
        client_secret="csec",
        username="user",
        password="pass",
        locale="en_US",
        transport=transport,
    )


# ---------------------------------------------------------------------------
# TestMappings
# ---------------------------------------------------------------------------


class TestExtractValue:
    """Tests for _extract_value helper."""

    def test_exact_locale_match(self):
        vals = {"name": [{"locale": "en_US", "scope": None, "data": "Shirt"}]}
        assert _extract_value(vals, "name", "en_US") == "Shirt"

    def test_locale_agnostic_fallback(self):
        vals = {"brand": [{"locale": None, "scope": None, "data": "Acme"}]}
        assert _extract_value(vals, "brand", "en_US") == "Acme"

    def test_missing_attribute(self):
        assert _extract_value({}, "missing", "en_US") is None

    def test_empty_entries(self):
        assert _extract_value({"x": []}, "x", "en_US") is None

    def test_first_entry_fallback(self):
        vals = {"name": [{"locale": "fr_FR", "scope": None, "data": "Chemise"}]}
        assert _extract_value(vals, "name", "en_US") == "Chemise"


class TestMapProduct:
    """Tests for map_product."""

    def test_full_mapping(self):
        product = map_product(SAMPLE_PRODUCT, locale="en_US")
        assert isinstance(product, ProductData)
        assert product.sku == "SKU-001"
        assert product.title == "Casual Shirt"
        assert product.description == "A comfortable casual shirt."
        assert product.short_description == "Casual shirt"
        assert product.brand == "Acme"
        assert product.category_path == ["master", "shirts", "casual"]
        assert "https://cdn.example.com/shirt.jpg" in product.images
        assert "SKU-002" in product.variants
        assert "SKU-003" in product.variants
        assert product.status == "active"
        assert product.source_system == "akeneo"
        assert product.last_modified is not None
        # color should appear in attributes (not explicitly mapped)
        assert product.attributes.get("color") == "blue"

    def test_disabled_product(self):
        raw = {**SAMPLE_PRODUCT, "enabled": False}
        assert map_product(raw).status == "inactive"

    def test_no_associations(self):
        raw = {**SAMPLE_PRODUCT}
        raw.pop("associations")
        assert map_product(raw).variants == []

    def test_no_values(self):
        raw = {"identifier": "SKU-X", "enabled": True}
        product = map_product(raw)
        assert product.sku == "SKU-X"
        assert product.title == ""

    def test_bad_updated_date(self):
        raw = {**SAMPLE_PRODUCT, "updated": "not-a-date"}
        assert map_product(raw).last_modified is None


class TestMapAsset:
    """Tests for map_asset."""

    def test_full_mapping(self):
        asset = map_asset(SAMPLE_ASSET)
        assert isinstance(asset, AssetData)
        assert asset.id == "asset-001"
        assert asset.url == "a/b/asset.jpg"
        assert asset.filename == "product.jpg"
        assert asset.content_type == "image/jpeg"
        assert asset.alt_text == "Product image"

    def test_no_media(self):
        raw = {"code": "empty", "values": {}}
        asset = map_asset(raw)
        assert asset.id == "empty"
        assert asset.url == ""
        assert asset.filename is None

    def test_string_media_data(self):
        raw = {
            "code": "str-media",
            "values": {"media": [{"locale": None, "scope": None, "data": "path/to/file.png"}]},
        }
        asset = map_asset(raw)
        assert asset.url == "path/to/file.png"
        assert asset.filename == "file.png"
        assert asset.content_type == "image/png"


# ---------------------------------------------------------------------------
# TestAuth
# ---------------------------------------------------------------------------


class TestAuth:
    """Tests for AkeneoAuth token handling."""

    @pytest.mark.asyncio
    async def test_get_headers_acquires_token(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_TOKEN_RESPONSE)

        auth = AkeneoAuth(
            base_url="https://akeneo.test",
            client_id="cid",
            client_secret="csec",
            username="user",
            password="pass",
            transport=httpx.MockTransport(handler),
        )
        headers = await auth.get_headers()
        assert headers["Authorization"] == "Bearer tok-123"

    @pytest.mark.asyncio
    async def test_token_cached(self):
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(200, json=_TOKEN_RESPONSE)

        auth = AkeneoAuth(
            base_url="https://akeneo.test",
            client_id="cid",
            client_secret="csec",
            username="user",
            password="pass",
            transport=httpx.MockTransport(handler),
        )
        await auth.get_headers()
        await auth.get_headers()
        assert call_count == 1  # second call uses cache

    @pytest.mark.asyncio
    async def test_token_refresh_on_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"error": "invalid_grant"})

        auth = AkeneoAuth(
            base_url="https://akeneo.test",
            client_id="cid",
            client_secret="csec",
            username="user",
            password="pass",
            transport=httpx.MockTransport(handler),
        )
        with pytest.raises(httpx.HTTPStatusError):
            await auth.get_headers()


# ---------------------------------------------------------------------------
# TestConnector
# ---------------------------------------------------------------------------


class TestGetProduct:
    """Tests for AkeneoConnector.get_product."""

    @pytest.mark.asyncio
    async def test_found(self):
        def api(request: httpx.Request) -> httpx.Response:
            assert "/api/rest/v1/products/SKU-001" in str(request.url)
            return httpx.Response(200, json=SAMPLE_PRODUCT)

        connector = _make_connector(httpx.MockTransport(_oauth_then(api)))
        product = await connector.get_product("SKU-001")
        assert product is not None
        assert product.sku == "SKU-001"
        assert product.title == "Casual Shirt"

    @pytest.mark.asyncio
    async def test_not_found(self):
        def api(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, json={})

        connector = _make_connector(httpx.MockTransport(_oauth_then(api)))
        assert await connector.get_product("missing") is None

    @pytest.mark.asyncio
    async def test_server_error(self):
        def api(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={})

        connector = _make_connector(httpx.MockTransport(_oauth_then(api)))
        with pytest.raises(AdapterError, match="HTTP 500"):
            await connector.get_product("fail")


class TestListProducts:
    """Tests for AkeneoConnector.list_products."""

    @pytest.mark.asyncio
    async def test_success(self):
        def api(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={"_embedded": {"items": [SAMPLE_PRODUCT]}},
            )

        connector = _make_connector(httpx.MockTransport(_oauth_then(api)))
        products = await connector.list_products()
        assert len(products) == 1
        assert products[0].sku == "SKU-001"

    @pytest.mark.asyncio
    async def test_with_category_filter(self):
        def api(request: httpx.Request) -> httpx.Response:
            assert "search" in str(request.url)
            return httpx.Response(200, json={"_embedded": {"items": []}})

        connector = _make_connector(httpx.MockTransport(_oauth_then(api)))
        await connector.list_products(category="shirts")

    @pytest.mark.asyncio
    async def test_error(self):
        def api(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, json={})

        connector = _make_connector(httpx.MockTransport(_oauth_then(api)))
        with pytest.raises(AdapterError, match="HTTP 503"):
            await connector.list_products()


class TestSearchProducts:
    """Tests for AkeneoConnector.search_products."""

    @pytest.mark.asyncio
    async def test_success(self):
        def api(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={"_embedded": {"items": [SAMPLE_PRODUCT]}},
            )

        connector = _make_connector(httpx.MockTransport(_oauth_then(api)))
        results = await connector.search_products("shirt")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_error(self):
        def api(request: httpx.Request) -> httpx.Response:
            return httpx.Response(400, json={})

        connector = _make_connector(httpx.MockTransport(_oauth_then(api)))
        with pytest.raises(AdapterError):
            await connector.search_products("q")


class TestGetProductAssets:
    """Tests for AkeneoConnector.get_product_assets."""

    @pytest.mark.asyncio
    async def test_found(self):
        def api(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={"_embedded": {"items": [SAMPLE_ASSET]}},
            )

        connector = _make_connector(httpx.MockTransport(_oauth_then(api)))
        assets = await connector.get_product_assets("SKU-001")
        assert len(assets) == 1
        assert assets[0].id == "asset-001"

    @pytest.mark.asyncio
    async def test_404_returns_empty(self):
        def api(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, json={})

        connector = _make_connector(httpx.MockTransport(_oauth_then(api)))
        assert await connector.get_product_assets("gone") == []

    @pytest.mark.asyncio
    async def test_error(self):
        def api(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={})

        connector = _make_connector(httpx.MockTransport(_oauth_then(api)))
        with pytest.raises(AdapterError):
            await connector.get_product_assets("fail")


class TestGetCategories:
    """Tests for AkeneoConnector.get_categories."""

    @pytest.mark.asyncio
    async def test_success(self):
        cats = [{"code": "master"}, {"code": "shirts"}]

        def api(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"_embedded": {"items": cats}})

        connector = _make_connector(httpx.MockTransport(_oauth_then(api)))
        result = await connector.get_categories()
        assert len(result) == 2
        assert result[0]["code"] == "master"

    @pytest.mark.asyncio
    async def test_error(self):
        def api(request: httpx.Request) -> httpx.Response:
            return httpx.Response(502, json={})

        connector = _make_connector(httpx.MockTransport(_oauth_then(api)))
        with pytest.raises(AdapterError):
            await connector.get_categories()
