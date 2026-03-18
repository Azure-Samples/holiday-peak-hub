"""Event handlers for logistics returns support service."""

from __future__ import annotations

import json

from holiday_peak_lib.utils.event_hub import EventHandler
from holiday_peak_lib.utils.logging import configure_logging

from .adapters import build_returns_support_adapters


def build_event_handlers() -> dict[str, EventHandler]:
    """Build event handlers for returns support subscriptions."""
    logger = configure_logging(app_name="logistics-returns-support-events")
    adapters = build_returns_support_adapters()

    async def handle_order_event(partition_context, event) -> None:  # noqa: ANN001
        payload = json.loads(event.body_as_str())
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        tracking_id = _resolve_tracking_id(data)
        if not tracking_id:
            logger.info("returns_event_skipped", event_type=payload.get("event_type"))
            return

        context = await adapters.logistics.build_logistics_context(tracking_id)
        if context is None:
            logger.info(
                "returns_event_missing",
                event_type=payload.get("event_type"),
                tracking_id=tracking_id,
            )
            return

        plan = await adapters.assistant.build_returns_plan(context)
        logger.info(
            "returns_event_processed",
            event_type=payload.get("event_type"),
            tracking_id=tracking_id,
            eligible=plan.get("eligible_for_return"),
            status=plan.get("status"),
        )

    return {
        "order-events": handle_order_event,
        "return-events": handle_order_event,
    }


def _resolve_tracking_id(data: dict[str, object]) -> str | None:
    tracking_id = data.get("tracking_id") or data.get("shipment_id")
    if tracking_id:
        return str(tracking_id)
    order_id = data.get("order_id") or data.get("id")
    if order_id:
        return f"T-{order_id}"
    return None
