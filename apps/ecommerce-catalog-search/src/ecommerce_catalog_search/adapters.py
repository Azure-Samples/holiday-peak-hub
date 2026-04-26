"""Adapters for the ecommerce catalog search service (ACP-aware).

The catalog-search agent is isolated from the CRUD service. Its product read
path is Azure AI Search; the agent applies a secondary filter to ground
retrieved products on user intent. ``MockProductAdapter`` remains the default
in-process fallback for tests and local development.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

from holiday_peak_lib.adapters.acp_mapper import AcpCatalogMapper
from holiday_peak_lib.adapters.inventory_adapter import InventoryConnector
from holiday_peak_lib.adapters.mock_adapters import (
    MockInventoryAdapter,
    MockProductAdapter,
)
from holiday_peak_lib.adapters.product_adapter import ProductConnector

SEARCH_MODE_KEYWORD = "keyword"
SEARCH_MODE_INTELLIGENT = "intelligent"
SUPPORTED_SEARCH_MODES = {SEARCH_MODE_KEYWORD, SEARCH_MODE_INTELLIGENT}
ENRICHED_RESULT_FIELDS = (
    "use_cases",
    "complementary_products",
    "substitute_products",
    "enriched_description",
)
_SEARCH_TERM_TOKEN_PATTERN = re.compile(r"[a-z0-9]{3,}")


@dataclass
class CatalogAdapters:
    """Container for catalog search adapters."""

    products: ProductConnector
    inventory: InventoryConnector
    mapping: AcpCatalogMapper


def normalize_search_mode(mode: str | None) -> str:
    """Normalize incoming search mode and default unknown values to intelligent."""
    normalized = (mode or SEARCH_MODE_INTELLIGENT).strip().lower()
    if normalized in SUPPORTED_SEARCH_MODES:
        return normalized
    return SEARCH_MODE_INTELLIGENT


def merge_enriched_fields(
    base_payload: dict[str, object],
    enriched_fields: dict[str, object] | None,
) -> dict[str, object]:
    """Merge optional enrichment fields into ACP payload without breaking shape."""
    if not enriched_fields:
        return base_payload

    payload = dict(base_payload)
    extended = payload.get("extended_attributes")
    extended_attributes = dict(extended) if isinstance(extended, dict) else {}

    for field in ENRICHED_RESULT_FIELDS:
        if field in enriched_fields and enriched_fields[field] is not None:
            value = enriched_fields[field]
            payload[field] = value
            extended_attributes[field] = value

    payload["extended_attributes"] = extended_attributes
    return payload


def build_catalog_adapters(
    *,
    product_connector: Optional[ProductConnector] = None,
    inventory_connector: Optional[InventoryConnector] = None,
) -> CatalogAdapters:
    """Create adapters for catalog search workflows."""
    products = product_connector or ProductConnector(adapter=MockProductAdapter())
    inventory = inventory_connector or InventoryConnector(adapter=MockInventoryAdapter())
    mapping = AcpCatalogMapper()
    return CatalogAdapters(products=products, inventory=inventory, mapping=mapping)


def merge_scored_results(
    batches: list[list[Any]],
    limit: int,
    *,
    rank_denominator: int | None = None,
) -> list[Any]:
    """Score-based merge of ranked AI Search result batches.

    Each item must expose ``.sku``, ``.score``, and ``.enriched_fields``.
    Items found in multiple batches are boosted.  The variant with the
    richest enrichment payload is preserved.

    ``rank_denominator`` controls the divisor for rank-bonus calculation.
    Defaults to ``limit`` when *None*.
    """
    if limit <= 0:
        return []

    denom = rank_denominator if rank_denominator is not None else limit

    merged: dict[str, dict[str, Any]] = {}
    for batch in batches:
        for rank, candidate in enumerate(batch, start=1):
            entry = merged.setdefault(
                candidate.sku,
                {
                    "candidate": candidate,
                    "best_score": candidate.score,
                    "hits": 0,
                    "rank_bonus": 0.0,
                },
            )
            entry["hits"] += 1
            entry["best_score"] = max(entry["best_score"], candidate.score)
            entry["rank_bonus"] += max((denom - rank + 1) / max(denom, 1), 0.0)

            if len(candidate.enriched_fields) > len(entry["candidate"].enriched_fields):
                entry["candidate"] = candidate

    ranked = sorted(
        merged.values(),
        key=lambda item: (item["hits"], item["best_score"], item["rank_bonus"]),
        reverse=True,
    )
    return [item["candidate"] for item in ranked[:limit]]
