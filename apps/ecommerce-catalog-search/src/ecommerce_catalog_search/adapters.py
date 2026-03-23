"""Adapters for the ecommerce catalog search service (ACP-aware)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

import httpx
from holiday_peak_lib.adapters.base import BaseAdapter
from holiday_peak_lib.adapters.inventory_adapter import InventoryConnector
from holiday_peak_lib.adapters.mock_adapters import (
    MockInventoryAdapter,
    MockProductAdapter,
)
from holiday_peak_lib.adapters.product_adapter import ProductConnector

if TYPE_CHECKING:
    from holiday_peak_lib.schemas.product import CatalogProduct

try:
    from holiday_peak_lib.adapters.acp_mapper import AcpCatalogMapper
except ImportError:

    class AcpCatalogMapper:
        """Compatibility ACP mapper fallback for older holiday_peak_lib images."""

        def to_acp_product(
            self,
            product: "CatalogProduct",
            *,
            availability: str,
            currency: str = "usd",
        ) -> dict[str, Any]:
            price = float(product.price or 0.0)
            return {
                "item_id": product.sku,
                "title": product.name,
                "description": product.description or "",
                "url": f"https://example.com/products/{product.sku}",
                "image_url": product.image_url or "https://example.com/images/placeholder.png",
                "brand": product.brand or "",
                "price": f"{price:.2f} {currency}",
                "availability": availability,
                "protocol_version": "1.0",
                "extended_attributes": dict(product.attributes or {}),
            }


SEARCH_MODE_KEYWORD = "keyword"
SEARCH_MODE_INTELLIGENT = "intelligent"
SUPPORTED_SEARCH_MODES = {SEARCH_MODE_KEYWORD, SEARCH_MODE_INTELLIGENT}
ENRICHED_RESULT_FIELDS = (
    "use_cases",
    "complementary_products",
    "substitute_products",
    "enriched_description",
)


@dataclass
class CatalogAdapters:
    """Container for catalog search adapters."""

    products: ProductConnector
    inventory: InventoryConnector
    mapping: AcpCatalogMapper


class CRUDCatalogProductAdapter(BaseAdapter):
    """CRUD-backed product adapter for catalog connector queries."""

    def __init__(
        self,
        crud_service_url: str,
        *,
        timeout: float = 5.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        super().__init__(timeout=timeout)
        self._base_url = crud_service_url.rstrip("/")
        self._transport = transport

    async def _connect_impl(self, **kwargs: Any) -> None:
        return None

    async def _fetch_impl(self, query: dict[str, Any]) -> list[dict[str, Any]]:
        entity = str(query.get("entity") or "").strip().lower()
        sku = str(query.get("sku") or "").strip()
        if not sku:
            return []

        try:
            if entity == "product":
                product = await self._fetch_product_by_sku(sku)
                return [product] if product else []
            if entity == "related":
                limit = max(1, int(query.get("limit") or 5))
                return await self._fetch_related_by_sku(sku=sku, limit=limit)
        except (httpx.HTTPError, ValueError, TypeError):
            return []

        return []

    async def _upsert_impl(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        return None

    async def _delete_impl(self, identifier: str) -> bool:
        return False

    async def _fetch_product_by_sku(self, sku: str) -> dict[str, Any] | None:
        try:
            payload = await self._request_json("GET", f"/api/products/{sku}")
            if isinstance(payload, dict):
                return self._normalize_product_record(payload, sku_hint=sku)
        except httpx.HTTPError:
            pass

        payload = await self._request_json(
            "GET",
            "/api/products",
            params={"search": sku, "limit": 20},
        )
        if not isinstance(payload, list):
            return None

        for candidate in payload:
            candidate_sku = str(candidate.get("sku") or candidate.get("id") or "")
            if candidate_sku == sku:
                return self._normalize_product_record(candidate, sku_hint=sku)

        for candidate in payload:
            if isinstance(candidate, dict):
                return self._normalize_product_record(candidate, sku_hint=sku)
        return None

    async def _fetch_related_by_sku(self, *, sku: str, limit: int) -> list[dict[str, Any]]:
        anchor = await self._fetch_product_by_sku(sku)
        if anchor is None:
            return []

        category = str(anchor.get("category") or "").strip()
        if not category:
            return []

        payload = await self._request_json(
            "GET",
            "/api/products",
            params={"category": category, "limit": max(limit + 1, 2)},
        )
        if not isinstance(payload, list):
            return []

        related: list[dict[str, Any]] = []
        for item in payload:
            normalized = self._normalize_product_record(item)
            if normalized["sku"] == sku:
                continue
            related.append(normalized)
            if len(related) >= limit:
                break
        return related

    async def _request_json(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        url = f"{self._base_url}{endpoint}"
        async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
            response = await client.request(method, url, params=params)
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, list):
                return [item for item in payload if isinstance(item, dict)]
            if isinstance(payload, dict):
                return payload
            return {}

    @staticmethod
    def _normalize_product_record(
        record: dict[str, Any],
        *,
        sku_hint: str | None = None,
    ) -> dict[str, Any]:
        sku = str(record.get("sku") or record.get("id") or sku_hint or "")
        return {
            "sku": sku,
            "name": str(record.get("name") or sku or "unknown-product"),
            "description": record.get("description") or "",
            "category": record.get("category") or record.get("category_id"),
            "price": record.get("price"),
            "currency": record.get("currency") or "USD",
            "image_url": record.get("image_url"),
        }


def normalize_search_mode(mode: str | None) -> str:
    """Normalize incoming search mode while keeping backward-compatible defaults."""
    normalized = (mode or SEARCH_MODE_KEYWORD).strip().lower()
    if normalized in SUPPORTED_SEARCH_MODES:
        return normalized
    return SEARCH_MODE_KEYWORD


def merge_enriched_fields(
    base_payload: dict[str, object],
    enriched_fields: dict[str, object] | None,
) -> dict[str, object]:
    """Merge optional enrichment fields into ACP payload without breaking shape."""
    if not enriched_fields:
        return base_payload

    payload = dict(base_payload)
    extended = payload.get("extended_attributes")
    extended_attributes = dict(extended) if isinstance(extended, dict) else {}

    for field in ENRICHED_RESULT_FIELDS:
        if field in enriched_fields and enriched_fields[field] is not None:
            value = enriched_fields[field]
            payload[field] = value
            extended_attributes[field] = value

    payload["extended_attributes"] = extended_attributes
    return payload


def build_catalog_adapters(
    *,
    product_connector: Optional[ProductConnector] = None,
    inventory_connector: Optional[InventoryConnector] = None,
) -> CatalogAdapters:
    """Create adapters for catalog search workflows."""
    products = product_connector or _build_product_connector()
    inventory = inventory_connector or InventoryConnector(adapter=MockInventoryAdapter())
    mapping = AcpCatalogMapper()
    return CatalogAdapters(products=products, inventory=inventory, mapping=mapping)


def _build_product_connector() -> ProductConnector:
    crud_service_url = (os.getenv("CRUD_SERVICE_URL") or "").strip()
    if crud_service_url:
        return ProductConnector(adapter=CRUDCatalogProductAdapter(crud_service_url))
    return ProductConnector(adapter=MockProductAdapter())
