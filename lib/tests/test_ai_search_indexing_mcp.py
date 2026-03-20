"""Unit tests for AI Search indexing MCP wrappers."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta

import httpx
import pytest
from azure.core.credentials import AccessToken

from holiday_peak_lib.mcp.ai_search_indexing import (
    AISearchIndexingClient,
    AISearchIndexingSettings,
    build_ai_search_indexing_client_from_env,
    register_ai_search_indexing_tools,
)


class _DummyMCP:
    def __init__(self) -> None:
        self.tools: dict[str, Callable[[dict[str, object]], Awaitable[dict[str, object]]]] = {}

    def add_tool(
        self,
        path: str,
        handler: Callable[[dict[str, object]], Awaitable[dict[str, object]]],
    ) -> None:
        self.tools[path] = handler


class _AsyncCredential:
    async def get_token(self, _scope: str) -> AccessToken:
        expires_on = int((datetime.now() + timedelta(minutes=30)).timestamp())
        return AccessToken("token-123", expires_on)


def _build_client(
    handler,
    *,
    credential=None,
    api_key: str | None = "admin-key",
    default_indexer_name: str | None = "products-indexer",
) -> AISearchIndexingClient:
    settings = AISearchIndexingSettings(
        endpoint="https://unit-test.search.windows.net",
        api_key=api_key,
        default_index_name="product_search_index",
        default_indexer_name=default_indexer_name,
        max_retries=1,
    )
    return AISearchIndexingClient(
        settings=settings,
        credential=credential,
        transport=httpx.MockTransport(handler),
    )


@pytest.mark.asyncio
async def test_ai_search_client_run_status_reset_and_stats() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("api-key") == "admin-key"
        if request.url.path.endswith("/search.run"):
            return httpx.Response(202, json={})
        if request.url.path.endswith("/search.status"):
            return httpx.Response(
                200,
                json={
                    "status": "running",
                    "lastResult": {
                        "status": "success",
                        "startTime": "2026-03-19T01:00:00Z",
                        "endTime": "2026-03-19T01:01:00Z",
                        "itemCount": 17,
                        "failedItemCount": 1,
                    },
                },
            )
        if request.url.path.endswith("/search.reset"):
            return httpx.Response(204, json={})
        if request.url.path.endswith("/stats"):
            return httpx.Response(200, json={"documentCount": 42})
        return httpx.Response(404, json={"error": "not found"})

    client = _build_client(handler)

    run_result = await client.trigger_indexer_run("products-indexer")
    status_result = await client.get_indexer_status("products-indexer")
    reset_result = await client.reset_indexer("products-indexer")
    stats_result = await client.get_index_stats("product_search_index")

    assert run_result["status"] in {"accepted", "ok"}
    assert status_result["result"]["status"] == "running"
    assert status_result["execution_status"] == "success"
    assert status_result["last_run_time"] == "2026-03-19T01:01:00Z"
    assert status_result["document_count"] == 17
    assert status_result["failed_document_count"] == 1
    assert reset_result["status"] == "ok"
    assert stats_result["result"]["documentCount"] == 42


@pytest.mark.asyncio
async def test_ai_search_client_index_documents_adds_default_action() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        first = body["value"][0]
        assert first["@search.action"] == "mergeOrUpload"
        return httpx.Response(200, json={"value": [{"key": "SKU-1", "status": True}]})

    client = _build_client(handler)
    result = await client.index_documents("product_search_index", [{"id": "SKU-1", "name": "shoe"}])
    assert result["status"] == "ok"
    assert result["result"]["value"][0]["status"] is True


@pytest.mark.asyncio
async def test_ai_search_client_uses_bearer_token_when_credential_available() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization") == "Bearer token-123"
        assert request.headers.get("api-key") is None
        return httpx.Response(202, json={})

    client = _build_client(handler, credential=_AsyncCredential(), api_key=None)
    result = await client.trigger_indexer_run("products-indexer")
    assert result["status"] in {"accepted", "ok"}


@pytest.mark.asyncio
async def test_ai_search_mcp_tools_return_structured_http_errors() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/search.status"):
            return httpx.Response(404, json={"error": {"message": "missing"}})
        if request.url.path.endswith("/search.reset"):
            return httpx.Response(503, json={"error": {"message": "busy"}})
        return httpx.Response(429, json={"error": {"message": "throttled"}})

    client = _build_client(handler)
    mcp = _DummyMCP()
    register_ai_search_indexing_tools(mcp, client=client)

    status_result = await mcp.tools["/ai-search-indexing/get_indexer_status"]({"indexer_name": "idx"})
    reset_result = await mcp.tools["/ai-search-indexing/reset_indexer"]({"indexer_name": "idx"})
    run_result = await mcp.tools["/ai-search-indexing/trigger_indexer_run"]({"indexer_name": "idx"})

    assert status_result["status"] == "error"
    assert status_result["http_status"] == 404
    assert reset_result["status"] == "error"
    assert reset_result["http_status"] == 503
    assert run_result["status"] == "error"
    assert run_result["http_status"] == 429


@pytest.mark.asyncio
async def test_ai_search_mcp_tools_enforce_indexer_run_rate_limit() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(202, json={})

    client = _build_client(handler)
    mcp = _DummyMCP()
    register_ai_search_indexing_tools(mcp, client=client)

    tool = mcp.tools["/ai-search-indexing/trigger_indexer_run"]
    for _ in range(10):
        ok = await tool({"indexer_name": "idx"})
        assert ok["status"] in {"accepted", "ok"}

    overflow = await tool({"indexer_name": "idx"})
    assert overflow["status"] == "error"
    assert overflow["http_status"] == 429


def test_build_client_uses_default_indexer_name_when_env_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_SEARCH_ENDPOINT", "https://unit-test.search.windows.net")
    monkeypatch.delenv("AI_SEARCH_INDEXER_NAME", raising=False)
    monkeypatch.delenv("AI_SEARCH_ADMIN_KEY", raising=False)

    client = build_ai_search_indexing_client_from_env()

    assert client is not None
    assert client.settings.default_indexer_name == "product-search-indexer"
