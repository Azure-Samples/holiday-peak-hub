"""Event handlers for ecommerce order status service."""

from __future__ import annotations

import json

from holiday_peak_lib.events import parse_retail_event
from holiday_peak_lib.utils.event_hub import EventHandler
from holiday_peak_lib.utils.logging import configure_logging
from pydantic import ValidationError

from .adapters import build_order_status_adapters


def build_event_handlers() -> dict[str, EventHandler]:
    """Build event handlers for order status subscriptions."""
    logger = configure_logging(app_name="ecommerce-order-status-events")
    adapters = build_order_status_adapters()

    async def handle_order_event(_partition_context, event) -> None:  # noqa: ANN001
        try:
            payload = json.loads(event.body_as_str())
        except json.JSONDecodeError:
            logger.warning(
                "order_status_event_invalid_json",
                extra={"event_type": None},
            )
            return
        try:
            order_event = parse_retail_event(payload, topic="order-events")
        except (ValidationError, ValueError) as exc:
            logger.warning(
                "order_status_event_invalid",
                extra={"error_type": type(exc).__name__},
            )
            return

        order_data = order_event.data
        order_id = order_data.order_id
        tracking_id = order_data.tracking_id or order_data.shipment_id
        if not tracking_id and order_id:
            tracking_id = await adapters.resolver.resolve_tracking_id(str(order_id))
        if not tracking_id:
            logger.info(
                "order_status_event_skipped",
                extra={"event_type": order_event.event_type},
            )
            return

        context = await adapters.logistics.build_logistics_context(str(tracking_id))
        logger.info(
            "order_status_event_processed",
            extra={
                "event_type": order_event.event_type,
                "order_id": order_id,
                "tracking_id": tracking_id,
                "status": context.shipment.status if context else None,
                "event_count": len(context.events) if context else 0,
            },
        )

    return {"order-events": handle_order_event}
