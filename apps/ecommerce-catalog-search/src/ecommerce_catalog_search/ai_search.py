"""Azure AI Search integration helpers for catalog-search runtime paths."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from azure.core.exceptions import (
    AzureError,
    ClientAuthenticationError,
    HttpResponseError,
    ServiceRequestError,
    ServiceResponseError,
)
from azure.core.credentials import AzureKeyCredential
from azure.identity.aio import DefaultAzureCredential
from azure.search.documents.aio import SearchClient


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AISearchConfig:
    """Runtime configuration for Azure AI Search connectivity."""

    endpoint: str
    index_name: str
    auth_mode: str
    key: str | None = None


@dataclass(frozen=True)
class AISearchSkuResult:
    """AI Search SKU lookup result with optional fallback reason."""

    skus: list[str]
    fallback_reason: str | None = None


def load_ai_search_config() -> AISearchConfig | None:
    """Load AI Search settings from environment variables."""
    endpoint = (os.getenv("AI_SEARCH_ENDPOINT") or "").strip()
    index_name = (os.getenv("AI_SEARCH_INDEX") or "").strip()
    if not endpoint or not index_name:
        return None

    auth_mode = (os.getenv("AI_SEARCH_AUTH_MODE") or "managed_identity").strip().lower()
    key = (os.getenv("AI_SEARCH_KEY") or "").strip() or None
    return AISearchConfig(
        endpoint=endpoint,
        index_name=index_name,
        auth_mode=auth_mode,
        key=key,
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
    if config is None or not query.strip() or limit <= 0:
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
            select=["sku", "item_id", "product_id", "id"],
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
