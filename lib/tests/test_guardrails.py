"""Tests for EnrichmentGuardrail, SourceValidationResult, and async middleware (#83)."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest
from holiday_peak_lib.agents.guardrails import (
    ContentAttributor,
    EnrichmentGuardrail,
    GuardrailMiddleware,
    SourceRef,
    SourceValidationResult,
    SourceValidator,
)


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


# ---------------------------------------------------------------------------
# SourceRef tests
# ---------------------------------------------------------------------------


class TestSourceRef:
    def test_as_tag_format(self):
        ref = SourceRef(source_system="pim", source_id="SKU-001")
        assert ref.as_tag() == "pim:SKU-001"

    def test_default_confidence_is_one(self):
        ref = SourceRef(source_system="dam", source_id="ASSET-99")
        assert ref.confidence == 1.0

    def test_custom_confidence(self):
        ref = SourceRef(source_system="pim", source_id="SKU-X", confidence=0.75)
        assert ref.confidence == 0.75

    def test_retrieved_at_is_populated(self):
        ref = SourceRef(source_system="pim", source_id="SKU-001")
        assert ref.retrieved_at  # non-empty ISO string


# ---------------------------------------------------------------------------
# SourceValidator tests
# ---------------------------------------------------------------------------


class TestSourceValidator:
    @pytest.fixture
    def validator(self) -> SourceValidator:
        return SourceValidator()

    @pytest.fixture
    def mock_product(self):
        p = MagicMock()
        p.sku = "SKU-001"
        return p

    @pytest.fixture
    def real_acp_content(self):
        return {
            "sku": "SKU-001",
            "long_description": "Premium wireless headphones.",
            "features": ["ANC", "Bluetooth 5.0"],
        }

    @pytest.fixture
    def stub_acp_content(self):
        return {
            "sku": "SKU-999",
            "long_description": "Rich, ACP-supplied product description.",
            "features": [],
        }

    @pytest.mark.asyncio
    async def test_returns_pim_ref_when_product_provided(self, validator, mock_product):
        refs = await validator.validate(sku="SKU-001", product=mock_product)
        assert refs is not None
        assert any(r.source_system == "pim" for r in refs)

    @pytest.mark.asyncio
    async def test_returns_dam_ref_when_real_acp_content(self, validator, real_acp_content):
        refs = await validator.validate(sku="SKU-001", product=None, acp_content=real_acp_content)
        assert refs is not None
        assert any(r.source_system == "dam" for r in refs)

    @pytest.mark.asyncio
    async def test_both_pim_and_dam_when_both_provided(
        self, validator, mock_product, real_acp_content
    ):
        refs = await validator.validate(
            sku="SKU-001", product=mock_product, acp_content=real_acp_content
        )
        assert refs is not None
        systems = {r.source_system for r in refs}
        assert "pim" in systems
        assert "dam" in systems

    @pytest.mark.asyncio
    async def test_returns_none_when_no_sources(self, validator):
        refs = await validator.validate(sku="SKU-MISSING", product=None, acp_content=None)
        assert refs is None

    @pytest.mark.asyncio
    async def test_returns_none_for_stub_acp_and_no_product(self, validator, stub_acp_content):
        refs = await validator.validate(sku="SKU-999", product=None, acp_content=stub_acp_content)
        assert refs is None

    @pytest.mark.asyncio
    async def test_external_hook_can_contribute_refs(self, validator):
        class ExtendedValidator(SourceValidator):
            async def _validate_external(self, sku: str) -> list[SourceRef]:
                return [SourceRef(source_system="akeneo", source_id=sku)]

        ext = ExtendedValidator()
        refs = await ext.validate(sku="SKU-EXT", product=None)
        assert refs is not None
        assert any(r.source_system == "akeneo" for r in refs)


# ---------------------------------------------------------------------------
# ContentAttributor tests
# ---------------------------------------------------------------------------


class TestContentAttributor:
    @pytest.fixture
    def attributor(self) -> ContentAttributor:
        return ContentAttributor()

    @pytest.fixture
    def sources(self) -> list[SourceRef]:
        return [
            SourceRef(source_system="pim", source_id="SKU-001", confidence=0.9),
            SourceRef(source_system="dam", source_id="SKU-001", confidence=0.8),
        ]

    def test_injects_sources_list(self, attributor, sources):
        output = {"name": "Headphones"}
        tagged = attributor.attribute(output, sources)
        assert tagged["_sources"] == ["pim:SKU-001", "dam:SKU-001"]

    def test_injects_source_system_list(self, attributor, sources):
        output = {"name": "Headphones"}
        attributor.attribute(output, sources)
        assert output["_source_system"] == ["pim", "dam"]

    def test_injects_source_id_list(self, attributor, sources):
        output = {"name": "Headphones"}
        attributor.attribute(output, sources)
        assert output["_source_id"] == ["SKU-001", "SKU-001"]

    def test_confidence_is_mean_of_sources(self, attributor, sources):
        output = {"name": "Headphones"}
        attributor.attribute(output, sources)
        assert output["_confidence"] == pytest.approx(0.85, abs=1e-4)

    def test_explicit_confidence_override(self, attributor, sources):
        output = {"name": "Headphones"}
        attributor.attribute(output, sources, overall_confidence=0.5)
        assert output["_confidence"] == pytest.approx(0.5, abs=1e-4)

    def test_attributed_at_is_set(self, attributor, sources):
        output = {"name": "Headphones"}
        attributor.attribute(output, sources)
        assert "_attributed_at" in output

    def test_mutates_dict_in_place_and_returns_it(self, attributor, sources):
        output = {"name": "Headphones"}
        returned = attributor.attribute(output, sources)
        assert returned is output

    def test_empty_sources_defaults_confidence_to_one(self, attributor):
        output = {"name": "No source product"}
        attributor.attribute(output, [])
        assert output["_confidence"] == 1.0
        assert output["_sources"] == []


# ---------------------------------------------------------------------------
# GuardrailMiddleware tests
# ---------------------------------------------------------------------------


class TestGuardrailMiddleware:
    @pytest.fixture
    def middleware(self) -> GuardrailMiddleware:
        return GuardrailMiddleware()

    @pytest.fixture
    def mock_product(self):
        p = MagicMock()
        p.sku = "SKU-001"
        return p

    @pytest.fixture
    def valid_request(self, mock_product):
        return {
            "sku": "SKU-001",
            "product": mock_product,
            "acp_content": {
                "sku": "SKU-001",
                "long_description": "Great headphones.",
                "features": ["ANC"],
            },
        }

    @pytest.fixture
    def invalid_request(self):
        return {"sku": "SKU-MISSING"}

    @pytest.mark.asyncio
    async def test_validate_passes_request_with_valid_sources(self, middleware, valid_request):
        result = await middleware.validate_enrichment_request(valid_request)
        assert result is not None
        assert "_source_refs" in result
        assert len(result["_source_refs"]) > 0

    @pytest.mark.asyncio
    async def test_validate_returns_none_for_no_sources(self, middleware, invalid_request):
        result = await middleware.validate_enrichment_request(invalid_request)
        assert result is None

    @pytest.mark.asyncio
    async def test_validate_preserves_original_request_keys(self, middleware, valid_request):
        result = await middleware.validate_enrichment_request(valid_request)
        assert result is not None
        assert result["sku"] == "SKU-001"

    @pytest.mark.asyncio
    async def test_attribute_output_injects_provenance(self, middleware):
        sources = [SourceRef(source_system="pim", source_id="SKU-001")]
        output = {"long_description": "Good product."}
        attributed = await middleware.attribute_output(output, sources)
        assert "_sources" in attributed
        assert "_confidence" in attributed

    @pytest.mark.asyncio
    async def test_audit_enrichment_logs_info(self, middleware, caplog):
        sources = [SourceRef(source_system="pim", source_id="SKU-001")]
        request = {"sku": "SKU-001"}
        output = {"long_description": "Good product.", "_confidence": 0.9, "_sources": ["pim:SKU-001"]}
        with caplog.at_level(
            logging.INFO, logger="holiday_peak_lib.agents.guardrails.enrichment_guardrail"
        ):
            await middleware.audit_enrichment(request, output, sources)
        assert any("Enrichment audit" in r.message for r in caplog.records)

    @pytest.mark.asyncio
    async def test_validate_warns_on_rejection(self, middleware, invalid_request, caplog):
        with caplog.at_level(
            logging.WARNING, logger="holiday_peak_lib.agents.guardrails.enrichment_guardrail"
        ):
            await middleware.validate_enrichment_request(invalid_request)
        assert any(r.levelno == logging.WARNING for r in caplog.records)

    @pytest.mark.asyncio
    async def test_custom_validator_is_used(self):
        class AlwaysValidValidator(SourceValidator):
            async def validate(self, *, sku, product, acp_content=None):
                return [SourceRef(source_system="mock", source_id=sku)]

        middleware = GuardrailMiddleware(validator=AlwaysValidValidator())
        result = await middleware.validate_enrichment_request({"sku": "ANY-SKU"})
        assert result is not None
        assert result["_source_refs"][0].source_system == "mock"

    @pytest.mark.asyncio
    async def test_custom_attributor_is_used(self):
        class NoOpAttributor(ContentAttributor):
            def attribute(self, output, sources, *, overall_confidence=None):
                output["_custom"] = True
                return output

        middleware = GuardrailMiddleware(attributor=NoOpAttributor())
        sources = [SourceRef(source_system="pim", source_id="SKU-001")]
        result = await middleware.attribute_output({"name": "x"}, sources)
        assert result["_custom"] is True
