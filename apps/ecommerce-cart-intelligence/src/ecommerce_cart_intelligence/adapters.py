"""Adapters for the ecommerce cart intelligence service."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from holiday_peak_lib.adapters.inventory_adapter import InventoryConnector
from holiday_peak_lib.adapters.mock_adapters import (
    MockInventoryAdapter,
    MockPricingAdapter,
    MockProductAdapter,
)
from holiday_peak_lib.adapters.pricing_adapter import PricingConnector
from holiday_peak_lib.adapters.product_adapter import ProductConnector
from holiday_peak_lib.schemas.inventory import InventoryContext
from holiday_peak_lib.schemas.pricing import PriceContext


@dataclass
class CartAdapters:
    """Container for cart intelligence adapters."""

    products: ProductConnector
    pricing: PricingConnector
    inventory: InventoryConnector
    analytics: "CartAnalyticsAdapter"


class CartAnalyticsAdapter:
    """Lightweight heuristics for cart risk and monitoring signals."""

    async def estimate_abandonment_risk(
        self,
        cart_items: Iterable[dict[str, object]],
        *,
        inventory: list[InventoryContext | None],
        pricing: list[PriceContext],
    ) -> dict[str, object]:
        drivers: list[str] = []
        risk = 0.1

        for item, inv in zip(cart_items, inventory):
            sku = str(item.get("sku"))
            qty = int(item.get("quantity", 1))
            if inv is None:
                risk += 0.15
                drivers.append(f"missing inventory for {sku}")
                continue
            available = inv.item.available
            if available <= 0:
                risk += 0.35
                drivers.append(f"out of stock for {sku}")
            elif available < qty:
                risk += 0.2
                drivers.append(f"low stock for {sku}")

        for price_ctx in pricing:
            if price_ctx.active is None:
                risk += 0.1
                drivers.append(f"no active price for {price_ctx.sku}")
            elif not price_ctx.active.promotional:
                risk += 0.05
                drivers.append(f"no promotion for {price_ctx.sku}")

        risk = min(risk, 1.0)
        return {"risk_score": round(risk, 2), "drivers": drivers}


def build_cart_adapters(
    *,
    product_connector: Optional[ProductConnector] = None,
    pricing_connector: Optional[PricingConnector] = None,
    inventory_connector: Optional[InventoryConnector] = None,
) -> CartAdapters:
    """Create adapters for cart intelligence workflows.

    Uses mock adapters by default for local development.
    """
    products = product_connector or ProductConnector(adapter=MockProductAdapter())
    pricing = pricing_connector or PricingConnector(adapter=MockPricingAdapter())
    inventory = inventory_connector or InventoryConnector(adapter=MockInventoryAdapter())
    analytics = CartAnalyticsAdapter()
    return CartAdapters(products=products, pricing=pricing, inventory=inventory, analytics=analytics)
