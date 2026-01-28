"""Adapters for the ecommerce checkout support service."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from holiday_peak_lib.adapters.inventory_adapter import InventoryConnector
from holiday_peak_lib.adapters.mock_adapters import MockInventoryAdapter, MockPricingAdapter
from holiday_peak_lib.adapters.pricing_adapter import PricingConnector
from holiday_peak_lib.schemas.inventory import InventoryContext
from holiday_peak_lib.schemas.pricing import PriceContext


@dataclass
class CheckoutAdapters:
    """Container for checkout support adapters."""

    pricing: PricingConnector
    inventory: InventoryConnector
    validator: "CheckoutValidationAdapter"


class CheckoutValidationAdapter:
    """Validate checkout items for pricing and availability issues."""

    async def validate(
        self,
        items: Iterable[dict[str, object]],
        *,
        pricing: list[PriceContext],
        inventory: list[InventoryContext | None],
    ) -> dict[str, object]:
        issues: list[dict[str, object]] = []
        for item, price_ctx, inv_ctx in zip(items, pricing, inventory):
            sku = str(item.get("sku"))
            qty = int(item.get("quantity", 1))
            if inv_ctx is None:
                issues.append({"sku": sku, "type": "inventory_missing"})
            else:
                if inv_ctx.item.available <= 0:
                    issues.append({"sku": sku, "type": "out_of_stock"})
                elif inv_ctx.item.available < qty:
                    issues.append({"sku": sku, "type": "insufficient_stock", "available": inv_ctx.item.available})
            if price_ctx.active is None:
                issues.append({"sku": sku, "type": "missing_price"})
        status = "ready" if not issues else "blocked"
        return {"status": status, "issues": issues}


def build_checkout_adapters(
    *,
    pricing_connector: Optional[PricingConnector] = None,
    inventory_connector: Optional[InventoryConnector] = None,
) -> CheckoutAdapters:
    """Create adapters for checkout support workflows."""
    pricing = pricing_connector or PricingConnector(adapter=MockPricingAdapter())
    inventory = inventory_connector or InventoryConnector(adapter=MockInventoryAdapter())
    validator = CheckoutValidationAdapter()
    return CheckoutAdapters(pricing=pricing, inventory=inventory, validator=validator)
