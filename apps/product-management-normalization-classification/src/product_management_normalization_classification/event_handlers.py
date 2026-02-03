"""Event handlers for product normalization/classification service."""
from __future__ import annotations

import json

from holiday_peak_lib.utils.event_hub import EventHandler
from holiday_peak_lib.utils.logging import configure_logging

from .adapters import build_normalization_adapters


def build_event_handlers() -> dict[str, EventHandler]:
    """Build event handlers for product normalization subscriptions."""
    logger = configure_logging(
        app_name="product-management-normalization-classification-events"
    )
    adapters = build_normalization_adapters()

    async def handle_product_event(partition_context, event) -> None:  # noqa: ANN001
        payload = json.loads(event.body_as_str())
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        sku = data.get("sku") or data.get("product_id") or data.get("id")
        if not sku:
            logger.info("normalization_event_skipped", event_type=payload.get("event_type"))
            return

        product = await adapters.products.get_product(str(sku))
        if product is None:
            logger.info(
                "normalization_event_missing",
                event_type=payload.get("event_type"),
                sku=sku,
            )
            return

        normalized = await adapters.normalizer.normalize(product)
        logger.info(
            "normalization_event_processed",
            event_type=payload.get("event_type"),
            sku=sku,
            classification=normalized.get("classification"),
            normalized_category=normalized.get("normalized_category"),
        )

    return {"product-events": handle_product_event}
