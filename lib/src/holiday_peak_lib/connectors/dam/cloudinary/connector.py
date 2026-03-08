"""Cloudinary DAM connector.

Integrates with the Cloudinary Admin and Upload REST APIs.

Authentication: API Key + API Secret (HMAC/SHA-1 signed requests).
Cloud name:     ``CLOUDINARY_CLOUD_NAME`` env var.
API key:        ``CLOUDINARY_API_KEY`` env var.
API secret:     ``CLOUDINARY_API_SECRET`` env var.

References:
    https://cloudinary.com/documentation/admin_api
    https://cloudinary.com/documentation/image_transformations
"""

from __future__ import annotations

import os

import httpx
from holiday_peak_lib.adapters.base import AdapterError
from holiday_peak_lib.connectors.dam.cloudinary.auth import CloudinaryAuth
from holiday_peak_lib.connectors.dam.cloudinary.mappings import map_resource
from holiday_peak_lib.integrations.contracts import AssetData, DAMConnectorBase

_ADMIN_API_BASE = "https://api.cloudinary.com/v1_1"
_RES_API_BASE = "https://res.cloudinary.com"
_MAX_RESULTS = 500


class CloudinaryConnector(DAMConnectorBase):
    """DAM connector for the Cloudinary Admin and Delivery APIs.

    Parameters
    ----------
    cloud_name / api_key / api_secret:
        Cloudinary credentials.  Fall back to ``CLOUDINARY_*`` env vars.
    transport:
        Optional ``httpx`` transport for testing.
    """

    def __init__(
        self,
        *,
        cloud_name: str | None = None,
        api_key: str | None = None,
        api_secret: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._auth = CloudinaryAuth(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
        )
        self._transport = transport
        self._admin_base = (os.environ.get("CLOUDINARY_ADMIN_BASE_URL", _ADMIN_API_BASE)).rstrip(
            "/"
        )

    def _admin_client(self) -> httpx.AsyncClient:
        """Return an HTTP client targeting the Cloudinary Admin API."""
        return httpx.AsyncClient(
            base_url=f"{self._admin_base}/{self._auth.cloud_name}",
            auth=(self._auth.api_key, self._auth.api_secret),
            transport=self._transport,
            timeout=30.0,
        )

    async def get_asset(self, asset_id: str) -> AssetData | None:
        """Fetch an asset by its Cloudinary ``public_id``.

        Returns ``None`` when the asset does not exist.
        """
        async with self._admin_client() as client:
            response = await client.get(f"/resources/image/upload/{asset_id}")
            if response.status_code == 404:
                return None
            if response.status_code != 200:
                raise AdapterError(f"Cloudinary get_asset failed: HTTP {response.status_code}")
            return map_resource(response.json())

    async def get_assets_by_product(self, sku: str) -> list[AssetData]:
        """Get assets tagged with the product SKU."""
        return await self.search_assets(sku, tags=[sku])

    async def search_assets(
        self,
        query: str,
        *,
        tags: list[str] | None = None,
        content_type: str | None = None,
        limit: int = 50,
    ) -> list[AssetData]:
        """Search assets using Cloudinary's Search API.

        Parameters
        ----------
        query:
            Full-text expression applied to asset metadata and public IDs.
        tags:
            Restrict results to assets carrying all of these tags.
        content_type:
            Restrict by ``resource_type`` (``image``, ``video``, ``raw``).
        limit:
            Maximum number of results (capped at ``_MAX_RESULTS``).
        """
        expressions: list[str] = []
        if query:
            expressions.append(f'"{query}"')
        for tag in tags or []:
            expressions.append(f"tags={tag}")
        if content_type:
            expressions.append(f"resource_type={content_type}")

        payload: dict = {
            "expression": " AND ".join(expressions) if expressions else "",
            "max_results": min(limit, _MAX_RESULTS),
        }

        async with self._admin_client() as client:
            response = await client.post("/resources/search", json=payload)
            if response.status_code != 200:
                raise AdapterError(f"Cloudinary search_assets failed: HTTP {response.status_code}")
            body = response.json()
            return [map_resource(r) for r in body.get("resources", [])]

    async def get_transformed_url(
        self,
        asset_id: str,
        *,
        width: int | None = None,
        height: int | None = None,
        output_format: str | None = None,
        quality: int | None = None,
    ) -> str:
        """Build a Cloudinary transformation URL for the given asset.

        Transformations are encoded in the delivery URL path.  No API call is
        required.

        Parameters
        ----------
        asset_id:
            Cloudinary ``public_id``.
        width / height:
            Desired output dimensions.
        output_format:
            Target format (e.g. ``webp``, ``jpg``).
        quality:
            JPEG/WebP quality 1-100.

        Returns
        -------
        str
            A Cloudinary CDN URL with the requested transformations applied.
        """
        transforms: list[str] = []
        if width:
            transforms.append(f"w_{width}")
        if height:
            transforms.append(f"h_{height}")
        if quality:
            transforms.append(f"q_{quality}")
        if transforms:
            transforms.append("c_limit")
        transform_str = ",".join(transforms)
        fmt = f".{output_format}" if output_format else ""
        cloud = self._auth.cloud_name
        if transform_str:
            return f"{_RES_API_BASE}/{cloud}/image/upload/{transform_str}/{asset_id}{fmt}"
        return f"{_RES_API_BASE}/{cloud}/image/upload/{asset_id}{fmt}"
