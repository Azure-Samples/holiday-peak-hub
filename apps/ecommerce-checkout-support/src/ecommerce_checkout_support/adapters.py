"""Adapters for the ecommerce checkout support service."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable, Optional

from holiday_peak_lib.adapters import BaseExternalAPIAdapter
from holiday_peak_lib.adapters.inventory_adapter import InventoryConnector
from holiday_peak_lib.adapters.mock_adapters import (
    MockInventoryAdapter,
    MockPricingAdapter,
)
from holiday_peak_lib.adapters.pricing_adapter import PricingConnector
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer
from holiday_peak_lib.schemas.inventory import InventoryContext
from holiday_peak_lib.schemas.pricing import PriceContext
from holiday_peak_lib.utils.inventory_rules import StockStatus, classify_item_stock


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
            classification = classify_item_stock(sku, qty, inv_ctx)
            if classification.status == StockStatus.MISSING:
                issues.append({"sku": sku, "type": "inventory_missing"})
            elif classification.status == StockStatus.OUT_OF_STOCK:
                issues.append({"sku": sku, "type": "out_of_stock"})
            elif classification.status == StockStatus.LOW_STOCK:
                issues.append(
                    {
                        "sku": sku,
                        "type": "insufficient_stock",
                        "available": classification.available,
                    }
                )
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


def register_external_api_tools(mcp: FastAPIMCPServer) -> None:
    """Register payment API tools with MCP when configured."""
    base_url = os.getenv("PAYMENT_API_URL")
    if not base_url:
        return
    api_key = os.getenv("PAYMENT_API_KEY")
    adapter = BaseExternalAPIAdapter("payment", base_url=base_url, api_key=api_key)
    adapter.add_api_tool("authorize", "POST", "/authorize")
    adapter.add_api_tool("capture", "POST", "/capture")
    adapter.add_api_tool("refund", "POST", "/refund")
    adapter.register_mcp_tools(mcp)
