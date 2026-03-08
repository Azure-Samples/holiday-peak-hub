"""Akeneo PIM connector.

Integrates with the Akeneo PIM REST API v1.

Authentication: OAuth 2.0 password grant
                (``AKENEO_CLIENT_ID``, ``AKENEO_CLIENT_SECRET``,
                 ``AKENEO_USERNAME``, ``AKENEO_PASSWORD``).
Base URL:       ``AKENEO_BASE_URL`` env var.

References:
    https://api.akeneo.com/api-reference.html
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import httpx
from holiday_peak_lib.adapters.base import AdapterError
from holiday_peak_lib.connectors.pim.akeneo.auth import AkeneoAuth
from holiday_peak_lib.connectors.pim.akeneo.mappings import map_asset, map_product
from holiday_peak_lib.integrations.contracts import AssetData, PIMConnectorBase, ProductData

_DEFAULT_BASE_URL = "https://demo.akeneo.com"


class AkeneoConnector(PIMConnectorBase):
    """PIM connector for Akeneo REST API v1.

    Parameters
    ----------
    base_url:
        Akeneo instance URL.  Falls back to ``AKENEO_BASE_URL`` env var.
    client_id / client_secret / username / password:
        OAuth 2.0 credentials.  Fall back to ``AKENEO_*`` env vars.
    locale:
        Default locale for attribute values (default ``en_US``).
    transport:
        Optional ``httpx`` transport for testing.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        username: str | None = None,
        password: str | None = None,
        locale: str = "en_US",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        resolved_url = (base_url or os.environ.get("AKENEO_BASE_URL", _DEFAULT_BASE_URL)).rstrip(
            "/"
        )
        self._base_url = resolved_url
        self._auth = AkeneoAuth(
            base_url=resolved_url,
            client_id=client_id,
            client_secret=client_secret,
            username=username,
            password=password,
            transport=transport,
        )
        self._locale = locale
        self._transport = transport

    async def _client(self) -> tuple[httpx.AsyncClient, dict[str, str]]:
        """Return a configured HTTP client and auth headers."""
        headers = await self._auth.get_headers()
        client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=headers,
            transport=self._transport,
            timeout=30.0,
        )
        return client, headers

    async def get_product(self, sku: str) -> ProductData | None:
        """Fetch a single product by SKU (Akeneo ``identifier``)."""
        client, _ = await self._client()
        async with client:
            response = await client.get(f"/api/rest/v1/products/{sku}")
            if response.status_code == 404:
                return None
            if response.status_code != 200:
                raise AdapterError(f"Akeneo get_product failed: HTTP {response.status_code}")
            return map_product(response.json(), locale=self._locale)

    async def list_products(
        self,
        *,
        category: str | None = None,
        modified_since: datetime | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> list[ProductData]:
        """List products with optional category and date filters."""
        params: dict[str, str | int] = {
            "page": page,
            "limit": page_size,
            "with_count": "false",
        }
        search_filters: dict = {}
        if category:
            search_filters["categories"] = [{"operator": "IN", "value": [category]}]
        if modified_since:
            search_filters["updated"] = [{"operator": ">", "value": modified_since.isoformat()}]
        if search_filters:
            params["search"] = json.dumps(search_filters)

        client, _ = await self._client()
        async with client:
            response = await client.get("/api/rest/v1/products", params=params)
            if response.status_code != 200:
                raise AdapterError(f"Akeneo list_products failed: HTTP {response.status_code}")
            body = response.json()
            items = body.get("_embedded", {}).get("items", [])
            return [map_product(p, locale=self._locale) for p in items]

    async def search_products(self, query: str, limit: int = 50) -> list[ProductData]:
        """Search products by keyword using Akeneo search filters."""
        search = json.dumps(
            {
                "label_or_identifier": [
                    {"operator": "CONTAINS", "value": query, "locale": self._locale}
                ]
            }
        )
        params: dict[str, str | int] = {"search": search, "limit": limit}
        client, _ = await self._client()
        async with client:
            response = await client.get("/api/rest/v1/products", params=params)
            if response.status_code != 200:
                raise AdapterError(f"Akeneo search_products failed: HTTP {response.status_code}")
            body = response.json()
            items = body.get("_embedded", {}).get("items", [])
            return [map_product(p, locale=self._locale) for p in items]

    async def get_product_assets(self, sku: str) -> list[AssetData]:
        """Get assets linked to a product via the asset manager."""
        client, _ = await self._client()
        async with client:
            response = await client.get(f"/api/rest/v1/products/{sku}/assets")
            if response.status_code == 404:
                return []
            if response.status_code != 200:
                raise AdapterError(f"Akeneo get_product_assets failed: HTTP {response.status_code}")
            body = response.json()
            items = body.get("_embedded", {}).get("items", [])
            return [map_asset(a) for a in items]

    async def get_categories(self) -> list[dict]:
        """Return the Akeneo category tree."""
        client, _ = await self._client()
        async with client:
            response = await client.get("/api/rest/v1/categories")
            if response.status_code != 200:
                raise AdapterError(f"Akeneo get_categories failed: HTTP {response.status_code}")
            body = response.json()
            return body.get("_embedded", {}).get("items", [])
