"""Unit tests for GenericDAMConnector."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from holiday_peak_lib.integrations.contracts import AssetData
from holiday_peak_lib.integrations.dam_generic import (
    DAMConnectionConfig,
    GenericDAMConnector,
    _classify_role,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def bearer_config() -> DAMConnectionConfig:
    return DAMConnectionConfig(
        base_url="https://dam.example.com",
        auth_type="bearer",
        auth_credentials={"token": "test-token"},
        cdn_base_url="https://cdn.example.com",
        max_retries=1,
    )


@pytest.fixture
def api_key_config() -> DAMConnectionConfig:
    return DAMConnectionConfig(
        base_url="https://dam.example.com",
        auth_type="api_key",
        auth_credentials={"header": "X-Api-Key", "key": "secret-key"},
        max_retries=1,
    )


@pytest.fixture
def oauth2_config() -> DAMConnectionConfig:
    return DAMConnectionConfig(
        base_url="https://dam.example.com",
        auth_type="oauth2",
        auth_credentials={
            "token_url": "https://auth.example.com/token",
            "client_id": "client-id",
            "client_secret": "client-secret",
            "scope": "dam.read",
        },
        max_retries=1,
    )


_DUMMY_REQUEST = httpx.Request("GET", "https://dam.example.com/api/assets")


def _make_response(body: dict | list, status_code: int = 200) -> httpx.Response:
    """Build a fake httpx.Response with a dummy request attached."""
    content = json.dumps(body).encode()
    return httpx.Response(status_code=status_code, content=content, request=_DUMMY_REQUEST)


def _mock_client(response: httpx.Response) -> AsyncMock:
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=response)
    return client


# ---------------------------------------------------------------------------
# _classify_role helper
# ---------------------------------------------------------------------------


class TestClassifyRole:
    def test_metadata_role_wins(self):
        assert _classify_role("anything.jpg", [], {"role": "swatch"}) == "swatch"

    def test_filename_primary(self):
        assert _classify_role("product_main.jpg", [], {}) == "primary"

    def test_filename_swatch(self):
        assert _classify_role("colour_chip.png", [], {}) == "swatch"

    def test_tag_lifestyle(self):
        assert _classify_role(None, ["lifestyle", "outdoor"], {}) == "lifestyle"

    def test_default_gallery(self):
        assert _classify_role("unknown.jpg", [], {}) == "gallery"


# ---------------------------------------------------------------------------
# DAMConnectionConfig
# ---------------------------------------------------------------------------


class TestDAMConnectionConfig:
    def test_defaults(self):
        cfg = DAMConnectionConfig(
            base_url="https://dam.example.com",
            auth_type="bearer",
            auth_credentials={},
        )
        assert cfg.asset_endpoint == "/api/assets"
        assert cfg.cdn_base_url is None
        assert cfg.supported_roles == ["primary", "gallery", "swatch", "lifestyle"]
        assert cfg.max_retries == 3

    def test_custom_values(self):
        cfg = DAMConnectionConfig(
            base_url="https://dam.example.com",
            auth_type="api_key",
            auth_credentials={"key": "k"},
            cdn_base_url="https://cdn.example.com",
            supported_roles=["primary"],
        )
        assert cfg.cdn_base_url == "https://cdn.example.com"
        assert cfg.supported_roles == ["primary"]


# ---------------------------------------------------------------------------
# Auth headers
# ---------------------------------------------------------------------------


class TestAuthHeaders:
    @pytest.mark.asyncio
    async def test_bearer(self, bearer_config):
        connector = GenericDAMConnector(bearer_config, http_client=AsyncMock())
        headers = await connector._auth_headers()
        assert headers == {"Authorization": "Bearer test-token"}

    @pytest.mark.asyncio
    async def test_api_key(self, api_key_config):
        connector = GenericDAMConnector(api_key_config, http_client=AsyncMock())
        headers = await connector._auth_headers()
        assert headers == {"X-Api-Key": "secret-key"}

    @pytest.mark.asyncio
    async def test_oauth2(self, oauth2_config):
        connector = GenericDAMConnector(oauth2_config, http_client=AsyncMock())
        with patch(
            "holiday_peak_lib.integrations.dam_generic._fetch_oauth2_token",
            new=AsyncMock(return_value=("oauth-token", 3600)),
        ):
            headers = await connector._auth_headers()
        assert headers == {"Authorization": "Bearer oauth-token"}

    @pytest.mark.asyncio
    async def test_unsupported_auth(self, bearer_config):
        cfg = bearer_config.model_copy(update={"auth_type": "unknown"})
        connector = GenericDAMConnector(cfg, http_client=AsyncMock())
        with pytest.raises(ValueError, match="Unsupported auth_type"):
            await connector._auth_headers()


# ---------------------------------------------------------------------------
# map_to_internal
# ---------------------------------------------------------------------------


class TestMapToInternal:
    @pytest.fixture
    def connector(self, bearer_config):
        return GenericDAMConnector(bearer_config)

    def test_basic_mapping(self, connector):
        raw = {
            "id": "a1",
            "url": "https://dam.example.com/assets/a1.jpg",
            "content_type": "image/jpeg",
            "filename": "main_product.jpg",
            "width": 800,
            "height": 600,
            "size": 102400,
            "alt_text": "Product hero image",
            "tags": ["hero", "product"],
            "metadata": {},
        }
        asset = connector.map_to_internal(raw)
        assert asset.id == "a1"
        assert asset.content_type == "image/jpeg"
        assert asset.width == 800
        assert asset.height == 600
        assert asset.size_bytes == 102400
        assert asset.alt_text == "Product hero image"
        assert "primary" in asset.metadata.get("role", "")

    def test_fallback_fields(self, connector):
        raw = {"asset_id": "b2", "download_url": "/files/b2.jpg", "mime_type": "image/png"}
        asset = connector.map_to_internal(raw)
        assert asset.id == "b2"
        assert asset.content_type == "image/png"
        # Relative URL with cdn_base_url should be resolved
        assert asset.url.startswith("https://cdn.example.com")

    def test_tags_as_string(self, connector):
        raw = {"id": "c3", "url": "https://cdn.example.com/c3.jpg", "tags": "swatch,color"}
        asset = connector.map_to_internal(raw)
        assert "swatch" in asset.tags

    def test_role_classification_gallery(self, connector):
        raw = {"id": "d4", "url": "https://cdn.example.com/d4.jpg", "tags": []}
        asset = connector.map_to_internal(raw)
        assert asset.metadata.get("role") == "gallery"


# ---------------------------------------------------------------------------
# get_asset
# ---------------------------------------------------------------------------


class TestGetAsset:
    @pytest.mark.asyncio
    async def test_returns_asset(self, bearer_config):
        raw = {"id": "x1", "url": "https://dam.example.com/x1.jpg", "content_type": "image/jpeg"}
        client = _mock_client(_make_response(raw))
        connector = GenericDAMConnector(bearer_config, http_client=client)
        asset = await connector.get_asset("x1")
        assert isinstance(asset, AssetData)
        assert asset.id == "x1"

    @pytest.mark.asyncio
    async def test_returns_none_on_404(self, bearer_config):
        response_404 = httpx.Response(
            404,
            request=httpx.Request("GET", "https://dam.example.com/api/assets/missing"),
        )
        error = httpx.HTTPStatusError(
            "not found", request=response_404.request, response=response_404
        )
        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(side_effect=error)
        connector = GenericDAMConnector(bearer_config, http_client=client)
        result = await connector.get_asset("missing")
        assert result is None


# ---------------------------------------------------------------------------
# get_assets_by_product
# ---------------------------------------------------------------------------


class TestGetAssetsByProduct:
    @pytest.mark.asyncio
    async def test_list_response(self, bearer_config):
        items = [
            {"id": "a1", "url": "https://dam.example.com/a1.jpg", "content_type": "image/jpeg"},
            {"id": "a2", "url": "https://dam.example.com/a2.jpg", "content_type": "image/png"},
        ]
        client = _mock_client(_make_response(items))
        connector = GenericDAMConnector(bearer_config, http_client=client)
        assets = await connector.get_assets_by_product("SKU-001")
        assert len(assets) == 2
        assert all(isinstance(a, AssetData) for a in assets)

    @pytest.mark.asyncio
    async def test_paginated_dict_response(self, bearer_config):
        payload = {
            "items": [
                {"id": "b1", "url": "https://dam.example.com/b1.jpg", "content_type": "image/jpeg"}
            ]
        }
        client = _mock_client(_make_response(payload))
        connector = GenericDAMConnector(bearer_config, http_client=client)
        assets = await connector.get_assets_by_product("SKU-002")
        assert len(assets) == 1

    @pytest.mark.asyncio
    async def test_fetch_assets_alias(self, bearer_config):
        client = _mock_client(_make_response([]))
        connector = GenericDAMConnector(bearer_config, http_client=client)
        result = await connector.fetch_assets("SKU-003")
        assert result == []


# ---------------------------------------------------------------------------
# search_assets
# ---------------------------------------------------------------------------


class TestSearchAssets:
    @pytest.mark.asyncio
    async def test_search_returns_results(self, bearer_config):
        results_payload = {
            "results": [
                {"id": "s1", "url": "https://dam.example.com/s1.jpg", "content_type": "image/jpeg"}
            ]
        }
        client = _mock_client(_make_response(results_payload))
        connector = GenericDAMConnector(bearer_config, http_client=client)
        assets = await connector.search_assets(
            "jacket", tags=["outdoor"], content_type="image/jpeg"
        )
        assert len(assets) == 1

    @pytest.mark.asyncio
    async def test_search_empty_results(self, bearer_config):
        client = _mock_client(_make_response([]))
        connector = GenericDAMConnector(bearer_config, http_client=client)
        assets = await connector.search_assets("nonexistent")
        assert assets == []


# ---------------------------------------------------------------------------
# get_transformed_url
# ---------------------------------------------------------------------------


class TestGetTransformedUrl:
    @pytest.mark.asyncio
    async def test_full_params(self, bearer_config):
        connector = GenericDAMConnector(bearer_config, http_client=AsyncMock())
        url = await connector.get_transformed_url(
            "img1", width=400, height=300, output_format="webp", quality=80
        )
        assert "https://cdn.example.com/cdn/img1" in url
        assert "w=400" in url
        assert "h=300" in url
        assert "fmt=webp" in url
        assert "q=80" in url

    @pytest.mark.asyncio
    async def test_no_params(self, bearer_config):
        connector = GenericDAMConnector(bearer_config, http_client=AsyncMock())
        url = await connector.get_transformed_url("img2")
        assert url == "https://cdn.example.com/cdn/img2"

    @pytest.mark.asyncio
    async def test_fallback_to_base_url(self, api_key_config):
        connector = GenericDAMConnector(api_key_config, http_client=AsyncMock())
        url = await connector.get_transformed_url("img3")
        assert url.startswith("https://dam.example.com/cdn/img3")


# ---------------------------------------------------------------------------
# resolve_urls
# ---------------------------------------------------------------------------


class TestResolveUrls:
    @pytest.mark.asyncio
    async def test_resolves_with_cdn(self, bearer_config):
        assets = [
            AssetData(id="r1", url="https://dam.example.com/r1.jpg", content_type="image/jpeg"),
            AssetData(id="r2", url="https://dam.example.com/r2.jpg", content_type="image/jpeg"),
        ]
        connector = GenericDAMConnector(bearer_config, http_client=AsyncMock())
        resolved = await connector.resolve_urls(assets)
        for asset in resolved:
            assert asset.url.startswith("https://cdn.example.com/cdn/")

    @pytest.mark.asyncio
    async def test_no_cdn_unchanged(self, api_key_config):
        assets = [
            AssetData(id="r3", url="https://dam.example.com/r3.jpg", content_type="image/jpeg"),
        ]
        connector = GenericDAMConnector(api_key_config, http_client=AsyncMock())
        resolved = await connector.resolve_urls(assets)
        assert resolved[0].url == "https://dam.example.com/r3.jpg"


# ---------------------------------------------------------------------------
# Retry logic
# ---------------------------------------------------------------------------


class TestRetryLogic:
    @pytest.mark.asyncio
    async def test_retries_on_transport_error(self, bearer_config):
        cfg = bearer_config.model_copy(update={"max_retries": 3, "retry_backoff_seconds": 0.0})
        client = AsyncMock(spec=httpx.AsyncClient)
        call_count = 0

        async def flaky_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.TransportError("network blip")
            req = httpx.Request("GET", args[0] if args else "https://dam.example.com/")
            return httpx.Response(
                200,
                content=json.dumps(
                    {
                        "id": "ok",
                        "url": "https://dam.example.com/ok.jpg",
                        "content_type": "image/jpeg",
                    }
                ).encode(),
                request=req,
            )

        client.get = flaky_get
        connector = GenericDAMConnector(cfg, http_client=client)
        asset = await connector.get_asset("ok")
        assert asset is not None
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self, bearer_config):
        cfg = bearer_config.model_copy(update={"max_retries": 2, "retry_backoff_seconds": 0.0})
        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(side_effect=httpx.TransportError("always fails"))
        connector = GenericDAMConnector(cfg, http_client=client)
        with pytest.raises(httpx.TransportError):
            await connector.get_asset("fail")


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:
    @pytest.mark.asyncio
    async def test_close_owned_client(self, bearer_config):
        connector = GenericDAMConnector(bearer_config)
        _ = await connector._get_client()
        await connector.close()
        assert connector._client is None

    @pytest.mark.asyncio
    async def test_close_external_client_not_closed(self, bearer_config):
        ext_client = AsyncMock(spec=httpx.AsyncClient)
        connector = GenericDAMConnector(bearer_config, http_client=ext_client)
        await connector.close()
        ext_client.aclose.assert_not_called()
