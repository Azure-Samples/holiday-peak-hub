"""Event handlers for ecommerce cart intelligence service."""

from __future__ import annotations

import asyncio
import json

from holiday_peak_lib.utils.event_hub import EventHandler
from holiday_peak_lib.utils.logging import configure_logging

from .adapters import build_cart_adapters
from .agents import _coerce_cart_items


def build_event_handlers() -> dict[str, EventHandler]:
    """Build event handlers for cart intelligence subscriptions."""
    logger = configure_logging(app_name="ecommerce-cart-intelligence-events")
    adapters = build_cart_adapters()

    async def handle_order_event(partition_context, event) -> None:  # noqa: ANN001
        payload = json.loads(event.body_as_str())
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        items = _coerce_cart_items(data.get("items"))
        order_id = data.get("order_id") or data.get("id")
        if not items:
            logger.info(
                "cart_event_skipped",
                event_type=payload.get("event_type"),
                order_id=order_id,
            )
            return

        product_tasks = [
            adapters.products.build_product_context(item["sku"], related_limit=3) for item in items
        ]
        pricing_tasks = [
            adapters.pricing.build_price_context(item["sku"], limit=5) for item in items
        ]
        inventory_tasks = [
            adapters.inventory.build_inventory_context(item["sku"]) for item in items
        ]
        product_contexts, pricing_contexts, inventory_contexts = await asyncio.gather(
            asyncio.gather(*product_tasks),
            asyncio.gather(*pricing_tasks),
            asyncio.gather(*inventory_tasks),
        )
        risk = await adapters.analytics.estimate_abandonment_risk(
            items, inventory=inventory_contexts, pricing=pricing_contexts
        )
        logger.info(
            "cart_event_processed",
            event_type=payload.get("event_type"),
            order_id=order_id,
            risk_score=risk.get("risk_score"),
            driver_count=len(risk.get("drivers", [])),
            product_contexts=len(product_contexts),
        )

    return {"order-events": handle_order_event}
