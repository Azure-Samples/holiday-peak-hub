"""Adapters for the assortment optimization service."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from holiday_peak_lib.adapters.mock_adapters import MockProductAdapter
from holiday_peak_lib.adapters.product_adapter import ProductConnector
from holiday_peak_lib.schemas.product import CatalogProduct


@dataclass
class AssortmentAdapters:
    """Container for assortment optimization adapters."""

    products: ProductConnector
    optimizer: "AssortmentOptimizer"


class AssortmentOptimizer:
    """Score products for assortment decisions."""

    async def score_products(self, products: list[CatalogProduct]) -> list[dict[str, Any]]:
        scored = []
        for product in products:
            rating = product.rating if product.rating is not None else 3.5
            price = product.price if product.price is not None else 0.0
            score = (rating * 2) - (price / 100)
            scored.append(
                {
                    "sku": product.sku,
                    "name": product.name,
                    "rating": rating,
                    "price": price,
                    "score": round(score, 3),
                }
            )
        return sorted(scored, key=lambda item: item["score"], reverse=True)

    async def recommend_assortment(
        self, products: list[CatalogProduct], *, target_size: int
    ) -> dict[str, Any]:
        scored = await self.score_products(products)
        keep = scored[:target_size]
        drop = scored[target_size:]
        return {"keep": keep, "drop": drop, "target_size": target_size}


def build_assortment_adapters(
    *, product_connector: Optional[ProductConnector] = None
) -> AssortmentAdapters:
    """Create adapters for assortment optimization workflows."""
    products = product_connector or ProductConnector(adapter=MockProductAdapter())
    optimizer = AssortmentOptimizer()
    return AssortmentAdapters(products=products, optimizer=optimizer)
