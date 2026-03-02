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


@dataclass
class CatalogAdapters:
    """Container for catalog search adapters."""

    products: ProductConnector
    inventory: InventoryConnector
    mapping: AcpCatalogMapper


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
