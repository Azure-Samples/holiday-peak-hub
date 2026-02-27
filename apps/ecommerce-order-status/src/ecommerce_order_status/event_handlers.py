"""Event handlers for ecommerce order status service."""

from __future__ import annotations

import json

from holiday_peak_lib.utils.event_hub import EventHandler
from holiday_peak_lib.utils.logging import configure_logging

from .adapters import build_order_status_adapters


def build_event_handlers() -> dict[str, EventHandler]:
    """Build event handlers for order status subscriptions."""
    logger = configure_logging(app_name="ecommerce-order-status-events")
    adapters = build_order_status_adapters()

    async def handle_order_event(partition_context, event) -> None:  # noqa: ANN001
        payload = json.loads(event.body_as_str())
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        order_id = data.get("order_id") or data.get("id")
        tracking_id = data.get("tracking_id") or data.get("shipment_id")
        if not tracking_id and order_id:
            tracking_id = await adapters.resolver.resolve_tracking_id(str(order_id))
        if not tracking_id:
            logger.info("order_status_event_skipped", event_type=payload.get("event_type"))
            return

        context = await adapters.logistics.build_logistics_context(str(tracking_id))
        logger.info(
            "order_status_event_processed",
            event_type=payload.get("event_type"),
            order_id=order_id,
            tracking_id=tracking_id,
            status=context.shipment.status if context else None,
            event_count=len(context.events) if context else 0,
        )

    return {"order-events": handle_order_event}
