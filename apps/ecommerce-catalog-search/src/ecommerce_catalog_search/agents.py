"""Catalog search agent implementation and MCP tool registration (ACP-aware)."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

from holiday_peak_lib.adapters import BaseCRUDAdapter
from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.agents.base_agent import AgentDependencies
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer
from holiday_peak_lib.schemas.product import CatalogProduct
from holiday_peak_lib.schemas.truth import IntentClassification
from pydantic import ValidationError

try:
    from holiday_peak_lib.agents.prompt_loader import load_prompt_instructions
except ImportError:

    def load_prompt_instructions(*args: Any, **kwargs: Any) -> str:
        return ""


try:
    from holiday_peak_lib.evaluation import (
        intent_accuracy,
        mean_reciprocal_rank,
        ndcg_at_k,
        precision_at_k,
        run_evaluation,
    )
except ImportError:

    def run_evaluation(*args: Any, **kwargs: Any) -> dict[str, float]:
        return {}

    def precision_at_k(*args: Any, **kwargs: Any) -> float:
        return 0.0

    def mean_reciprocal_rank(*args: Any, **kwargs: Any) -> float:
        return 0.0

    def ndcg_at_k(*args: Any, **kwargs: Any) -> float:
        return 0.0

    def intent_accuracy(*args: Any, **kwargs: Any) -> float:
        return 0.0


from .adapters import (
    CatalogAdapters,
    build_catalog_adapters,
    merge_enriched_fields,
    normalize_search_mode,
)
from .ai_search import (
    AISearchDocumentResult,
    multi_query_search,
    search_catalog_skus_detailed,
)

logger = logging.getLogger(__name__)


class CatalogSearchAgent(BaseRetailAgent):
    """Agent that performs ACP-compliant catalog discovery."""

    def __init__(self, config: AgentDependencies, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)
        self._adapters = build_catalog_adapters()

    @property
    def adapters(self) -> CatalogAdapters:
        return self._adapters

    def _assess_complexity(self, request: dict[str, Any]) -> float:
        query = str(request.get("query") or "").strip()
        if not query:
            return 0.0

        sku_like = query.upper().startswith("SKU-") or query.replace("-", "").isalnum()
        if sku_like and len(query.split()) <= 2:
            return 0.1

        token_count = len(query.split())
        complexity = min(token_count / 12.0, 1.0)
        hints = (
            "compare",
            "best",
            "recommend",
            "difference",
            "instead",
            "for",
            "with",
        )
        if any(hint in query.lower() for hint in hints):
            complexity += 0.25
        if "?" in query or "," in query:
            complexity += 0.15
        return min(complexity, 1.0)

    def assess_complexity(self, query: str) -> float:
        """Public wrapper for complexity scoring used by MCP handlers/helpers."""
        return self._assess_complexity({"query": query})

    async def classify_intent(self, query: str) -> IntentClassification:
        """Classify query intent for intelligent path routing."""
        return await self._classify_intent(query)

    async def _classify_intent(self, query: str) -> IntentClassification:
        """Internal intent classification hook used by intelligent retrieval path."""
        baseline = IntentClassification(intent="keyword_lookup", confidence=0.0, entities={})
        if not query.strip() or not (self.slm or self.llm):
            return baseline

        messages = [
            {
                "role": "system",
                "content": (
                    "Classify ecommerce search intent and return strict JSON with keys: "
                    "intent (string), confidence (0..1), entities (object), reasoning (string)."
                ),
            },
            {
                "role": "user",
                "content": {"query": query},
            },
        ]

        try:
            response = await self.invoke_model(
                request={"query": query, "requires_multi_tool": True},
                messages=messages,
            )
            parsed = _parse_intent_response(response)
            return parsed or baseline
        except (RuntimeError, ValueError, TypeError, ValidationError):
            logger.warning(
                "catalog_intent_classification_failed",
                extra={"query_length": len(query)},
                exc_info=True,
            )
            return baseline

    def _build_sub_queries(self, query: str, intent: IntentClassification) -> list[str]:
        """Build unique sub-queries used for intelligent multi-query retrieval."""
        return _build_sub_queries(query=query, intent=intent)

    def build_sub_queries(self, query: str, intent: IntentClassification) -> list[str]:
        """Public wrapper used by integration helpers and tests."""
        return self._build_sub_queries(query, intent)

    def _merge_results(
        self,
        results_list: list[list[AISearchDocumentResult]],
        limit: int,
    ) -> list[AISearchDocumentResult]:
        """Merge ranked result batches by SKU and preserve strongest enrichment payloads."""
        if limit <= 0:
            return []

        merged: dict[str, dict[str, Any]] = {}
        for batch in results_list:
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
                entry["rank_bonus"] += max((limit - rank + 1) / max(limit, 1), 0.0)

                merged_candidate: AISearchDocumentResult = entry["candidate"]
                if len(candidate.enriched_fields) > len(merged_candidate.enriched_fields):
                    entry["candidate"] = candidate

        ranked = sorted(
            merged.values(),
            key=lambda item: (item["hits"], item["best_score"], item["rank_bonus"]),
            reverse=True,
        )
        return [item["candidate"] for item in ranked[:limit]]

    def merge_results(
        self,
        results_list: list[list[AISearchDocumentResult]],
        limit: int,
    ) -> list[AISearchDocumentResult]:
        """Public wrapper used by integration helpers and tests."""
        return self._merge_results(results_list, limit)

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        query = request.get("query", "")
        limit = int(request.get("limit", 5))
        mode = normalize_search_mode(str(request.get("mode") or "keyword"))
        filters = request.get("filters")
        filter_payload = filters if isinstance(filters, dict) else None

        self._trace_decision(
            decision="search_mode_selection",
            outcome=mode,
            metadata={
                "query_length": len(str(query)),
                "limit": limit,
            },
        )

        products, enrichment_by_sku, intent = await _search_products(
            self,
            self.adapters,
            query=query,
            limit=limit,
            mode=mode,
            filters=filter_payload,
        )
        availability = await _resolve_availability(self.adapters, products)
        acp_products = [
            merge_enriched_fields(
                self.adapters.mapping.to_acp_product(product, availability=availability[idx]),
                enrichment_by_sku.get(product.sku),
            )
            for idx, product in enumerate(products)
        ]
        baseline_products: list[CatalogProduct] = []
        if mode == "intelligent":
            baseline_products = await _search_products_keyword(
                self.adapters, query=query, limit=limit
            )

        _record_search_evaluation(
            self,
            query=str(query),
            mode=mode,
            products=products,
            baseline_products=baseline_products,
            intent=intent,
            limit=limit,
        )

        if self.slm or self.llm:
            messages = [
                {
                    "role": "system",
                    "content": _catalog_instructions(self.service_name or "catalog"),
                },
                {
                    "role": "user",
                    "content": {
                        "query": query,
                        "results": acp_products,
                    },
                },
            ]
            return await self.invoke_model(request=request, messages=messages)

        return {
            "service": self.service_name,
            "query": query,
            "mode": mode,
            "results": acp_products,
            "intent": intent.model_dump(mode="json") if intent is not None else None,
        }


def register_mcp_tools(mcp: FastAPIMCPServer, agent: BaseRetailAgent) -> None:
    """Expose MCP tools for ACP catalog search."""
    adapters = getattr(agent, "adapters", build_catalog_adapters())

    async def search_catalog(payload: dict[str, Any]) -> dict[str, Any]:
        query = payload.get("query", "")
        limit = int(payload.get("limit", 5))
        mode = normalize_search_mode(str(payload.get("mode") or "keyword"))
        filters = payload.get("filters")
        filter_payload = filters if isinstance(filters, dict) else None

        search_agent = agent if isinstance(agent, CatalogSearchAgent) else None
        products, enrichment_by_sku, intent = await _search_products(
            search_agent,
            adapters,
            query=query,
            limit=limit,
            mode=mode,
            filters=filter_payload,
        )
        availability = await _resolve_availability(adapters, products)
        results = [
            merge_enriched_fields(
                adapters.mapping.to_acp_product(product, availability=availability[idx]),
                enrichment_by_sku.get(product.sku),
            )
            for idx, product in enumerate(products)
        ]
        return {
            "query": query,
            "mode": mode,
            "intent": intent.model_dump(mode="json") if intent is not None else None,
            "results": results,
        }

    async def classify_catalog_intent(payload: dict[str, Any]) -> dict[str, Any]:
        query = str(payload.get("query") or "")
        if not query:
            return {"error": "query is required"}

        if isinstance(agent, CatalogSearchAgent):
            intent = await agent.classify_intent(query)
            complexity = agent.assess_complexity(query)
        else:
            intent = IntentClassification(intent="keyword_lookup", confidence=0.0, entities={})
            complexity = 0.0
        return {
            "query": query,
            "complexity": complexity,
            "intent": intent.model_dump(mode="json"),
        }

    async def get_product_details(payload: dict[str, Any]) -> dict[str, Any]:
        sku = payload.get("sku")
        if not sku:
            return {"error": "sku is required"}
        product = await adapters.products.get_product(str(sku))
        if product is None:
            return {"error": "not_found", "sku": sku}
        availability = await _availability_for_sku(adapters, product.sku)
        return {
            "product": adapters.mapping.to_acp_product(product, availability=availability),
        }

    mcp.add_tool("/catalog/search", search_catalog)
    mcp.add_tool("/catalog/intent", classify_catalog_intent)
    mcp.add_tool("/catalog/product", get_product_details)
    _register_crud_tools(mcp)


def _register_crud_tools(mcp: FastAPIMCPServer) -> None:
    crud_url = os.getenv("CRUD_SERVICE_URL")
    if not crud_url:
        return
    BaseCRUDAdapter(crud_url).register_mcp_tools(mcp)


def _catalog_instructions(service_name: str) -> str:
    return load_prompt_instructions(__file__, service_name)


def _coerce_query_to_sku(query: str) -> str:
    if not query:
        return "SKU-1"
    return f"SKU-{abs(hash(query)) % 1000}"


async def _search_products(
    agent: CatalogSearchAgent | None,
    adapters: CatalogAdapters,
    *,
    query: str,
    limit: int,
    mode: str,
    filters: dict[str, Any] | None,
) -> tuple[list[CatalogProduct], dict[str, dict[str, Any]], IntentClassification | None]:
    if mode == "intelligent":
        return await _search_products_intelligent(
            agent,
            adapters,
            query=query,
            limit=limit,
            filters=filters,
        )

    products = await _search_products_keyword(adapters, query=query, limit=limit)
    return products, {}, None


async def _search_products_keyword(
    adapters: CatalogAdapters,
    *,
    query: str,
    limit: int,
) -> list[CatalogProduct]:
    ai_search_result = await search_catalog_skus_detailed(query=query, limit=limit)
    ai_search_skus = ai_search_result.skus
    if ai_search_skus:
        resolved_products = await asyncio.gather(
            *[adapters.products.get_product(sku) for sku in ai_search_skus]
        )
        ai_search_products = [product for product in resolved_products if product is not None]
        if ai_search_products:
            return ai_search_products[:limit]

    if ai_search_result.fallback_reason is not None:
        logger.warning(
            "catalog_search_fallback_path",
            extra={
                "fallback_reason": ai_search_result.fallback_reason,
                "query_length": len(query),
                "limit": limit,
            },
        )

    primary_sku = _coerce_query_to_sku(query)
    primary = await adapters.products.get_product(primary_sku)
    related = await adapters.products.get_related(primary_sku, limit=max(limit - 1, 0))
    products = [p for p in [primary] if p is not None] + related
    return products[:limit]


async def _search_products_intelligent(
    agent: CatalogSearchAgent | None,
    adapters: CatalogAdapters,
    *,
    query: str,
    limit: int,
    filters: dict[str, Any] | None,
) -> tuple[list[CatalogProduct], dict[str, dict[str, Any]], IntentClassification | None]:
    if agent is None:
        products = await _search_products_keyword(adapters, query=query, limit=limit)
        return products, {}, None

    complexity = agent.assess_complexity(query)
    if complexity < agent.complexity_threshold:
        products = await _search_products_keyword(adapters, query=query, limit=limit)
        return (
            products,
            {},
            IntentClassification(
                intent="keyword_lookup",
                confidence=1.0,
                entities={"reason": "low_complexity"},
            ),
        )

    intent = await agent.classify_intent(query)
    if intent.confidence < 0.6:
        products = await _search_products_keyword(adapters, query=query, limit=limit)
        return products, {}, intent

    sub_queries = agent.build_sub_queries(query=query, intent=intent)
    ranked_batches = [
        await multi_query_search(sub_queries=sub_queries, filters=filters, top_k=limit)
    ]
    ranked = agent.merge_results(ranked_batches, limit)
    intelligent_products, enrichment_by_sku = await _resolve_ranked_products(
        adapters,
        ranked,
        limit,
    )
    if intelligent_products:
        return intelligent_products, enrichment_by_sku, intent

    products = await _search_products_keyword(adapters, query=query, limit=limit)
    return products, {}, intent


def _build_sub_queries(query: str, intent: IntentClassification) -> list[str]:
    sub_queries = [query.strip()] if query.strip() else []
    entities = intent.entities if isinstance(intent.entities, dict) else {}
    for key in ("category", "brand", "use_case", "features", "keywords"):
        value = entities.get(key)
        if isinstance(value, str) and value.strip():
            sub_queries.append(value.strip())
        elif isinstance(value, list):
            sub_queries.extend(
                item.strip() for item in value if isinstance(item, str) and item.strip()
            )
    unique: list[str] = []
    seen: set[str] = set()
    for candidate in sub_queries:
        normalized = candidate.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        unique.append(candidate)
    return unique


async def _resolve_ranked_products(
    adapters: CatalogAdapters,
    ranked_results: list[AISearchDocumentResult],
    limit: int,
) -> tuple[list[CatalogProduct], dict[str, dict[str, Any]]]:
    if not ranked_results:
        return [], {}

    products: list[CatalogProduct] = []
    enrichment_by_sku: dict[str, dict[str, Any]] = {}
    for result in ranked_results[:limit]:
        product = await adapters.products.get_product(result.sku)
        if product is None:
            continue
        products.append(product)
        enrichment_by_sku[result.sku] = result.enriched_fields
    return products[:limit], enrichment_by_sku


def _parse_intent_response(response: dict[str, Any]) -> IntentClassification | None:
    payload: Any = response
    if isinstance(response, dict):
        for key in ("intent", "confidence"):
            if key in response:
                payload = response
                break
        else:
            payload = response.get("content") or response.get("output") or response

    if isinstance(payload, str):
        normalized = payload.strip()
        if normalized.startswith("```"):
            normalized = normalized.strip("`")
            normalized = normalized.replace("json", "", 1).strip()
        try:
            payload = json.loads(normalized)
        except json.JSONDecodeError:
            return None

    if not isinstance(payload, dict):
        return None

    try:
        return IntentClassification.model_validate(payload)
    except ValidationError:
        return None


async def _resolve_availability(
    adapters: CatalogAdapters, products: list[CatalogProduct]
) -> list[str]:
    inventory = await asyncio.gather(
        *[adapters.inventory.get_item(product.sku) for product in products]
    )
    availability: list[str] = []
    for item in inventory:
        if item is None:
            availability.append("unknown")
        elif item.available > 0:
            availability.append("in_stock")
        else:
            availability.append("out_of_stock")
    return availability


async def _availability_for_sku(adapters: CatalogAdapters, sku: str) -> str:
    item = await adapters.inventory.get_item(sku)
    if item is None:
        return "unknown"
    return "in_stock" if item.available > 0 else "out_of_stock"


def _record_search_evaluation(
    agent: CatalogSearchAgent,
    *,
    query: str,
    mode: str,
    products: list[CatalogProduct],
    baseline_products: list[CatalogProduct],
    intent: IntentClassification | None,
    limit: int,
) -> None:
    ranked_skus = [product.sku for product in products]
    baseline_skus = [product.sku for product in baseline_products]

    top_k = max(1, min(10, max(len(ranked_skus), 1), max(limit, 1)))
    relevance = {sku: float(max(top_k - index, 1)) for index, sku in enumerate(ranked_skus[:top_k])}

    anchor_relevant = {ranked_skus[0]} if ranked_skus else set()
    overlap = len(set(ranked_skus[:top_k]) & set(baseline_skus[:top_k]))
    overlap_ratio = overlap / max(1, min(top_k, len(ranked_skus), len(baseline_skus) or 1))

    expected_intent = (
        "keyword_lookup"
        if mode != "intelligent"
        else (intent.intent if intent else "keyword_lookup")
    )
    predicted_intent = intent.intent if intent else "keyword_lookup"

    def _evaluator(_dataset: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "query": query,
            "mode": mode,
            "results_count": float(len(ranked_skus)),
            "ndcg_at_10": ndcg_at_k(ranked_skus, relevance, top_k),
            "mrr": mean_reciprocal_rank([ranked_skus], anchor_relevant),
            "precision_at_10": precision_at_k(ranked_skus, anchor_relevant, top_k),
            "intent_accuracy": intent_accuracy([predicted_intent], [expected_intent]),
            "agentic_keyword_overlap_at_10": float(overlap_ratio),
        }

    result = run_evaluation(
        dataset=[{"query": query, "mode": mode, "top_k": top_k}],
        evaluator=_evaluator,
        run_name="ecommerce-catalog-search",
    )
    agent._get_foundry_tracer().record_evaluation(  # pylint: disable=protected-access
        {
            "domain": "search",
            "backend": result.backend,
            "status": result.status,
            "metrics": result.metrics,
            "details": result.details,
        }
    )
