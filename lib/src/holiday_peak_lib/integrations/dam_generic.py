"""Generic REST-based DAM connector.

Implements :class:`DAMConnectorBase` for any REST-compatible Digital Asset
Management system.  Auth strategies supported: ``bearer``, ``api_key``, and
``oauth2`` (client-credentials).

Retry with exponential back-off is applied to all outbound HTTP calls via
:func:`holiday_peak_lib.utils.retry.async_retry`.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import urlencode, urljoin

import httpx
from pydantic import BaseModel, Field

from holiday_peak_lib.integrations.contracts import AssetData, DAMConnectorBase

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Asset role classification helpers
# ---------------------------------------------------------------------------

_ROLE_KEYWORDS: dict[str, list[str]] = {
    "primary": ["main", "primary", "hero", "front", "default"],
    "swatch": ["swatch", "colour", "color", "chip"],
    "lifestyle": ["lifestyle", "context", "scene", "model", "worn"],
    "gallery": ["gallery", "alt", "additional", "back", "side"],
}


def _classify_role(filename: str | None, tags: list[str], metadata: dict) -> str:
    """Derive an asset role from filename, tags, and metadata."""
    role_hint = metadata.get("role") or metadata.get("asset_role") or ""
    if role_hint:
        return str(role_hint).lower()

    candidates = " ".join(
        filter(None, [filename or "", " ".join(tags), metadata.get("description", "")])
    ).lower()

    for role, keywords in _ROLE_KEYWORDS.items():
        if any(kw in candidates for kw in keywords):
            return role
    return "gallery"


# ---------------------------------------------------------------------------
# Configuration model
# ---------------------------------------------------------------------------


class DAMConnectionConfig(BaseModel):
    """Runtime configuration for :class:`GenericDAMConnector`."""

    base_url: str
    auth_type: str = Field(
        description="Authentication strategy: 'bearer', 'api_key', or 'oauth2'."
    )
    auth_credentials: dict = Field(default_factory=dict)
    asset_endpoint: str = "/api/assets"
    cdn_base_url: str | None = None
    supported_roles: list[str] = Field(
        default_factory=lambda: ["primary", "gallery", "swatch", "lifestyle"]
    )
    timeout_seconds: float = 30.0
    max_retries: int = 3
    retry_backoff_seconds: float = 0.5


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------


class _OAuth2TokenCache:
    """Minimal client-credentials token cache."""

    def __init__(self) -> None:
        self._token: str | None = None
        self._expires_at: float = 0.0

    def is_valid(self) -> bool:
        import time

        return self._token is not None and time.monotonic() < self._expires_at

    def store(self, token: str, expires_in: int) -> None:
        import time

        self._token = token
        self._expires_at = time.monotonic() + max(0, expires_in - 30)

    @property
    def token(self) -> str | None:
        return self._token


async def _fetch_oauth2_token(credentials: dict, timeout: float) -> str:
    """Obtain an OAuth2 access token using the client-credentials flow."""
    token_url: str = credentials["token_url"]
    payload = {
        "grant_type": "client_credentials",
        "client_id": credentials["client_id"],
        "client_secret": credentials["client_secret"],
    }
    if "scope" in credentials:
        payload["scope"] = credentials["scope"]

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(token_url, data=payload)
        response.raise_for_status()
        data = response.json()
        return data["access_token"], int(data.get("expires_in", 3600))


# ---------------------------------------------------------------------------
# GenericDAMConnector
# ---------------------------------------------------------------------------


class GenericDAMConnector(DAMConnectorBase):
    """Generic REST DAM connector.

    Parameters
    ----------
    config:
        :class:`DAMConnectionConfig` instance describing connection details.
    http_client:
        Optional pre-built :class:`httpx.AsyncClient`.  When *None* a new
        client is created on first use and closed via :meth:`close`.
    """

    def __init__(
        self,
        config: DAMConnectionConfig,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._config = config
        self._client = http_client
        self._owns_client = http_client is None
        self._oauth_cache = _OAuth2TokenCache()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._config.timeout_seconds)
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client if it was created internally."""
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def health(self) -> dict:
        """Return a simple health status dict."""
        try:
            client = await self._get_client()
            headers = await self._auth_headers()
            url = urljoin(self._config.base_url, self._config.asset_endpoint)
            response = await client.get(url, headers=headers, params={"limit": 1})
            return {"ok": response.status_code < 500}
        except Exception as exc:  # pragma: no cover
            logger.warning("DAM health check failed: %s", exc)
            return {"ok": False}

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    async def _auth_headers(self) -> dict[str, str]:
        auth_type = self._config.auth_type.lower()
        creds = self._config.auth_credentials

        if auth_type == "bearer":
            token = creds.get("token", "")
            return {"Authorization": f"Bearer {token}"}

        if auth_type == "api_key":
            header_name = creds.get("header", "X-Api-Key")
            return {header_name: creds.get("key", "")}

        if auth_type == "oauth2":
            if not self._oauth_cache.is_valid():
                token, expires_in = await _fetch_oauth2_token(
                    creds, self._config.timeout_seconds
                )
                self._oauth_cache.store(token, expires_in)
            return {"Authorization": f"Bearer {self._oauth_cache.token}"}

        raise ValueError(f"Unsupported auth_type: {self._config.auth_type!r}")

    # ------------------------------------------------------------------
    # Retry wrapper
    # ------------------------------------------------------------------

    async def _get_with_retry(
        self, url: str, *, params: dict | None = None
    ) -> httpx.Response:
        client = await self._get_client()
        headers = await self._auth_headers()
        backoff = self._config.retry_backoff_seconds
        last_exc: Exception | None = None
        for attempt in range(max(1, self._config.max_retries)):
            try:
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                return response
            except (httpx.HTTPStatusError, httpx.TransportError) as exc:
                last_exc = exc
                if attempt < self._config.max_retries - 1:
                    await asyncio.sleep(backoff * (2**attempt))
        raise last_exc  # type: ignore[misc]

    # ------------------------------------------------------------------
    # DAMConnectorBase implementation
    # ------------------------------------------------------------------

    async def get_asset(self, asset_id: str) -> AssetData | None:
        """Fetch a single asset by its identifier."""
        url = urljoin(
            self._config.base_url,
            f"{self._config.asset_endpoint}/{asset_id}",
        )
        try:
            response = await self._get_with_retry(url)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise
        return self.map_to_internal(response.json())

    async def get_assets_by_product(self, sku: str) -> list[AssetData]:
        """Fetch all assets associated with a product SKU."""
        url = urljoin(self._config.base_url, self._config.asset_endpoint)
        response = await self._get_with_retry(url, params={"sku": sku})
        raw_list = response.json()
        if isinstance(raw_list, dict):
            raw_list = raw_list.get("items") or raw_list.get("assets") or []
        return [self.map_to_internal(item) for item in raw_list]

    async def search_assets(
        self,
        query: str,
        *,
        tags: list[str] | None = None,
        content_type: str | None = None,
        limit: int = 50,
    ) -> list[AssetData]:
        """Search assets by query string with optional tag/type filters."""
        params: dict[str, Any] = {"q": query, "limit": limit}
        if tags:
            params["tags"] = ",".join(tags)
        if content_type:
            params["content_type"] = content_type

        url = urljoin(self._config.base_url, f"{self._config.asset_endpoint}/search")
        response = await self._get_with_retry(url, params=params)
        raw_list = response.json()
        if isinstance(raw_list, dict):
            raw_list = raw_list.get("items") or raw_list.get("results") or []
        return [self.map_to_internal(item) for item in raw_list]

    async def get_transformed_url(
        self,
        asset_id: str,
        *,
        width: int | None = None,
        height: int | None = None,
        output_format: str | None = None,
        quality: int | None = None,
    ) -> str:
        """Resolve a CDN/transform URL for an asset with optional resize params."""
        base = self._config.cdn_base_url or self._config.base_url
        path = f"/cdn/{asset_id}"
        query_params: dict[str, Any] = {}
        if width is not None:
            query_params["w"] = width
        if height is not None:
            query_params["h"] = height
        if output_format is not None:
            query_params["fmt"] = output_format
        if quality is not None:
            query_params["q"] = quality

        url = urljoin(base, path)
        if query_params:
            url = f"{url}?{urlencode(query_params)}"
        return url

    # ------------------------------------------------------------------
    # Convenience / extended methods
    # ------------------------------------------------------------------

    async def fetch_assets(self, entity_id: str) -> list[AssetData]:
        """Alias for :meth:`get_assets_by_product` (entity-centric name)."""
        return await self.get_assets_by_product(entity_id)

    async def fetch_asset(self, asset_id: str) -> AssetData | None:
        """Alias for :meth:`get_asset`."""
        return await self.get_asset(asset_id)

    async def resolve_urls(self, assets: list[AssetData]) -> list[AssetData]:
        """Resolve CDN URLs for a list of assets in-place.

        Each asset's ``url`` is replaced with the resolved CDN/signed URL
        when a :attr:`DAMConnectionConfig.cdn_base_url` is configured.
        """
        if not self._config.cdn_base_url:
            return assets
        resolved = []
        for asset in assets:
            cdn_url = await self.get_transformed_url(asset.id)
            resolved.append(asset.model_copy(update={"url": cdn_url}))
        return resolved

    def map_to_internal(self, raw: dict) -> AssetData:
        """Transform a raw DAM API response dict into an :class:`AssetData` model.

        The mapper is intentionally permissive: unknown keys are silently
        ignored, and only ``id`` / ``url`` are treated as mandatory (falling
        back to empty strings when absent).
        """
        asset_id = str(raw.get("id") or raw.get("asset_id") or "")
        url = str(raw.get("url") or raw.get("download_url") or raw.get("src") or "")
        content_type = str(
            raw.get("content_type") or raw.get("mime_type") or raw.get("type") or ""
        )
        filename = raw.get("filename") or raw.get("name") or raw.get("file_name")
        size_bytes: int | None = raw.get("size") or raw.get("size_bytes") or raw.get("file_size")
        width: int | None = raw.get("width")
        height: int | None = raw.get("height")
        alt_text: str | None = raw.get("alt_text") or raw.get("alt") or raw.get("title")

        tags: list[str] = raw.get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]

        metadata: dict = raw.get("metadata") or {}

        # Apply CDN base URL if the returned URL is a relative path
        if url and not url.startswith(("http://", "https://")) and self._config.cdn_base_url:
            url = urljoin(self._config.cdn_base_url, url)

        # Classify asset role and store in metadata when not already present
        if "role" not in metadata:
            role = _classify_role(filename, tags, metadata)
            if role in self._config.supported_roles:
                metadata = {**metadata, "role": role}

        return AssetData(
            id=asset_id,
            url=url,
            content_type=content_type,
            filename=filename,
            size_bytes=size_bytes,
            width=width,
            height=height,
            alt_text=alt_text,
            tags=tags,
            metadata=metadata,
        )
