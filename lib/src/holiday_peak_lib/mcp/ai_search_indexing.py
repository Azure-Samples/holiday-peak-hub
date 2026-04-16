"""Azure AI Search indexing MCP tool wrappers.

Provides command-style functions for:

- Triggering and monitoring indexers
- Resetting indexers
- Pushing documents directly to an index
- Reading index statistics
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Awaitable, Callable, Protocol
from uuid import uuid4

import httpx
from azure.core.credentials import AccessToken
from azure.core.credentials_async import AsyncTokenCredential
from holiday_peak_lib.utils.logging import configure_logging
from holiday_peak_lib.utils.rate_limiter import RateLimiter, RateLimitExceededError

logger = configure_logging(app_name="ai-search-indexing-mcp")

_API_VERSION = "2025-09-01"
_DEFAULT_INDEX_NAME = "product_search_index"
_DEFAULT_INDEXER_NAME = "product-search-indexer"
_DEFAULT_BATCH_LIMIT = 500
_TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}


class MCPToolServer(Protocol):
    """Minimal protocol for MCP server registration."""

    def add_tool(
        self,
        path: str,
        handler: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]],
    ) -> None: ...


@dataclass(slots=True)
class AISearchIndexingSettings:
    """Settings for Azure AI Search indexing operations."""

    endpoint: str
    api_key: str | None = None
    default_index_name: str = _DEFAULT_INDEX_NAME
    default_indexer_name: str | None = None
    api_version: str = _API_VERSION
    batch_limit: int = _DEFAULT_BATCH_LIMIT
    max_retries: int = 3
    retry_backoff_base_seconds: float = 0.5
    timeout_seconds: float = 15.0


@dataclass(slots=True)
class AISearchIndexingClient:
    """Command-style wrapper for Azure AI Search indexing REST operations."""

    settings: AISearchIndexingSettings
    credential: AsyncTokenCredential | None = None
    transport: httpx.AsyncBaseTransport | None = None
    _token: AccessToken | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.settings.endpoint:
            raise ValueError("AI Search endpoint is required")
        if not self.settings.endpoint.startswith("https://"):
            raise ValueError("AI Search endpoint must start with https://")
        if self.settings.batch_limit < 1:
            raise ValueError("batch_limit must be >= 1")

    async def trigger_indexer_run(self, indexer_name: str) -> dict[str, Any]:
        """Trigger an indexer run."""
        resolved_indexer = self._resolve_indexer_name(indexer_name)
        path = f"/indexers('{resolved_indexer}')/search.run"
        response = await self._request_with_retry("POST", path)
        return {
            "status": "accepted" if response.status_code == 202 else "ok",
            "operation": "trigger_indexer_run",
            "indexer_name": resolved_indexer,
            "http_status": response.status_code,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    async def get_indexer_status(self, indexer_name: str) -> dict[str, Any]:
        """Return indexer status payload."""
        resolved_indexer = self._resolve_indexer_name(indexer_name)
        path = f"/indexers('{resolved_indexer}')/search.status"
        response = await self._request_with_retry("GET", path)
        data = self._safe_json(response)
        status_summary = _extract_indexer_status_summary(data)
        return {
            "status": "ok",
            "operation": "get_indexer_status",
            "indexer_name": resolved_indexer,
            "http_status": response.status_code,
            "execution_status": status_summary.get("execution_status"),
            "last_run_time": status_summary.get("last_run_time"),
            "document_count": status_summary.get("document_count"),
            "failed_document_count": status_summary.get("failed_document_count"),
            "result": data,
        }

    async def reset_indexer(self, indexer_name: str) -> dict[str, Any]:
        """Reset an indexer."""
        resolved_indexer = self._resolve_indexer_name(indexer_name)
        path = f"/indexers('{resolved_indexer}')/search.reset"
        response = await self._request_with_retry("POST", path)
        return {
            "status": "ok",
            "operation": "reset_indexer",
            "indexer_name": resolved_indexer,
            "http_status": response.status_code,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    async def index_documents(
        self,
        index_name: str,
        documents: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Push a document batch into an index via `docs/search.index`."""
        resolved_index = self._resolve_index_name(index_name)
        if not documents:
            return {
                "status": "error",
                "operation": "index_documents",
                "error": {
                    "kind": "validation",
                    "message": "documents must not be empty",
                },
            }
        if len(documents) > self.settings.batch_limit:
            return {
                "status": "error",
                "operation": "index_documents",
                "error": {
                    "kind": "validation",
                    "message": (
                        f"documents batch exceeds limit {self.settings.batch_limit}; "
                        f"received {len(documents)}"
                    ),
                },
            }

        actions = []
        for document in documents:
            if not isinstance(document, dict):
                return {
                    "status": "error",
                    "operation": "index_documents",
                    "error": {
                        "kind": "validation",
                        "message": "all documents must be objects",
                    },
                }
            normalized = dict(document)
            normalized.setdefault("@search.action", "mergeOrUpload")
            actions.append(normalized)

        path = f"/indexes('{resolved_index}')/docs/search.index"
        response = await self._request_with_retry("POST", path, json_body={"value": actions})
        data = self._safe_json(response)
        return {
            "status": "ok",
            "operation": "index_documents",
            "index_name": resolved_index,
            "http_status": response.status_code,
            "result": data,
        }

    async def get_index_stats(self, index_name: str) -> dict[str, Any]:
        """Return index statistics payload."""
        resolved_index = self._resolve_index_name(index_name)
        path = f"/indexes('{resolved_index}')/stats"
        response = await self._request_with_retry("GET", path)
        data = self._safe_json(response)
        return {
            "status": "ok",
            "operation": "get_index_stats",
            "index_name": resolved_index,
            "http_status": response.status_code,
            "result": data,
        }

    async def _request_with_retry(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Issue request with retry/backoff for transient status codes."""
        last_exc: Exception | None = None
        for attempt in range(self.settings.max_retries + 1):
            try:
                return await self._request_once(method, path, json_body=json_body)
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                if status_code in _TRANSIENT_STATUS_CODES and attempt < self.settings.max_retries:
                    delay = self._retry_delay_seconds(exc.response, attempt)
                    logger.warning(
                        "ai_search_transient_error status=%s retry_in=%.2fs attempt=%d",
                        status_code,
                        delay,
                        attempt + 1,
                    )
                    await asyncio.sleep(delay)
                    last_exc = exc
                    continue
                raise
            except httpx.HTTPError as exc:
                if attempt < self.settings.max_retries:
                    delay = self.settings.retry_backoff_base_seconds * (2**attempt)
                    await asyncio.sleep(delay)
                    last_exc = exc
                    continue
                raise
        if last_exc:
            raise last_exc
        raise RuntimeError("Unexpected state while issuing AI Search request")

    async def _request_once(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> httpx.Response:
        url = self._build_url(path)
        headers = await self._build_headers()
        async with httpx.AsyncClient(
            timeout=self.settings.timeout_seconds,
            transport=self.transport,
        ) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                json=json_body,
            )
        response.raise_for_status()
        return response

    async def _build_headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-ms-client-request-id": str(uuid4()),
        }
        if self.credential is not None:
            token = await self._get_bearer_token()
            headers["Authorization"] = f"Bearer {token}"
            return headers
        if self.settings.api_key:
            headers["api-key"] = self.settings.api_key
            return headers
        raise ValueError("AI Search authentication requires managed identity or admin key")

    async def _get_bearer_token(self) -> str:
        now_epoch = int(datetime.now(UTC).timestamp())
        if self._token and self._token.expires_on - 60 > now_epoch:
            return self._token.token
        if self.credential is None:
            raise ValueError("credential is required for bearer token authentication")
        self._token = await self.credential.get_token("https://search.azure.com/.default")
        token = self._token
        if token is None:
            raise ValueError("Unable to obtain bearer token")
        return token.token

    def _build_url(self, path: str) -> str:
        endpoint = self.settings.endpoint.rstrip("/")
        return f"{endpoint}{path}?api-version={self.settings.api_version}"

    def _resolve_index_name(self, index_name: str | None) -> str:
        resolved = index_name or self.settings.default_index_name
        if not resolved:
            raise ValueError("index_name is required")
        return resolved

    def _resolve_indexer_name(self, indexer_name: str | None) -> str:
        resolved = indexer_name or self.settings.default_indexer_name
        if not resolved:
            raise ValueError("indexer_name is required")
        return resolved

    @staticmethod
    def _safe_json(response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError:
            return {"raw": response.text}
        if isinstance(payload, dict):
            return payload
        return {"value": payload}

    def _retry_delay_seconds(self, response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("retry-after")
        if retry_after:
            try:
                return max(float(retry_after), 0.1)
            except ValueError:
                pass
        return self.settings.retry_backoff_base_seconds * (2**attempt)


def build_ai_search_indexing_client_from_env(
    *,
    transport: httpx.AsyncBaseTransport | None = None,
) -> AISearchIndexingClient | None:
    """Build client from environment variables.

    Returns ``None`` when endpoint is not configured.
    """

    endpoint = (os.getenv("AI_SEARCH_ENDPOINT") or "").strip()
    if not endpoint:
        return None

    api_key = (os.getenv("AI_SEARCH_ADMIN_KEY") or "").strip() or None
    default_index_name = (os.getenv("AI_SEARCH_VECTOR_INDEX") or _DEFAULT_INDEX_NAME).strip()
    default_indexer_name = (
        os.getenv("AI_SEARCH_INDEXER_NAME") or _DEFAULT_INDEXER_NAME
    ).strip() or None

    credential: AsyncTokenCredential | None = None
    if api_key is None:
        from azure.identity.aio import DefaultAzureCredential

        credential = DefaultAzureCredential()

    settings = AISearchIndexingSettings(
        endpoint=endpoint,
        api_key=api_key,
        default_index_name=default_index_name,
        default_indexer_name=default_indexer_name,
    )
    return AISearchIndexingClient(
        settings=settings,
        credential=credential,
        transport=transport,
    )


def register_ai_search_indexing_tools(
    mcp: MCPToolServer,
    *,
    client: AISearchIndexingClient,
    run_rate_limiter: RateLimiter | None = None,
) -> None:
    """Register AI Search indexing MCP endpoints on an MCP server."""

    limiter = run_rate_limiter or RateLimiter(limit=10, window_seconds=60.0)

    async def trigger_indexer_run(payload: dict[str, Any]) -> dict[str, Any]:
        indexer_name = payload.get("indexer_name") or client.settings.default_indexer_name
        if not indexer_name:
            return _error_response(
                operation="trigger_indexer_run",
                status_code=400,
                error_kind="validation",
                message="indexer_name is required",
            )
        try:
            await limiter.check("global")
            return await client.trigger_indexer_run(str(indexer_name))
        except RateLimitExceededError as exc:
            return _error_response(
                operation="trigger_indexer_run",
                status_code=429,
                error_kind="rate_limit",
                message=str(exc),
            )
        except httpx.HTTPStatusError as exc:
            return _http_error_response("trigger_indexer_run", exc)
        except (httpx.HTTPError, ValueError, RuntimeError) as exc:
            return _error_response(
                operation="trigger_indexer_run",
                status_code=500,
                error_kind="runtime",
                message=str(exc),
            )

    async def get_indexer_status(payload: dict[str, Any]) -> dict[str, Any]:
        indexer_name = payload.get("indexer_name") or client.settings.default_indexer_name
        if not indexer_name:
            return _error_response(
                operation="get_indexer_status",
                status_code=400,
                error_kind="validation",
                message="indexer_name is required",
            )
        try:
            return await client.get_indexer_status(str(indexer_name))
        except httpx.HTTPStatusError as exc:
            return _http_error_response("get_indexer_status", exc)
        except (httpx.HTTPError, ValueError, RuntimeError) as exc:
            return _error_response(
                operation="get_indexer_status",
                status_code=500,
                error_kind="runtime",
                message=str(exc),
            )

    async def reset_indexer(payload: dict[str, Any]) -> dict[str, Any]:
        indexer_name = payload.get("indexer_name") or client.settings.default_indexer_name
        if not indexer_name:
            return _error_response(
                operation="reset_indexer",
                status_code=400,
                error_kind="validation",
                message="indexer_name is required",
            )
        try:
            return await client.reset_indexer(str(indexer_name))
        except httpx.HTTPStatusError as exc:
            return _http_error_response("reset_indexer", exc)
        except (httpx.HTTPError, ValueError, RuntimeError) as exc:
            return _error_response(
                operation="reset_indexer",
                status_code=500,
                error_kind="runtime",
                message=str(exc),
            )

    async def index_documents(payload: dict[str, Any]) -> dict[str, Any]:
        index_name = payload.get("index_name") or client.settings.default_index_name
        documents = payload.get("documents")
        if not isinstance(documents, list):
            return _error_response(
                operation="index_documents",
                status_code=400,
                error_kind="validation",
                message="documents must be a list",
            )
        try:
            return await client.index_documents(str(index_name), documents)
        except httpx.HTTPStatusError as exc:
            return _http_error_response("index_documents", exc)
        except (httpx.HTTPError, ValueError, RuntimeError) as exc:
            return _error_response(
                operation="index_documents",
                status_code=500,
                error_kind="runtime",
                message=str(exc),
            )

    async def get_index_stats(payload: dict[str, Any]) -> dict[str, Any]:
        index_name = payload.get("index_name") or client.settings.default_index_name
        if not index_name:
            return _error_response(
                operation="get_index_stats",
                status_code=400,
                error_kind="validation",
                message="index_name is required",
            )
        try:
            return await client.get_index_stats(str(index_name))
        except httpx.HTTPStatusError as exc:
            return _http_error_response("get_index_stats", exc)
        except (httpx.HTTPError, ValueError, RuntimeError) as exc:
            return _error_response(
                operation="get_index_stats",
                status_code=500,
                error_kind="runtime",
                message=str(exc),
            )

    mcp.add_tool("/ai-search-indexing/trigger_indexer_run", trigger_indexer_run)
    mcp.add_tool("/ai-search-indexing/get_indexer_status", get_indexer_status)
    mcp.add_tool("/ai-search-indexing/reset_indexer", reset_indexer)
    mcp.add_tool("/ai-search-indexing/index_documents", index_documents)
    mcp.add_tool("/ai-search-indexing/get_index_stats", get_index_stats)


def _http_error_response(operation: str, exc: httpx.HTTPStatusError) -> dict[str, Any]:
    status_code = exc.response.status_code
    error_kind = "http_error"
    if status_code == 404:
        error_kind = "not_found"
    elif status_code == 429:
        error_kind = "throttled"
    elif status_code == 503:
        error_kind = "service_unavailable"

    return _error_response(
        operation=operation,
        status_code=status_code,
        error_kind=error_kind,
        message=exc.response.text or str(exc),
    )


def _error_response(
    *,
    operation: str,
    status_code: int,
    error_kind: str,
    message: str,
) -> dict[str, Any]:
    return {
        "status": "error",
        "operation": operation,
        "http_status": status_code,
        "error": {
            "kind": error_kind,
            "message": message,
        },
    }


def _extract_indexer_status_summary(payload: dict[str, Any]) -> dict[str, Any]:
    last_result: dict[str, Any] = {}
    candidate = payload.get("lastResult")
    if isinstance(candidate, dict):
        last_result = candidate

    def _first_number(*keys: str) -> int | None:
        for key in keys:
            value = last_result.get(key)
            if isinstance(value, int):
                return value
        return None

    document_count = _first_number(
        "itemCount",
        "itemsProcessed",
        "outputItemCount",
    )
    failed_document_count = _first_number(
        "failedItemCount",
        "itemsFailed",
    )
    last_run_time = (
        last_result.get("endTime") or last_result.get("startTime") or payload.get("lastRunTime")
    )
    execution_status = (
        last_result.get("status")
        if isinstance(last_result.get("status"), str)
        else payload.get("status")
    )

    return {
        "execution_status": execution_status,
        "last_run_time": last_run_time,
        "document_count": document_count,
        "failed_document_count": failed_document_count,
    }
