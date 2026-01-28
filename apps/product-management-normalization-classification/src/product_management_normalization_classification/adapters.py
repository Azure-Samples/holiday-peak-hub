"""Adapters for product normalization and classification service."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from holiday_peak_lib.adapters.mock_adapters import MockProductAdapter
from holiday_peak_lib.adapters.product_adapter import ProductConnector
from holiday_peak_lib.schemas.product import CatalogProduct


@dataclass
class ProductNormalizationAdapters:
    """Container for normalization/classification adapters."""

    products: ProductConnector
    normalizer: "ProductNormalizer"


class ProductNormalizer:
    """Normalize and classify product catalog entries."""

    async def normalize(self, product: CatalogProduct) -> dict[str, Any]:
        normalized_name = product.name.strip().lower() if product.name else ""
        category = product.category or product.attributes.get("category")
        tags = [tag.lower() for tag in product.tags]
        classification = _classify_product(product)
        return {
            "sku": product.sku,
            "normalized_name": normalized_name,
            "normalized_category": category.lower() if category else None,
            "tags": tags,
            "classification": classification,
        }


def build_normalization_adapters(
    *, product_connector: Optional[ProductConnector] = None
) -> ProductNormalizationAdapters:
    """Create adapters for product normalization workflows."""
    products = product_connector or ProductConnector(adapter=MockProductAdapter())
    normalizer = ProductNormalizer()
    return ProductNormalizationAdapters(products=products, normalizer=normalizer)


def _classify_product(product: CatalogProduct) -> str:
    text = f"{product.name} {product.description or ''}".lower()
    if any(word in text for word in ["shoe", "sneaker", "boot"]):
        return "footwear"
    if any(word in text for word in ["shirt", "jacket", "apparel"]):
        return "apparel"
    if any(word in text for word in ["phone", "laptop", "camera"]):
        return "electronics"
    return "general"
