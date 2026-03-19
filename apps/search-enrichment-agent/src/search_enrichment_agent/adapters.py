"""Adapter boundaries for search enrichment service."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from holiday_peak_lib.mcp.ai_search_indexing import (
    AISearchIndexingClient,
    build_ai_search_indexing_client_from_env,
)
from holiday_peak_lib.schemas.truth import SearchEnrichedProduct
from holiday_peak_lib.utils.logging import configure_logging
from holiday_peak_lib.utils.rate_limiter import RateLimiter, RateLimitExceededError

logger = configure_logging(app_name="search-enrichment-agent")


class ApprovedTruthAdapter:
    """Fetch approved truth attributes for a product entity."""

    def __init__(self, seeded_truth: dict[str, dict[str, Any]] | None = None) -> None:
        self._seeded_truth = seeded_truth or {}

    async def get_approved_data(self, entity_id: str) -> dict[str, Any] | None:
        data = self._seeded_truth.get(entity_id)
        if data is None:
            return None
        return dict(data)


class SearchEnrichedStoreAdapter:
    """Persist and fetch search-enriched products."""

    def __init__(self) -> None:
        self._memory_store: dict[str, dict[str, Any]] = {}

    async def upsert(self, enriched: SearchEnrichedProduct) -> dict[str, Any]:
        payload = enriched.model_dump(mode="json", by_alias=True)
        payload["id"] = enriched.sku
        payload["status"] = "upserted"
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._memory_store[enriched.sku] = payload
        logger.info(
            "search_enriched_product_upserted sku=%s container=%s",
            enriched.sku,
            "search_enriched_products",
        )
        return payload

    async def get_status(self, entity_id: str) -> dict[str, Any]:
        record = self._memory_store.get(entity_id)
        if record is None:
            return {
                "entity_id": entity_id,
                "status": "not_found",
                "container": "search_enriched_products",
            }
        return {
            "entity_id": entity_id,
            "status": record.get("status", "upserted"),
            "container": "search_enriched_products",
            "updated_at": record.get("updated_at"),
            "record": record,
        }


class FoundryEnrichmentAdapter:
    """Wrap model invocation for complex search enrichment generation."""

    def __init__(self) -> None:
        self._invoker: Callable[..., Awaitable[dict[str, Any]]] | None = None

    def set_model_invoker(self, invoker: Callable[..., Awaitable[dict[str, Any]]] | None) -> None:
        self._invoker = invoker

    async def enrich_complex_fields(
        self,
        *,
        entity_id: str,
        approved_truth: dict[str, Any],
    ) -> dict[str, Any]:
        if self._invoker is None:
            return {"_status": "fallback", "_reason": "foundry_not_configured"}

        messages = self._build_messages(entity_id=entity_id, approved_truth=approved_truth)
        try:
            raw = await self._invoker(
                request={"entity_id": entity_id, "intent": "search_enrichment"},
                messages=messages,
            )
        except (RuntimeError, ValueError, TypeError) as exc:
            logger.warning(
                "foundry_enrichment_unavailable entity_id=%s error=%s",
                entity_id,
                str(exc),
            )
            return {"_status": "fallback", "_reason": "foundry_unavailable"}

        if not isinstance(raw, dict):
            return {"_status": "fallback", "_reason": "invalid_foundry_payload"}

        allowed_keys = {
            "use_cases",
            "complementary_products",
            "substitute_products",
            "search_keywords",
            "enriched_description",
        }
        parsed = {key: raw.get(key) for key in allowed_keys if key in raw}
        parsed["_status"] = "ok"
        return parsed

    def _build_messages(self, *, entity_id: str, approved_truth: dict[str, Any]) -> list[dict[str, Any]]:
        instruction = (
            "Generate search enrichment fields from approved truth data. "
            "Return a JSON object with keys: use_cases, complementary_products, "
            "substitute_products, search_keywords, enriched_description."
        )
        return [
            {"role": "system", "content": "You produce search-optimized product enrichments."},
            {
                "role": "user",
                "content": {
                    "instruction": instruction,
                    "entity_id": entity_id,
                    "approved_truth": approved_truth,
                },
            },
        ]


class SearchIndexingAdapter:
    """Trigger or push AI Search indexing after enrichment upsert."""

    def __init__(
        self,
        client: AISearchIndexingClient,
        *,
        run_rate_limiter: RateLimiter | None = None,
    ) -> None:
        self._client = client
        self._run_rate_limiter = run_rate_limiter or RateLimiter(limit=10, window_seconds=60.0)

    async def sync_after_upsert(
        self,
        *,
        entity_id: str,
        enriched: SearchEnrichedProduct,
    ) -> dict[str, Any]:
        immediate_push = (os.getenv("AI_SEARCH_PUSH_IMMEDIATE") or "").lower() in {
            "1",
            "true",
            "yes",
        }
        if immediate_push:
            document = enriched.model_dump(mode="json", by_alias=True)
            document.setdefault("id", entity_id)
            document.setdefault("sku", entity_id)
            return await self._client.index_documents(self._client.settings.default_index_name, [document])

        indexer_name = self._client.settings.default_indexer_name
        if not indexer_name:
            return {
                "status": "skipped",
                "operation": "trigger_indexer_run",
                "reason": "missing_indexer_name",
            }

        try:
            await self._run_rate_limiter.check("global")
        except RateLimitExceededError as exc:
            return {
                "status": "error",
                "operation": "trigger_indexer_run",
                "http_status": 429,
                "error": {
                    "kind": "rate_limit",
                    "message": str(exc),
                },
            }
        return await self._client.trigger_indexer_run(indexer_name)


@dataclass
class SearchEnrichmentAdapters:
    """Container for all search enrichment adapters."""

    approved_truth: ApprovedTruthAdapter = field(default_factory=ApprovedTruthAdapter)
    enriched_store: SearchEnrichedStoreAdapter = field(default_factory=SearchEnrichedStoreAdapter)
    foundry: FoundryEnrichmentAdapter = field(default_factory=FoundryEnrichmentAdapter)
    search_indexing: SearchIndexingAdapter | None = None


def build_search_enrichment_adapters() -> SearchEnrichmentAdapters:
    """Create default adapters with optional local seeded data."""
    seeded_sku = os.getenv("SEARCH_ENRICHMENT_SEEDED_SKU")
    seeded_name = os.getenv("SEARCH_ENRICHMENT_SEEDED_NAME")

    seeded_truth: dict[str, dict[str, Any]] = {}
    if seeded_sku:
        seeded_truth[seeded_sku] = {
            "sku": seeded_sku,
            "name": seeded_name or seeded_sku,
            "category": os.getenv("SEARCH_ENRICHMENT_SEEDED_CATEGORY", "product"),
            "description": os.getenv(
                "SEARCH_ENRICHMENT_SEEDED_DESCRIPTION",
                "Approved truth record available for search enrichment.",
            ),
            "brand": os.getenv("SEARCH_ENRICHMENT_SEEDED_BRAND", ""),
        }

    ai_search_client = build_ai_search_indexing_client_from_env()
    search_indexing = SearchIndexingAdapter(ai_search_client) if ai_search_client else None

    return SearchEnrichmentAdapters(
        approved_truth=ApprovedTruthAdapter(seeded_truth=seeded_truth),
        search_indexing=search_indexing,
    )
