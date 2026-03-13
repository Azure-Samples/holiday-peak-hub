"""Event handlers for ecommerce catalog search service."""

from __future__ import annotations

import json

from holiday_peak_lib.utils.event_hub import EventHandler
from holiday_peak_lib.utils.logging import configure_logging

from .adapters import build_catalog_adapters
from .ai_search import delete_catalog_document, upsert_catalog_document


def build_event_handlers() -> dict[str, EventHandler]:
    """Build event handlers for catalog search subscriptions."""
    logger = configure_logging(app_name="ecommerce-catalog-search-events")
    adapters = build_catalog_adapters()

    async def handle_product_event(_partition_context, event) -> None:  # noqa: ANN001
        payload = json.loads(event.body_as_str())
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        event_type = str(payload.get("event_type") or "")
        sku = data.get("sku") or data.get("product_id") or data.get("id")
        if not sku:
            logger.info(
                "catalog_event_skipped",
                extra={"event_type": event_type},
            )
            return

        if "delete" in event_type.lower():
            deleted = await delete_catalog_document(str(sku))
            logger.info(
                "catalog_event_index_delete",
                extra={
                    "event_type": event_type,
                    "sku": sku,
                    "indexed": deleted,
                },
            )
            return

        product = await adapters.products.get_product(str(sku))
        if product is None:
            logger.info(
                "catalog_event_missing_product",
                extra={
                    "event_type": event_type,
                    "sku": sku,
                },
            )
            return

        inventory_item = await adapters.inventory.get_item(str(sku))
        if inventory_item is None:
            availability = "unknown"
        elif inventory_item.available > 0:
            availability = "in_stock"
        else:
            availability = "out_of_stock"

        acp_payload = adapters.mapping.to_acp_product(product, availability=availability)
        search_document = {
            "id": product.sku,
            "sku": product.sku,
            "title": product.name,
            "description": product.description or "",
            "content": " ".join(
                value
                for value in [
                    product.name,
                    product.description or "",
                    product.category,
                    product.brand or "",
                ]
                if value
            ),
            "category": product.category,
            "brand": product.brand or "",
            "availability": availability,
            "price": float(product.price or 0.0),
        }
        indexed = await upsert_catalog_document(search_document)
        logger.info(
            "catalog_event_processed",
            extra={
                "event_type": event_type,
                "sku": sku,
                "availability": availability,
                "title": product.name,
                "acp_item_id": acp_payload.get("item_id"),
                "indexed": indexed,
            },
        )

    return {"product-events": handle_product_event}
