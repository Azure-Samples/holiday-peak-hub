"""Internal data enrichment guardrails for AI agents.

Enforces the critical constraint that AI-powered enrichment uses ONLY
company-owned data from PIM/DAM/CRM systems. Agents must NEVER generate
product descriptions, images, or attributes without source data.

Classes:

- :class:`EnrichmentGuardrail` — core validation and audit logging (sync).
- :class:`SourceRef` — typed reference to an internal data source.
- :class:`SourceValidator` — checks that referenced source data exists in PIM/DAM.
- :class:`ContentAttributor` — tags enriched output with source provenance.
- :class:`GuardrailMiddleware` — async facade that combines all of the above into
  a single enrichment-pipeline integration point.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

_ENRICHMENT_UNAVAILABLE = "enrichment not available"


@dataclass
class SourceValidationResult:
    """Result of validating source data availability for enrichment.

    Attributes:
        is_valid: Whether enrichment can proceed.
        source_ids: Identifiers of the internal data sources used.
        rejection_reason: Human-readable reason when ``is_valid`` is False.
    """

    is_valid: bool
    source_ids: list[str] = field(default_factory=list)
    rejection_reason: str | None = None


class EnrichmentGuardrail:
    """Guardrail that enforces internal-data-only enrichment policy.

    This middleware validates that at least one internal data source
    (product catalog / PIM or ACP/DAM content) exists for a given SKU
    before allowing enrichment to proceed.  If no owned source data is
    available the request is rejected and an audit entry is emitted.

    Usage::

        guardrail = EnrichmentGuardrail()
        result = guardrail.validate_sources(product=product, acp_content=acp_content)
        if not result.is_valid:
            guardrail.log_audit(sku, result.source_ids, rejection_reason=result.rejection_reason)
            return {"error": _ENRICHMENT_UNAVAILABLE, "reason": result.rejection_reason}
        guardrail.log_audit(sku, result.source_ids)
        enriched = guardrail.tag_content(enriched, result.source_ids)
    """

    # Sentinel used to detect placeholder / stub ACP responses that contain
    # no real company-owned data (the stub always returns this generic text).
    _STUB_DESCRIPTION = "Rich, ACP-supplied product description."

    def validate_sources(
        self,
        *,
        product: Any | None,
        acp_content: dict[str, Any] | None = None,
    ) -> SourceValidationResult:
        """Determine whether enrichment can proceed based on available source data.

        The rules are:
        1. If a product record exists in the catalog (PIM), enrichment is
           permitted — the catalog entry is the primary owned data source.
        2. If no product exists but ACP/DAM content is available and is *not*
           a generic placeholder, enrichment is permitted from that source.
        3. If neither owned source has real data, enrichment is rejected.

        Args:
            product: CatalogProduct instance (or None when not found).
            acp_content: Dict returned by the ACP/DAM adapter (or None).

        Returns:
            SourceValidationResult with is_valid flag and populated source_ids.
        """
        source_ids: list[str] = []

        # Primary source: product catalog (PIM)
        if product is not None:
            sku = getattr(product, "sku", None) or str(product)
            source_ids.append(f"pim:{sku}")

        # Secondary source: ACP / DAM content — only if it contains real data
        if acp_content and self._has_real_acp_content(acp_content):
            sku_tag = acp_content.get("sku", "unknown")
            source_ids.append(f"acp:{sku_tag}")

        if source_ids:
            return SourceValidationResult(is_valid=True, source_ids=source_ids)

        return SourceValidationResult(
            is_valid=False,
            source_ids=[],
            rejection_reason="No internal source data found for SKU. Enrichment requires PIM or ACP data.",
        )

    def _has_real_acp_content(self, acp_content: dict[str, Any]) -> bool:
        """Return True when ACP content contains company-owned (non-stub) data."""
        description = acp_content.get("long_description") or ""
        features = acp_content.get("features") or []
        # Reject the generic stub placeholder used when no real ACP data exists
        if description == self._STUB_DESCRIPTION and not features:
            return False
        return bool(description or features)

    def tag_content(
        self,
        enriched: dict[str, Any],
        source_ids: list[str],
    ) -> dict[str, Any]:
        """Attach source attribution metadata to enriched content.

        Args:
            enriched: The enriched product dictionary to annotate.
            source_ids: List of internal source identifiers used.

        Returns:
            The same dict with a ``_sources`` key added.
        """
        enriched["_sources"] = source_ids
        return enriched

    def log_audit(
        self,
        sku: str,
        source_ids: list[str],
        *,
        rejection_reason: str | None = None,
    ) -> None:
        """Emit an audit log entry for data lineage tracking.

        Args:
            sku: The product SKU being enriched.
            source_ids: Internal source identifiers used (empty when rejected).
            rejection_reason: Set when enrichment was rejected.
        """
        timestamp = datetime.now(tz=timezone.utc).isoformat()
        if rejection_reason:
            logger.warning(
                "Enrichment rejected",
                extra={
                    "audit": True,
                    "sku": sku,
                    "sources": source_ids,
                    "rejection_reason": rejection_reason,
                    "timestamp": timestamp,
                },
            )
        else:
            logger.info(
                "Enrichment approved",
                extra={
                    "audit": True,
                    "sku": sku,
                    "sources": source_ids,
                    "timestamp": timestamp,
                },
            )


# ---------------------------------------------------------------------------
# SourceRef — typed reference to an internal data source
# ---------------------------------------------------------------------------


@dataclass
class SourceRef:
    """Reference to an internal data source used during enrichment.

    Attributes:
        source_system: Originating system identifier (e.g. ``"pim"``, ``"dam"``).
        source_id: Entity identifier within that system (e.g. SKU or asset ID).
        confidence: Optional confidence score in the range [0.0, 1.0].
        retrieved_at: Timestamp when the source data was retrieved.
    """

    source_system: str
    source_id: str
    confidence: float = 1.0
    retrieved_at: str = field(
        default_factory=lambda: datetime.now(tz=timezone.utc).isoformat()
    )

    def as_tag(self) -> str:
        """Return a compact string tag suitable for embedding in content metadata."""
        return f"{self.source_system}:{self.source_id}"


# ---------------------------------------------------------------------------
# SourceValidator — checks that referenced source data exists in PIM/DAM
# ---------------------------------------------------------------------------


class SourceValidator:
    """Validates that referenced SKUs / asset IDs exist in the internal catalog.

    This is a lightweight check that operates on the available in-process
    objects (product record, ACP/DAM content dict).  For heavier cross-service
    validation (e.g. verifying against a live Akeneo instance) override
    :meth:`_validate_external` in a subclass.

    Usage::

        validator = SourceValidator()
        refs = await validator.validate(sku="SKU-001", product=product, acp_content=content)
        if refs is None:
            return {"error": "enrichment not available"}
    """

    async def validate(
        self,
        *,
        sku: str,
        product: Any | None,
        acp_content: dict[str, Any] | None = None,
    ) -> list[SourceRef] | None:
        """Build :class:`SourceRef` list from available source objects.

        Returns a non-empty list when at least one valid internal source is
        found for *sku*, or ``None`` when no source data is available and
        enrichment must be rejected.

        Args:
            sku: The product identifier being enriched.
            product: CatalogProduct instance or any object with a ``sku`` attr.
            acp_content: Dict returned by the ACP/DAM adapter (optional).

        Returns:
            List of :class:`SourceRef` objects, or ``None`` when no sources found.
        """
        refs: list[SourceRef] = []

        if product is not None:
            product_sku = getattr(product, "sku", None) or sku
            refs.append(SourceRef(source_system="pim", source_id=str(product_sku)))

        if acp_content and self._has_real_content(acp_content):
            acp_sku = acp_content.get("sku", sku)
            refs.append(SourceRef(source_system="dam", source_id=str(acp_sku)))

        external_refs = await self._validate_external(sku)
        refs.extend(external_refs)

        return refs if refs else None

    async def _validate_external(self, sku: str) -> list[SourceRef]:  # noqa: ARG002
        """Hook for subclasses to add cross-service source validation.

        Default implementation returns an empty list (no external check).
        Override this method to verify against live PIM/DAM systems.
        """
        return []

    @staticmethod
    def _has_real_content(acp_content: dict[str, Any]) -> bool:
        """Return True when ACP content contains meaningful company-owned data."""
        description = acp_content.get("long_description") or ""
        features = acp_content.get("features") or []
        stub = "Rich, ACP-supplied product description."
        if description == stub and not features:
            return False
        return bool(description or features)


# ---------------------------------------------------------------------------
# ContentAttributor — tags enriched output with source provenance
# ---------------------------------------------------------------------------


class ContentAttributor:
    """Tags all agent output with source provenance metadata.

    Every enriched content dictionary produced by an agent must carry
    provenance information: which systems contributed data, the identifiers
    within those systems, and an overall confidence rating.  This enables
    downstream auditing and the HITL review queue to surface evidence.

    Usage::

        attributor = ContentAttributor()
        tagged = attributor.attribute(enriched_dict, sources)
    """

    def attribute(
        self,
        output: dict[str, Any],
        sources: list[SourceRef],
        *,
        overall_confidence: float | None = None,
    ) -> dict[str, Any]:
        """Add ``_sources``, ``_source_system``, ``_source_id``, and
        ``_confidence`` keys to *output*.

        Following ADR-025, these keys are prefixed with ``_`` to distinguish
        framework-injected metadata from agent-produced content.

        Args:
            output: The enriched product/content dictionary to annotate.
            sources: List of internal :class:`SourceRef` objects used.
            overall_confidence: Optional override for the top-level confidence
                score.  When omitted, defaults to the mean of source confidences
                (or 1.0 when no sources).

        Returns:
            The same *output* dict, mutated in-place, with provenance keys added.
        """
        if overall_confidence is None:
            overall_confidence = (
                sum(r.confidence for r in sources) / len(sources) if sources else 1.0
            )

        output["_sources"] = [r.as_tag() for r in sources]
        output["_source_system"] = [r.source_system for r in sources]
        output["_source_id"] = [r.source_id for r in sources]
        output["_confidence"] = round(overall_confidence, 4)
        output["_attributed_at"] = datetime.now(tz=timezone.utc).isoformat()
        return output


# ---------------------------------------------------------------------------
# GuardrailMiddleware — async facade for the full enrichment pipeline
# ---------------------------------------------------------------------------


class GuardrailMiddleware:
    """Async middleware that enforces enrichment guardrails across the pipeline.

    Combines :class:`SourceValidator`, :class:`ContentAttributor`, and audit
    logging into a single cohesive entry point.  Agent enrichment handlers
    should call :meth:`validate_enrichment_request` before invoking the model,
    then :meth:`attribute_output` on the result, and finally
    :meth:`audit_enrichment` to write the lineage record.

    Usage::

        middleware = GuardrailMiddleware()

        validated = await middleware.validate_enrichment_request(request)
        if validated is None:
            return {"error": "enrichment not available"}

        agent_output = await run_agent(validated)

        attributed = await middleware.attribute_output(
            agent_output,
            sources=validated["_source_refs"],
        )
        await middleware.audit_enrichment(request, attributed, validated["_source_refs"])
        return attributed
    """

    def __init__(
        self,
        *,
        validator: SourceValidator | None = None,
        attributor: ContentAttributor | None = None,
    ) -> None:
        self._validator = validator or SourceValidator()
        self._attributor = attributor or ContentAttributor()

    async def validate_enrichment_request(
        self,
        request: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Validate that the enrichment request has sufficient internal source data.

        The request dict must contain at minimum a ``sku`` key.  Optional keys:
        - ``product``: CatalogProduct instance (or any object with ``sku`` attr).
        - ``acp_content``: Dict from the ACP/DAM adapter.

        When validation passes the resolved :class:`SourceRef` objects are
        embedded in the returned dict under the ``_source_refs`` key so
        downstream methods can consume them without re-validation.

        Args:
            request: Enrichment request dictionary from the agent handler.

        Returns:
            Annotated request dict with ``_source_refs`` injected, or ``None``
            when no internal source data is available (enrichment rejected).
        """
        sku: str = request.get("sku") or request.get("product_id") or ""
        product = request.get("product")
        acp_content = request.get("acp_content")

        refs = await self._validator.validate(
            sku=sku,
            product=product,
            acp_content=acp_content,
        )

        if refs is None:
            logger.warning(
                "Enrichment request rejected — no internal source data for SKU '%s'",
                sku,
                extra={"audit": True, "sku": sku, "reason": _ENRICHMENT_UNAVAILABLE},
            )
            return None

        return {**request, "_source_refs": refs}

    async def attribute_output(
        self,
        output: dict[str, Any],
        sources: list[SourceRef],
        *,
        overall_confidence: float | None = None,
    ) -> dict[str, Any]:
        """Attach source provenance metadata to the enriched output dict.

        Args:
            output: The enriched content dictionary produced by the agent.
            sources: Source references collected during validation.
            overall_confidence: Optional explicit confidence override.

        Returns:
            The attributed output dict (mutated in-place).
        """
        return self._attributor.attribute(
            output,
            sources,
            overall_confidence=overall_confidence,
        )

    async def audit_enrichment(
        self,
        request: dict[str, Any],
        output: dict[str, Any],
        sources: list[SourceRef],
    ) -> None:
        """Emit a structured audit log entry for the enrichment operation.

        Args:
            request: Original enrichment request dict (contains SKU, context).
            output: Attributed enrichment output produced by the agent.
            sources: Source references used during enrichment.
        """
        sku: str = request.get("sku") or request.get("product_id") or "unknown"
        timestamp = datetime.now(tz=timezone.utc).isoformat()
        logger.info(
            "Enrichment audit",
            extra={
                "audit": True,
                "sku": sku,
                "sources": [r.as_tag() for r in sources],
                "output_keys": sorted(output.keys()),
                "confidence": output.get("_confidence"),
                "timestamp": timestamp,
            },
        )
