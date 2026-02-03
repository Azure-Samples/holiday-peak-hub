"""Event handlers for product ACP transformation service."""
from __future__ import annotations

import json

from holiday_peak_lib.utils.event_hub import EventHandler
from holiday_peak_lib.utils.logging import configure_logging

from .adapters import build_acp_transformation_adapters


def build_event_handlers() -> dict[str, EventHandler]:
    """Build event handlers for ACP transformation subscriptions."""
    logger = configure_logging(app_name="product-management-acp-transformation-events")
    adapters = build_acp_transformation_adapters()

    async def handle_product_event(partition_context, event) -> None:  # noqa: ANN001
        payload = json.loads(event.body_as_str())
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        sku = data.get("sku") or data.get("product_id") or data.get("id")
        if not sku:
            logger.info("acp_transform_event_skipped", event_type=payload.get("event_type"))
            return

        product = await adapters.products.get_product(str(sku))
        if product is None:
            logger.info(
                "acp_transform_event_missing",
                event_type=payload.get("event_type"),
                sku=sku,
            )
            return

        acp_payload = adapters.mapper.to_acp_product(product, availability="in_stock")
        logger.info(
            "acp_transform_event_processed",
            event_type=payload.get("event_type"),
            sku=sku,
            acp_item_id=acp_payload.get("item_id"),
        )

    return {"product-events": handle_product_event}
