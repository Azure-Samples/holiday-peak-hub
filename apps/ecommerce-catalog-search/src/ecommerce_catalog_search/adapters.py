"""Adapters for the ecommerce catalog search service (ACP-aware)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from holiday_peak_lib.adapters.inventory_adapter import InventoryConnector
from holiday_peak_lib.adapters.mock_adapters import MockInventoryAdapter, MockProductAdapter
from holiday_peak_lib.adapters.product_adapter import ProductConnector
from holiday_peak_lib.schemas.product import CatalogProduct


@dataclass
class CatalogAdapters:
    """Container for catalog search adapters."""

    products: ProductConnector
    inventory: InventoryConnector
    mapping: "AcpCatalogMapper"


class AcpCatalogMapper:
    """Map catalog products to ACP Product Feed-like fields."""

    def to_acp_product(
        self,
        product: CatalogProduct,
        *,
        availability: str,
        currency: str = "usd",
    ) -> dict[str, object]:
        sku = product.sku
        price = product.price if product.price is not None else 0.0
        image_url = product.image_url or "https://example.com/images/placeholder.png"
        product_url = f"https://example.com/products/{sku}"
        return {
            "item_id": sku,
            "title": product.name,
            "description": product.description or "",
            "url": product_url,
            "image_url": image_url,
            "brand": product.brand or "",
            "price": f"{price:.2f} {currency}",
            "availability": availability,
            "is_eligible_search": True,
            "is_eligible_checkout": True,
            "store_name": "Example Store",
            "seller_url": "https://example.com/store",
            "seller_privacy_policy": "https://example.com/privacy",
            "seller_tos": "https://example.com/terms",
            "return_policy": "https://example.com/returns",
            "return_window": 30,
            "target_countries": ["US"],
            "store_country": "US",
        }


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
