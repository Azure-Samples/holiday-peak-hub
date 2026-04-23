"""Azure AI Search integration helpers for catalog-search runtime paths."""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import (
    AzureError,
    ClientAuthenticationError,
    HttpResponseError,
    ServiceRequestError,
    ServiceResponseError,
)
from azure.identity.aio import DefaultAzureCredential
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import VectorizableTextQuery

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AISearchConfig:
    """Runtime configuration for Azure AI Search connectivity."""

    endpoint: str
    index_name: str
    vector_index_name: str
    embedding_deployment_name: str | None
    auth_mode: str
    key: str | None = None


@dataclass(frozen=True)
class AISearchSkuResult:
    """AI Search SKU lookup result with optional fallback reason."""

    skus: list[str]
    fallback_reason: str | None = None


@dataclass(frozen=True)
class AISearchDocumentResult:
    """Ranked AI Search document result with optional enrichment payload."""

    sku: str
    score: float
    document: dict[str, Any]
    enriched_fields: dict[str, Any]


@dataclass(frozen=True)
class AISearchIndexStatus:
    """Health snapshot for AI Search runtime enforcement checks."""

    configured: bool
    reachable: bool
    non_empty: bool
    reason: str | None = None


_ENRICHED_FIELDS = (
    "use_cases",
    "complementary_products",
    "substitute_products",
    "enriched_description",
)
_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}


def load_ai_search_config() -> AISearchConfig | None:
    """Load AI Search settings from environment variables."""
    endpoint = (os.getenv("AI_SEARCH_ENDPOINT") or "").strip()
    index_name = (os.getenv("AI_SEARCH_INDEX") or "").strip()
    vector_index_name = (os.getenv("AI_SEARCH_VECTOR_INDEX") or "").strip()
    if not endpoint or not (index_name or vector_index_name):
        return None

    resolved_index_name = index_name or vector_index_name
    resolved_vector_index = vector_index_name or resolved_index_name

    auth_mode = (os.getenv("AI_SEARCH_AUTH_MODE") or "managed_identity").strip().lower()
    key = (os.getenv("AI_SEARCH_KEY") or "").strip() or None
    embedding_deployment_name = (os.getenv("EMBEDDING_DEPLOYMENT_NAME") or "").strip() or None
    return AISearchConfig(
        endpoint=endpoint,
        index_name=resolved_index_name,
        vector_index_name=resolved_vector_index,
        embedding_deployment_name=embedding_deployment_name,
        auth_mode=auth_mode,
        key=key,
    )


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default

    normalized = value.strip().lower()
    if not normalized:
        return default
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    return default


def _parse_positive_int(
    value: str | None,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    if value is None:
        return default

    try:
        resolved = int(value)
    except (TypeError, ValueError):
        return default

    return max(minimum, min(maximum, resolved))


def ai_search_required_runtime_enabled() -> bool:
    """Resolve strict AI Search mode (AKS default, env override supported)."""
    aks_default = bool((os.getenv("KUBERNETES_SERVICE_HOST") or "").strip())
    override = os.getenv("CATALOG_SEARCH_REQUIRE_AI_SEARCH")
    return _parse_bool(override, default=aks_default)


def _resolve_credential(config: AISearchConfig) -> AzureKeyCredential | DefaultAzureCredential:
    if config.auth_mode == "api_key" and config.key:
        return AzureKeyCredential(config.key)
    return DefaultAzureCredential()


async def _safe_close(obj: Any) -> None:
    close = getattr(obj, "close", None)
    if close is None:
        return
    result = close()
    if hasattr(result, "__await__"):
        await result


def _extract_sku(document: dict[str, Any]) -> str | None:
    for field in ("sku", "item_id", "product_id", "id"):
        value = document.get(field)
        if value:
            return str(value)
    return None


def _extract_score(document: dict[str, Any]) -> float:
    for field in ("@search.score", "@search.reranker_score", "score"):
        value = document.get(field)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return 0.0


def _normalize_result_document(document: dict[str, Any]) -> AISearchDocumentResult | None:
    sku = _extract_sku(document)
    if not sku:
        return None
    enriched_fields = {
        field: document.get(field) for field in _ENRICHED_FIELDS if document.get(field) is not None
    }
    return AISearchDocumentResult(
        sku=sku,
        score=_extract_score(document),
        document=dict(document),
        enriched_fields=enriched_fields,
    )


def _as_search_filter(filters: dict[str, Any] | None) -> str | None:
    if not filters:
        return None

    clauses: list[str] = []
    for field, value in filters.items():
        if value is None:
            continue
        if isinstance(value, str):
            safe = value.replace("'", "''")
            clauses.append(f"{field} eq '{safe}'")
            continue
        if isinstance(value, bool):
            clauses.append(f"{field} eq {'true' if value else 'false'}")
            continue
        if isinstance(value, (int, float)):
            clauses.append(f"{field} eq {value}")
            continue
        if isinstance(value, (list, tuple, set)):
            values = [item for item in value if isinstance(item, (str, int, float))]
            if not values:
                continue
            or_parts: list[str] = []
            for item in values:
                if isinstance(item, str):
                    safe = item.replace("'", "''")
                    or_parts.append(f"{field} eq '{safe}'")
                else:
                    or_parts.append(f"{field} eq {item}")
            clauses.append(f"({' or '.join(or_parts)})")

    if not clauses:
        return None
    return " and ".join(clauses)


async def _search_documents(
    *,
    config: AISearchConfig,
    index_name: str,
    search_text: str | None,
    top_k: int,
    filters: dict[str, Any] | None = None,
    vector_queries: list[Any] | None = None,
    operation: str,
) -> list[AISearchDocumentResult]:
    if top_k <= 0:
        return []

    credential = _resolve_credential(config)
    client = SearchClient(
        endpoint=config.endpoint,
        index_name=index_name,
        credential=credential,
    )
    filter_expression = _as_search_filter(filters)
    search_kwargs: dict[str, Any] = {
        "search_text": search_text,
        "top": top_k,
        "filter": filter_expression,
        "vector_queries": vector_queries,
    }

    try:
        results = await client.search(**search_kwargs)
        documents: list[AISearchDocumentResult] = []
        async for document in results:
            parsed = _normalize_result_document(document)
            if parsed is not None:
                documents.append(parsed)
        return documents
    except AzureError as error:
        logger.warning(
            "ai_search_documents_fallback",
            extra={
                **_safe_error_context(config, operation=operation),
                "fallback_reason": _fallback_reason_from_error(error),
                "query_length": len(search_text or ""),
                "top_k": top_k,
                "error_type": type(error).__name__,
            },
            exc_info=True,
        )
        return []
    finally:
        await _safe_close(client)
        await _safe_close(credential)


async def keyword_search(
    query_text: str,
    filters: dict[str, Any] | None,
    top_k: int,
) -> list[AISearchDocumentResult]:
    """Execute keyword search using the configured AI Search index."""
    config = load_ai_search_config()
    if config is None or not query_text.strip() or top_k <= 0:
        return []
    return await _search_documents(
        config=config,
        index_name=config.index_name,
        search_text=query_text,
        top_k=top_k,
        filters=filters,
        operation="keyword_query",
    )


async def vector_search(
    query_text: str,
    filters: dict[str, Any] | None,
    top_k: int,
) -> list[AISearchDocumentResult]:
    """Execute vector-only retrieval against ``AI_SEARCH_VECTOR_INDEX``."""
    config = load_ai_search_config()
    if config is None or not query_text.strip() or top_k <= 0:
        return []

    vector_field = (os.getenv("AI_SEARCH_VECTOR_FIELD") or "content_vector").strip()
    vector_query = VectorizableTextQuery(
        text=query_text,
        k_nearest_neighbors=top_k,
        fields=vector_field,
    )
    return await _search_documents(
        config=config,
        index_name=config.vector_index_name,
        search_text=None,
        top_k=top_k,
        filters=filters,
        vector_queries=[vector_query],
        operation="vector_query",
    )


async def hybrid_search(
    query_text: str,
    filters: dict[str, Any] | None,
    top_k: int,
) -> list[AISearchDocumentResult]:
    """Execute combined text + vector retrieval against vector index."""
    config = load_ai_search_config()
    if config is None or not query_text.strip() or top_k <= 0:
        return []

    vector_field = (os.getenv("AI_SEARCH_VECTOR_FIELD") or "content_vector").strip()
    vector_query = VectorizableTextQuery(
        text=query_text,
        k_nearest_neighbors=top_k,
        fields=vector_field,
    )
    return await _search_documents(
        config=config,
        index_name=config.vector_index_name,
        search_text=query_text,
        top_k=top_k,
        filters=filters,
        vector_queries=[vector_query],
        operation="hybrid_query",
    )


async def multi_query_search(
    sub_queries: list[str],
    filters: dict[str, Any] | None,
    top_k: int = 5,
) -> list[AISearchDocumentResult]:
    """Execute hybrid search over sub-queries and merge by SKU with dedupe/rank."""
    cleaned_queries = [query.strip() for query in sub_queries if query and query.strip()]
    if not cleaned_queries or top_k <= 0:
        return []

    merged: dict[str, dict[str, Any]] = {}
    all_results = await asyncio.gather(
        *[hybrid_search(query_text=q, filters=filters, top_k=top_k) for q in cleaned_queries],
        return_exceptions=True,
    )
    for query_results in all_results:
        if isinstance(query_results, BaseException):
            continue
        for rank, candidate in enumerate(query_results, start=1):
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
            entry["rank_bonus"] += max((top_k - rank + 1) / max(top_k, 1), 0.0)

            merged_candidate: AISearchDocumentResult = entry["candidate"]
            if len(candidate.enriched_fields) > len(merged_candidate.enriched_fields):
                entry["candidate"] = candidate

    ranked = sorted(
        merged.values(),
        key=lambda item: (item["hits"], item["best_score"], item["rank_bonus"]),
        reverse=True,
    )
    return [item["candidate"] for item in ranked[:top_k]]


def _safe_endpoint_host(endpoint: str) -> str:
    parsed = urlparse(endpoint)
    return parsed.netloc or endpoint


def _fallback_reason_from_error(error: AzureError) -> str:
    if isinstance(error, ClientAuthenticationError):
        return "ai_search_auth_error"
    if isinstance(error, (ServiceRequestError, ServiceResponseError)):
        return "ai_search_transport_error"
    if isinstance(error, HttpResponseError):
        status_code = getattr(error, "status_code", None)
        if status_code in {401, 403}:
            return "ai_search_permission_error"
    return "ai_search_error"


def _safe_error_context(config: AISearchConfig, operation: str) -> dict[str, Any]:
    return {
        "operation": operation,
        "endpoint_host": _safe_endpoint_host(config.endpoint),
        "index_name": config.index_name,
        "auth_mode": config.auth_mode,
    }


async def search_catalog_skus_detailed(query: str, limit: int) -> AISearchSkuResult:
    """Query AI Search index and include explicit fallback metadata when degraded."""
    config = load_ai_search_config()
    if config is None:
        return AISearchSkuResult(skus=[], fallback_reason="ai_search_not_configured")
    if not query.strip() or limit <= 0:
        return AISearchSkuResult(skus=[])

    credential = _resolve_credential(config)
    client = SearchClient(
        endpoint=config.endpoint,
        index_name=config.index_name,
        credential=credential,
    )

    skus: list[str] = []
    try:
        results = await client.search(
            search_text=query,
            top=limit,
            select=["sku", "id"],
        )
        async for doc in results:
            sku = _extract_sku(doc)
            if sku:
                skus.append(sku)
        return AISearchSkuResult(skus=skus)
    except AzureError as error:
        fallback_reason = _fallback_reason_from_error(error)
        logger.warning(
            "ai_search_query_fallback",
            extra={
                **_safe_error_context(config, operation="query"),
                "fallback_reason": fallback_reason,
                "query_length": len(query),
                "limit": limit,
                "error_type": type(error).__name__,
            },
            exc_info=True,
        )
        return AISearchSkuResult(skus=[], fallback_reason=fallback_reason)
    finally:
        await _safe_close(client)
        await _safe_close(credential)


async def search_catalog_skus(query: str, limit: int) -> list[str]:
    """Query AI Search index and return SKU-like identifiers in rank order."""
    result = await search_catalog_skus_detailed(query=query, limit=limit)
    return result.skus


async def upsert_catalog_document(document: dict[str, Any]) -> bool:
    """Upload or merge a catalog search document when AI Search is configured."""
    config = load_ai_search_config()
    if config is None:
        return False

    credential = _resolve_credential(config)
    client = SearchClient(
        endpoint=config.endpoint,
        index_name=config.index_name,
        credential=credential,
    )

    try:
        await client.merge_or_upload_documents(documents=[document])
        return True
    except AzureError as error:
        logger.warning(
            "ai_search_upsert_failed",
            extra={
                **_safe_error_context(config, operation="upsert"),
                "fallback_reason": _fallback_reason_from_error(error),
                "document_id": document.get("id") or document.get("sku"),
                "error_type": type(error).__name__,
            },
            exc_info=True,
        )
        return False
    finally:
        await _safe_close(client)
        await _safe_close(credential)


async def delete_catalog_document(sku: str) -> bool:
    """Delete catalog document from AI Search by SKU."""
    config = load_ai_search_config()
    if config is None or not sku.strip():
        return False

    credential = _resolve_credential(config)
    client = SearchClient(
        endpoint=config.endpoint,
        index_name=config.index_name,
        credential=credential,
    )

    try:
        await client.delete_documents(documents=[{"id": sku, "sku": sku}])
        return True
    except AzureError as error:
        logger.warning(
            "ai_search_delete_failed",
            extra={
                **_safe_error_context(config, operation="delete"),
                "fallback_reason": _fallback_reason_from_error(error),
                "sku": sku,
                "error_type": type(error).__name__,
            },
            exc_info=True,
        )
        return False
    finally:
        await _safe_close(client)
        await _safe_close(credential)


async def get_catalog_index_status() -> AISearchIndexStatus:
    """Inspect index configuration, reachability, and whether at least one document exists."""
    config = load_ai_search_config()
    if config is None:
        return AISearchIndexStatus(
            configured=False,
            reachable=False,
            non_empty=False,
            reason="ai_search_not_configured",
        )

    credential = _resolve_credential(config)
    client = SearchClient(
        endpoint=config.endpoint,
        index_name=config.index_name,
        credential=credential,
    )

    try:
        results = await client.search(
            search_text="*",
            top=1,
            select=["id", "sku"],
        )
        async for _ in results:
            return AISearchIndexStatus(
                configured=True,
                reachable=True,
                non_empty=True,
            )

        return AISearchIndexStatus(
            configured=True,
            reachable=True,
            non_empty=False,
            reason="ai_search_index_empty",
        )
    except AzureError as error:
        reason = _fallback_reason_from_error(error)
        logger.warning(
            "catalog_ai_search_index_status_failed",
            extra={
                **_safe_error_context(config, operation="index_status"),
                "reason": reason,
                "error_type": type(error).__name__,
            },
            exc_info=True,
        )
        return AISearchIndexStatus(
            configured=True,
            reachable=False,
            non_empty=False,
            reason=reason,
        )
    finally:
        await _safe_close(client)
        await _safe_close(credential)
