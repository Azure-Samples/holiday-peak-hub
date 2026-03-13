"""Focused tests for AI Search fallback telemetry and reason signaling."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, Mock, patch

import pytest
from azure.core.exceptions import ClientAuthenticationError, ServiceRequestError

from ecommerce_catalog_search.ai_search import (
    AISearchSkuResult,
    search_catalog_skus,
    search_catalog_skus_detailed,
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "expected_reason"),
    [
        (ServiceRequestError("transport down"), "ai_search_transport_error"),
        (ClientAuthenticationError("auth failed"), "ai_search_auth_error"),
    ],
)
async def test_search_catalog_skus_detailed_returns_reason_and_logs_warning(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    error: Exception,
    expected_reason: str,
) -> None:
    monkeypatch.setenv("AI_SEARCH_ENDPOINT", "https://example.search.windows.net")
    monkeypatch.setenv("AI_SEARCH_INDEX", "catalog")

    credential = Mock()
    credential.close = AsyncMock()

    client = Mock()
    client.search = AsyncMock(side_effect=error)
    client.close = AsyncMock()

    caplog.set_level(logging.WARNING, logger="ecommerce_catalog_search.ai_search")

    with (
        patch("ecommerce_catalog_search.ai_search._resolve_credential", return_value=credential),
        patch("ecommerce_catalog_search.ai_search.SearchClient", return_value=client),
    ):
        result = await search_catalog_skus_detailed(query="wireless earbuds", limit=4)

    assert result == AISearchSkuResult(skus=[], fallback_reason=expected_reason)
    assert any(
        record.msg == "ai_search_query_fallback"
        and getattr(record, "fallback_reason", None) == expected_reason
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_search_catalog_skus_legacy_contract_keeps_empty_list_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_SEARCH_ENDPOINT", "https://example.search.windows.net")
    monkeypatch.setenv("AI_SEARCH_INDEX", "catalog")

    credential = Mock()
    credential.close = AsyncMock()

    client = Mock()
    client.search = AsyncMock(side_effect=ServiceRequestError("transport down"))
    client.close = AsyncMock()

    with (
        patch("ecommerce_catalog_search.ai_search._resolve_credential", return_value=credential),
        patch("ecommerce_catalog_search.ai_search.SearchClient", return_value=client),
    ):
        result = await search_catalog_skus(query="wireless earbuds", limit=4)

    assert result == []
