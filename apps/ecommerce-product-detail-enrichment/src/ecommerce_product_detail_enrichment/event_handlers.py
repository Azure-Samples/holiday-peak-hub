"""Event handlers for ecommerce product detail enrichment service."""
from __future__ import annotations

import asyncio
import json

from holiday_peak_lib.utils.event_hub import EventHandler
from holiday_peak_lib.utils.logging import configure_logging

from .adapters import build_enrichment_adapters, merge_product_enrichment


def build_event_handlers() -> dict[str, EventHandler]:
    """Build event handlers for product detail enrichment subscriptions."""
    logger = configure_logging(app_name="ecommerce-product-detail-enrichment-events")
    adapters = build_enrichment_adapters()

    async def handle_product_event(partition_context, event) -> None:  # noqa: ANN001
        payload = json.loads(event.body_as_str())
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        sku = data.get("sku") or data.get("product_id") or data.get("id")
        if not sku:
            logger.info("enrichment_event_skipped", event_type=payload.get("event_type"))
            return

        product_task = adapters.products.get_product(str(sku))
        inventory_task = adapters.inventory.build_inventory_context(str(sku))
        acp_task = adapters.acp.get_content(str(sku))
        review_task = adapters.reviews.get_summary(str(sku))

        product, inventory, acp_content, review_summary = await asyncio.gather(
            product_task,
            inventory_task,
            acp_task,
            review_task,
        )

        enriched = merge_product_enrichment(product, acp_content, review_summary)
        enriched["inventory"] = inventory.model_dump() if inventory else None

        logger.info(
            "enrichment_event_processed",
            event_type=payload.get("event_type"),
            sku=sku,
            has_inventory=inventory is not None,
            review_count=review_summary.get("review_count"),
            has_product=product is not None,
            enrichment_keys=list(enriched.keys()),
        )

    return {"product-events": handle_product_event}
