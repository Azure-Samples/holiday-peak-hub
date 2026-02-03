"""Event handlers for ecommerce checkout support service."""
from __future__ import annotations

import asyncio
import json

from holiday_peak_lib.utils.event_hub import EventHandler
from holiday_peak_lib.utils.logging import configure_logging

from .adapters import build_checkout_adapters
from .agents import _coerce_items


def build_event_handlers() -> dict[str, EventHandler]:
    """Build event handlers for checkout support subscriptions."""
    logger = configure_logging(app_name="ecommerce-checkout-support-events")
    adapters = build_checkout_adapters()

    async def handle_order_event(partition_context, event) -> None:  # noqa: ANN001
        payload = json.loads(event.body_as_str())
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        items = _coerce_items(data.get("items"))
        order_id = data.get("order_id") or data.get("id")
        if not items:
            logger.info(
                "checkout_event_skipped",
                event_type=payload.get("event_type"),
                order_id=order_id,
            )
            return

        pricing_tasks = [
            adapters.pricing.build_price_context(item["sku"]) for item in items
        ]
        inventory_tasks = [
            adapters.inventory.build_inventory_context(item["sku"]) for item in items
        ]
        pricing_contexts, inventory_contexts = await asyncio.gather(
            asyncio.gather(*pricing_tasks),
            asyncio.gather(*inventory_tasks),
        )
        validation = await adapters.validator.validate(
            items, pricing=pricing_contexts, inventory=inventory_contexts
        )
        logger.info(
            "checkout_event_processed",
            event_type=payload.get("event_type"),
            order_id=order_id,
            status=validation.get("status"),
            issue_count=len(validation.get("issues", [])),
        )

    async def handle_inventory_event(partition_context, event) -> None:  # noqa: ANN001
        payload = json.loads(event.body_as_str())
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        sku = data.get("sku") or data.get("product_id")
        if not sku:
            logger.info(
                "inventory_event_skipped", event_type=payload.get("event_type")
            )
            return
        context = await adapters.inventory.build_inventory_context(str(sku))
        available = context.item.available if context else None
        logger.info(
            "inventory_event_processed",
            event_type=payload.get("event_type"),
            sku=sku,
            available=available,
        )

    return {
        "order-events": handle_order_event,
        "inventory-events": handle_inventory_event,
    }
