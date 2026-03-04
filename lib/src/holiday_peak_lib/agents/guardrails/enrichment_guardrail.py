"""Internal data enrichment guardrails for AI agents.

Enforces the critical constraint that AI-powered enrichment uses ONLY
company-owned data from PIM/DAM/CRM systems. Agents must NEVER generate
product descriptions, images, or attributes without source data.
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
