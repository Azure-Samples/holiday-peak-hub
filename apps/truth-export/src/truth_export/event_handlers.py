"""Event handlers for the truth-export service."""

from __future__ import annotations

import json
import uuid

from holiday_peak_lib.utils.event_hub import EventHandler
from holiday_peak_lib.utils.logging import configure_logging

from .adapters import build_truth_export_adapters
from .export_engine import ExportEngine


def build_event_handlers() -> dict[str, EventHandler]:
    """Build event handlers for the export-jobs Event Hub subscription."""
    logger = configure_logging(app_name="truth-export-events")
    adapters = build_truth_export_adapters()
    engine = ExportEngine()

    async def handle_export_job(partition_context, event) -> None:  # noqa: ANN001
        payload = json.loads(event.body_as_str())
        data = payload.get("data", {}) if isinstance(payload, dict) else {}

        entity_id = data.get("entity_id") or data.get("product_id")
        protocol = data.get("protocol", "ucp")

        if not entity_id:
            logger.info(
                "export_job_skipped",
                event_type=payload.get("event_type"),
                reason="missing entity_id",
            )
            return

        product = await adapters.truth_store.get_product_style(str(entity_id))
        if product is None:
            logger.info(
                "export_job_missing_product",
                entity_id=entity_id,
                protocol=protocol,
            )
            return

        attributes = await adapters.truth_store.get_truth_attributes(str(entity_id))
        mapping = await adapters.truth_store.get_protocol_mapping(str(protocol))

        job_id = str(uuid.uuid4())
        result = engine.export(
            job_id=job_id,
            product=product,
            attributes=attributes,
            protocol=str(protocol),
            mapping=mapping,
            partner_id=data.get("partner_id"),
        )

        await adapters.truth_store.save_export_result(result.model_dump())

        audit = engine.build_audit_event(job_id, product, str(protocol))
        await adapters.truth_store.save_audit_event(audit.model_dump())

        logger.info(
            "export_job_processed",
            job_id=job_id,
            entity_id=entity_id,
            protocol=protocol,
            status=result.status,
        )

    return {"export-jobs": handle_export_job}
