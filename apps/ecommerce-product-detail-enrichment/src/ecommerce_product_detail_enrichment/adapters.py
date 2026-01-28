"""Adapters for the ecommerce product detail enrichment service."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from holiday_peak_lib.adapters.inventory_adapter import InventoryConnector
from holiday_peak_lib.adapters.mock_adapters import MockInventoryAdapter, MockProductAdapter
from holiday_peak_lib.adapters.product_adapter import ProductConnector
from holiday_peak_lib.schemas.product import CatalogProduct


@dataclass
class EnrichmentAdapters:
    """Container for enrichment adapters."""

    products: ProductConnector
    inventory: InventoryConnector
    acp: "AcpContentAdapter"
    reviews: "ReviewAdapter"


class AcpContentAdapter:
    """Stub ACP content adapter for enriched descriptions/features."""

    async def get_content(self, sku: str) -> dict[str, object]:
        return {
            "sku": sku,
            "long_description": "Rich, ACP-supplied product description.",
            "features": ["Feature A", "Feature B", "Feature C"],
            "media": [
                {
                    "type": "image",
                    "url": f"https://example.com/images/{sku}.png",
                }
            ],
        }


class ReviewAdapter:
    """Stub review adapter for aggregate ratings."""

    async def get_summary(self, sku: str) -> dict[str, object]:
        return {
            "sku": sku,
            "rating": 4.6,
            "review_count": 128,
            "highlights": ["Great quality", "Fast shipping"],
        }


def build_enrichment_adapters(
    *,
    product_connector: Optional[ProductConnector] = None,
    inventory_connector: Optional[InventoryConnector] = None,
) -> EnrichmentAdapters:
    """Create adapters for product detail enrichment workflows."""
    products = product_connector or ProductConnector(adapter=MockProductAdapter())
    inventory = inventory_connector or InventoryConnector(adapter=MockInventoryAdapter())
    acp = AcpContentAdapter()
    reviews = ReviewAdapter()
    return EnrichmentAdapters(products=products, inventory=inventory, acp=acp, reviews=reviews)


def merge_product_enrichment(
    product: CatalogProduct | None,
    acp_content: dict[str, object],
    review_summary: dict[str, object],
) -> dict[str, object]:
    if product is None:
        return {
            "sku": acp_content.get("sku"),
            "description": acp_content.get("long_description"),
            "features": acp_content.get("features", []),
            "reviews": review_summary,
        }
    return {
        "sku": product.sku,
        "name": product.name,
        "description": acp_content.get("long_description") or product.description,
        "features": acp_content.get("features", []),
        "rating": review_summary.get("rating"),
        "review_count": review_summary.get("review_count"),
        "media": acp_content.get("media", []),
        "product": product.model_dump(),
    }
