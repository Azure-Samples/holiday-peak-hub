"""Event handlers for search enrichment jobs."""

from __future__ import annotations

import json

from holiday_peak_lib.utils.event_hub import EventHandler
from holiday_peak_lib.utils.logging import configure_logging

from .adapters import SearchEnrichmentAdapters, build_search_enrichment_adapters
from .agents import SearchEnrichmentOrchestrator
from .enrichment_engine import SearchEnrichmentEngine


def build_event_handlers(
    adapters: SearchEnrichmentAdapters | None = None,
    engine: SearchEnrichmentEngine | None = None,
) -> dict[str, EventHandler]:
    """Build event handlers for `search-enrichment-jobs` subscriptions."""
    logger = configure_logging(app_name="search-enrichment-agent-events")
    resolved_adapters = adapters or build_search_enrichment_adapters()
    resolved_engine = engine or SearchEnrichmentEngine()
    orchestrator = SearchEnrichmentOrchestrator(resolved_adapters, resolved_engine)

    async def handle_search_enrichment_job(_partition_context, event) -> None:  # noqa: ANN001
        payload = json.loads(event.body_as_str())
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        entity_id = data.get("entity_id") or data.get("sku") or data.get("product_id")
        if not entity_id:
            logger.info("search_enrichment_event_skipped_missing_entity")
            return

        result = await orchestrator.run(
            entity_id=str(entity_id),
            has_model_backend=False,
            trigger="event",
        )
        logger.info(
            "search_enrichment_event_processed entity_id=%s status=%s strategy=%s",
            entity_id,
            result.get("status"),
            result.get("strategy"),
        )

    return {"search-enrichment-jobs": handle_search_enrichment_job}
