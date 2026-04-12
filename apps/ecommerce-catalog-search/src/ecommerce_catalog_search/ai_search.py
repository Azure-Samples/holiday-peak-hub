"""Azure AI Search integration helpers for catalog-search runtime paths."""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx
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


@dataclass(frozen=True)
class AISearchSeedResult:
    """Result payload for bounded AI Search index seeding attempts."""

    attempted: bool
    success: bool
    attempt_count: int
    seeded_documents: int
    reason: str | None = None


_ENRICHED_FIELDS = (
    "use_cases",
    "complementary_products",
    "substitute_products",
    "enriched_description",
)
_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}
_DEFAULT_SEED_MAX_ATTEMPTS = 2
_DEFAULT_SEED_BATCH_SIZE = 50


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


def resolve_seed_max_attempts() -> int:
    """Return bounded max seeding attempts for startup/readiness self-healing."""
    return _parse_positive_int(
        os.getenv("CATALOG_SEARCH_SEED_MAX_ATTEMPTS"),
        default=_DEFAULT_SEED_MAX_ATTEMPTS,
        minimum=1,
        maximum=10,
    )


def resolve_seed_batch_size() -> int:
    """Return bounded product batch size used while seeding AI Search index."""
    return _parse_positive_int(
        os.getenv("CATALOG_SEARCH_SEED_BATCH_SIZE"),
        default=_DEFAULT_SEED_BATCH_SIZE,
        minimum=1,
        maximum=100,
    )


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


async def upsert_catalog_documents(documents: list[dict[str, Any]]) -> bool:
    """Bulk upload or merge catalog documents for startup/readiness seed flows."""
    if not documents:
        return False

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
        await client.merge_or_upload_documents(documents=documents)
        return True
    except AzureError as error:
        logger.warning(
            "ai_search_bulk_upsert_failed",
            extra={
                **_safe_error_context(config, operation="bulk_upsert"),
                "fallback_reason": _fallback_reason_from_error(error),
                "document_count": len(documents),
                "error_type": type(error).__name__,
            },
            exc_info=True,
        )
        return False
    finally:
        await _safe_close(client)
        await _safe_close(credential)


def _resolve_availability_from_product(product: dict[str, Any]) -> str:
    inventory = product.get("inventory")
    available_raw: Any | None = None
    if isinstance(inventory, dict):
        available_raw = inventory.get("available")
    if available_raw is None:
        available_raw = product.get("available")

    if isinstance(available_raw, (int, float)):
        return "in_stock" if available_raw > 0 else "out_of_stock"
    return "unknown"


def _to_search_document(product: dict[str, Any]) -> dict[str, Any] | None:
    sku = str(product.get("sku") or product.get("id") or "").strip()
    if not sku:
        return None

    title = str(product.get("name") or sku).strip() or sku
    description = str(product.get("description") or "")
    category = str(product.get("category") or product.get("category_id") or "")
    brand = str(product.get("brand") or "")
    features_raw = product.get("features")
    features: list[str] = []
    if isinstance(features_raw, list):
        features = [str(item).strip() for item in features_raw if str(item).strip()]

    price_raw = product.get("price")
    try:
        price = float(price_raw or 0.0)
    except (TypeError, ValueError):
        price = 0.0

    return {
        "id": sku,
        "sku": sku,
        "title": title,
        "description": description,
        "content": " ".join(
            part
            for part in (
                title,
                description,
                category,
                brand,
                " ".join(features),
            )
            if part
        ).strip(),
        "category": category,
        "brand": brand,
        "availability": _resolve_availability_from_product(product),
        "price": price,
    }


async def _fetch_seed_products_from_crud(limit: int) -> tuple[list[dict[str, Any]], str | None]:
    crud_service_url = (os.getenv("CRUD_SERVICE_URL") or "").strip().rstrip("/")
    if not crud_service_url:
        return [], "crud_service_not_configured"

    timeout_seconds = _parse_positive_int(
        os.getenv("CATALOG_SEARCH_SEED_HTTP_TIMEOUT_SECONDS"),
        default=5,
        minimum=1,
        maximum=60,
    )

    try:
        async with httpx.AsyncClient(timeout=float(timeout_seconds)) as client:
            response = await client.get(
                f"{crud_service_url}/api/products",
                params={"limit": limit},
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError:
        logger.warning(
            "catalog_ai_search_seed_crud_fetch_failed",
            extra={
                "crud_service_url": crud_service_url,
                "limit": limit,
            },
            exc_info=True,
        )
        return [], "crud_fetch_failed"

    if not isinstance(payload, list):
        return [], "crud_invalid_payload"

    products = [item for item in payload if isinstance(item, dict)]
    if not products:
        return [], "crud_no_products"
    return products, None


async def seed_catalog_index_from_crud(
    *,
    max_attempts: int | None = None,
    batch_size: int | None = None,
) -> AISearchSeedResult:
    """Attempt bounded CRUD-based seeding when AI Search index is empty/unusable."""
    config = load_ai_search_config()
    if config is None:
        return AISearchSeedResult(
            attempted=False,
            success=False,
            attempt_count=0,
            seeded_documents=0,
            reason="ai_search_not_configured",
        )

    if max_attempts is not None and max_attempts <= 0:
        return AISearchSeedResult(
            attempted=False,
            success=False,
            attempt_count=0,
            seeded_documents=0,
            reason="seed_attempt_budget_exhausted",
        )

    resolved_attempts = (
        _parse_positive_int(
            str(max_attempts),
            default=resolve_seed_max_attempts(),
            minimum=1,
            maximum=10,
        )
        if max_attempts is not None
        else resolve_seed_max_attempts()
    )
    resolved_batch_size = (
        _parse_positive_int(
            str(batch_size),
            default=resolve_seed_batch_size(),
            minimum=1,
            maximum=100,
        )
        if batch_size is not None
        else resolve_seed_batch_size()
    )

    last_reason: str | None = None
    best_seed_count = 0
    for attempt in range(1, resolved_attempts + 1):
        logger.info(
            "catalog_ai_search_seed_attempt",
            extra={
                "attempt": attempt,
                "max_attempts": resolved_attempts,
                "batch_size": resolved_batch_size,
                "endpoint_host": _safe_endpoint_host(config.endpoint),
                "index_name": config.index_name,
            },
        )

        products, fetch_reason = await _fetch_seed_products_from_crud(resolved_batch_size)
        if fetch_reason is not None:
            last_reason = fetch_reason
            continue

        documents = [
            document
            for product in products
            if (document := _to_search_document(product)) is not None
        ]
        if not documents:
            last_reason = "crud_no_seedable_products"
            continue

        best_seed_count = max(best_seed_count, len(documents))
        indexed = await upsert_catalog_documents(documents)
        if not indexed:
            last_reason = "ai_search_seed_upsert_failed"
            continue

        status = await get_catalog_index_status()
        if status.non_empty:
            logger.info(
                "catalog_ai_search_seed_success",
                extra={
                    "attempt": attempt,
                    "seeded_documents": len(documents),
                    "endpoint_host": _safe_endpoint_host(config.endpoint),
                    "index_name": config.index_name,
                },
            )
            return AISearchSeedResult(
                attempted=True,
                success=True,
                attempt_count=attempt,
                seeded_documents=len(documents),
            )

        last_reason = status.reason or "ai_search_index_empty_after_seed"
        logger.warning(
            "catalog_ai_search_seed_check_failed",
            extra={
                "attempt": attempt,
                "seeded_documents": len(documents),
                "reason": last_reason,
            },
        )

    return AISearchSeedResult(
        attempted=True,
        success=False,
        attempt_count=resolved_attempts,
        seeded_documents=best_seed_count,
        reason=last_reason or "catalog_ai_search_seed_failed",
    )


async def ensure_catalog_index_seeded_if_empty(
    *,
    max_attempts: int | None = None,
    batch_size: int | None = None,
) -> tuple[AISearchIndexStatus, AISearchSeedResult | None]:
    """Return current index status and seed once when index is missing documents."""
    status = await get_catalog_index_status()
    if status.non_empty:
        return status, None

    seed_result = await seed_catalog_index_from_crud(
        max_attempts=max_attempts,
        batch_size=batch_size,
    )
    refreshed = await get_catalog_index_status()
    return refreshed, seed_result
