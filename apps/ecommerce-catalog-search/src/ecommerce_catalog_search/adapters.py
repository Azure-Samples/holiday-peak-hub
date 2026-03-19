"""Adapters for the ecommerce catalog search service (ACP-aware)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from holiday_peak_lib.adapters.acp_mapper import AcpCatalogMapper
from holiday_peak_lib.adapters.inventory_adapter import InventoryConnector
from holiday_peak_lib.adapters.mock_adapters import (
    MockInventoryAdapter,
    MockProductAdapter,
)
from holiday_peak_lib.adapters.product_adapter import ProductConnector

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
    products = product_connector or ProductConnector(adapter=MockProductAdapter())
    inventory = inventory_connector or InventoryConnector(adapter=MockInventoryAdapter())
    mapping = AcpCatalogMapper()
    return CatalogAdapters(products=products, inventory=inventory, mapping=mapping)
