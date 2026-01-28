"""Adapters for the product consistency validation service."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from holiday_peak_lib.adapters.mock_adapters import MockProductAdapter
from holiday_peak_lib.adapters.product_adapter import ProductConnector
from holiday_peak_lib.schemas.product import CatalogProduct


@dataclass
class ProductConsistencyAdapters:
    """Container for product consistency validation adapters."""

    products: ProductConnector
    validator: "ProductConsistencyValidator"


class ProductConsistencyValidator:
    """Validate product data for completeness and consistency."""

    async def validate(self, product: CatalogProduct) -> dict[str, Any]:
        issues = []
        if not product.name:
            issues.append("missing_name")
        if product.price is not None and product.price < 0:
            issues.append("negative_price")
        if product.price is not None and not product.currency:
            issues.append("missing_currency")
        if not product.image_url:
            issues.append("missing_image")
        return {
            "sku": product.sku,
            "issues": issues,
            "status": "invalid" if issues else "valid",
        }


def build_consistency_adapters(
    *, product_connector: Optional[ProductConnector] = None
) -> ProductConsistencyAdapters:
    """Create adapters for product consistency validation workflows."""
    products = product_connector or ProductConnector(adapter=MockProductAdapter())
    validator = ProductConsistencyValidator()
    return ProductConsistencyAdapters(products=products, validator=validator)
