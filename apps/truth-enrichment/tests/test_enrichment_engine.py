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


def test_parse_ai_response_dict(engine):
    raw = {"value": "red", "confidence": 0.9, "evidence": "product description mentions red"}
    parsed = engine.parse_ai_response(raw)
    assert parsed["value"] == "red"
    assert parsed["confidence"] == 0.9


def test_parse_ai_response_fallback(engine):
    parsed = engine.parse_ai_response("just a string")
    assert parsed["value"] == "just a string"
    assert parsed["confidence"] == 0.4


def test_score_confidence_clamps(engine):
    assert engine.score_confidence({"confidence": -0.5}) == 0.0
    assert engine.score_confidence({"confidence": 1.5}) == 1.0
    assert engine.score_confidence({"confidence": 0.7}) == pytest.approx(0.7)


def test_build_proposed_attribute_auto_approve(engine):
    parsed = {"value": "blue", "confidence": 0.97, "evidence": "high confidence"}
    proposed = engine.build_proposed_attribute("sku-1", "color", parsed, model_id="gpt-5")
    assert proposed["status"] == "auto_approved"
    assert proposed["entity_id"] == "sku-1"
    assert proposed["field_name"] == "color"
    assert proposed["source_model"] == "gpt-5"


def test_build_proposed_attribute_pending(engine):
    parsed = {"value": "blue", "confidence": 0.7, "evidence": "medium confidence"}
    proposed = engine.build_proposed_attribute("sku-2", "color", parsed)
    assert proposed["status"] == "pending"


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
