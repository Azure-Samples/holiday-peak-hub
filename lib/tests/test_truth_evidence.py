"""Unit tests for truth-layer evidence extraction (lib/truth/evidence.py)."""

from __future__ import annotations

from datetime import timezone

import pytest
from holiday_peak_lib.truth.evidence import (
    VALID_MODELS,
    VALID_SOURCE_TYPES,
    EnrichmentEvidence,
    EvidenceConfig,
    EvidenceExtractor,
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

    def test_id_and_entity_id_default_to_empty_string(self):
        ev = EnrichmentEvidence(
            source_type="ai_reasoning",
            source_text="Some text.",
            model_used="slm",
            prompt_version="v1.0",
        )
        assert ev.id == ""
        assert ev.entity_id == ""

    def test_id_and_entity_id_can_be_set(self):
        ev = EnrichmentEvidence(
            id="cosmos-doc-1",
            entity_id="prod-001",
            source_type="product_context",
            source_text="Category is Outdoor Gear.",
            model_used="llm",
            prompt_version="v2.1",
        )
        assert ev.id == "cosmos-doc-1"
        assert ev.entity_id == "prod-001"

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
# EvidenceConfig
# ---------------------------------------------------------------------------


class TestEvidenceConfig:
    def test_defaults(self):
        cfg = EvidenceConfig(tenant_id="t-001")
        assert cfg.tenant_id == "t-001"
        assert cfg.evidence_extraction_enabled is False
        assert cfg.auto_approve_threshold is None

    def test_enable_evidence_extraction(self):
        cfg = EvidenceConfig(tenant_id="t-002", evidence_extraction_enabled=True)
        assert cfg.evidence_extraction_enabled is True

    def test_auto_approve_threshold_valid(self):
        cfg = EvidenceConfig(tenant_id="t-003", auto_approve_threshold=0.95)
        assert cfg.auto_approve_threshold == 0.95

    def test_auto_approve_threshold_upper_bound(self):
        with pytest.raises(Exception):
            EvidenceConfig(tenant_id="t-bad", auto_approve_threshold=1.5)

    def test_auto_approve_threshold_lower_bound(self):
        with pytest.raises(Exception):
            EvidenceConfig(tenant_id="t-bad", auto_approve_threshold=-0.1)

    def test_missing_tenant_id_raises(self):
        with pytest.raises(Exception):
            EvidenceConfig()  # type: ignore[call-arg]


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

    def test_extract_refs_returns_items_and_refs(self):
        extractor = EvidenceExtractor(model_used="slm", prompt_version="v1.0")
        output = {
            "evidence": [
                {
                    "source_type": "product_context",
                    "source_text": "Product description says 'navy blue'.",
                    "confidence_factors": ["direct mention"],
                }
            ]
        }
        items, refs = extractor.extract_refs(output, entity_id="prod-001")
        assert len(items) == 1
        assert len(refs) == 1
        assert items[0].entity_id == "prod-001"
        # IDs are empty strings until Cosmos assigns them
        assert refs[0] == items[0].id

    def test_extract_refs_empty_output(self):
        extractor = EvidenceExtractor(model_used="slm", prompt_version="v1.0")
        items, refs = extractor.extract_refs({})
        assert items == []
        assert refs == []

    def test_extract_refs_assigns_entity_id(self):
        extractor = EvidenceExtractor(model_used="llm", prompt_version="v2.0")
        output = {
            "evidence": [
                {"source_type": "ai_reasoning", "source_text": "Reason A."},
                {"source_type": "category_inference", "source_text": "Reason B."},
            ]
        }
        items, _ = extractor.extract_refs(output, entity_id="sku-42")
        for item in items:
            assert item.entity_id == "sku-42"


# ---------------------------------------------------------------------------
# Integration: EvidenceConfig toggle
# ---------------------------------------------------------------------------


class TestEvidenceToggle:
    """Verify the toggle pattern: extractor only runs when config says so."""

    def _run_extraction(
        self,
        config: EvidenceConfig,
        model_output: dict,
    ) -> list[EnrichmentEvidence]:
        """Simulate the enrichment-pipeline extraction branch."""
        if not config.evidence_extraction_enabled:
            return []
        extractor = EvidenceExtractor(model_used="slm", prompt_version="v1.0")
        return extractor.extract(model_output)

    def test_toggle_off_no_evidence(self):
        cfg = EvidenceConfig(tenant_id="t-off")
        output = {"evidence": [{"source_type": "ai_reasoning", "source_text": "Some text."}]}
        result = self._run_extraction(cfg, output)
        assert result == []

    def test_toggle_on_evidence_captured(self):
        cfg = EvidenceConfig(tenant_id="t-on", evidence_extraction_enabled=True)
        output = {"evidence": [{"source_type": "ai_reasoning", "source_text": "Some text."}]}
        result = self._run_extraction(cfg, output)
        assert len(result) == 1
