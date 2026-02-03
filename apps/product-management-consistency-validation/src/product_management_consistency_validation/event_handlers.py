"""Event handlers for product consistency validation service."""
from __future__ import annotations

import json

from holiday_peak_lib.utils.event_hub import EventHandler
from holiday_peak_lib.utils.logging import configure_logging

from .adapters import build_consistency_adapters


def build_event_handlers() -> dict[str, EventHandler]:
    """Build event handlers for consistency validation subscriptions."""
    logger = configure_logging(
        app_name="product-management-consistency-validation-events"
    )
    adapters = build_consistency_adapters()

    async def handle_product_event(partition_context, event) -> None:  # noqa: ANN001
        payload = json.loads(event.body_as_str())
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        sku = data.get("sku") or data.get("product_id") or data.get("id")
        if not sku:
            logger.info("consistency_event_skipped", event_type=payload.get("event_type"))
            return

        product = await adapters.products.get_product(str(sku))
        if product is None:
            logger.info(
                "consistency_event_missing",
                event_type=payload.get("event_type"),
                sku=sku,
            )
            return

        validation = await adapters.validator.validate(product)
        logger.info(
            "consistency_event_processed",
            event_type=payload.get("event_type"),
            sku=sku,
            status=validation.get("status"),
            issue_count=len(validation.get("issues", [])),
        )

    return {"product-events": handle_product_event}
