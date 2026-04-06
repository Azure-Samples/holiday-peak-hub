"""Catalog search agent implementation and MCP tool registration (ACP-aware)."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from holiday_peak_lib.adapters import BaseCRUDAdapter
from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.agents.base_agent import AgentDependencies
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer
from holiday_peak_lib.agents.memory import (
    NamespaceContext,
    build_canonical_memory_key,
    resolve_namespace_context,
)
from holiday_peak_lib.schemas.product import CatalogProduct
from holiday_peak_lib.schemas.truth import IntentClassification
from pydantic import ValidationError

try:
    from holiday_peak_lib.agents.prompt_loader import load_prompt_instructions
except ImportError:

    def load_prompt_instructions(*_args: Any, **_kwargs: Any) -> str:
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

    def run_evaluation(*_args: Any, **_kwargs: Any) -> Any:
        return SimpleNamespace(backend="disabled", status="skipped", metrics={}, details={})

    def precision_at_k(*_args: Any, **_kwargs: Any) -> float:
        return 0.0

    def mean_reciprocal_rank(*_args: Any, **_kwargs: Any) -> float:
        return 0.0

    def ndcg_at_k(*_args: Any, **_kwargs: Any) -> float:
        return 0.0

    def intent_accuracy(*_args: Any, **_kwargs: Any) -> float:
        return 0.0


from .adapters import (
    CatalogAdapters,
    build_catalog_adapters,
    merge_enriched_fields,
    normalize_search_mode,
)
from .ai_search import (
    AISearchDocumentResult,
    ai_search_required_runtime_enabled,
    multi_query_search,
    search_catalog_skus_detailed,
)

logger = logging.getLogger(__name__)


HOT_HISTORY_MAX_ENTRIES = 20
HOT_HISTORY_TTL_SECONDS = 3600
INTENT_CONFIDENCE_THRESHOLD = 0.55
GENERIC_KEYWORD_LIMIT = 8
QUERY_EXPANSION_QUERY_LIMIT = 4
DEGRADED_MODEL_FALLBACK_MESSAGE = (
    "Showing the best available catalog guidance while intelligent generation "
    "is temporarily unavailable."
)

_LEXICAL_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

GENERIC_KEYWORD_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "be",
        "best",
        "by",
        "for",
        "from",
        "how",
        "i",
        "in",
        "is",
        "it",
        "me",
        "my",
        "of",
        "on",
        "or",
        "please",
        "recommend",
        "show",
        "suggest",
        "that",
        "the",
        "to",
        "what",
        "which",
        "with",
        "you",
        "your",
    }
)

LEXICAL_CANONICAL_OVERRIDES: dict[str, str] = {
    "bags": "bag",
    "backpacks": "backpack",
    "headphones": "headphone",
    "laptops": "laptop",
    "phones": "phone",
    "shoes": "shoe",
    "sneakers": "sneaker",
    "watches": "watch",
    "wearing": "wear",
    "wears": "wear",
    "wore": "wear",
}


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
        fallback_intent = _deterministic_intent_policy(query)
        if not query.strip() or not (self.slm or self.llm):
            return fallback_intent

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
            response = await asyncio.wait_for(
                self.invoke_model(
                    request={"query": query, "requires_multi_tool": True},
                    messages=messages,
                ),
                timeout=_resolve_timeout_seconds(
                    "CATALOG_INTENT_MODEL_TIMEOUT_SECONDS",
                    8.0,
                ),
            )
            parsed = _parse_intent_response(response)
            return _merge_intent_with_fallback(parsed, fallback_intent, query)
        except asyncio.TimeoutError:
            logger.warning(
                "catalog_intent_classification_timeout",
                extra={"query_length": len(query)},
            )
            return fallback_intent
        except Exception:  # pylint: disable=broad-exception-caught
            logger.warning(
                "catalog_intent_classification_failed",
                extra={"query_length": len(query)},
                exc_info=True,
            )
            return fallback_intent

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
        requested_mode = str(request.get("mode") or "intelligent")
        mode = normalize_search_mode(requested_mode)
        search_stage = _normalize_search_stage(request.get("search_stage"))
        user_id = _coerce_optional_str(request.get("user_id"))
        user_ip = _coerce_optional_str(request.get("user_ip"))
        query_history = _coerce_optional_string_list(request.get("query_history"))
        baseline_candidate_skus = _coerce_optional_string_list(
            request.get("baseline_candidate_skus")
        )
        namespace_context = resolve_namespace_context(
            request,
            self.service_name or "catalog-search",
            session_fallback=user_id or user_ip,
        )
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

        history_record = _build_search_history_record(
            query=str(query),
            mode=mode,
            search_stage=search_stage,
            result_skus=[product.sku for product in products],
            user_id=user_id,
            user_ip=user_ip,
            query_history=query_history,
            baseline_candidate_skus=baseline_candidate_skus,
        )
        await _persist_search_history(self, namespace_context, history_record)

        summary, recommendation = _build_catalog_fallback_answer(
            query=str(query),
            products=products,
            intent=intent,
        )

        deterministic_response: dict[str, Any] = {
            "service": self.service_name,
            "query": query,
            "mode": mode,
            "requested_mode": requested_mode,
            "search_stage": search_stage,
            "session_id": namespace_context.session_id,
            "results": acp_products,
            "intent": intent.model_dump(mode="json") if intent is not None else None,
            "summary": summary,
            "recommendation": recommendation,
            "answer_source": "agent_fallback",
            "result_type": "deterministic",
            "degraded": False,
            "model_attempted": False,
        }

        if self.slm or self.llm:
            deterministic_response["model_attempted"] = True
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
                        "fallback_summary": summary,
                        "fallback_recommendation": recommendation,
                    },
                },
            ]
            try:
                model_response = await asyncio.wait_for(
                    self.invoke_model(request=request, messages=messages),
                    timeout=_resolve_timeout_seconds(
                        "CATALOG_RESPONSE_MODEL_TIMEOUT_SECONDS",
                        14.0,
                    ),
                )
                model_response["requested_mode"] = requested_mode
                model_response["search_stage"] = search_stage
                model_response["session_id"] = namespace_context.session_id
                model_response["answer_source"] = "agent_model"
                model_response["result_type"] = "model_answer"
                model_response["degraded"] = False
                model_response["model_attempted"] = True
                model_response["model_status"] = "success"
                return model_response
            except asyncio.TimeoutError:
                logger.warning(
                    "catalog_search_model_response_timeout",
                    extra={
                        "query_length": len(str(query)),
                        "mode": mode,
                        "search_stage": search_stage,
                    },
                )
                deterministic_response.update(
                    {
                        "result_type": "degraded_fallback",
                        "degraded": True,
                        "degraded_reason": "model_timeout",
                        "degraded_message": DEGRADED_MODEL_FALLBACK_MESSAGE,
                        "fallback_keywords": _build_fallback_keywords(str(query), intent),
                        "model_status": "timeout",
                    }
                )
            except Exception:  # pylint: disable=broad-exception-caught
                logger.warning(
                    "catalog_search_model_response_fallback",
                    extra={
                        "query_length": len(str(query)),
                        "mode": mode,
                        "search_stage": search_stage,
                    },
                    exc_info=True,
                )
                deterministic_response.update(
                    {
                        "result_type": "degraded_fallback",
                        "degraded": True,
                        "degraded_reason": "model_error",
                        "degraded_message": DEGRADED_MODEL_FALLBACK_MESSAGE,
                        "fallback_keywords": _build_fallback_keywords(str(query), intent),
                        "model_status": "error",
                    }
                )

        return deterministic_response


def register_mcp_tools(mcp: FastAPIMCPServer, agent: BaseRetailAgent) -> None:
    """Expose MCP tools for ACP catalog search."""
    adapters = getattr(agent, "adapters", build_catalog_adapters())

    async def search_catalog(payload: dict[str, Any]) -> dict[str, Any]:
        query = payload.get("query", "")
        limit = int(payload.get("limit", 5))
        mode = normalize_search_mode(str(payload.get("mode") or "intelligent"))
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
            intent = _deterministic_intent_policy(query)
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


def _tokenize_lexical_terms(value: str) -> set[str]:
    raw_tokens = set(_LEXICAL_TOKEN_PATTERN.findall(value.lower()))
    expanded_tokens = set(raw_tokens)
    for token in raw_tokens:
        normalized = _normalize_lexical_token(token)
        if normalized:
            expanded_tokens.add(normalized)
    return expanded_tokens


def _normalize_lexical_token(token: str) -> str:
    normalized = LEXICAL_CANONICAL_OVERRIDES.get(token, token)

    if normalized.endswith("ies") and len(normalized) > 4:
        normalized = f"{normalized[:-3]}y"
    elif normalized.endswith("ing") and len(normalized) > 5:
        normalized = normalized[:-3]
    elif normalized.endswith("ed") and len(normalized) > 4:
        normalized = normalized[:-2]
    elif normalized.endswith("es") and len(normalized) > 4:
        normalized = normalized[:-2]
    elif normalized.endswith("s") and len(normalized) > 3:
        normalized = normalized[:-1]

    return LEXICAL_CANONICAL_OVERRIDES.get(normalized, normalized)


def _coerce_keyword_list(raw_keywords: Any) -> list[str]:
    if isinstance(raw_keywords, str):
        value = raw_keywords.strip()
        return [value] if value else []

    if not isinstance(raw_keywords, list):
        return []

    return [item.strip() for item in raw_keywords if isinstance(item, str) and item.strip()]


def _build_fallback_keywords(
    query: str,
    intent: IntentClassification | None,
) -> list[str]:
    raw_keywords: list[str] = []

    if intent is not None and isinstance(intent.entities, dict):
        raw_keywords.extend(_coerce_keyword_list(intent.entities.get("keywords")))

    raw_keywords.extend(_LEXICAL_TOKEN_PATTERN.findall(query.lower()))

    deduplicated: list[str] = []
    seen_keywords: set[str] = set()
    for keyword in raw_keywords:
        value = keyword.strip()
        if not value:
            continue

        normalized = value.lower()
        if normalized in seen_keywords:
            continue

        seen_keywords.add(normalized)
        deduplicated.append(value)
        if len(deduplicated) >= GENERIC_KEYWORD_LIMIT:
            break

    return deduplicated


def _deterministic_intent_policy(query: str) -> IntentClassification:
    normalized_query = query.strip()
    if not normalized_query:
        return IntentClassification(
            intent="keyword_lookup",
            queryType="simple",
            useCase="product discovery",
            confidence=0.0,
            entities={},
            reasoning="Empty query defaults to generic keyword lookup.",
        )

    tokens = _tokenize_lexical_terms(normalized_query)
    keywords = _extract_generic_keywords(tokens)
    query_type = "complex" if _is_complex_query(normalized_query, tokens) else "simple"
    intent_name = "semantic_search" if query_type == "complex" else "keyword_lookup"
    confidence = 0.72 if intent_name == "semantic_search" else 0.56

    return IntentClassification(
        intent=intent_name,
        queryType=query_type,
        useCase="product discovery",
        confidence=confidence,
        entities={"keywords": keywords},
        reasoning="Generic deterministic fallback derived from query complexity and keywords.",
    )


def _is_sku_like_query(query: str) -> bool:
    normalized = query.strip()
    if not normalized:
        return False
    return normalized.upper().startswith("SKU-") or normalized.replace("-", "").isalnum()


def _is_complex_query(query: str, tokens: set[str]) -> bool:
    complexity_hints = {
        "alternative",
        "alternatives",
        "best",
        "compare",
        "difference",
        "recommend",
        "under",
        "versus",
        "vs",
    }
    return len(tokens) >= 7 or "?" in query or bool(tokens & complexity_hints)


def _dedupe_keywords(raw_keywords: list[str]) -> list[str]:
    deduplicated: list[str] = []
    seen: set[str] = set()
    for keyword in raw_keywords:
        normalized = keyword.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduplicated.append(normalized)
        if len(deduplicated) >= GENERIC_KEYWORD_LIMIT:
            break
    return deduplicated


def _extract_generic_keywords(tokens: set[str]) -> list[str]:
    candidate_keywords = [
        token
        for token in sorted(tokens)
        if len(token) >= 3 and token not in GENERIC_KEYWORD_STOPWORDS
    ]
    return _dedupe_keywords(candidate_keywords)


def _merge_intent_with_fallback(
    parsed_intent: IntentClassification | None,
    fallback_intent: IntentClassification,
    query: str,
) -> IntentClassification:
    if parsed_intent is None:
        return fallback_intent

    resolved_intent = parsed_intent.model_copy(deep=True)
    fallback_entities = (
        dict(fallback_intent.entities) if isinstance(fallback_intent.entities, dict) else {}
    )
    resolved_entities = (
        dict(resolved_intent.entities) if isinstance(resolved_intent.entities, dict) else {}
    )

    if not resolved_intent.intent:
        resolved_intent.intent = fallback_intent.intent
    if resolved_intent.query_type is None:
        resolved_intent.query_type = fallback_intent.query_type
    if not resolved_intent.use_case:
        resolved_intent.use_case = fallback_intent.use_case
    if not resolved_intent.category and fallback_intent.category:
        resolved_intent.category = fallback_intent.category
    if not resolved_intent.brand and fallback_intent.brand:
        resolved_intent.brand = fallback_intent.brand

    parsed_keywords = _coerce_keyword_list(resolved_entities.get("keywords"))
    fallback_keywords = _coerce_keyword_list(fallback_entities.get("keywords"))
    if not parsed_keywords:
        parsed_keywords = _extract_generic_keywords(_tokenize_lexical_terms(query))

    merged_keywords = _dedupe_keywords(parsed_keywords + fallback_keywords)
    if merged_keywords:
        resolved_entities["keywords"] = merged_keywords

    resolved_intent.entities = resolved_entities

    if (
        resolved_intent.confidence < 0.25
        and fallback_intent.confidence >= resolved_intent.confidence
    ):
        return fallback_intent

    return resolved_intent


def _should_run_semantic_pass(intent: IntentClassification | None) -> bool:
    if intent is None:
        return False
    intent_name = str(intent.intent or "").lower()
    return intent_name != "keyword_lookup" and intent.confidence >= INTENT_CONFIDENCE_THRESHOLD


def _product_search_text(product: CatalogProduct) -> str:
    values: list[str] = [
        product.name,
        product.description or "",
        product.category or "",
        product.brand or "",
        *[tag for tag in product.tags if isinstance(tag, str)],
    ]
    for value in product.attributes.values():
        if isinstance(value, str):
            values.append(value)
        elif isinstance(value, list):
            values.extend(str(item) for item in value if isinstance(item, (str, int, float)))
    return " ".join(values).lower()


def _rank_products_by_query_relevance(
    *,
    query: str,
    products: list[CatalogProduct],
    limit: int,
) -> list[CatalogProduct]:
    if limit <= 0:
        return []

    query_tokens = _tokenize_lexical_terms(query)
    ranked_entries: dict[str, tuple[CatalogProduct, int, int]] = {}
    for index, product in enumerate(products):
        product_tokens = _tokenize_lexical_terms(_product_search_text(product))
        overlap_score = len(query_tokens & product_tokens)
        existing = ranked_entries.get(product.sku)
        if existing is None or overlap_score > existing[1]:
            ranked_entries[product.sku] = (product, overlap_score, index)

    ranked = sorted(
        ranked_entries.values(),
        key=lambda entry: (-entry[1], entry[2], entry[0].sku),
    )
    return [entry[0] for entry in ranked[:limit]]


async def _expand_products_with_sub_queries(
    *,
    adapters: CatalogAdapters,
    query: str,
    baseline_products: list[CatalogProduct],
    sub_queries: list[str],
    limit: int,
) -> list[CatalogProduct]:
    if limit <= 0:
        return []

    expansion_queries: list[str] = []
    seen_queries: set[str] = {query.strip().lower()}
    for candidate in sub_queries:
        normalized = candidate.strip().lower()
        if not normalized or normalized in seen_queries:
            continue
        seen_queries.add(normalized)
        expansion_queries.append(candidate.strip())
        if len(expansion_queries) >= QUERY_EXPANSION_QUERY_LIMIT:
            break

    if not expansion_queries:
        return baseline_products[:limit]

    expanded_batches = await asyncio.gather(
        *[
            _search_products_keyword(
                adapters,
                query=expanded_query,
                limit=limit,
            )
            for expanded_query in expansion_queries
        ],
        return_exceptions=True,
    )

    expanded_products = list(baseline_products)
    for batch in expanded_batches:
        if isinstance(batch, list):
            expanded_products.extend(
                product for product in batch if isinstance(product, CatalogProduct)
            )

    return _rank_products_by_query_relevance(
        query=query,
        products=expanded_products,
        limit=limit,
    )


async def _search_products_text_fallback(
    adapters: CatalogAdapters,
    *,
    query: str,
    limit: int,
) -> list[CatalogProduct]:
    search = getattr(adapters.products, "search", None)
    if search is None or not query.strip() or limit <= 0:
        return []

    try:
        try:
            result = search(query=query, limit=limit)
        except TypeError:
            result = search(query, limit=limit)

        if hasattr(result, "__await__"):
            result = await result
    except Exception:  # pylint: disable=broad-exception-caught
        logger.warning(
            "catalog_search_text_fallback_error",
            extra={"query_length": len(query), "limit": limit},
            exc_info=True,
        )
        return []

    if not isinstance(result, list):
        return []
    return [product for product in result if isinstance(product, CatalogProduct)][:limit]


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
    return products, {}, _deterministic_intent_policy(query)


async def _search_products_keyword(
    adapters: CatalogAdapters,
    *,
    query: str,
    limit: int,
) -> list[CatalogProduct]:
    ai_search_result = await search_catalog_skus_detailed(query=query, limit=limit)
    ai_search_skus = ai_search_result.skus
    strict_mode = ai_search_required_runtime_enabled()
    if ai_search_skus:
        resolved_products = await asyncio.gather(
            *[adapters.products.get_product(sku) for sku in ai_search_skus],
            return_exceptions=False,
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

    if strict_mode and ai_search_result.fallback_reason is not None:
        logger.warning(
            "catalog_search_strict_mode_blocked_fallback",
            extra={
                "fallback_reason": ai_search_result.fallback_reason,
                "query_length": len(query),
                "limit": limit,
            },
        )
        return []

    if not _is_sku_like_query(query):
        text_fallback_products = await _search_products_text_fallback(
            adapters,
            query=query,
            limit=limit,
        )
        if text_fallback_products:
            return text_fallback_products

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
    baseline_products = await _search_products_keyword(adapters, query=query, limit=limit)
    fallback_intent = _deterministic_intent_policy(query)

    if agent is None:
        return baseline_products, {}, fallback_intent

    intent = await agent.classify_intent(query)
    sub_queries = agent.build_sub_queries(query=query, intent=intent)

    if not _should_run_semantic_pass(intent):
        expanded_products = await _expand_products_with_sub_queries(
            adapters=adapters,
            query=query,
            baseline_products=baseline_products,
            sub_queries=sub_queries,
            limit=limit,
        )
        return expanded_products, {}, intent

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

    expanded_products = await _expand_products_with_sub_queries(
        adapters=adapters,
        query=query,
        baseline_products=baseline_products,
        sub_queries=sub_queries,
        limit=limit,
    )
    return expanded_products, {}, intent


def _build_sub_queries(query: str, intent: IntentClassification) -> list[str]:
    sub_queries = [query.strip()] if query.strip() else []

    if intent.use_case:
        sub_queries.append(intent.use_case)
    if intent.category:
        sub_queries.append(intent.category)
    if intent.brand:
        sub_queries.append(intent.brand)
    sub_queries.extend(
        item.strip() for item in intent.sub_queries if isinstance(item, str) and item.strip()
    )
    sub_queries.extend(
        item.strip() for item in intent.attributes if isinstance(item, str) and item.strip()
    )

    entities = intent.entities if isinstance(intent.entities, dict) else {}
    for key in (
        "category",
        "brand",
        "use_case",
        "useCase",
        "features",
        "keywords",
        "sub_queries",
        "subQueries",
        "attributes",
    ):
        value = entities.get(key)
        if isinstance(value, str) and value.strip():
            sub_queries.append(value.strip())
        elif isinstance(value, list):
            sub_queries.extend(
                item.strip() for item in value if isinstance(item, str) and item.strip()
            )

    if len(sub_queries) <= 1:
        sub_queries.extend(_extract_generic_keywords(_tokenize_lexical_terms(query)))

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
        *[adapters.inventory.get_item(product.sku) for product in products],
        return_exceptions=False,
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


def _normalize_search_stage(raw_value: Any) -> str:
    stage = str(raw_value or "baseline").strip().lower()
    return stage if stage in {"baseline", "rerank"} else "baseline"


def _coerce_optional_str(raw_value: Any) -> str | None:
    if raw_value is None:
        return None
    value = str(raw_value).strip()
    return value or None


def _resolve_timeout_seconds(environment_variable: str, default_seconds: float) -> float:
    raw_value = os.getenv(environment_variable)
    if raw_value is None:
        return default_seconds

    try:
        resolved = float(raw_value)
    except (TypeError, ValueError):
        return default_seconds

    return resolved if resolved > 0 else default_seconds


def _build_catalog_fallback_answer(
    *,
    query: str,
    products: list[CatalogProduct],
    intent: IntentClassification | None,
) -> tuple[str, str]:
    normalized_query = query.strip()

    if not products:
        entities = (
            intent.entities if intent is not None and isinstance(intent.entities, dict) else {}
        )
        keywords = _coerce_keyword_list(entities.get("keywords"))
        keyword_hint = ", ".join(keywords[:4])
        if keyword_hint:
            return (
                "No exact products were returned in time.",
                (
                    f"For '{normalized_query}', try narrowing by terms like {keyword_hint}, "
                    "or add a brand, budget, or must-have feature."
                ),
            )

        return (
            "No catalog matches were available in time.",
            "Try refining your query with product type, brand, budget, and key features.",
        )

    highlighted = ", ".join(product.name for product in products[:3])
    if intent is not None and _should_run_semantic_pass(intent):
        return (
            "Recommended products were selected using semantic and keyword retrieval.",
            (
                f"Top options are {highlighted}. Add constraints like budget, brand, "
                "or feature preferences to refine further."
            ),
        )

    return (
        "Recommended products were selected from your request.",
        f"Best matches are {highlighted}. Refine with additional details for tighter ranking.",
    )


def _coerce_optional_string_list(raw_value: Any) -> list[str] | None:
    if raw_value is None:
        return None
    if not isinstance(raw_value, list):
        return None

    values = [str(item).strip() for item in raw_value]
    return [value for value in values if value]


def _build_search_history_record(
    *,
    query: str,
    mode: str,
    search_stage: str,
    result_skus: list[str],
    user_id: str | None,
    user_ip: str | None,
    query_history: list[str] | None,
    baseline_candidate_skus: list[str] | None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "query": query,
        "mode": mode,
        "search_stage": search_stage,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "result_skus": result_skus,
    }

    if user_id:
        record["user_id"] = user_id
    if user_ip:
        record["user_ip"] = user_ip
    if query_history is not None:
        record["query_history"] = query_history
    if baseline_candidate_skus is not None:
        record["baseline_candidate_skus"] = baseline_candidate_skus
    return record


async def _persist_search_history(
    agent: CatalogSearchAgent,
    namespace_context: NamespaceContext,
    record: dict[str, Any],
) -> None:
    record_id = (
        f"{namespace_context.service}:{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        f":{uuid4().hex}"
    )
    persisted_record = {
        "id": record_id,
        "service": namespace_context.service,
        "tenant_id": namespace_context.tenant_id,
        "session_id": namespace_context.session_id,
        **record,
    }

    hot_history_key = build_canonical_memory_key(namespace_context, "catalog-search-history")
    if agent.hot_memory:
        try:
            existing = await agent.hot_memory.get(hot_history_key)
            history = _parse_hot_history(existing)
            history.append(record)
            history = history[-HOT_HISTORY_MAX_ENTRIES:]
            await agent.hot_memory.set(
                key=hot_history_key,
                value=json.dumps(history),
                ttl_seconds=HOT_HISTORY_TTL_SECONDS,
            )
        except Exception:  # pylint: disable=broad-exception-caught
            logger.warning(
                "catalog_search_hot_memory_persist_failed",
                extra={
                    "service": namespace_context.service,
                    "tenant_id": namespace_context.tenant_id,
                    "session_id": namespace_context.session_id,
                },
                exc_info=True,
            )

    if agent.warm_memory:
        try:
            await agent.warm_memory.upsert(persisted_record)
        except Exception:  # pylint: disable=broad-exception-caught
            logger.warning(
                "catalog_search_warm_memory_persist_failed",
                extra={
                    "service": namespace_context.service,
                    "tenant_id": namespace_context.tenant_id,
                    "session_id": namespace_context.session_id,
                    "record_id": record_id,
                },
                exc_info=True,
            )

    if agent.cold_memory:
        try:
            blob_name = (
                f"{namespace_context.service}/search-history/tenant={namespace_context.tenant_id}"
                f"/session={namespace_context.session_id}/{record_id}.json"
            )
            await agent.cold_memory.upload_text(
                blob_name=blob_name,
                data=json.dumps(persisted_record),
            )
        except Exception:  # pylint: disable=broad-exception-caught
            logger.warning(
                "catalog_search_cold_memory_persist_failed",
                extra={
                    "service": namespace_context.service,
                    "tenant_id": namespace_context.tenant_id,
                    "session_id": namespace_context.session_id,
                    "record_id": record_id,
                },
                exc_info=True,
            )


def _parse_hot_history(raw_value: Any) -> list[dict[str, Any]]:
    payload = raw_value
    if isinstance(raw_value, str):
        try:
            payload = json.loads(raw_value)
        except json.JSONDecodeError:
            return []

    if isinstance(payload, list):
        return [entry for entry in payload if isinstance(entry, dict)]
    if isinstance(payload, dict):
        return [payload]
    return []


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
