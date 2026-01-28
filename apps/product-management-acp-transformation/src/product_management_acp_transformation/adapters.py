"""Adapters for the product ACP transformation service."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from holiday_peak_lib.adapters.mock_adapters import MockProductAdapter
from holiday_peak_lib.adapters.product_adapter import ProductConnector
from holiday_peak_lib.schemas.product import CatalogProduct


@dataclass
class AcpTransformationAdapters:
    """Container for ACP transformation adapters."""

    products: ProductConnector
    mapper: "AcpCatalogMapper"


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


def build_acp_transformation_adapters(
    *, product_connector: Optional[ProductConnector] = None
) -> AcpTransformationAdapters:
    """Create adapters for ACP transformation workflows."""
    products = product_connector or ProductConnector(adapter=MockProductAdapter())
    mapper = AcpCatalogMapper()
    return AcpTransformationAdapters(products=products, mapper=mapper)
