"""Event handlers for inventory health check service."""
from __future__ import annotations

import asyncio
import json

from holiday_peak_lib.utils.event_hub import EventHandler
from holiday_peak_lib.utils.logging import configure_logging

from .adapters import build_inventory_health_adapters


def build_event_handlers() -> dict[str, EventHandler]:
    """Build event handlers for inventory health subscriptions."""
    logger = configure_logging(app_name="inventory-health-check-events")
    adapters = build_inventory_health_adapters()

    async def handle_order_event(partition_context, event) -> None:  # noqa: ANN001
        payload = json.loads(event.body_as_str())
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        items = data.get("items") or []
        skus = _extract_skus(items)
        order_id = data.get("order_id") or data.get("id")
        if not skus:
            logger.info(
                "inventory_health_order_skipped",
                event_type=payload.get("event_type"),
                order_id=order_id,
            )
            return

        contexts = await asyncio.gather(
            *[adapters.inventory.build_inventory_context(sku) for sku in skus]
        )
        results = []
        for context in contexts:
            if context is None:
                continue
            results.append(await adapters.analytics.evaluate_health(context))

        degraded = [result for result in results if result.get("health") != "healthy"]
        logger.info(
            "inventory_health_order_processed",
            event_type=payload.get("event_type"),
            order_id=order_id,
            sku_count=len(skus),
            degraded_count=len(degraded),
        )

    async def handle_inventory_event(partition_context, event) -> None:  # noqa: ANN001
        payload = json.loads(event.body_as_str())
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        sku = data.get("sku") or data.get("product_id") or data.get("id")
        if not sku:
            logger.info(
                "inventory_health_event_skipped", event_type=payload.get("event_type")
            )
            return

        context = await adapters.inventory.build_inventory_context(str(sku))
        if context is None:
            logger.info(
                "inventory_health_event_missing",
                event_type=payload.get("event_type"),
                sku=sku,
            )
            return

        health = await adapters.analytics.evaluate_health(context)
        logger.info(
            "inventory_health_event_processed",
            event_type=payload.get("event_type"),
            sku=sku,
            health=health.get("health"),
            issue_count=len(health.get("issues", [])),
        )

    return {
        "order-events": handle_order_event,
        "inventory-events": handle_inventory_event,
    }


def _extract_skus(items: list[object]) -> list[str]:
    skus: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        sku = item.get("sku") or item.get("product_id") or item.get("id")
        if sku:
            skus.append(str(sku))
    return skus
