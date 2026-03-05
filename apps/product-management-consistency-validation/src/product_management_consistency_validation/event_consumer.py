"""Event Hub consumer handlers for the completeness-jobs pipeline."""

from __future__ import annotations

import json
import os
from typing import Any

from holiday_peak_lib.utils.event_hub import EventHandler
from holiday_peak_lib.utils.logging import configure_logging

from .adapters import build_consistency_adapters
from .completeness_engine import CompletenessEngine

_LOGGER = configure_logging(app_name="product-management-consistency-validation-events")


async def _publish_enrichment_job(
    entity_id: str,
    report: Any,
) -> None:
    """Send an enrichment-jobs event to Event Hub for a gap-heavy product."""
    connection_string = os.getenv("EVENTHUB_CONNECTION_STRING")
    if not connection_string:
        _LOGGER.warning("enrichment_publish_skipped_no_connection entity_id=%s", entity_id)
        return

    try:
        from azure.eventhub import EventData  # noqa: PLC0415
        from azure.eventhub.aio import EventHubProducerClient  # noqa: PLC0415

        payload = json.dumps(
            {
                "event_type": "enrichment_requested",
                "data": {
                    "entity_id": entity_id,
                    "category_id": report.category_id,
                    "schema_version": report.schema_version,
                    "completeness_score": report.completeness_score,
                    "enrichable_gap_count": len(report.enrichable_gaps),
                    "enrichable_fields": [g.field_name for g in report.enrichable_gaps],
                },
            }
        )

        async with EventHubProducerClient.from_connection_string(
            conn_str=connection_string,
            eventhub_name="enrichment-jobs",
        ) as producer:
            batch = await producer.create_batch()
            batch.add(EventData(payload))
            await producer.send_batch(batch)

        _LOGGER.info("enrichment_job_published entity_id=%s", entity_id)

    except Exception as exc:  # noqa: BLE001
        _LOGGER.error("enrichment_publish_failed entity_id=%s error=%s", entity_id, exc)


def build_completeness_event_handlers(
    *,
    completeness_threshold: float = 0.7,
) -> dict[str, EventHandler]:
    """Build event handlers keyed by Event Hub topic name.

    Handles:
    - ``completeness-jobs``: loads product + schema, evaluates completeness,
      stores the :class:`~completeness_engine.GapReport`, and publishes to
      ``enrichment-jobs`` when the score is below *completeness_threshold*.
    """
    adapters = build_consistency_adapters()
    engine = CompletenessEngine()

    async def handle_completeness_job(partition_context: Any, event: Any) -> None:
        payload = json.loads(event.body_as_str())
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        entity_id = data.get("entity_id") or data.get("product_id") or data.get("sku")
        if not entity_id:
            _LOGGER.info(
                "completeness_event_skipped event_type=%s",
                payload.get("event_type"),
            )
            return

        product = await adapters.products.get_product(str(entity_id))
        if product is None:
            _LOGGER.info("completeness_event_missing entity_id=%s", entity_id)
            return

        category_id = data.get("category_id") or (product.category or "default")
        schema = await adapters.completeness.get_schema(category_id)
        if schema is None:
            _LOGGER.warning("completeness_schema_missing category_id=%s", category_id)
            return

        report = engine.evaluate(str(entity_id), product.model_dump(), schema)
        await adapters.completeness.store_gap_report(report)

        _LOGGER.info(
            "completeness_evaluated entity_id=%s score=%s gaps=%d",
            entity_id,
            report.completeness_score,
            len(report.gaps),
        )

        if report.completeness_score < completeness_threshold and report.enrichable_gaps:
            await _publish_enrichment_job(str(entity_id), report)

    return {"completeness-jobs": handle_completeness_job}
