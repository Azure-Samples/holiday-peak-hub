"""Event handlers for the Truth Enrichment service."""

from __future__ import annotations

import json

from holiday_peak_lib.agents.base_agent import AgentDependencies
from holiday_peak_lib.utils.event_hub import EventHandler
from holiday_peak_lib.utils.logging import configure_logging

from .adapters import build_enrichment_adapters
from .agents import TruthEnrichmentAgent
from .enrichment_engine import EnrichmentEngine


def build_event_handlers() -> dict[str, EventHandler]:
    """Build event handlers for enrichment-jobs subscriptions."""
    logger = configure_logging(app_name="truth-enrichment-events")
    adapters = build_enrichment_adapters()
    engine = EnrichmentEngine()
    orchestrator = TruthEnrichmentAgent(
        config=AgentDependencies(
            service_name="truth-enrichment-events",
            router=None,
            tools={},
            slm=None,
            llm=None,
        ),
        adapters=adapters,
        engine=engine,
    )

    async def handle_enrichment_job(partition_context, event) -> None:  # noqa: ANN001
        payload = json.loads(event.body_as_str())
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        entity_id = (
            data.get("entity_id") or data.get("product_id") or data.get("sku") or data.get("id")
        )
        if not entity_id:
            logger.info(
                "enrichment_event_skipped %s",
                {"event_type": payload.get("event_type")},
            )
            return

        result = await orchestrator.handle({"entity_id": str(entity_id)})
        if result.get("error"):
            logger.info(
                "enrichment_event_skipped %s",
                {"entity_id": entity_id, "error": result.get("error")},
            )
            return

        proposed = result.get("proposed", [])
        proposed_count = len(proposed)
        hitl_count = sum(1 for item in proposed if item.get("status") == "pending")

        logger.info(
            "enrichment_event_processed %s",
            {
                "entity_id": entity_id,
                "gaps": proposed_count,
                "proposed": proposed_count,
                "hitl_queued": hitl_count,
            },
        )

    return {"enrichment-jobs": handle_enrichment_job}
