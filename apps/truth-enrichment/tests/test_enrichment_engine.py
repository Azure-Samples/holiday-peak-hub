"""Unit tests for the enrichment engine."""

from __future__ import annotations

import pytest
from truth_enrichment.enrichment_engine import EnrichmentEngine


@pytest.fixture()
def engine():
    return EnrichmentEngine(auto_approve_threshold=0.95)


def test_build_prompt_returns_two_messages(engine):
    product = {"id": "p1", "name": "Widget", "category": "tools"}
    messages = engine.build_prompt(product, "color")
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"


def test_build_vision_prompt_uses_image_url_content_parts(engine):
    messages = engine.build_vision_prompt(
        product={"id": "p1", "name": "Widget"},
        field_name="material",
        field_definition={"type": "string", "description": "Fabric composition"},
        image_urls=["https://cdn.example.com/a.jpg", "https://cdn.example.com/b.jpg"],
    )

    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    content = messages[1]["content"]
    assert isinstance(content, list)
    assert content[0]["type"] == "text"
    assert content[1] == {
        "type": "image_url",
        "image_url": {"url": "https://cdn.example.com/a.jpg"},
    }
    assert content[2] == {
        "type": "image_url",
        "image_url": {"url": "https://cdn.example.com/b.jpg"},
    }


def test_parse_ai_response_dict(engine):
    raw = {
        "value": "red",
        "confidence": 0.9,
        "evidence": "product description mentions red",
        "metadata": {"source": "image_analysis"},
    }
    parsed = engine.parse_ai_response(raw)
    assert parsed["value"] == "red"
    assert parsed["confidence"] == 0.9
    assert parsed["metadata"]["source"] == "image_analysis"


def test_parse_ai_response_fallback(engine):
    parsed = engine.parse_ai_response("just a string")
    assert parsed["value"] == "just a string"
    assert parsed["confidence"] == 0.4


def test_score_confidence_clamps(engine):
    assert engine.score_confidence({"confidence": -0.5}) == 0.0
    assert engine.score_confidence({"confidence": 1.5}) == 1.0
    assert engine.score_confidence({"confidence": 0.7}) == pytest.approx(0.7)


def test_build_proposed_attribute_auto_approve(engine):
    parsed = {
        "value": "blue",
        "confidence": 0.97,
        "evidence": "high confidence",
        "reasoning": "hybrid merge selected image value",
        "source_type": "hybrid",
        "source_assets": ["https://cdn.example.com/a.jpg"],
        "original_data": {"color": None},
        "enriched_data": {"color": "blue"},
        "metadata": {"source": "image_analysis", "assets_count": 2},
    }
    proposed = engine.build_proposed_attribute("sku-1", "color", parsed, model_id="gpt-5")
    assert proposed["status"] == "auto_approved"
    assert proposed["entity_id"] == "sku-1"
    assert proposed["field_name"] == "color"
    assert proposed["source_model"] == "gpt-5"
    assert proposed["source_type"] == "hybrid"
    assert proposed["source_assets"] == ["https://cdn.example.com/a.jpg"]
    assert proposed["original_data"] == {"color": None}
    assert proposed["enriched_data"] == {"color": "blue"}
    assert proposed["reasoning"] == "hybrid merge selected image value"
    assert proposed["confidence_metadata"]["source"] == "image_analysis"


def test_build_proposed_attribute_pending(engine):
    parsed = {"value": "blue", "confidence": 0.7, "evidence": "medium confidence"}
    proposed = engine.build_proposed_attribute("sku-2", "color", parsed)
    assert proposed["status"] == "pending"
    assert proposed["source_type"] == "text_enrichment"
    assert proposed["source_assets"] == []
    assert proposed["original_data"] == {"color": None}
    assert proposed["enriched_data"] == {"color": "blue"}


def test_merge_enrichment_candidates_hybrid(engine):
    merged = engine.merge_enrichment_candidates(
        field_name="material",
        original_data={"material": None},
        image_parsed={
            "value": "cotton",
            "confidence": 0.91,
            "evidence": "image texture",
            "metadata": {"assets": ["https://cdn.example.com/a.jpg"]},
        },
        text_parsed={
            "value": "cotton blend",
            "confidence": 0.82,
            "evidence": "title suggests blend",
            "metadata": {"source": "text_enrichment"},
        },
    )

    assert merged["source_type"] == "hybrid"
    assert merged["value"] == "cotton"
    assert merged["source_assets"] == ["https://cdn.example.com/a.jpg"]
    assert merged["original_data"] == {"material": None}
    assert merged["enriched_data"] == {"material": "cotton"}
    assert merged["metadata"]["sources_used"] == ["image_analysis", "text_enrichment"]


def test_merge_enrichment_candidates_text_only(engine):
    merged = engine.merge_enrichment_candidates(
        field_name="pattern",
        original_data={"pattern": None},
        image_parsed={
            "value": None,
            "confidence": 0.0,
            "evidence": "no usable image",
            "metadata": {"fallback_reason": "no_assets"},
        },
        text_parsed={
            "value": "striped",
            "confidence": 0.78,
            "evidence": "description mentions striped",
            "metadata": {"source": "text_enrichment"},
        },
    )

    assert merged["source_type"] == "text_enrichment"
    assert merged["value"] == "striped"
    assert merged["source_assets"] == []
    assert merged["enriched_data"] == {"pattern": "striped"}


def test_needs_hitl_pending(engine):
    proposed = {"status": "pending"}
    assert engine.needs_hitl(proposed) is True


def test_needs_hitl_auto_approved(engine):
    proposed = {"status": "auto_approved"}
    assert engine.needs_hitl(proposed) is False


def test_build_audit_event(engine):
    proposed = {
        "id": "attr-1",
        "entity_id": "sku-1",
        "field_name": "color",
        "confidence": 0.9,
        "status": "pending",
    }
    event = engine.build_audit_event("enrichment_proposed", "sku-1", "color", proposed)
    assert event["action"] == "enrichment_proposed"
    assert event["entity_id"] == "sku-1"
    assert event["field_name"] == "color"
    assert event["proposed_attribute_id"] == "attr-1"
    assert "timestamp" in event
