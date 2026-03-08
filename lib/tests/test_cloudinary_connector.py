"""Unit tests for the Cloudinary DAM connector."""

from __future__ import annotations

import json

import httpx
import pytest
from holiday_peak_lib.adapters.base import AdapterError
from holiday_peak_lib.connectors.dam.cloudinary.auth import CloudinaryAuth
from holiday_peak_lib.connectors.dam.cloudinary.connector import CloudinaryConnector
from holiday_peak_lib.connectors.dam.cloudinary.mappings import map_resource
from holiday_peak_lib.integrations.contracts import AssetData

# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

_CREDS = {
    "cloud_name": "demo",
    "api_key": "123456",
    "api_secret": "abcdef",
}

SAMPLE_RESOURCE: dict = {
    "public_id": "products/shirt-front",
    "format": "jpg",
    "resource_type": "image",
    "url": "http://res.cloudinary.com/demo/image/upload/products/shirt-front.jpg",
    "secure_url": "https://res.cloudinary.com/demo/image/upload/products/shirt-front.jpg",
    "bytes": 120453,
    "width": 1200,
    "height": 800,
    "tags": ["product", "lifestyle"],
    "context": {"custom": {"alt": "Product lifestyle shot", "caption": "Summer collection"}},
    "created_at": "2024-01-15T10:00:00Z",
}


def _mock_transport(handler):
    """Wrap a request handler into an httpx.MockTransport."""
    return httpx.MockTransport(handler)


def _make_connector(transport: httpx.MockTransport) -> CloudinaryConnector:
    return CloudinaryConnector(**_CREDS, transport=transport)


# ---------------------------------------------------------------------------
# TestMappings
# ---------------------------------------------------------------------------


class TestMappings:
    """Tests for dam.cloudinary.mappings.map_resource."""

    def test_map_resource_full(self):
        asset = map_resource(SAMPLE_RESOURCE)
        assert isinstance(asset, AssetData)
        assert asset.id == "products/shirt-front"
        assert asset.url == SAMPLE_RESOURCE["secure_url"]
        assert asset.content_type == "image/jpeg"
        assert asset.filename == "shirt-front.jpg"
        assert asset.size_bytes == 120453
        assert asset.width == 1200
        assert asset.height == 800
        assert asset.alt_text == "Product lifestyle shot"
        assert asset.tags == ["product", "lifestyle"]
        assert "created_at" in asset.metadata

    def test_map_resource_prefers_secure_url(self):
        raw = {**SAMPLE_RESOURCE, "secure_url": "https://secure.example.com/img.jpg"}
        assert map_resource(raw).url == "https://secure.example.com/img.jpg"

    def test_map_resource_falls_back_to_url(self):
        raw = {k: v for k, v in SAMPLE_RESOURCE.items() if k != "secure_url"}
        assert map_resource(raw).url == SAMPLE_RESOURCE["url"]

    def test_map_resource_no_context(self):
        raw = {**SAMPLE_RESOURCE}
        raw.pop("context")
        asset = map_resource(raw)
        assert asset.alt_text is None

    def test_map_resource_empty_tags(self):
        raw = {**SAMPLE_RESOURCE, "tags": []}
        assert map_resource(raw).tags == []

    def test_map_resource_png_format(self):
        raw = {**SAMPLE_RESOURCE, "format": "png"}
        assert map_resource(raw).content_type == "image/png"

    def test_map_resource_video_format(self):
        raw = {**SAMPLE_RESOURCE, "resource_type": "video", "format": "mp4"}
        assert map_resource(raw).content_type == "video/mp4"

    def test_map_resource_raw_unknown_format(self):
        raw = {**SAMPLE_RESOURCE, "resource_type": "raw", "format": "xyz"}
        assert map_resource(raw).content_type == "application/xyz"

    def test_map_resource_minimal(self):
        raw = {"public_id": "x", "format": "jpg", "resource_type": "image"}
        asset = map_resource(raw)
        assert asset.id == "x"
        assert asset.url == ""
        assert asset.size_bytes is None


# ---------------------------------------------------------------------------
# TestAuth
# ---------------------------------------------------------------------------


class TestAuth:
    """Tests for CloudinaryAuth."""

    def test_auth_from_params(self):
        auth = CloudinaryAuth(**_CREDS)
        assert auth.cloud_name == "demo"
        assert auth.api_key == "123456"
        assert auth.api_secret == "abcdef"

    def test_auth_missing_credentials(self, monkeypatch):
        monkeypatch.delenv("CLOUDINARY_CLOUD_NAME", raising=False)
        monkeypatch.delenv("CLOUDINARY_API_KEY", raising=False)
        monkeypatch.delenv("CLOUDINARY_API_SECRET", raising=False)
        with pytest.raises(ValueError, match="Cloudinary credentials are required"):
            CloudinaryAuth()

    def test_sign_params(self):
        auth = CloudinaryAuth(**_CREDS)
        signed = auth.sign_params({"public_id": "sample"})
        assert "signature" in signed
        assert "timestamp" in signed
        assert signed["api_key"] == "123456"


# ---------------------------------------------------------------------------
# TestConnector
# ---------------------------------------------------------------------------


class TestGetAsset:
    """Tests for CloudinaryConnector.get_asset."""

    @pytest.mark.asyncio
    async def test_get_asset_found(self):
        def handler(request: httpx.Request) -> httpx.Response:
            assert "/resources/image/upload/products/shirt-front" in str(request.url)
            return httpx.Response(200, json=SAMPLE_RESOURCE)

        connector = _make_connector(_mock_transport(handler))
        asset = await connector.get_asset("products/shirt-front")
        assert asset is not None
        assert asset.id == "products/shirt-front"
        assert asset.content_type == "image/jpeg"

    @pytest.mark.asyncio
    async def test_get_asset_not_found(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, json={"error": {"message": "Resource not found"}})

        connector = _make_connector(_mock_transport(handler))
        result = await connector.get_asset("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_asset_server_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"error": {"message": "Internal error"}})

        connector = _make_connector(_mock_transport(handler))
        with pytest.raises(AdapterError, match="HTTP 500"):
            await connector.get_asset("fail")


class TestSearchAssets:
    """Tests for CloudinaryConnector.search_assets."""

    @pytest.mark.asyncio
    async def test_search_assets_success(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"resources": [SAMPLE_RESOURCE]})

        connector = _make_connector(_mock_transport(handler))
        results = await connector.search_assets("product")
        assert len(results) == 1
        assert results[0].id == "products/shirt-front"

    @pytest.mark.asyncio
    async def test_search_assets_empty(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"resources": []})

        connector = _make_connector(_mock_transport(handler))
        results = await connector.search_assets("nothing")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_assets_with_tags_and_type(self):
        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            assert "tags=product" in body["expression"]
            assert "resource_type=video" in body["expression"]
            return httpx.Response(200, json={"resources": []})

        connector = _make_connector(_mock_transport(handler))
        await connector.search_assets("q", tags=["product"], content_type="video")

    @pytest.mark.asyncio
    async def test_search_assets_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, json={})

        connector = _make_connector(_mock_transport(handler))
        with pytest.raises(AdapterError, match="HTTP 503"):
            await connector.search_assets("q")


class TestGetAssetsByProduct:
    """Tests for CloudinaryConnector.get_assets_by_product."""

    @pytest.mark.asyncio
    async def test_delegates_to_search(self):
        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            assert "tags=SKU-1" in body["expression"]
            return httpx.Response(200, json={"resources": [SAMPLE_RESOURCE]})

        connector = _make_connector(_mock_transport(handler))
        results = await connector.get_assets_by_product("SKU-1")
        assert len(results) == 1


class TestGetTransformedUrl:
    """Tests for CloudinaryConnector.get_transformed_url."""

    @pytest.mark.asyncio
    async def test_url_with_transforms(self):
        connector = _make_connector(_mock_transport(lambda r: httpx.Response(200)))
        url = await connector.get_transformed_url("sample/img", width=300, height=200, quality=80)
        assert "w_300" in url
        assert "h_200" in url
        assert "q_80" in url
        assert "c_limit" in url
        assert "/demo/" in url

    @pytest.mark.asyncio
    async def test_url_with_format(self):
        connector = _make_connector(_mock_transport(lambda r: httpx.Response(200)))
        url = await connector.get_transformed_url("sample/img", output_format="webp")
        assert url.endswith(".webp")

    @pytest.mark.asyncio
    async def test_url_no_transforms(self):
        connector = _make_connector(_mock_transport(lambda r: httpx.Response(200)))
        url = await connector.get_transformed_url("sample/img")
        assert "/image/upload/sample/img" in url
