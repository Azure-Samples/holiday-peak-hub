"""Event handlers for the Truth Enrichment service."""

from __future__ import annotations

import json

from holiday_peak_lib.utils.event_hub import EventHandler
from holiday_peak_lib.utils.logging import configure_logging

from .adapters import build_enrichment_adapters
from .enrichment_engine import EnrichmentEngine


def build_event_handlers() -> dict[str, EventHandler]:
    """Build event handlers for enrichment-jobs subscriptions."""
    logger = configure_logging(app_name="truth-enrichment-events")
    adapters = build_enrichment_adapters()
    engine = EnrichmentEngine()

    async def handle_enrichment_job(partition_context, event) -> None:  # noqa: ANN001
        payload = json.loads(event.body_as_str())
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        entity_id = data.get("entity_id") or data.get("product_id") or data.get("id")
        if not entity_id:
            logger.info("enrichment_event_skipped", event_type=payload.get("event_type"))
            return

        product = await adapters.products.get_product(str(entity_id))
        if product is None:
            logger.info("enrichment_event_missing_product", entity_id=entity_id)
            return

        category = product.get("category", "")
        schema = await adapters.products.get_schema(category)
        required_fields: list[str] = (schema or {}).get("required_fields", [])
        gaps = [f for f in required_fields if not product.get(f)]

        proposed_count = 0
        hitl_count = 0
        for field_name in gaps:
            field_defs = (schema or {}).get("fields", {})
            field_def = field_defs.get(field_name) if field_defs else None
            messages = engine.build_prompt(product, field_name, field_def)
            # Without a live agent handle, we record a zero-confidence proposal
            parsed = {"value": None, "confidence": 0.0, "evidence": "event-driven stub"}
            proposed = engine.build_proposed_attribute(
                entity_id=str(entity_id),
                field_name=field_name,
                parsed=parsed,
                model_id="event-handler-stub",
                job_id=data.get("job_id"),
            )
            await adapters.proposed.upsert(proposed)
            audit = engine.build_audit_event(
                "enrichment_proposed", str(entity_id), field_name, proposed
            )
            await adapters.audit.append(audit)
            if engine.needs_hitl(proposed):
                await adapters.hitl_publisher.publish(
                    {"entity_id": entity_id, "field_name": field_name, "proposed_id": proposed["id"]}
                )
                hitl_count += 1
            else:
                await adapters.truth.upsert({**proposed, "status": "approved"})
            proposed_count += 1

        logger.info(
            "enrichment_event_processed",
            entity_id=entity_id,
            gaps=len(gaps),
            proposed=proposed_count,
            hitl_queued=hitl_count,
        )

    return {"enrichment-jobs": handle_enrichment_job}
