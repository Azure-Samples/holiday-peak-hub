"""Tests for EnrichmentGuardrail and SourceValidationResult."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest
from holiday_peak_lib.agents.guardrails import EnrichmentGuardrail, SourceValidationResult


@pytest.fixture
def guardrail() -> EnrichmentGuardrail:
    return EnrichmentGuardrail()


@pytest.fixture
def mock_product():
    product = MagicMock()
    product.sku = "SKU-001"
    return product


@pytest.fixture
def real_acp_content():
    return {
        "sku": "SKU-001",
        "long_description": "Premium wireless headphones with noise cancellation.",
        "features": ["Active noise cancellation", "30-hour battery", "Bluetooth 5.0"],
        "media": [{"type": "image", "url": "https://example.com/images/SKU-001.png"}],
    }


@pytest.fixture
def stub_acp_content():
    """Placeholder ACP content returned when no real data exists."""
    return {
        "sku": "SKU-999",
        "long_description": "Rich, ACP-supplied product description.",
        "features": [],
        "media": [],
    }


class TestSourceValidationResult:
    def test_valid_result(self):
        result = SourceValidationResult(is_valid=True, source_ids=["pim:SKU-001"])
        assert result.is_valid is True
        assert result.source_ids == ["pim:SKU-001"]
        assert result.rejection_reason is None

    def test_invalid_result(self):
        result = SourceValidationResult(
            is_valid=False, rejection_reason="No internal source data found."
        )
        assert result.is_valid is False
        assert result.source_ids == []
        assert result.rejection_reason is not None


class TestEnrichmentGuardrailValidateSources:
    def test_valid_when_product_exists(self, guardrail, mock_product):
        result = guardrail.validate_sources(product=mock_product)
        assert result.is_valid is True
        assert "pim:SKU-001" in result.source_ids

    def test_valid_when_product_and_real_acp(self, guardrail, mock_product, real_acp_content):
        result = guardrail.validate_sources(product=mock_product, acp_content=real_acp_content)
        assert result.is_valid is True
        assert "pim:SKU-001" in result.source_ids
        assert "acp:SKU-001" in result.source_ids

    def test_valid_when_only_real_acp_content(self, guardrail, real_acp_content):
        result = guardrail.validate_sources(product=None, acp_content=real_acp_content)
        assert result.is_valid is True
        assert "acp:SKU-001" in result.source_ids
        assert not any(s.startswith("pim:") for s in result.source_ids)

    def test_invalid_when_no_product_and_no_acp(self, guardrail):
        result = guardrail.validate_sources(product=None, acp_content=None)
        assert result.is_valid is False
        assert result.source_ids == []
        assert result.rejection_reason is not None

    def test_invalid_when_only_stub_acp_content(self, guardrail, stub_acp_content):
        """Stub/placeholder ACP content should NOT be treated as real internal data."""
        result = guardrail.validate_sources(product=None, acp_content=stub_acp_content)
        assert result.is_valid is False
        assert result.rejection_reason is not None

    def test_invalid_when_empty_acp_content(self, guardrail):
        result = guardrail.validate_sources(product=None, acp_content={})
        assert result.is_valid is False

    def test_valid_acp_with_features_only(self, guardrail):
        acp = {"sku": "SKU-002", "features": ["Feature X"], "long_description": ""}
        result = guardrail.validate_sources(product=None, acp_content=acp)
        assert result.is_valid is True
        assert "acp:SKU-002" in result.source_ids


class TestEnrichmentGuardrailTagContent:
    def test_tag_content_adds_sources_key(self, guardrail):
        enriched = {"sku": "SKU-001", "name": "Test Product"}
        source_ids = ["pim:SKU-001", "acp:SKU-001"]
        tagged = guardrail.tag_content(enriched, source_ids)
        assert tagged["_sources"] == source_ids

    def test_tag_content_returns_same_dict(self, guardrail):
        enriched = {"sku": "SKU-001"}
        tagged = guardrail.tag_content(enriched, ["pim:SKU-001"])
        assert tagged is enriched

    def test_tag_content_with_empty_sources(self, guardrail):
        enriched = {"sku": "SKU-001"}
        tagged = guardrail.tag_content(enriched, [])
        assert tagged["_sources"] == []


class TestEnrichmentGuardrailLogAudit:
    def test_log_audit_approved_emits_info(self, guardrail, caplog):
        with caplog.at_level(
            logging.INFO, logger="holiday_peak_lib.agents.guardrails.enrichment_guardrail"
        ):
            guardrail.log_audit("SKU-001", ["pim:SKU-001"])
        assert any("Enrichment approved" in r.message for r in caplog.records)

    def test_log_audit_rejected_emits_warning(self, guardrail, caplog):
        with caplog.at_level(
            logging.WARNING, logger="holiday_peak_lib.agents.guardrails.enrichment_guardrail"
        ):
            guardrail.log_audit("SKU-999", [], rejection_reason="No source data")
        assert any("Enrichment rejected" in r.message for r in caplog.records)

    def test_log_audit_approved_does_not_warn(self, guardrail, caplog):
        with caplog.at_level(
            logging.WARNING, logger="holiday_peak_lib.agents.guardrails.enrichment_guardrail"
        ):
            guardrail.log_audit("SKU-001", ["pim:SKU-001"])
        assert not any(r.levelno == logging.WARNING for r in caplog.records)
