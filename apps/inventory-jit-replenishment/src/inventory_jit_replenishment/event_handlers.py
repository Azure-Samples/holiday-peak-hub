"""Event handlers for inventory JIT replenishment service."""
from __future__ import annotations

import json

from holiday_peak_lib.utils.event_hub import EventHandler
from holiday_peak_lib.utils.logging import configure_logging

from .adapters import build_replenishment_adapters


def build_event_handlers() -> dict[str, EventHandler]:
    """Build event handlers for replenishment subscriptions."""
    logger = configure_logging(app_name="inventory-jit-replenishment-events")
    adapters = build_replenishment_adapters()

    async def handle_inventory_event(partition_context, event) -> None:  # noqa: ANN001
        payload = json.loads(event.body_as_str())
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        sku = data.get("sku") or data.get("product_id") or data.get("id")
        if not sku:
            logger.info(
                "replenishment_event_skipped", event_type=payload.get("event_type")
            )
            return

        context = await adapters.inventory.build_inventory_context(str(sku))
        if context is None:
            logger.info(
                "replenishment_event_missing",
                event_type=payload.get("event_type"),
                sku=sku,
            )
            return

        plan = await adapters.planner.build_replenishment_plan(context)
        logger.info(
            "replenishment_event_processed",
            event_type=payload.get("event_type"),
            sku=sku,
            reorder_qty=plan.get("recommended_reorder_qty"),
            target_stock=plan.get("target_stock"),
        )

    return {"inventory-events": handle_inventory_event}
