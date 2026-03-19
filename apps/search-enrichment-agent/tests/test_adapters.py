"""Unit tests for search enrichment adapters."""

from __future__ import annotations

import pytest
from holiday_peak_lib.schemas.truth import SearchEnrichedProduct, SourceType
from search_enrichment_agent.adapters import (
    ApprovedTruthAdapter,
    FoundryEnrichmentAdapter,
    SearchEnrichedStoreAdapter,
)


@pytest.mark.asyncio
async def test_approved_truth_adapter_returns_seeded_data() -> None:
    adapter = ApprovedTruthAdapter(seeded_truth={"SKU-1": {"sku": "SKU-1", "name": "Demo"}})

    data = await adapter.get_approved_data("SKU-1")

    assert data is not None
    assert data["name"] == "Demo"


@pytest.mark.asyncio
async def test_foundry_adapter_graceful_fallback_on_error() -> None:
    adapter = FoundryEnrichmentAdapter()

    async def failing_invoker(*, request, messages):  # noqa: ANN001
        raise RuntimeError("foundry down")

    adapter.set_model_invoker(failing_invoker)

    result = await adapter.enrich_complex_fields(entity_id="SKU-2", approved_truth={"sku": "SKU-2"})

    assert result["_status"] == "fallback"
    assert result["_reason"] == "foundry_unavailable"


@pytest.mark.asyncio
async def test_search_enriched_store_upsert_and_status() -> None:
    store = SearchEnrichedStoreAdapter()
    model = SearchEnrichedProduct(
        sku="SKU-3",
        score=0.8,
        sourceType=SourceType.AI_REASONING,
        originalData={"sku": "SKU-3"},
        enrichedData={"search_keywords": ["demo"]},
        intentClassification=None,
    )

    stored = await store.upsert(model)
    status = await store.get_status("SKU-3")

    assert stored["id"] == "SKU-3"
    assert status["status"] == "upserted"
    assert status["container"] == "search_enriched_products"
