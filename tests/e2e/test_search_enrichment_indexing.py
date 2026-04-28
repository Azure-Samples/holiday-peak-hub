"""E2E tests: search enrichment pipeline populates AI Search.

Validates the flow from approved truth data through the search enrichment
orchestrator to AI Search index population — both immediate-push and
indexer-trigger modes.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from search_enrichment_agent.agents import SearchEnrichmentAgent, SearchEnrichmentOrchestrator
from search_enrichment_agent.enrichment_engine import SearchEnrichmentEngine
from search_enrichment_agent.event_handlers import build_event_handlers

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]


# ---------------------------------------------------------------------------
# Approved-truth fixtures (simulating data that came through truth-enrichment)
# ---------------------------------------------------------------------------

_APPROVED_JACKET = {
    "sku": "STYLE-100",
    "name": "Explorer Jacket",
    "brand": "Contoso",
    "category": "outerwear",
    "description": "Weather-resistant commuter jacket with reflective trim.",
    "price": 129.99,
    "color": "Midnight Blue",
    "material": "Recycled Nylon",
    "features": ["water-resistant", "reflective trim", "packable"],
}

_APPROVED_SOFA = {
    "sku": "FURN-200",
    "name": "Metro Sectional Sofa",
    "brand": "UrbanLiving",
    "category": "home_furniture",
    "description": (
        "Modern L-shaped sectional sofa in performance linen. "
        "Features removable cushion covers, solid hardwood frame, "
        "and modular configuration for apartments and open-plan living spaces. "
        "Available in three neutral tones."
    ),
    "price": 1899.00,
    "material": "Performance Linen",
    "features": [
        "removable covers",
        "modular",
        "hardwood frame",
        "apartment-friendly",
    ],
}

_APPROVED_COLLAR = {
    "sku": "PET-300",
    "name": "Adventure Dog Collar",
    "brand": "TrailPaws",
    "category": "pet_supplies",
    "description": "Adjustable reflective dog collar for outdoor walks.",
    "price": 24.99,
}


def _all_approved_truth() -> dict[str, dict[str, Any]]:
    return {
        "STYLE-100": _APPROVED_JACKET,
        "FURN-200": _APPROVED_SOFA,
        "PET-300": _APPROVED_COLLAR,
    }


# ---------------------------------------------------------------------------
# Test: Full pipeline — orchestrator enriches and pushes to AI Search (immediate)
# ---------------------------------------------------------------------------


async def test_orchestrator_enriches_and_indexes_immediate_push(
    build_search_enrichment_harness,
) -> None:
    """Approved truth → orchestrator → enriched store + AI Search push."""
    harness = build_search_enrichment_harness(
        approved_truth=_all_approved_truth(),
        push_immediate=True,
    )
    engine = SearchEnrichmentEngine()
    orchestrator = SearchEnrichmentOrchestrator(harness.adapters, engine)

    result = await orchestrator.run(
        entity_id="STYLE-100",
        has_model_backend=False,
        trigger="test",
    )

    # Orchestrator returns enriched status
    assert result["status"] == "enriched"
    assert result["entity_id"] == "STYLE-100"
    assert result["strategy"] == "simple"

    # Enriched product is in the store
    store_status = await harness.enriched_store.get_status("STYLE-100")
    assert store_status["status"] == "upserted"

    # Document was pushed to AI Search index
    assert len(harness.indexed_documents) == 1
    doc = harness.indexed_documents[0]
    assert doc["index"] == "product_search_index"
    assert doc["sku"] == "STYLE-100"

    # Enriched fields are populated (in enrichedData dict)
    enriched = result["enriched"]
    enriched_data = enriched["enrichedData"]
    assert len(enriched_data["use_cases"]) > 0
    assert len(enriched_data["search_keywords"]) > 0
    assert enriched_data["enriched_description"]
    assert "Explorer Jacket" in enriched_data["enriched_description"]

    # Indexing response is successful
    assert result["indexing"]["status"] == "ok"
    assert result["indexing"]["operation"] == "index_documents"


async def test_orchestrator_indexes_via_indexer_trigger(
    build_search_enrichment_harness,
) -> None:
    """When AI_SEARCH_PUSH_IMMEDIATE is off, the orchestrator triggers the indexer."""
    harness = build_search_enrichment_harness(
        approved_truth=_all_approved_truth(),
        push_immediate=False,
    )
    engine = SearchEnrichmentEngine()
    orchestrator = SearchEnrichmentOrchestrator(harness.adapters, engine)

    result = await orchestrator.run(
        entity_id="FURN-200",
        has_model_backend=False,
        trigger="test",
    )

    assert result["status"] == "enriched"
    # No direct push — document not in indexed_documents
    assert len(harness.indexed_documents) == 0
    # Indexer was triggered instead
    assert len(harness.indexer_runs) == 1
    assert harness.indexer_runs[0] == "product-search-indexer"


# ---------------------------------------------------------------------------
# Test: Multi-product batch enrichment → AI Search receives all
# ---------------------------------------------------------------------------


async def test_batch_enrichment_populates_search_index(
    build_search_enrichment_harness,
) -> None:
    """Multiple products enriched sequentially all appear in AI Search."""
    harness = build_search_enrichment_harness(
        approved_truth=_all_approved_truth(),
        push_immediate=True,
    )
    engine = SearchEnrichmentEngine()
    orchestrator = SearchEnrichmentOrchestrator(harness.adapters, engine)

    skus = ["STYLE-100", "FURN-200", "PET-300"]
    results = []
    for sku in skus:
        r = await orchestrator.run(
            entity_id=sku,
            has_model_backend=False,
            trigger="batch-test",
        )
        results.append(r)

    # All 3 enriched
    assert all(r["status"] == "enriched" for r in results)

    # All 3 pushed to AI Search
    assert len(harness.indexed_documents) == 3
    indexed_skus = {doc["sku"] for doc in harness.indexed_documents}
    assert indexed_skus == {"STYLE-100", "FURN-200", "PET-300"}

    # Each has proper enriched fields (in enrichedData dict)
    for r in results:
        enriched_data = r["enriched"]["enrichedData"]
        assert len(enriched_data["use_cases"]) > 0
        assert len(enriched_data["search_keywords"]) > 0
        assert enriched_data["enriched_description"]


# ---------------------------------------------------------------------------
# Test: Complex product triggers complex strategy when model available
# ---------------------------------------------------------------------------


async def test_complex_product_uses_complex_strategy_with_model(
    build_search_enrichment_harness,
) -> None:
    """Sofa (long description + 4 features) uses complex strategy if model available."""
    harness = build_search_enrichment_harness(
        approved_truth=_all_approved_truth(),
        push_immediate=True,
    )

    # Verify the engine detects complexity
    engine = SearchEnrichmentEngine()
    assert engine.is_complex(_APPROVED_SOFA) is True
    assert engine.is_complex(_APPROVED_COLLAR) is False

    # With model backend, the orchestrator attempts agentic/complex strategy
    # but our mock foundry adapter has no invoker, so it degrades to simple
    orchestrator = SearchEnrichmentOrchestrator(harness.adapters, engine)
    result = await orchestrator.run(
        entity_id="FURN-200",
        has_model_backend=True,
        trigger="test",
    )

    # Graceful degradation — fell back to simple since no model invoker
    assert result["status"] == "enriched"
    assert result["strategy"] == "simple"
    assert result["graceful_degradation"] is True

    # Product still indexed despite degradation
    assert len(harness.indexed_documents) == 1
    doc = harness.indexed_documents[0]
    assert doc["sku"] == "FURN-200"


# ---------------------------------------------------------------------------
# Test: Event Hub triggers search enrichment → AI Search
# ---------------------------------------------------------------------------


async def test_event_hub_triggers_enrichment_and_indexing(
    build_search_enrichment_harness,
    make_event,
) -> None:
    """search-enrichment-jobs Event Hub event flows through to AI Search index."""
    harness = build_search_enrichment_harness(
        approved_truth=_all_approved_truth(),
        push_immediate=True,
    )
    engine = SearchEnrichmentEngine()

    handlers = build_event_handlers(adapters=harness.adapters, engine=engine)
    handler = handlers["search-enrichment-jobs"]

    event = make_event({
        "event_type": "enrichment.completed",
        "source": "truth-enrichment",
        "data": {"entity_id": "STYLE-100"},
    })

    await handler(None, event)

    # Document was pushed to AI Search
    assert len(harness.indexed_documents) == 1
    doc = harness.indexed_documents[0]
    assert doc["sku"] == "STYLE-100"
    assert doc["index"] == "product_search_index"


async def test_event_hub_batch_events_populate_index(
    build_search_enrichment_harness,
    make_event,
) -> None:
    """Multiple Event Hub events sequentially populate the search index."""
    harness = build_search_enrichment_harness(
        approved_truth=_all_approved_truth(),
        push_immediate=True,
    )
    engine = SearchEnrichmentEngine()
    handlers = build_event_handlers(adapters=harness.adapters, engine=engine)
    handler = handlers["search-enrichment-jobs"]

    for sku in ["STYLE-100", "FURN-200", "PET-300"]:
        event = make_event({
            "event_type": "enrichment.completed",
            "source": "truth-enrichment",
            "data": {"entity_id": sku},
        })
        await handler(None, event)

    assert len(harness.indexed_documents) == 3
    indexed_skus = {doc["sku"] for doc in harness.indexed_documents}
    assert indexed_skus == {"STYLE-100", "FURN-200", "PET-300"}


# ---------------------------------------------------------------------------
# Test: Missing approved truth → not_found, nothing indexed
# ---------------------------------------------------------------------------


async def test_missing_approved_truth_skips_indexing(
    build_search_enrichment_harness,
) -> None:
    """Entity with no approved truth returns not_found, no indexing occurs."""
    harness = build_search_enrichment_harness(
        approved_truth=_all_approved_truth(),
        push_immediate=True,
    )
    engine = SearchEnrichmentEngine()
    orchestrator = SearchEnrichmentOrchestrator(harness.adapters, engine)

    result = await orchestrator.run(
        entity_id="UNKNOWN-999",
        has_model_backend=False,
        trigger="test",
    )

    assert result["status"] == "not_found"
    assert len(harness.indexed_documents) == 0


# ---------------------------------------------------------------------------
# Test: AI Search not configured → enrichment still succeeds, indexing skipped
# ---------------------------------------------------------------------------


async def test_enrichment_succeeds_when_ai_search_not_configured(
    build_search_enrichment_harness,
) -> None:
    """When search_indexing is None, enrichment completes and indexing is skipped."""
    harness = build_search_enrichment_harness(
        approved_truth=_all_approved_truth(),
        push_immediate=True,
    )
    # Remove search indexing adapter to simulate unconfigured AI Search
    harness.adapters.search_indexing = None

    engine = SearchEnrichmentEngine()
    orchestrator = SearchEnrichmentOrchestrator(harness.adapters, engine)

    result = await orchestrator.run(
        entity_id="STYLE-100",
        has_model_backend=False,
        trigger="test",
    )

    assert result["status"] == "enriched"
    assert result["indexing"]["status"] == "skipped"
    assert result["indexing"]["reason"] == "ai_search_not_configured"

    # Product is still in the enriched store
    store_status = await harness.enriched_store.get_status("STYLE-100")
    assert store_status["status"] == "upserted"


# ---------------------------------------------------------------------------
# Test: Enriched document fields match AI Search schema expectations
# ---------------------------------------------------------------------------


async def test_indexed_document_contains_search_schema_fields(
    build_search_enrichment_harness,
) -> None:
    """Indexed document contains all fields expected by the AI Search index schema."""
    harness = build_search_enrichment_harness(
        approved_truth=_all_approved_truth(),
        push_immediate=True,
    )
    engine = SearchEnrichmentEngine()
    orchestrator = SearchEnrichmentOrchestrator(harness.adapters, engine)

    await orchestrator.run(
        entity_id="STYLE-100",
        has_model_backend=False,
        trigger="test",
    )

    assert len(harness.indexed_documents) == 1
    doc = harness.indexed_documents[0]

    # Core identity fields required by AI Search
    assert doc["id"] == "STYLE-100"
    assert doc["sku"] == "STYLE-100"

    # enrichedData contains the actual search enrichment fields
    enriched_data = doc["enrichedData"]
    assert len(enriched_data["use_cases"]) > 0
    assert len(enriched_data["search_keywords"]) > 0
    assert enriched_data["enriched_description"]
    assert "complementary_products" in enriched_data
    assert "substitute_products" in enriched_data

    # Amplification dimensions in enrichedData
    assert "marketing_bullets" in enriched_data
    assert "facet_tags" in enriched_data

    # Metadata at document level
    assert "enrichedAt" in doc
    assert "score" in doc
    assert "sourceType" in doc
    assert "originalData" in doc
    assert "enrichedData" in doc


# ---------------------------------------------------------------------------
# Test: Full pipeline — ingest → enrich → search-enrich → index
# ---------------------------------------------------------------------------


async def test_end_to_end_ingest_enrich_to_search_index(
    agent_config_with_slm,
    build_ingestion_harness,
    build_enrichment_harness,
    build_search_enrichment_harness,
    raw_product_payload,
    make_event,
) -> None:
    """Full pipeline: ingest product → truth-enrich → search-enrich → AI Search."""
    from truth_enrichment.agents import TruthEnrichmentAgent
    from truth_ingestion.adapters import ingest_single_product

    # Step 1: Ingest
    ingestion = build_ingestion_harness(
        dam_assets=[{"url": "https://cdn.example.com/style-100-front.jpg"}]
    )
    ingested = await ingest_single_product(raw_product_payload, ingestion.adapters)
    assert ingested["entity_id"] == "STYLE-100"

    # Step 2: Truth enrichment (simulate agent enriching the product)
    style_record = dict(ingested["style"])
    style_record["color"] = None

    enrichment = build_enrichment_harness(
        product=style_record,
        schema={"required_fields": ["color"]},
        image_response={
            "value": "Midnight Blue",
            "confidence": 0.93,
            "evidence": "Dominant color from product imagery.",
            "metadata": {
                "source": "image_analysis",
                "assets": ["https://cdn.example.com/style-100-front.jpg"],
            },
        },
    )

    with patch("truth_enrichment.agents.build_enrichment_adapters", return_value=enrichment.adapters):
        agent = TruthEnrichmentAgent(config=agent_config_with_slm)
        agent.invoke_model = AsyncMock(
            return_value={
                "value": "Navy",
                "confidence": 0.82,
                "evidence": "Description and title indicate navy tone.",
                "metadata": {"source": "text_enrichment"},
            }
        )
        enrich_result = await agent.handle({"entity_id": style_record["entity_id"]})

    assert enrich_result["proposed"][0]["proposed_value"] in ("Midnight Blue", "Navy")

    # Step 3: Build approved truth from enrichment result (simulate auto-approve)
    proposed = enrich_result["proposed"][0]
    approved_data = dict(style_record)
    approved_data[proposed["field_name"]] = proposed["proposed_value"]
    approved_data["name"] = raw_product_payload["name"]
    approved_data["brand"] = raw_product_payload["brand"]
    approved_data["category"] = raw_product_payload["category"]
    approved_data["description"] = raw_product_payload["description"]

    # Step 4: Search enrichment → AI Search index
    search_harness = build_search_enrichment_harness(
        approved_truth={style_record["entity_id"]: approved_data},
        push_immediate=True,
    )
    engine = SearchEnrichmentEngine()
    handlers = build_event_handlers(adapters=search_harness.adapters, engine=engine)

    event = make_event({
        "event_type": "enrichment.completed",
        "source": "truth-enrichment",
        "data": {"entity_id": style_record["entity_id"]},
    })
    await handlers["search-enrichment-jobs"](None, event)

    # Verify: product is in AI Search index
    assert len(search_harness.indexed_documents) == 1
    doc = search_harness.indexed_documents[0]
    assert doc["sku"] == "STYLE-100"
    assert doc["index"] == "product_search_index"
    enriched_data = doc["enrichedData"]
    assert len(enriched_data["use_cases"]) > 0
    assert len(enriched_data["search_keywords"]) > 0
    assert enriched_data["enriched_description"]


# ---------------------------------------------------------------------------
# Test: Enrichment fields are category-aware
# ---------------------------------------------------------------------------


async def test_enriched_fields_are_category_aware(
    build_search_enrichment_harness,
) -> None:
    """use_cases and keywords reflect the product category context."""
    harness = build_search_enrichment_harness(
        approved_truth=_all_approved_truth(),
        push_immediate=True,
    )
    engine = SearchEnrichmentEngine()
    orchestrator = SearchEnrichmentOrchestrator(harness.adapters, engine)

    # Enrich the pet collar
    result = await orchestrator.run(
        entity_id="PET-300",
        has_model_backend=False,
        trigger="test",
    )

    enriched_data = result["enriched"]["enrichedData"]
    keywords_lower = [k.lower() for k in enriched_data["search_keywords"]]
    description_lower = (enriched_data.get("enriched_description") or "").lower()

    # Keywords or description should reflect the pet/collar context
    has_pet_context = any(
        term in " ".join(keywords_lower) or term in description_lower
        for term in ["pet", "dog", "collar", "adventure", "trailpaws"]
    )
    assert has_pet_context, (
        f"Expected pet/collar context in keywords or description. "
        f"Keywords: {enriched_data['search_keywords']}, Description: {enriched_data['enriched_description']}"
    )
