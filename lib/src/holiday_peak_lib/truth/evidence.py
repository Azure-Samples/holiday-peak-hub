"""Evidence extraction for AI enrichments in the Product Truth Layer.

Captures the reasoning and evidence that supports AI-generated proposed
attribute values, enabling HITL reviewers to understand and verify enrichment
decisions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

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


class ProposedAttribute(BaseModel):
    """A candidate attribute value produced by the enrichment pipeline.

    When ``evidence_extraction_enabled`` is ``True`` in :class:`TenantConfig`,
    the ``evidence`` list is populated with :class:`EnrichmentEvidence` items
    that justify the proposed value.

    >>> attr = ProposedAttribute(
    ...     entity_id="prod-001",
    ...     attribute_name="waterproof",
    ...     proposed_value=True,
    ...     confidence=0.92,
    ...     source="slm",
    ... )
    >>> attr.entity_id
    'prod-001'
    >>> attr.evidence
    []
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    entity_id: str = Field(..., description="ID of the product/entity being enriched.")
    attribute_name: str = Field(..., description="Name of the attribute being proposed.")
    proposed_value: Any = Field(..., description="The value proposed by the enrichment model.")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score in [0, 1].",
    )
    source: str = Field(..., description="Service or model that generated the proposal.")
    status: str = Field(
        default="pending",
        description="Review status: 'pending', 'approved', or 'rejected'.",
    )
    evidence: list[EnrichmentEvidence] = Field(
        default_factory=list,
        description="Evidence items captured when evidence extraction is enabled.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class TenantConfig(BaseModel):
    """Per-tenant configuration for the enrichment pipeline.

    Controls optional features such as evidence extraction.  All toggles
    default to their most conservative (off) setting so that existing
    tenants are unaffected when new features are deployed.

    >>> cfg = TenantConfig(tenant_id="t-001")
    >>> cfg.evidence_extraction_enabled
    False
    >>> TenantConfig(tenant_id="t-002", evidence_extraction_enabled=True).evidence_extraction_enabled
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
        evidence = extractor.extract(model_output)
        proposed.evidence = evidence
    """

    def __init__(self, model_used: str = "slm", prompt_version: str = "v1.0") -> None:
        if model_used not in VALID_MODELS:
            raise ValueError(
                f"model_used must be one of {VALID_MODELS}, got {model_used!r}"
            )
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

    def attach_evidence(
        self,
        proposed: ProposedAttribute,
        model_output: dict[str, Any],
    ) -> ProposedAttribute:
        """Convenience method: extract evidence and attach it to *proposed*.

        Returns the same ``ProposedAttribute`` instance (mutated in-place) so
        callers can chain the call.

        Args:
            proposed: The :class:`ProposedAttribute` to enrich with evidence.
            model_output: Raw dict from the enrichment model.

        Returns:
            The updated ``proposed`` object.
        """
        proposed.evidence = self.extract(model_output)
        return proposed
