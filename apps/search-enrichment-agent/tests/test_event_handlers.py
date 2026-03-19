"""Unit and integration-like tests for search enrichment event handlers."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from search_enrichment_agent.adapters import SearchEnrichmentAdapters
from search_enrichment_agent.event_handlers import build_event_handlers


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
