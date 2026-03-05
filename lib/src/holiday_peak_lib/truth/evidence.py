"""Evidence extraction for AI enrichments in the Product Truth Layer.

Captures the reasoning and evidence that supports AI-generated proposed
attribute values, enabling HITL reviewers to understand and verify enrichment
decisions.

The :class:`EvidenceExtractor` produces :class:`EnrichmentEvidence` objects
which are stored in the Cosmos ``evidence`` container and linked to
:class:`~holiday_peak_lib.schemas.truth.ProposedAttribute` via the
``evidence_refs`` field.  The :class:`EvidenceConfig` controls whether
extraction runs for a given tenant (off by default).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Supported source types for enrichment evidence
# ---------------------------------------------------------------------------
SOURCE_TYPE_AI_REASONING = "ai_reasoning"
SOURCE_TYPE_PRODUCT_CONTEXT = "product_context"
SOURCE_TYPE_CATEGORY_INFERENCE = "category_inference"
SOURCE_TYPE_IMAGE_ANALYSIS = "image_analysis"

VALID_SOURCE_TYPES = {
    SOURCE_TYPE_AI_REASONING,
    SOURCE_TYPE_PRODUCT_CONTEXT,
    SOURCE_TYPE_CATEGORY_INFERENCE,
    SOURCE_TYPE_IMAGE_ANALYSIS,
}

# Supported model identifiers
VALID_MODELS = {"slm", "llm"}


class EnrichmentEvidence(BaseModel):
    """Evidence captured when an AI model generates a proposed attribute value.

    Records the source text, confidence factors, and model metadata so that
    HITL reviewers can understand *why* the model produced a given value.
    Instances are stored in the Cosmos ``evidence`` container and referenced
    from :class:`~holiday_peak_lib.schemas.truth.ProposedAttribute` via
    ``evidence_refs``.

    >>> ev = EnrichmentEvidence(
    ...     source_type="ai_reasoning",
    ...     source_text="Product title contains 'waterproof'.",
    ...     confidence_factors=["keyword match", "category alignment"],
    ...     model_used="slm",
    ...     prompt_version="v1.0",
    ... )
    >>> ev.source_type
    'ai_reasoning'
    >>> ev.model_used
    'slm'
    """

    id: str = Field(
        default="",
        description="Cosmos document ID; populated on write.",
    )
    entity_id: str = Field(
        default="",
        description="ID of the product/entity this evidence belongs to.",
    )
    source_type: str = Field(
        ...,
        description=(
            "Category of evidence: 'ai_reasoning', 'product_context', "
            "'category_inference', or 'image_analysis'."
        ),
    )
    source_text: str = Field(
        ...,
        description="The text or context that led to the proposed value.",
    )
    confidence_factors: list[str] = Field(
        default_factory=list,
        description="Factors that contributed to the confidence score.",
    )
    model_used: str = Field(
        ...,
        description="Identifier of the model that produced the evidence: 'slm' or 'llm'.",
    )
    prompt_version: str = Field(
        ...,
        description="Version tag of the prompt used for extraction.",
    )
    extracted_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the evidence was captured.",
    )


class EvidenceConfig(BaseModel):
    """Evidence-extraction feature flags for the enrichment pipeline.

    This model controls only the evidence-extraction toggle and should be
    read alongside the tenant's top-level configuration.  It is intentionally
    narrow so it does not conflict with the writeback-focused
    :class:`~holiday_peak_lib.integrations.pim_writeback.TenantConfig`.

    >>> cfg = EvidenceConfig(tenant_id="t-001")
    >>> cfg.evidence_extraction_enabled
    False
    >>> EvidenceConfig(tenant_id="t-002", evidence_extraction_enabled=True).evidence_extraction_enabled
    True
    """

    tenant_id: str = Field(..., description="Unique identifier for the tenant.")
    evidence_extraction_enabled: bool = Field(
        default=False,
        description=(
            "When True, the enrichment pipeline captures evidence for each "
            "ProposedAttribute.  Adds ~20%% latency per call due to structured "
            "output parsing.  Disabled by default."
        ),
    )
    auto_approve_threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "Confidence threshold above which proposed attributes are automatically "
            "approved without HITL review.  None means all proposals require review."
        ),
    )


class EvidenceExtractor:
    """Extracts :class:`EnrichmentEvidence` from enrichment model outputs.

    The extractor is a lightweight utility that transforms the raw structured
    output from an AI model into validated ``EnrichmentEvidence`` objects.  It
    is designed to run as a non-blocking step inside the enrichment pipeline
    and must not raise exceptions that would interrupt enrichment when evidence
    extraction fails — callers should handle errors gracefully.

    Usage::

        extractor = EvidenceExtractor(model_used="slm", prompt_version="v1.0")
        evidence_items, refs = extractor.extract_refs(model_output, entity_id="prod-001")
        # persist evidence_items to Cosmos, then assign real IDs …
        proposed.evidence_refs = refs
    """

    def __init__(self, model_used: str = "slm", prompt_version: str = "v1.0") -> None:
        if model_used not in VALID_MODELS:
            raise ValueError(f"model_used must be one of {VALID_MODELS}, got {model_used!r}")
        self.model_used = model_used
        self.prompt_version = prompt_version

    def extract(self, model_output: dict[str, Any]) -> list[EnrichmentEvidence]:
        """Parse *model_output* and return a list of :class:`EnrichmentEvidence`.

        The extractor looks for an ``"evidence"`` key in *model_output*.  Each
        item in that list is expected to contain at minimum a ``"source_type"``
        and ``"source_text"`` field.  Items that cannot be parsed are skipped.

        Args:
            model_output: Raw dict returned by the enrichment model.  Must
                contain an optional ``"evidence"`` key whose value is a list of
                evidence dicts.

        Returns:
            A (possibly empty) list of validated :class:`EnrichmentEvidence`.
        """
        raw_items = model_output.get("evidence", [])
        if not isinstance(raw_items, list):
            return []

        results: list[EnrichmentEvidence] = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            source_type = item.get("source_type", SOURCE_TYPE_AI_REASONING)
            if source_type not in VALID_SOURCE_TYPES:
                source_type = SOURCE_TYPE_AI_REASONING
            source_text = item.get("source_text", "")
            if not source_text:
                continue
            confidence_factors = item.get("confidence_factors", [])
            if not isinstance(confidence_factors, list):
                confidence_factors = []
            results.append(
                EnrichmentEvidence(
                    source_type=source_type,
                    source_text=source_text,
                    confidence_factors=[str(f) for f in confidence_factors],
                    model_used=self.model_used,
                    prompt_version=self.prompt_version,
                )
            )
        return results

    def extract_refs(
        self,
        model_output: dict[str, Any],
        entity_id: str = "",
    ) -> tuple[list[EnrichmentEvidence], list[str]]:
        """Extract evidence items and return both items and placeholder ref IDs.

        This helper pairs naturally with
        :class:`~holiday_peak_lib.schemas.truth.ProposedAttribute`, which stores
        evidence as ``evidence_refs`` (a list of Cosmos document IDs).  Callers
        persist the returned :class:`EnrichmentEvidence` objects to Cosmos, then
        use the returned ref list to populate ``proposed.evidence_refs``.

        Args:
            model_output: Raw dict from the enrichment model.
            entity_id: Product/entity ID to tag on each evidence document.

        Returns:
            A tuple of ``(evidence_items, ref_ids)`` where *ref_ids* mirrors the
            ``id`` field of each item.  IDs are empty strings until the caller
            assigns them on Cosmos write.
        """
        items = self.extract(model_output)
        for item in items:
            item.entity_id = entity_id
        refs = [item.id for item in items]
        return items, refs
