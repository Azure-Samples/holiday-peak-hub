"""Generic REST PIM connector.

Implements :class:`PIMConnectorBase` for any PIM system that exposes a REST API
(Akeneo, Salsify, InRiver, etc.).

Design principles:
- Async HTTP via ``httpx.AsyncClient``
- Configurable field mapping (PIM field names → canonical fields)
- Token-bucket rate limiting
- Retry with exponential back-off for 429 / 5xx responses
- Auth credentials are never hard-coded; they must be supplied via Key Vault
  secrets or environment variables at startup
"""

from __future__ import annotations

import asyncio
import base64
import logging
import time
from datetime import datetime
from typing import Any

import httpx
from pydantic import BaseModel, Field

from holiday_peak_lib.integrations.contracts import (
    AssetData,
    DAMConnectorBase,
    PIMConnectorBase,
    ProductData,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration model
# ---------------------------------------------------------------------------


class PIMConnectionConfig(BaseModel):
    """Configuration for a generic REST PIM connector.

    ``auth_credentials`` must be loaded from Key Vault at startup — never
    stored in source code or plain-text configuration files.
    """

    base_url: str
    auth_type: str = "bearer"  # 'bearer' | 'basic' | 'api_key' | 'oauth2'
    auth_credentials: dict[str, Any] = Field(default_factory=dict)
    product_endpoint: str = "/api/products"
    asset_endpoint: str = "/api/assets"
    category_endpoint: str = "/api/categories"
    search_endpoint: str = "/api/products/search"
    field_mapping: dict[str, str] = Field(default_factory=dict)
    page_size: int = 100
    rate_limit_rps: int = 10
    # Retry settings
    max_retries: int = 3
    retry_backoff_base: float = 0.5  # seconds; actual delay = base * 2^attempt
    timeout_seconds: float = 30.0


# ---------------------------------------------------------------------------
# Token-bucket rate limiter
# ---------------------------------------------------------------------------


class _TokenBucket:
    """Simple token-bucket rate limiter for async code."""

    def __init__(self, rate: int) -> None:
        self._rate = rate  # tokens per second
        self._tokens: float = float(rate)
        self._last: float = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last
            self._tokens = min(float(self._rate), self._tokens + elapsed * self._rate)
            self._last = now
            if self._tokens < 1:
                wait = (1 - self._tokens) / self._rate
                await asyncio.sleep(wait)
                self._tokens = 0.0
            else:
                self._tokens -= 1.0


# ---------------------------------------------------------------------------
# Generic REST PIM connector
# ---------------------------------------------------------------------------


class GenericRestPIMConnector(PIMConnectorBase):
    """Concrete PIM connector that works with any REST-based PIM system.

    Parameters
    ----------
    config:
        Connection configuration including base URL, auth, and field mappings.
    dam_connector:
        Optional :class:`DAMConnectorBase` used to resolve product assets.
        When *None*, :meth:`get_product_assets` returns an empty list.
    """

    def __init__(
        self,
        config: PIMConnectionConfig,
        *,
        dam_connector: DAMConnectorBase | None = None,
    ) -> None:
        self._cfg = config
        self._dam = dam_connector
        self._bucket = _TokenBucket(config.rate_limit_rps)
        self._client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._cfg.base_url,
                headers=self._build_auth_headers(),
                timeout=self._cfg.timeout_seconds,
            )
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------
    # Auth helpers
    # ------------------------------------------------------------------

    def _build_auth_headers(self) -> dict[str, str]:
        creds = self._cfg.auth_credentials
        auth_type = self._cfg.auth_type.lower()

        if auth_type == "bearer":
            token = creds.get("token", "")
            return {"Authorization": f"Bearer {token}"}

        if auth_type == "basic":
            username = creds.get("username", "")
            password = creds.get("password", "")
            encoded = base64.b64encode(f"{username}:{password}".encode()).decode()
            return {"Authorization": f"Basic {encoded}"}

        if auth_type == "api_key":
            header_name = creds.get("header", "X-Api-Key")
            api_key = creds.get("key", "")
            return {header_name: api_key}

        if auth_type == "oauth2":
            # Caller is responsible for supplying a pre-fetched access token.
            token = creds.get("access_token", "")
            return {"Authorization": f"Bearer {token}"}

        logger.warning("Unknown auth_type '%s'; sending no auth header.", self._cfg.auth_type)
        return {}

    # ------------------------------------------------------------------
    # HTTP helpers with retry
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: Any = None,
    ) -> httpx.Response:
        """Execute an HTTP request with rate limiting and retry logic."""
        await self._bucket.acquire()
        client = await self._get_client()
        last_exc: Exception | None = None

        for attempt in range(self._cfg.max_retries + 1):
            try:
                response = await client.request(method, path, params=params, json=json)
                if response.status_code in (429, 500, 502, 503, 504):
                    if attempt < self._cfg.max_retries:
                        wait = self._cfg.retry_backoff_base * (2 ** attempt)
                        logger.warning(
                            "PIM responded %s; retrying in %.1fs (attempt %d/%d)",
                            response.status_code,
                            wait,
                            attempt + 1,
                            self._cfg.max_retries,
                        )
                        await asyncio.sleep(wait)
                        continue
                return response
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                last_exc = exc
                if attempt < self._cfg.max_retries:
                    wait = self._cfg.retry_backoff_base * (2 ** attempt)
                    logger.warning(
                        "Transport error contacting PIM: %s; retrying in %.1fs",
                        exc,
                        wait,
                    )
                    await asyncio.sleep(wait)

        raise httpx.RequestError(
            f"PIM request failed after {self._cfg.max_retries} retries"
        ) from last_exc

    # ------------------------------------------------------------------
    # Field-mapping helper
    # ------------------------------------------------------------------

    def _apply_field_mapping(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Return a copy of *raw* with PIM field names replaced by canonical names."""
        if not self._cfg.field_mapping:
            return raw
        mapped: dict[str, Any] = {}
        for key, value in raw.items():
            mapped[self._cfg.field_mapping.get(key, key)] = value
        return mapped

    # ------------------------------------------------------------------
    # PIMConnectorBase interface
    # ------------------------------------------------------------------

    async def get_product(self, sku: str) -> ProductData | None:
        """Fetch a single product by SKU."""
        path = f"{self._cfg.product_endpoint}/{sku}"
        try:
            response = await self._request("GET", path)
        except httpx.RequestError:
            logger.exception("Failed to fetch product '%s' from PIM.", sku)
            return None
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return self.map_to_internal(response.json())

    async def list_products(
        self,
        *,
        category: str | None = None,
        modified_since: datetime | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> list[ProductData]:
        """List products with optional filters, handling pagination transparently."""
        params: dict[str, Any] = {
            "page": page,
            "page_size": min(page_size, self._cfg.page_size),
        }
        if category:
            params["category"] = category
        if modified_since:
            params["modified_since"] = modified_since.isoformat()

        try:
            response = await self._request("GET", self._cfg.product_endpoint, params=params)
        except httpx.RequestError:
            logger.exception("Failed to list products from PIM.")
            return []
        response.raise_for_status()

        payload = response.json()
        items = payload if isinstance(payload, list) else payload.get("items", [])
        return [self.map_to_internal(raw) for raw in items]

    async def search_products(self, query: str, limit: int = 50) -> list[ProductData]:
        """Search products by keyword."""
        params: dict[str, Any] = {"q": query, "limit": limit}
        try:
            response = await self._request("GET", self._cfg.search_endpoint, params=params)
        except httpx.RequestError:
            logger.exception("Failed to search products in PIM.")
            return []
        response.raise_for_status()

        payload = response.json()
        items = payload if isinstance(payload, list) else payload.get("items", [])
        return [self.map_to_internal(raw) for raw in items]

    async def get_product_assets(self, sku: str) -> list[AssetData]:
        """Get assets linked to a product.

        Delegates to the DAM connector if one is configured, otherwise queries
        the PIM's own asset endpoint for the product.
        """
        if self._dam is not None:
            return await self._dam.get_assets_by_product(sku)

        path = f"{self._cfg.product_endpoint}/{sku}/assets"
        try:
            response = await self._request("GET", path)
        except httpx.RequestError:
            logger.exception("Failed to fetch assets for product '%s'.", sku)
            return []
        if response.status_code == 404:
            return []
        response.raise_for_status()

        payload = response.json()
        items = payload if isinstance(payload, list) else payload.get("items", [])
        return [self._raw_to_asset(a) for a in items]

    async def get_categories(self) -> list[dict]:
        """Get category taxonomy."""
        try:
            response = await self._request("GET", self._cfg.category_endpoint)
        except httpx.RequestError:
            logger.exception("Failed to fetch categories from PIM.")
            return []
        response.raise_for_status()

        payload = response.json()
        return payload if isinstance(payload, list) else payload.get("items", [])

    # ------------------------------------------------------------------
    # Additional PIM-specific operations (not in base class)
    # ------------------------------------------------------------------

    async def fetch_products(self, filters: dict | None = None) -> list[ProductData]:
        """Fetch products using arbitrary PIM-specific filter parameters.

        Parameters
        ----------
        filters:
            Dict of query parameters forwarded verbatim to the PIM API.
        """
        params: dict[str, Any] = filters or {}
        if "page_size" not in params:
            params["page_size"] = self._cfg.page_size

        try:
            response = await self._request("GET", self._cfg.product_endpoint, params=params)
        except httpx.RequestError:
            logger.exception("Failed to fetch products with filters %s.", filters)
            return []
        response.raise_for_status()

        payload = response.json()
        items = payload if isinstance(payload, list) else payload.get("items", [])
        return [self.map_to_internal(raw) for raw in items]

    async def fetch_product(self, external_id: str) -> ProductData | None:
        """Fetch a single product by the PIM's native external ID.

        Unlike :meth:`get_product`, this method uses the external ID as-is and
        does not assume it equals the canonical SKU.
        """
        return await self.get_product(external_id)

    async def push_enrichment(
        self,
        product: ProductData,
        fields: dict[str, Any],
    ) -> dict[str, Any]:
        """Push enriched fields back to the PIM system.

        This performs a PATCH (partial update) against the product endpoint.
        Only *fields* are sent — the full product record is **not** replaced.

        Parameters
        ----------
        product:
            The product whose data should be updated in the PIM.
        fields:
            Mapping of canonical field names → new values to push.

        Returns
        -------
        dict
            The PIM response body (typically the updated product record).
        """
        # Reverse-map canonical → PIM field names before sending
        reverse_mapping = {v: k for k, v in self._cfg.field_mapping.items()}
        pim_payload: dict[str, Any] = {}
        for canonical_key, value in fields.items():
            pim_key = reverse_mapping.get(canonical_key, canonical_key)
            pim_payload[pim_key] = value

        path = f"{self._cfg.product_endpoint}/{product.sku}"
        try:
            response = await self._request("PATCH", path, json=pim_payload)
        except httpx.RequestError:
            logger.exception("Failed to push enrichment for product '%s'.", product.sku)
            return {"ok": False, "error": "request_failed"}
        response.raise_for_status()
        return response.json()

    def map_to_internal(self, raw: dict[str, Any]) -> ProductData:
        """Transform a raw PIM API response dict to a canonical :class:`ProductData`.

        The field mapping defined in :attr:`PIMConnectionConfig.field_mapping`
        is applied first, then the canonical fields are extracted.

        Parameters
        ----------
        raw:
            A single product record as returned by the PIM REST API.
        """
        mapped = self._apply_field_mapping(raw)

        # Normalise last_modified
        last_modified: datetime | None = None
        raw_date = mapped.get("last_modified") or mapped.get("updated_at")
        if isinstance(raw_date, str):
            try:
                last_modified = datetime.fromisoformat(raw_date)
            except ValueError:
                logger.warning("Could not parse date '%s' for product.", raw_date)

        # Category path: accept both list and string
        category_raw = mapped.get("category_path") or mapped.get("categories") or []
        if isinstance(category_raw, str):
            category_path = [c.strip() for c in category_raw.split("/") if c.strip()]
        else:
            category_path = list(category_raw)

        return ProductData(
            sku=str(mapped.get("sku") or mapped.get("id") or ""),
            title=str(mapped.get("title") or mapped.get("name") or ""),
            description=mapped.get("description"),
            short_description=mapped.get("short_description"),
            brand=mapped.get("brand"),
            category_path=category_path,
            attributes={
                k: v
                for k, v in mapped.items()
                if k
                not in {
                    "sku",
                    "id",
                    "title",
                    "name",
                    "description",
                    "short_description",
                    "brand",
                    "category_path",
                    "categories",
                    "images",
                    "variants",
                    "status",
                    "source_system",
                    "last_modified",
                    "updated_at",
                }
            },
            images=list(mapped.get("images") or []),
            variants=list(mapped.get("variants") or []),
            status=str(mapped.get("status") or "active"),
            source_system=mapped.get("source_system"),
            last_modified=last_modified,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _raw_to_asset(raw: dict[str, Any]) -> AssetData:
        return AssetData(
            id=str(raw.get("id") or raw.get("asset_id") or ""),
            url=str(raw.get("url") or raw.get("download_url") or ""),
            content_type=str(raw.get("content_type") or raw.get("mime_type") or ""),
            filename=raw.get("filename") or raw.get("name"),
            size_bytes=raw.get("size_bytes") or raw.get("file_size"),
            width=raw.get("width"),
            height=raw.get("height"),
            alt_text=raw.get("alt_text"),
            tags=list(raw.get("tags") or []),
            metadata={
                k: v
                for k, v in raw.items()
                if k
                not in {
                    "id",
                    "asset_id",
                    "url",
                    "download_url",
                    "content_type",
                    "mime_type",
                    "filename",
                    "name",
                    "size_bytes",
                    "file_size",
                    "width",
                    "height",
                    "alt_text",
                    "tags",
                }
            },
        )

    async def health(self) -> dict[str, Any]:
        """Return a basic health status for the connector."""
        try:
            response = await self._request("GET", self._cfg.product_endpoint, params={"page": 1, "page_size": 1})
            return {"ok": response.is_success, "status_code": response.status_code}
        except httpx.HTTPError as exc:
            return {"ok": False, "error": str(exc)}
