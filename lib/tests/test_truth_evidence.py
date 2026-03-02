"""Unit tests for truth-layer evidence extraction (lib/truth/evidence.py)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from holiday_peak_lib.truth.evidence import (
    VALID_MODELS,
    VALID_SOURCE_TYPES,
    EnrichmentEvidence,
    EvidenceExtractor,
    ProposedAttribute,
    TenantConfig,
)


# ---------------------------------------------------------------------------
# EnrichmentEvidence
# ---------------------------------------------------------------------------


class TestEnrichmentEvidence:
    def test_minimal_creation(self):
        ev = EnrichmentEvidence(
            source_type="ai_reasoning",
            source_text="Product title contains 'waterproof'.",
            model_used="slm",
            prompt_version="v1.0",
        )
        assert ev.source_type == "ai_reasoning"
        assert ev.source_text == "Product title contains 'waterproof'."
        assert ev.model_used == "slm"
        assert ev.prompt_version == "v1.0"
        assert ev.confidence_factors == []

    def test_confidence_factors_populated(self):
        ev = EnrichmentEvidence(
            source_type="product_context",
            source_text="Category is 'Outdoor Gear'.",
            confidence_factors=["keyword match", "category alignment"],
            model_used="llm",
            prompt_version="v2.1",
        )
        assert "keyword match" in ev.confidence_factors
        assert len(ev.confidence_factors) == 2

    def test_extracted_at_defaults_to_utc(self):
        ev = EnrichmentEvidence(
            source_type="ai_reasoning",
            source_text="Some reasoning.",
            model_used="slm",
            prompt_version="v1.0",
        )
        assert ev.extracted_at.tzinfo is not None
        assert ev.extracted_at.tzinfo == timezone.utc

    def test_all_valid_source_types(self):
        for source_type in VALID_SOURCE_TYPES:
            ev = EnrichmentEvidence(
                source_type=source_type,
                source_text="Some text.",
                model_used="slm",
                prompt_version="v1.0",
            )
            assert ev.source_type == source_type

    def test_serialisation(self):
        ev = EnrichmentEvidence(
            source_type="image_analysis",
            source_text="Image shows red colour.",
            confidence_factors=["visual match"],
            model_used="llm",
            prompt_version="v3.0",
        )
        data = ev.model_dump()
        assert data["source_type"] == "image_analysis"
        assert "extracted_at" in data


# ---------------------------------------------------------------------------
# ProposedAttribute
# ---------------------------------------------------------------------------


class TestProposedAttribute:
    def test_minimal_creation(self):
        attr = ProposedAttribute(
            entity_id="prod-001",
            attribute_name="waterproof",
            proposed_value=True,
            confidence=0.92,
            source="slm",
        )
        assert attr.entity_id == "prod-001"
        assert attr.evidence == []
        assert attr.status == "pending"

    def test_id_auto_generated(self):
        a = ProposedAttribute(
            entity_id="e1", attribute_name="color", proposed_value="red", confidence=0.8, source="slm"
        )
        b = ProposedAttribute(
            entity_id="e2", attribute_name="color", proposed_value="blue", confidence=0.8, source="slm"
        )
        assert a.id != b.id

    def test_evidence_attached(self):
        ev = EnrichmentEvidence(
            source_type="ai_reasoning",
            source_text="Title says 'red'.",
            model_used="slm",
            prompt_version="v1.0",
        )
        attr = ProposedAttribute(
            entity_id="p1",
            attribute_name="color",
            proposed_value="red",
            confidence=0.95,
            source="slm",
            evidence=[ev],
        )
        assert len(attr.evidence) == 1
        assert attr.evidence[0].source_type == "ai_reasoning"

    def test_confidence_bounds(self):
        with pytest.raises(Exception):
            ProposedAttribute(
                entity_id="p1",
                attribute_name="x",
                proposed_value="y",
                confidence=1.5,
                source="slm",
            )
        with pytest.raises(Exception):
            ProposedAttribute(
                entity_id="p1",
                attribute_name="x",
                proposed_value="y",
                confidence=-0.1,
                source="slm",
            )

    def test_status_default(self):
        attr = ProposedAttribute(
            entity_id="e1", attribute_name="size", proposed_value="L", confidence=0.7, source="llm"
        )
        assert attr.status == "pending"


# ---------------------------------------------------------------------------
# TenantConfig
# ---------------------------------------------------------------------------


class TestTenantConfig:
    def test_defaults(self):
        cfg = TenantConfig(tenant_id="t-001")
        assert cfg.tenant_id == "t-001"
        assert cfg.evidence_extraction_enabled is False
        assert cfg.auto_approve_threshold is None

    def test_enable_evidence_extraction(self):
        cfg = TenantConfig(tenant_id="t-002", evidence_extraction_enabled=True)
        assert cfg.evidence_extraction_enabled is True

    def test_auto_approve_threshold_bounds(self):
        cfg = TenantConfig(tenant_id="t-003", auto_approve_threshold=0.95)
        assert cfg.auto_approve_threshold == 0.95

        with pytest.raises(Exception):
            TenantConfig(tenant_id="t-bad", auto_approve_threshold=1.5)

        with pytest.raises(Exception):
            TenantConfig(tenant_id="t-bad", auto_approve_threshold=-0.1)

    def test_missing_tenant_id_raises(self):
        with pytest.raises(Exception):
            TenantConfig()  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# EvidenceExtractor
# ---------------------------------------------------------------------------


class TestEvidenceExtractor:
    def test_invalid_model_raises(self):
        with pytest.raises(ValueError, match="model_used must be one of"):
            EvidenceExtractor(model_used="unknown")

    def test_valid_models(self):
        for model in VALID_MODELS:
            extractor = EvidenceExtractor(model_used=model, prompt_version="v1.0")
            assert extractor.model_used == model

    def test_extract_empty_output(self):
        extractor = EvidenceExtractor(model_used="slm", prompt_version="v1.0")
        result = extractor.extract({})
        assert result == []

    def test_extract_no_evidence_key(self):
        extractor = EvidenceExtractor(model_used="llm", prompt_version="v2.0")
        result = extractor.extract({"answer": "red", "reasoning": "title says red"})
        assert result == []

    def test_extract_parses_evidence_list(self):
        extractor = EvidenceExtractor(model_used="slm", prompt_version="v1.0")
        output = {
            "evidence": [
                {
                    "source_type": "ai_reasoning",
                    "source_text": "Title contains 'waterproof'.",
                    "confidence_factors": ["keyword match"],
                },
                {
                    "source_type": "product_context",
                    "source_text": "Category is Outdoor Gear.",
                    "confidence_factors": ["category alignment", "brand history"],
                },
            ]
        }
        result = extractor.extract(output)
        assert len(result) == 2
        assert result[0].source_type == "ai_reasoning"
        assert result[0].model_used == "slm"
        assert result[0].prompt_version == "v1.0"
        assert "keyword match" in result[0].confidence_factors
        assert result[1].source_type == "product_context"

    def test_extract_skips_items_without_source_text(self):
        extractor = EvidenceExtractor(model_used="slm", prompt_version="v1.0")
        output = {
            "evidence": [
                {"source_type": "ai_reasoning"},  # missing source_text → skip
                {"source_type": "ai_reasoning", "source_text": "Valid text."},
            ]
        }
        result = extractor.extract(output)
        assert len(result) == 1
        assert result[0].source_text == "Valid text."

    def test_extract_skips_non_dict_items(self):
        extractor = EvidenceExtractor(model_used="slm", prompt_version="v1.0")
        output = {"evidence": ["not a dict", 42, None]}
        result = extractor.extract(output)
        assert result == []

    def test_extract_falls_back_on_invalid_source_type(self):
        extractor = EvidenceExtractor(model_used="llm", prompt_version="v1.0")
        output = {
            "evidence": [
                {"source_type": "unknown_type", "source_text": "Some reasoning."},
            ]
        }
        result = extractor.extract(output)
        assert len(result) == 1
        assert result[0].source_type == "ai_reasoning"  # fallback

    def test_extract_non_list_evidence_returns_empty(self):
        extractor = EvidenceExtractor(model_used="slm", prompt_version="v1.0")
        result = extractor.extract({"evidence": "not a list"})
        assert result == []

    def test_attach_evidence(self):
        extractor = EvidenceExtractor(model_used="slm", prompt_version="v1.0")
        proposed = ProposedAttribute(
            entity_id="p1",
            attribute_name="color",
            proposed_value="blue",
            confidence=0.88,
            source="slm",
        )
        output = {
            "evidence": [
                {
                    "source_type": "product_context",
                    "source_text": "Product description says 'navy blue'.",
                    "confidence_factors": ["direct mention"],
                }
            ]
        }
        result = extractor.attach_evidence(proposed, output)
        assert result is proposed
        assert len(proposed.evidence) == 1
        assert proposed.evidence[0].source_type == "product_context"

    def test_attach_evidence_clears_existing(self):
        extractor = EvidenceExtractor(model_used="slm", prompt_version="v1.0")
        ev = EnrichmentEvidence(
            source_type="ai_reasoning",
            source_text="Old evidence.",
            model_used="slm",
            prompt_version="v0.1",
        )
        proposed = ProposedAttribute(
            entity_id="p2",
            attribute_name="size",
            proposed_value="M",
            confidence=0.75,
            source="slm",
            evidence=[ev],
        )
        extractor.attach_evidence(proposed, {})  # empty → clears
        assert proposed.evidence == []


# ---------------------------------------------------------------------------
# Integration: TenantConfig toggle
# ---------------------------------------------------------------------------


class TestEvidenceToggle:
    """Verify the toggle pattern: extractor only runs when config says so."""

    def _enrich_with_toggle(
        self,
        config: TenantConfig,
        model_output: dict,
    ) -> ProposedAttribute:
        proposed = ProposedAttribute(
            entity_id="p1",
            attribute_name="material",
            proposed_value="cotton",
            confidence=0.9,
            source="slm",
        )
        if config.evidence_extraction_enabled:
            extractor = EvidenceExtractor(model_used="slm", prompt_version="v1.0")
            extractor.attach_evidence(proposed, model_output)
        return proposed

    def test_toggle_off_no_evidence(self):
        cfg = TenantConfig(tenant_id="t-off")
        output = {
            "evidence": [{"source_type": "ai_reasoning", "source_text": "Some text."}]
        }
        result = self._enrich_with_toggle(cfg, output)
        assert result.evidence == []

    def test_toggle_on_evidence_captured(self):
        cfg = TenantConfig(tenant_id="t-on", evidence_extraction_enabled=True)
        output = {
            "evidence": [{"source_type": "ai_reasoning", "source_text": "Some text."}]
        }
        result = self._enrich_with_toggle(cfg, output)
        assert len(result.evidence) == 1
