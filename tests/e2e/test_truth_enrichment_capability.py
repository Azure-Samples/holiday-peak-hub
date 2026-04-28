"""E2E tests: validate truth-enrichment agent can actually enrich products.

These tests exercise the full TruthEnrichmentAgent pipeline — gap detection,
enrichment engine (image + text merge), confidence scoring, HITL routing,
proposed attribute persistence, and the search-enrichment bridge — using
deterministic mocks for AI backends but real engine logic throughout.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from truth_enrichment.agents import TruthEnrichmentAgent, _detect_gaps

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]


# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

_PRODUCT_JACKET = {
    "entity_id": "STYLE-100",
    "name": "Explorer Jacket",
    "category": "outerwear",
    "brand": "Contoso",
    "description": "Weather-resistant commuter jacket with reflective trim.",
    "price": 129.99,
    "color": None,
    "material": None,
    "features": ["water-resistant", "reflective trim", "packable"],
}

_PRODUCT_SOFA = {
    "entity_id": "FURN-200",
    "name": "Modular Cloud Sofa",
    "category": "home_furniture",
    "brand": "HomeWorks",
    "description": "A modular sofa with deep cushions and washable covers.",
    "price": 1499.00,
    "color": "Charcoal",
    "material": None,
    "weight_kg": None,
}

_PRODUCT_COLLAR = {
    "entity_id": "PET-300",
    "name": "TrailPaws Adventure Collar",
    "category": "pet_supplies",
    "brand": "TrailPaws",
    "description": "Durable dog collar for outdoor adventures.",
    "price": 24.99,
    "color": "Hunter Green",
    "material": "Recycled Nylon",
}

_SCHEMA_OUTERWEAR = {
    "required_fields": ["color", "material"],
    "optional_fields": ["weight_kg", "care_instructions"],
    "fields": {
        "color": {"type": "string", "description": "Primary product color"},
        "material": {"type": "string", "description": "Primary fabric or material"},
    },
}

_SCHEMA_FURNITURE = {
    "required_fields": ["material", "weight_kg"],
    "optional_fields": ["dimensions"],
}

_SCHEMA_PET = {
    "required_fields": ["color", "material"],
}


def _image_response(value: str, confidence: float = 0.93) -> dict:
    return {
        "value": value,
        "confidence": confidence,
        "evidence": f"Visual analysis indicates {value}.",
        "metadata": {
            "source": "image_analysis",
            "assets": ["https://cdn.example.com/img.jpg"],
        },
    }


def _text_response(value: str, confidence: float = 0.85) -> dict:
    return {
        "value": value,
        "confidence": confidence,
        "evidence": f"Text analysis indicates {value}.",
        "metadata": {"source": "text_enrichment"},
    }


# ---------------------------------------------------------------------------
# Gap detection
# ---------------------------------------------------------------------------


def test_gap_detection_finds_missing_required_fields() -> None:
    gaps = _detect_gaps(_PRODUCT_JACKET, _SCHEMA_OUTERWEAR)
    assert "color" in gaps
    assert "material" in gaps


def test_gap_detection_returns_empty_for_complete_product() -> None:
    gaps = _detect_gaps(_PRODUCT_COLLAR, _SCHEMA_PET)
    assert gaps == []


def test_gap_detection_returns_empty_when_schema_is_none() -> None:
    gaps = _detect_gaps(_PRODUCT_JACKET, None)
    assert gaps == []


# ---------------------------------------------------------------------------
# Single-field enrichment (image-only, text-only, hybrid)
# ---------------------------------------------------------------------------


async def test_single_field_image_only_enrichment(
    agent_config_without_models,
    build_enrichment_harness,
) -> None:
    """When no model backend is available, enrichment uses image analysis only."""
    enrichment = build_enrichment_harness(
        product=_PRODUCT_JACKET,
        schema=_SCHEMA_OUTERWEAR,
        image_response=_image_response("Midnight Blue"),
    )

    with patch(
        "truth_enrichment.agents.build_enrichment_adapters",
        return_value=enrichment.adapters,
    ):
        agent = TruthEnrichmentAgent(config=agent_config_without_models)
        proposed = await agent.enrich_field(
            entity_id="STYLE-100",
            field_name="color",
            product=_PRODUCT_JACKET,
            field_definition={"type": "string", "description": "Primary product color"},
        )

    assert proposed["proposed_value"] == "Midnight Blue"
    assert proposed["source_type"] == "image_analysis"
    assert proposed["confidence"] >= 0.9
    assert proposed["field_name"] == "color"
    assert proposed["entity_id"] == "STYLE-100"
    assert proposed["status"] == "pending_review"
    assert len(enrichment.proposed_records) == 1


async def test_single_field_hybrid_enrichment(
    agent_config_with_slm,
    build_enrichment_harness,
) -> None:
    """When both image and text backends produce values, the higher-confidence one wins."""
    enrichment = build_enrichment_harness(
        product=_PRODUCT_JACKET,
        schema=_SCHEMA_OUTERWEAR,
        image_response=_image_response("Midnight Blue", confidence=0.93),
    )

    with patch(
        "truth_enrichment.agents.build_enrichment_adapters",
        return_value=enrichment.adapters,
    ):
        agent = TruthEnrichmentAgent(config=agent_config_with_slm)
        agent.invoke_model = AsyncMock(
            return_value=_text_response("Navy", confidence=0.82),
        )
        proposed = await agent.enrich_field(
            entity_id="STYLE-100",
            field_name="color",
            product=_PRODUCT_JACKET,
        )

    # Image confidence (0.93) > text confidence (0.82), so image value wins
    assert proposed["source_type"] == "hybrid"
    assert proposed["proposed_value"] == "Midnight Blue"
    assert proposed["confidence"] >= 0.9
    assert len(enrichment.proposed_records) == 1
    assert len(enrichment.audit_records) == 1


async def test_single_field_text_wins_when_higher_confidence(
    agent_config_with_slm,
    build_enrichment_harness,
) -> None:
    """When text confidence exceeds image, text value is selected."""
    enrichment = build_enrichment_harness(
        product=_PRODUCT_SOFA,
        schema=_SCHEMA_FURNITURE,
        image_response=_image_response("Polyester Blend", confidence=0.60),
    )

    with patch(
        "truth_enrichment.agents.build_enrichment_adapters",
        return_value=enrichment.adapters,
    ):
        agent = TruthEnrichmentAgent(config=agent_config_with_slm)
        agent.invoke_model = AsyncMock(
            return_value=_text_response("Performance Fabric", confidence=0.88),
        )
        proposed = await agent.enrich_field(
            entity_id="FURN-200",
            field_name="material",
            product=_PRODUCT_SOFA,
        )

    assert proposed["source_type"] == "hybrid"
    assert proposed["proposed_value"] == "Performance Fabric"
    assert proposed["confidence"] >= 0.85


# ---------------------------------------------------------------------------
# Full handle() flow — multi-field enrichment
# ---------------------------------------------------------------------------


async def test_handle_enriches_all_gaps(
    agent_config_without_models,
    build_enrichment_harness,
) -> None:
    """handle() detects all schema gaps and enriches each one."""
    enrichment = build_enrichment_harness(
        product=_PRODUCT_JACKET,
        schema=_SCHEMA_OUTERWEAR,
        image_response=_image_response("Midnight Blue"),
    )

    with patch(
        "truth_enrichment.agents.build_enrichment_adapters",
        return_value=enrichment.adapters,
    ):
        agent = TruthEnrichmentAgent(config=agent_config_without_models)
        result = await agent.handle({"entity_id": "STYLE-100"})

    assert "proposed" in result
    proposed = result["proposed"]
    # Schema has required (color, material) + optional (weight_kg, care_instructions)
    # All missing fields are enriched
    field_names = {p["field_name"] for p in proposed}
    assert {"color", "material"}.issubset(field_names)
    assert len(proposed) >= 2
    assert all(p["entity_id"] == "STYLE-100" for p in proposed)
    assert all(p["status"] == "pending_review" for p in proposed)

    # Each proposed attribute was persisted and audited
    assert len(enrichment.proposed_records) == len(proposed)
    assert len(enrichment.audit_records) == len(proposed)


async def test_handle_skips_complete_product(
    agent_config_without_models,
    build_enrichment_harness,
) -> None:
    """handle() returns no proposals when the product has no gaps."""
    enrichment = build_enrichment_harness(
        product=_PRODUCT_COLLAR,
        schema=_SCHEMA_PET,
        image_response=_image_response("Hunter Green"),
    )

    with patch(
        "truth_enrichment.agents.build_enrichment_adapters",
        return_value=enrichment.adapters,
    ):
        agent = TruthEnrichmentAgent(config=agent_config_without_models)
        result = await agent.handle({"entity_id": "PET-300"})

    assert result["proposed"] == []
    assert result["message"] == "no enrichable gaps found"
    assert len(enrichment.proposed_records) == 0


async def test_handle_returns_error_for_missing_entity(
    agent_config_without_models,
) -> None:
    """handle() returns an error when no entity_id is provided."""
    with patch("truth_enrichment.agents.build_enrichment_adapters"):
        agent = TruthEnrichmentAgent(config=agent_config_without_models)
        result = await agent.handle({})

    assert "error" in result
    assert "entity_id" in result["error"]


async def test_handle_returns_error_for_unknown_product(
    agent_config_without_models,
    build_enrichment_harness,
) -> None:
    """handle() returns product not found when adapter returns None."""
    enrichment = build_enrichment_harness(
        product=_PRODUCT_JACKET,
        schema=_SCHEMA_OUTERWEAR,
        image_response=_image_response("Blue"),
    )
    # Override the adapter to return None for this entity
    enrichment.adapters.products.get_product = AsyncMock(return_value=None)

    with patch(
        "truth_enrichment.agents.build_enrichment_adapters",
        return_value=enrichment.adapters,
    ):
        agent = TruthEnrichmentAgent(config=agent_config_without_models)
        result = await agent.handle({"entity_id": "UNKNOWN-999"})

    assert result["error"] == "product not found"


# ---------------------------------------------------------------------------
# HITL routing — every enriched attribute triggers HITL publication
# ---------------------------------------------------------------------------


async def test_enrichment_publishes_hitl_events(
    agent_config_without_models,
    build_enrichment_harness,
) -> None:
    """Each proposed attribute below auto-approve threshold triggers HITL."""
    enrichment = build_enrichment_harness(
        product=_PRODUCT_JACKET,
        schema=_SCHEMA_OUTERWEAR,
        image_response=_image_response("Midnight Blue", confidence=0.90),
    )

    with patch(
        "truth_enrichment.agents.build_enrichment_adapters",
        return_value=enrichment.adapters,
    ):
        agent = TruthEnrichmentAgent(config=agent_config_without_models)
        result = await agent.handle({"entity_id": "STYLE-100"})

    assert len(result["proposed"]) >= 2
    # Confidence 0.90 < auto-approve threshold (0.95), so HITL events fire
    assert len(enrichment.hitl_events) == len(result["proposed"])


# ---------------------------------------------------------------------------
# Search enrichment bridge
# ---------------------------------------------------------------------------


async def test_handle_triggers_search_enrichment_bridge(
    agent_config_without_models,
    build_enrichment_harness,
) -> None:
    """After enrichment, the agent publishes to the search enrichment bridge."""
    enrichment = build_enrichment_harness(
        product=_PRODUCT_JACKET,
        schema=_SCHEMA_OUTERWEAR,
        image_response=_image_response("Midnight Blue"),
    )

    bridge_events: list[dict] = []

    async def capture_bridge(payload: dict) -> None:
        bridge_events.append(payload)

    enrichment.adapters.search_enrichment_publisher = AsyncMock()
    enrichment.adapters.search_enrichment_publisher.publish = AsyncMock(side_effect=capture_bridge)

    with patch(
        "truth_enrichment.agents.build_enrichment_adapters",
        return_value=enrichment.adapters,
    ):
        agent = TruthEnrichmentAgent(config=agent_config_without_models)
        result = await agent.handle({"entity_id": "STYLE-100"})

    assert len(result["proposed"]) >= 2
    assert len(bridge_events) == 1
    assert bridge_events[0]["event_type"] == "enrichment.completed"
    assert bridge_events[0]["data"]["entity_id"] == "STYLE-100"
    assert bridge_events[0]["data"]["proposed_count"] == len(result["proposed"])


async def test_bridge_failure_does_not_break_enrichment(
    agent_config_without_models,
    build_enrichment_harness,
) -> None:
    """If the search enrichment bridge fails, handle() still returns proposed."""
    enrichment = build_enrichment_harness(
        product=_PRODUCT_JACKET,
        schema=_SCHEMA_OUTERWEAR,
        image_response=_image_response("Midnight Blue"),
    )

    enrichment.adapters.search_enrichment_publisher = AsyncMock()
    enrichment.adapters.search_enrichment_publisher.publish = AsyncMock(
        side_effect=RuntimeError("Event Hub unavailable")
    )

    with patch(
        "truth_enrichment.agents.build_enrichment_adapters",
        return_value=enrichment.adapters,
    ):
        agent = TruthEnrichmentAgent(config=agent_config_without_models)
        result = await agent.handle({"entity_id": "STYLE-100"})

    # Enrichment still succeeds despite bridge failure
    assert len(result["proposed"]) >= 2
    assert all(p["status"] == "pending_review" for p in result["proposed"])


# ---------------------------------------------------------------------------
# Confidence scoring and metadata integrity
# ---------------------------------------------------------------------------


async def test_proposed_attribute_has_complete_metadata(
    agent_config_with_slm,
    build_enrichment_harness,
) -> None:
    """Every proposed attribute contains the full metadata envelope."""
    enrichment = build_enrichment_harness(
        product=_PRODUCT_JACKET,
        schema=_SCHEMA_OUTERWEAR,
        image_response=_image_response("Midnight Blue", confidence=0.93),
    )

    with patch(
        "truth_enrichment.agents.build_enrichment_adapters",
        return_value=enrichment.adapters,
    ):
        agent = TruthEnrichmentAgent(config=agent_config_with_slm)
        agent.invoke_model = AsyncMock(
            return_value=_text_response("Navy", confidence=0.82),
        )
        proposed = await agent.enrich_field(
            entity_id="STYLE-100",
            field_name="color",
            product=_PRODUCT_JACKET,
        )

    # Required metadata fields
    assert "id" in proposed
    assert "job_id" in proposed
    assert "entity_id" in proposed
    assert "field_name" in proposed
    assert "proposed_value" in proposed
    assert "confidence" in proposed
    assert "evidence" in proposed
    assert "reasoning" in proposed
    assert "source_type" in proposed
    assert "source_assets" in proposed
    assert "original_data" in proposed
    assert "enriched_data" in proposed
    assert "status" in proposed
    assert "created_at" in proposed
    assert "confidence_metadata" in proposed

    # Confidence metadata should track both sources
    meta = proposed["confidence_metadata"]
    assert "image" in meta
    assert "text" in meta
    assert meta["image"]["confidence"] >= 0.9
    assert meta["text"]["confidence"] >= 0.8
    assert len(meta["sources_used"]) == 2


async def test_multi_category_enrichment_produces_distinct_proposals(
    agent_config_without_models,
    build_enrichment_harness,
) -> None:
    """Enriching products from different categories produces category-relevant proposals."""
    # Jacket: 2 gaps (color, material)
    enrichment_jacket = build_enrichment_harness(
        product=_PRODUCT_JACKET,
        schema=_SCHEMA_OUTERWEAR,
        image_response=_image_response("Midnight Blue"),
    )

    with patch(
        "truth_enrichment.agents.build_enrichment_adapters",
        return_value=enrichment_jacket.adapters,
    ):
        agent = TruthEnrichmentAgent(config=agent_config_without_models)
        jacket_result = await agent.handle({"entity_id": "STYLE-100"})

    # Sofa: 2 gaps (material, weight_kg)
    enrichment_sofa = build_enrichment_harness(
        product=_PRODUCT_SOFA,
        schema=_SCHEMA_FURNITURE,
        image_response=_image_response("Linen Blend"),
    )

    with patch(
        "truth_enrichment.agents.build_enrichment_adapters",
        return_value=enrichment_sofa.adapters,
    ):
        agent2 = TruthEnrichmentAgent(config=agent_config_without_models)
        sofa_result = await agent2.handle({"entity_id": "FURN-200"})

    jacket_fields = {p["field_name"] for p in jacket_result["proposed"]}
    sofa_fields = {p["field_name"] for p in sofa_result["proposed"]}

    assert {"color", "material"}.issubset(jacket_fields)
    assert {"material", "weight_kg"}.issubset(sofa_fields)
    # Each category schema produces a different gap set
    assert not jacket_fields.issubset(sofa_fields) or not sofa_fields.issubset(jacket_fields)
