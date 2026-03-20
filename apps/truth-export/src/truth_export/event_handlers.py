"""Event handlers for the truth-export service."""

from __future__ import annotations

import json
import uuid
from typing import Any

from holiday_peak_lib.utils.event_hub import EventHandler
from holiday_peak_lib.utils.logging import configure_logging

from .adapters import TruthExportAdapters, build_truth_export_adapters
from .export_engine import ExportEngine


def build_event_handlers(
    *,
    adapters: TruthExportAdapters | None = None,
    engine: ExportEngine | None = None,
) -> dict[str, EventHandler]:
    """Build event handlers for the export-jobs Event Hub subscription."""
    logger = configure_logging(app_name="truth-export-events")
    adapters = adapters or build_truth_export_adapters()
    engine = engine or ExportEngine()

    async def handle_export_job(partition_context, event) -> None:  # noqa: ANN001
        _ = partition_context
        payload = json.loads(event.body_as_str())
        data = payload.get("data", {}) if isinstance(payload, dict) else {}

        entity_id = data.get("entity_id") or data.get("product_id")
        protocol = str(data.get("protocol", "ucp")).lower()

        if not entity_id:
            logger.info(
                "export_job_skipped event_type=%s reason=missing_entity_id",
                payload.get("event_type"),
            )
            return

        if _is_hitl_writeback_event(payload, data, protocol):
            approved_fields_raw = data.get("approved_fields")
            approved_fields = (
                [str(field) for field in approved_fields_raw if field]
                if isinstance(approved_fields_raw, list)
                else None
            )

            result = await engine.writeback_to_pim(
                adapters.writeback_manager,
                adapters.truth_store,
                str(entity_id),
                approved_attributes=approved_fields,
                dry_run=bool(data.get("dry_run", False)),
            )
            await adapters.truth_store.save_export_result(result)
            audit = engine.build_writeback_audit_event(
                entity_id=str(entity_id),
                result=result,
                trigger="event:export-jobs:hitl-approved",
            )
            await adapters.truth_store.save_audit_event(audit.model_dump())
            logger.info(
                "export_job_writeback_processed entity_id=%s protocol=%s status=%s",
                entity_id,
                protocol,
                result.get("status"),
            )
            return

        product = await adapters.truth_store.get_product_style(str(entity_id))
        if product is None:
            logger.info("export_job_missing_product entity_id=%s protocol=%s", entity_id, protocol)
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
            "export_job_processed job_id=%s entity_id=%s protocol=%s status=%s",
            job_id,
            entity_id,
            protocol,
            result.status,
        )

    return {"export-jobs": handle_export_job}


def _is_hitl_writeback_event(
    payload: dict[str, Any],
    data: dict[str, Any],
    protocol: str,
) -> bool:
    if protocol == "pim":
        return True

    event_type = str(payload.get("event_type", "")).lower()
    decision = str(data.get("decision") or data.get("status") or data.get("review_status") or "")
    source = str(data.get("source") or payload.get("source") or "").lower()

    is_approved = decision.lower() == "approved" or "approved" in event_type
    is_hitl = "hitl" in event_type or source == "truth-hitl"
    return is_approved and is_hitl
