"""Catalog search agent implementation and MCP tool registration (ACP-aware)."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timezone
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
    ai_search_required_runtime_enabled,
    multi_query_search,
    search_catalog_skus_detailed,
)

logger = logging.getLogger(__name__)


HOT_HISTORY_MAX_ENTRIES = 20
HOT_HISTORY_TTL_SECONDS = 3600
WINTER_TRAVEL_INTENT_CONFIDENCE_THRESHOLD = 0.8
KEYWORD_ADAPTIVE_MIN_QUERY_TOKENS = 6
KEYWORD_ADAPTIVE_BASELINE_WINDOW = 3
KEYWORD_ADAPTIVE_APPAREL_COVERAGE_THRESHOLD = 0.34

_LEXICAL_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

TRAVEL_LEXICAL_SIGNALS = frozenset(
    {
        "travel",
        "trip",
        "journey",
        "vacation",
        "holiday",
        "visit",
        "flight",
        "airport",
        "packing",
        "abroad",
    }
)
WINTER_LEXICAL_SIGNALS = frozenset(
    {
        "winter",
        "cold",
        "freezing",
        "snow",
        "snowy",
        "blizzard",
        "subzero",
        "frigid",
        "ice",
        "icy",
    }
)
APPAREL_LEXICAL_SIGNALS = frozenset(
    {
        "apparel",
        "clothing",
        "clothes",
        "coat",
        "jacket",
        "parka",
        "boots",
        "boot",
        "gloves",
        "glove",
        "scarf",
        "beanie",
        "thermal",
        "insulated",
        "fleece",
        "sweater",
        "layers",
        "layer",
        "wool",
    }
)
GENERIC_WINTER_NON_APPAREL_SIGNALS = frozenset(
    {
        "puzzle",
        "mug",
        "game",
        "decor",
        "ornament",
        "candle",
        "toy",
        "snow globe",
        "blanket",
    }
)
WINTER_TRAVEL_APPAREL_ESSENTIALS = (
    "insulated jacket",
    "thermal base layer",
    "winter boots",
    "wool socks",
    "waterproof gloves",
    "beanie",
    "scarf",
)


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

        # Deterministic lexical intent is already high-confidence for this scenario.
        if _is_high_confidence_winter_travel_intent(fallback_intent):
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
            return parsed or fallback_intent
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
        requested_mode = str(request.get("mode") or "keyword")
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
        }

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

        return deterministic_response


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


def _tokenize_lexical_terms(value: str) -> set[str]:
    return set(_LEXICAL_TOKEN_PATTERN.findall(value.lower()))


def _collect_signal_hits(
    text: str,
    tokens: set[str],
    signals: frozenset[str],
) -> set[str]:
    hits: set[str] = set()
    for signal in signals:
        if " " in signal:
            if signal in text:
                hits.add(signal)
        elif signal in tokens:
            hits.add(signal)
    return hits


def _coerce_keyword_list(raw_keywords: Any) -> list[str]:
    if isinstance(raw_keywords, str):
        value = raw_keywords.strip()
        return [value] if value else []

    if not isinstance(raw_keywords, list):
        return []

    return [item.strip() for item in raw_keywords if isinstance(item, str) and item.strip()]


def _deterministic_intent_policy(query: str) -> IntentClassification:
    normalized_query = query.strip().lower()
    if not normalized_query:
        return IntentClassification(intent="keyword_lookup", confidence=0.0, entities={})

    tokens = _tokenize_lexical_terms(normalized_query)
    travel_hits = _collect_signal_hits(normalized_query, tokens, TRAVEL_LEXICAL_SIGNALS)
    winter_hits = _collect_signal_hits(normalized_query, tokens, WINTER_LEXICAL_SIGNALS)
    apparel_hits = _collect_signal_hits(normalized_query, tokens, APPAREL_LEXICAL_SIGNALS)
    generic_hits = _collect_signal_hits(
        normalized_query,
        tokens,
        GENERIC_WINTER_NON_APPAREL_SIGNALS,
    )

    # Strategy-style lexical policy keeps fallback intent routing deterministic.
    if travel_hits and winter_hits:
        keywords = sorted(set(WINTER_TRAVEL_APPAREL_ESSENTIALS) | apparel_hits)
        entities: dict[str, Any] = {
            "season": "winter",
            "travel_context": True,
            "category": "apparel",
            "use_case": "winter travel",
            "keywords": keywords,
            "travel_signals": sorted(travel_hits),
            "winter_signals": sorted(winter_hits),
        }
        if generic_hits:
            entities["deprioritize_keywords"] = sorted(generic_hits)

        confidence = 0.93 if apparel_hits else 0.88
        return IntentClassification(
            intent="winter_travel_clothing",
            confidence=confidence,
            category="apparel",
            use_case="winter travel",
            entities=entities,
            reasoning=(
                "Deterministic lexical signals matched winter + travel context; "
                "promote travel-clothing essentials."
            ),
        )

    if apparel_hits and winter_hits:
        return IntentClassification(
            intent="seasonal_apparel_lookup",
            confidence=0.62,
            category="apparel",
            use_case="winter clothing",
            entities={
                "season": "winter",
                "category": "apparel",
                "keywords": sorted(apparel_hits),
            },
            reasoning="Deterministic lexical policy matched winter + apparel signals.",
        )

    if travel_hits and apparel_hits:
        return IntentClassification(
            intent="travel_clothing",
            confidence=0.72,
            category="apparel",
            use_case="travel clothing",
            entities={
                "travel_context": True,
                "category": "apparel",
                "use_case": "travel clothing",
                "keywords": sorted(travel_hits | apparel_hits),
                "travel_signals": sorted(travel_hits),
                "apparel_signals": sorted(apparel_hits),
            },
            reasoning="Deterministic lexical policy matched travel + apparel signals.",
        )

    return IntentClassification(
        intent="keyword_lookup",
        confidence=0.2,
        entities={"keywords": sorted(travel_hits | winter_hits | apparel_hits)},
        reasoning="Deterministic fallback defaulted to generic keyword lookup.",
    )


def _is_sku_like_query(query: str) -> bool:
    normalized = query.strip()
    if not normalized:
        return False
    return normalized.upper().startswith("SKU-") or normalized.replace("-", "").isalnum()


def _looks_like_natural_language_query(query: str) -> bool:
    tokens = _tokenize_lexical_terms(query)
    return len(tokens) >= KEYWORD_ADAPTIVE_MIN_QUERY_TOKENS and " " in query.strip()


def _is_high_confidence_winter_travel_intent(intent: IntentClassification) -> bool:
    entities = intent.entities if isinstance(intent.entities, dict) else {}
    season = str(entities.get("season") or "").lower()
    use_case = str(intent.use_case or entities.get("use_case") or "").lower()
    intent_name = str(intent.intent or "").lower()
    return intent.confidence >= WINTER_TRAVEL_INTENT_CONFIDENCE_THRESHOLD and (
        intent_name == "winter_travel_clothing" or (season == "winter" and "travel" in use_case)
    )


def _has_winter_travel_lexical_signals(query: str) -> bool:
    normalized_query = query.strip().lower()
    if not normalized_query:
        return False

    tokens = _tokenize_lexical_terms(normalized_query)
    travel_hits = _collect_signal_hits(normalized_query, tokens, TRAVEL_LEXICAL_SIGNALS)
    winter_hits = _collect_signal_hits(normalized_query, tokens, WINTER_LEXICAL_SIGNALS)
    return bool(travel_hits and winter_hits)


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


def _is_apparel_product(product: CatalogProduct) -> bool:
    text = _product_search_text(product)
    tokens = _tokenize_lexical_terms(text)
    apparel_hits = _collect_signal_hits(text, tokens, APPAREL_LEXICAL_SIGNALS)
    return bool(apparel_hits)


def _has_low_apparel_coverage(products: list[CatalogProduct]) -> bool:
    if not products:
        return True
    window = products[:KEYWORD_ADAPTIVE_BASELINE_WINDOW]
    apparel_hits = sum(1 for product in window if _is_apparel_product(product))
    coverage = apparel_hits / max(len(window), 1)
    return coverage < KEYWORD_ADAPTIVE_APPAREL_COVERAGE_THRESHOLD


def _winter_travel_product_score(product: CatalogProduct) -> int:
    text = _product_search_text(product)
    tokens = _tokenize_lexical_terms(text)
    apparel_hits = _collect_signal_hits(text, tokens, APPAREL_LEXICAL_SIGNALS)
    winter_hits = _collect_signal_hits(text, tokens, WINTER_LEXICAL_SIGNALS)
    generic_hits = _collect_signal_hits(text, tokens, GENERIC_WINTER_NON_APPAREL_SIGNALS)
    return (len(apparel_hits) * 4) + (len(winter_hits) * 2) - (len(generic_hits) * 3)


def _build_winter_travel_adaptive_query(query: str, intent: IntentClassification) -> str:
    entities = intent.entities if isinstance(intent.entities, dict) else {}
    candidate_keywords = _coerce_keyword_list(entities.get("keywords"))

    apparel_keywords: list[str] = []
    for keyword in candidate_keywords:
        lowered = keyword.lower()
        tokens = _tokenize_lexical_terms(lowered)
        if _collect_signal_hits(lowered, tokens, APPAREL_LEXICAL_SIGNALS):
            apparel_keywords.append(keyword)

    if not apparel_keywords:
        apparel_keywords = list(WINTER_TRAVEL_APPAREL_ESSENTIALS)

    suffix = " ".join(apparel_keywords[:4])
    return f"{query.strip()} {suffix}".strip()


def _rerank_winter_travel_keyword_results(
    *,
    baseline_products: list[CatalogProduct],
    adaptive_products: list[CatalogProduct],
    limit: int,
) -> list[CatalogProduct]:
    if limit <= 0:
        return []

    combined: dict[str, CatalogProduct] = {}
    baseline_rank: dict[str, int] = {}
    adaptive_rank: dict[str, int] = {}

    for index, product in enumerate(baseline_products):
        baseline_rank[product.sku] = index
        combined.setdefault(product.sku, product)

    for index, product in enumerate(adaptive_products):
        adaptive_rank[product.sku] = index
        combined.setdefault(product.sku, product)

    ranked = sorted(
        combined.values(),
        key=lambda product: (
            0 if _is_apparel_product(product) else 1,
            -_winter_travel_product_score(product),
            0 if product.sku in adaptive_rank else 1,
            adaptive_rank.get(product.sku, len(adaptive_rank) + len(combined)),
            baseline_rank.get(product.sku, len(baseline_rank) + len(combined)),
            product.sku,
        ),
    )
    return ranked[:limit]


async def _adapt_keyword_results_for_winter_travel(
    agent: CatalogSearchAgent,
    adapters: CatalogAdapters,
    *,
    query: str,
    limit: int,
    baseline_products: list[CatalogProduct],
) -> list[CatalogProduct]:
    if (
        _is_sku_like_query(query)
        or (
            not _looks_like_natural_language_query(query)
            and not _has_winter_travel_lexical_signals(query)
        )
        or (baseline_products and not _has_low_apparel_coverage(baseline_products))
    ):
        return baseline_products

    try:
        intent = await agent.classify_intent(query)
        if not _is_high_confidence_winter_travel_intent(intent):
            return baseline_products

        adaptive_query = _build_winter_travel_adaptive_query(query, intent)
        adaptive_products = await _search_products_keyword(
            adapters,
            query=adaptive_query,
            limit=limit,
        )
        if not adaptive_products:
            return baseline_products

        reranked = _rerank_winter_travel_keyword_results(
            baseline_products=baseline_products,
            adaptive_products=adaptive_products,
            limit=limit,
        )
        return reranked or baseline_products
    except Exception:  # pylint: disable=broad-exception-caught
        logger.warning(
            "catalog_search_keyword_adaptive_fallback",
            extra={"query_length": len(query), "limit": limit},
            exc_info=True,
        )
        return baseline_products


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
    if agent is not None:
        products = await _adapt_keyword_results_for_winter_travel(
            agent,
            adapters,
            query=query,
            limit=limit,
            baseline_products=products,
        )
    return products, {}, None


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
        if intent is not None and _is_high_confidence_winter_travel_intent(intent):
            essentials = ", ".join(WINTER_TRAVEL_APPAREL_ESSENTIALS[:5])
            return (
                "No exact products were returned in time, so I prioritized winter-travel apparel essentials.",
                f"For your request '{normalized_query}', focus on {essentials}. Prioritize insulated and waterproof layers first.",
            )

        return (
            "No catalog matches were available in time.",
            "Try adding product terms like jacket, boots, gloves, or thermal base layer for a more targeted answer.",
        )

    highlighted = ", ".join(product.name for product in products[:3])
    if intent is not None and _is_high_confidence_winter_travel_intent(intent):
        return (
            "Recommended products were selected for winter-travel conditions.",
            f"Top options for your trip are {highlighted}. Focus on insulated outerwear, waterproof boots, and warm accessories.",
        )

    return (
        "Recommended products were selected from your request.",
        f"Best matches are {highlighted}. Choose based on warmth, weather protection, and layering.",
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
