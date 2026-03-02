"""Event handlers for the Truth Ingestion service."""

from __future__ import annotations

import json

from holiday_peak_lib.utils.event_hub import EventHandler
from holiday_peak_lib.utils.logging import configure_logging

from .adapters import build_ingestion_adapters, ingest_single_product


def build_event_handlers() -> dict[str, EventHandler]:
    """Build event handlers for truth ingestion Event Hub subscriptions."""
    logger = configure_logging(app_name="truth-ingestion-events")
    adapters = build_ingestion_adapters()

    async def handle_ingest_job(partition_context, event) -> None:  # noqa: ANN001
        """Process an ingest-job event from Event Hub."""
        payload = json.loads(event.body_as_str())
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        entity_id = (
            data.get("entity_id") or data.get("id") or payload.get("entity_id")
        )

        if not data:
            logger.info(
                "ingest_job_skipped event_type=%s reason=empty_data",
                payload.get("event_type"),
            )
            return

        try:
            result = await ingest_single_product(data, adapters)
            logger.info(
                "ingest_job_processed entity_id=%s event_type=%s assets_resolved=%s",
                entity_id or result.get("entity_id"),
                payload.get("event_type"),
                result.get("assets_resolved", 0),
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "ingest_job_failed entity_id=%s error=%s",
                entity_id,
                str(exc),
            )

    return {"ingest-jobs": handle_ingest_job}
