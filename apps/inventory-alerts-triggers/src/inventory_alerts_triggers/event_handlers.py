"""Event handlers for inventory alerts and triggers service."""
from __future__ import annotations

import json

from holiday_peak_lib.utils.event_hub import EventHandler
from holiday_peak_lib.utils.logging import configure_logging

from .adapters import build_inventory_alerts_adapters


def build_event_handlers() -> dict[str, EventHandler]:
    """Build event handlers for inventory alert subscriptions."""
    logger = configure_logging(app_name="inventory-alerts-triggers-events")
    adapters = build_inventory_alerts_adapters()

    async def handle_inventory_event(partition_context, event) -> None:  # noqa: ANN001
        payload = json.loads(event.body_as_str())
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        sku = data.get("sku") or data.get("product_id") or data.get("id")
        if not sku:
            logger.info(
                "alerts_event_skipped", event_type=payload.get("event_type")
            )
            return

        context = await adapters.inventory.build_inventory_context(str(sku))
        if context is None:
            logger.info(
                "alerts_event_missing",
                event_type=payload.get("event_type"),
                sku=sku,
            )
            return

        alerts = await adapters.analytics.build_alerts(context)
        logger.info(
            "alerts_event_processed",
            event_type=payload.get("event_type"),
            sku=sku,
            status=alerts.get("status"),
            alert_count=len(alerts.get("alerts", [])),
        )

    return {"inventory-events": handle_inventory_event}
