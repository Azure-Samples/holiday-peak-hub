"""Event handlers for product assortment optimization service."""
from __future__ import annotations

import asyncio
import json

from holiday_peak_lib.utils.event_hub import EventHandler
from holiday_peak_lib.utils.logging import configure_logging

from .adapters import build_assortment_adapters


def build_event_handlers() -> dict[str, EventHandler]:
    """Build event handlers for assortment optimization subscriptions."""
    logger = configure_logging(app_name="product-management-assortment-optimization-events")
    adapters = build_assortment_adapters()

    async def handle_order_event(partition_context, event) -> None:  # noqa: ANN001
        payload = json.loads(event.body_as_str())
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        items = data.get("items") or []
        skus = _extract_skus(items)
        order_id = data.get("order_id") or data.get("id")
        if not skus:
            logger.info(
                "assortment_order_skipped",
                event_type=payload.get("event_type"),
                order_id=order_id,
            )
            return

        products = await _load_products(adapters, skus)
        if not products:
            logger.info(
                "assortment_order_missing",
                event_type=payload.get("event_type"),
                order_id=order_id,
            )
            return

        target_size = _coerce_int(data.get("target_size"), default=min(5, len(products)))
        recommendation = await adapters.optimizer.recommend_assortment(
            products,
            target_size=target_size,
        )
        logger.info(
            "assortment_order_processed",
            event_type=payload.get("event_type"),
            order_id=order_id,
            keep_count=len(recommendation.get("keep", [])),
            drop_count=len(recommendation.get("drop", [])),
        )

    async def handle_product_event(partition_context, event) -> None:  # noqa: ANN001
        payload = json.loads(event.body_as_str())
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        sku = data.get("sku") or data.get("product_id") or data.get("id")
        if not sku:
            logger.info("assortment_product_skipped", event_type=payload.get("event_type"))
            return

        product = await adapters.products.get_product(str(sku))
        if product is None:
            logger.info(
                "assortment_product_missing",
                event_type=payload.get("event_type"),
                sku=sku,
            )
            return

        related = await adapters.products.get_related(str(sku), limit=5)
        products = [product] + related
        target_size = _coerce_int(data.get("target_size"), default=min(3, len(products)))
        recommendation = await adapters.optimizer.recommend_assortment(
            products,
            target_size=target_size,
        )
        logger.info(
            "assortment_product_processed",
            event_type=payload.get("event_type"),
            sku=sku,
            keep_count=len(recommendation.get("keep", [])),
            drop_count=len(recommendation.get("drop", [])),
        )

    return {
        "order-events": handle_order_event,
        "product-events": handle_product_event,
    }


def _extract_skus(items: list[object]) -> list[str]:
    skus: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        sku = item.get("sku") or item.get("product_id") or item.get("id")
        if sku:
            skus.append(str(sku))
    return skus


async def _load_products(adapters, skus: list[str]):  # noqa: ANN001
    tasks = [adapters.products.get_product(sku) for sku in skus]
    results = await asyncio.gather(*tasks)
    return [product for product in results if product is not None]


def _coerce_int(value: object, *, default: int) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default
