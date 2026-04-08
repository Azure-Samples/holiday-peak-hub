"""Event handlers for search enrichment jobs."""

from __future__ import annotations

import json
from typing import Any

from holiday_peak_lib.utils.event_hub import EventHandler
from holiday_peak_lib.utils.logging import configure_logging
from holiday_peak_lib.utils.telemetry import get_foundry_tracer

from .adapters import SearchEnrichmentAdapters, build_search_enrichment_adapters
from .agents import SearchEnrichmentOrchestrator
from .enrichment_engine import SearchEnrichmentEngine

_EVENTHUB_NAME = "search-enrichment-jobs"
_EVENTHUB_LIVENESS_DECISION = "liveness.eventhub.search-enrichment-jobs"


def _extract_event_entity_id(data: dict[str, Any]) -> str | None:
    entity_id = data.get("entity_id") or data.get("sku") or data.get("product_id")
    if entity_id is None:
        return None
    return str(entity_id)


def _resolve_liveness_status(result: dict[str, Any], *, default: str) -> str:
    status = result.get("status")
    if status is not None:
        resolved = str(status).strip()
        if resolved:
            return resolved
    if result.get("error") is not None:
        return "error"
    return default


def _trace_eventhub_liveness(
    *,
    outcome: str,
    status: str,
    entity_id: str | None = None,
) -> None:
    metadata: dict[str, Any] = {
        "surface": "eventhub",
        "trigger": "event",
        "eventhub": _EVENTHUB_NAME,
        "status": status,
    }
    if entity_id is not None:
        metadata["entity_id"] = entity_id

    get_foundry_tracer("search-enrichment-agent").trace_decision(
        decision=_EVENTHUB_LIVENESS_DECISION,
        outcome=outcome,
        metadata=metadata,
    )


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
        entity_id = _extract_event_entity_id(data)
        if entity_id is None:
            _trace_eventhub_liveness(
                outcome="missing_entity_id",
                status="skipped",
            )
            logger.info("search_enrichment_event_skipped_missing_entity")
            return

        try:
            result = await orchestrator.run(
                entity_id=entity_id,
                has_model_backend=False,
                trigger="event",
            )
            status = _resolve_liveness_status(result, default="unknown")
            _trace_eventhub_liveness(
                outcome=status,
                status=status,
                entity_id=entity_id,
            )
            logger.info(
                "search_enrichment_event_processed entity_id=%s status=%s strategy=%s",
                entity_id,
                result.get("status"),
                result.get("strategy"),
            )
        except Exception:
            _trace_eventhub_liveness(
                outcome="error",
                status="error",
                entity_id=entity_id,
            )
            raise

    return {_EVENTHUB_NAME: handle_search_enrichment_job}
