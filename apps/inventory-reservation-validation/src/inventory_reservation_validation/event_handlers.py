"""Event handlers for inventory reservation validation service."""

from __future__ import annotations

import json

from holiday_peak_lib.utils.event_hub import EventHandler
from holiday_peak_lib.utils.logging import configure_logging

from .adapters import build_reservation_validation_adapters


def build_event_handlers() -> dict[str, EventHandler]:
    """Build event handlers for reservation validation subscriptions."""
    logger = configure_logging(app_name="inventory-reservation-validation-events")
    adapters = build_reservation_validation_adapters()

    async def handle_order_event(partition_context, event) -> None:  # noqa: ANN001
        payload = json.loads(event.body_as_str())
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        items = data.get("items") or []
        reservation_id = data.get("reservation_id") or data.get("order_id") or data.get("id")
        if not items:
            logger.info(
                "reservation_event_skipped",
                event_type=payload.get("event_type"),
                reservation_id=reservation_id,
            )
            return

        results: list[dict[str, object]] = []
        for item in items:
            if not isinstance(item, dict) or "sku" not in item:
                continue
            sku = str(item.get("sku"))
            request_qty = int(item.get("quantity", 1))
            context = await adapters.inventory.build_inventory_context(sku)
            if context is None:
                results.append(
                    {
                        "sku": sku,
                        "requested_qty": request_qty,
                        "approved": False,
                        "reason": "missing_inventory",
                    }
                )
                continue
            validation = await adapters.validator.validate(context, request_qty=request_qty)
            results.append(validation)

        approved_count = sum(1 for result in results if result.get("approved"))
        logger.info(
            "reservation_event_processed",
            event_type=payload.get("event_type"),
            reservation_id=reservation_id,
            item_count=len(results),
            approved_count=approved_count,
        )

    return {"order-events": handle_order_event}
