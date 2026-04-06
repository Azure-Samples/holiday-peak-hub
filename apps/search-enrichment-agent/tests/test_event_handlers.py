"""Unit and integration-like tests for search enrichment event handlers."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from holiday_peak_lib.utils.telemetry import get_foundry_tracer
from search_enrichment_agent.adapters import SearchEnrichmentAdapters
from search_enrichment_agent.event_handlers import build_event_handlers

_TRACE_SERVICE_NAME = "search-enrichment-agent"


@pytest.fixture(autouse=True)
def _clear_service_traces() -> None:
    tracer = get_foundry_tracer(_TRACE_SERVICE_NAME)
    tracer.set_enabled(True)
    tracer.clear()


def _eventhub_liveness_events() -> list[dict[str, object]]:
    return [
        event
        for event in get_foundry_tracer(_TRACE_SERVICE_NAME).get_traces(limit=100)
        if event.get("type") == "decision"
        and event.get("name") == "liveness.eventhub.search-enrichment-jobs"
    ]


@pytest.mark.asyncio
async def test_build_event_handlers_includes_search_enrichment_jobs() -> None:
    handlers = build_event_handlers()
    assert "search-enrichment-jobs" in handlers


@pytest.mark.asyncio
async def test_search_enrichment_event_handler_processes_job_with_mocks() -> None:
    approved_truth = AsyncMock()
    approved_truth.get_approved_data = AsyncMock(
        return_value={
            "sku": "SKU-9",
            "name": "Boot",
            "category": "shoe",
            "description": "Durable boot for outdoor use",
        }
    )

    enriched_store = AsyncMock()
    enriched_store.upsert = AsyncMock(side_effect=lambda payload: payload)

    foundry = AsyncMock()
    foundry.enrich_complex_fields = AsyncMock(return_value={"_status": "fallback"})

    adapters = SearchEnrichmentAdapters(
        approved_truth=approved_truth,
        enriched_store=enriched_store,
        foundry=foundry,
    )

    handlers = build_event_handlers(adapters=adapters)
    handler = handlers["search-enrichment-jobs"]

    event = MagicMock()
    event.body_as_str.return_value = json.dumps(
        {"event_type": "search_enrichment_requested", "data": {"entity_id": "SKU-9"}}
    )

    await handler(MagicMock(), event)

    enriched_store.upsert.assert_awaited_once()
    liveness_events = _eventhub_liveness_events()
    assert len(liveness_events) == 1
    assert liveness_events[0]["outcome"] == "enriched"
    assert liveness_events[0]["metadata"] == {
        "surface": "eventhub",
        "trigger": "event",
        "eventhub": "search-enrichment-jobs",
        "entity_id": "SKU-9",
        "status": "enriched",
    }


@pytest.mark.asyncio
async def test_search_enrichment_event_handler_traces_missing_entity() -> None:
    approved_truth = AsyncMock()
    approved_truth.get_approved_data = AsyncMock(return_value=None)

    enriched_store = AsyncMock()
    enriched_store.upsert = AsyncMock(side_effect=lambda payload: payload)

    foundry = AsyncMock()
    foundry.enrich_complex_fields = AsyncMock(return_value={"_status": "fallback"})

    adapters = SearchEnrichmentAdapters(
        approved_truth=approved_truth,
        enriched_store=enriched_store,
        foundry=foundry,
    )

    handlers = build_event_handlers(adapters=adapters)
    handler = handlers["search-enrichment-jobs"]

    event = MagicMock()
    event.body_as_str.return_value = json.dumps(
        {"event_type": "search_enrichment_requested", "data": {}}
    )

    await handler(MagicMock(), event)

    enriched_store.upsert.assert_not_awaited()
    liveness_events = _eventhub_liveness_events()
    assert len(liveness_events) == 1
    assert liveness_events[0]["outcome"] == "missing_entity_id"
    assert liveness_events[0]["metadata"] == {
        "surface": "eventhub",
        "trigger": "event",
        "eventhub": "search-enrichment-jobs",
        "status": "skipped",
    }


@pytest.mark.asyncio
async def test_search_enrichment_event_handler_traces_error_when_orchestrator_raises() -> None:
    approved_truth = AsyncMock()
    approved_truth.get_approved_data = AsyncMock(side_effect=RuntimeError("eventhub boom"))

    enriched_store = AsyncMock()
    enriched_store.upsert = AsyncMock(side_effect=lambda payload: payload)

    foundry = AsyncMock()
    foundry.enrich_complex_fields = AsyncMock(return_value={"_status": "fallback"})

    adapters = SearchEnrichmentAdapters(
        approved_truth=approved_truth,
        enriched_store=enriched_store,
        foundry=foundry,
    )

    handlers = build_event_handlers(adapters=adapters)
    handler = handlers["search-enrichment-jobs"]

    event = MagicMock()
    event.body_as_str.return_value = json.dumps(
        {"event_type": "search_enrichment_requested", "data": {"entity_id": "SKU-9"}}
    )

    with pytest.raises(RuntimeError, match="eventhub boom"):
        await handler(MagicMock(), event)

    enriched_store.upsert.assert_not_awaited()
    liveness_events = _eventhub_liveness_events()
    assert len(liveness_events) == 1
    assert liveness_events[0]["outcome"] == "error"
    assert liveness_events[0]["metadata"] == {
        "surface": "eventhub",
        "trigger": "event",
        "eventhub": "search-enrichment-jobs",
        "entity_id": "SKU-9",
        "status": "error",
    }
