"""Focused tests for AI Search fallback telemetry and reason signaling."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, Mock, patch

import pytest
from azure.core.exceptions import ClientAuthenticationError, ServiceRequestError
from ecommerce_catalog_search.ai_search import (
    AISearchDocumentResult,
    AISearchSkuResult,
    hybrid_search,
    multi_query_search,
    search_catalog_skus,
    search_catalog_skus_detailed,
    vector_search,
)


class _AsyncResults:
    def __init__(self, documents: list[dict[str, object]]) -> None:
        self._documents = documents

    def __aiter__(self):
        async def _iterator():
            for document in self._documents:
                yield document

        return _iterator()


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


@pytest.mark.asyncio
async def test_vector_search_uses_vector_index_and_returns_enriched_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_SEARCH_ENDPOINT", "https://example.search.windows.net")
    monkeypatch.setenv("AI_SEARCH_VECTOR_INDEX", "product_search_index")
    monkeypatch.setenv("EMBEDDING_DEPLOYMENT_NAME", "text-embedding-3-large")

    credential = Mock()
    credential.close = AsyncMock()

    client = Mock()
    client.close = AsyncMock()
    client.search = AsyncMock(
        return_value=_AsyncResults(
            [
                {
                    "sku": "SKU-101",
                    "@search.score": 1.2,
                    "use_cases": ["gaming", "streaming"],
                    "enriched_description": "High-fidelity over-ear headphones.",
                }
            ]
        )
    )

    with (
        patch("ecommerce_catalog_search.ai_search._resolve_credential", return_value=credential),
        patch("ecommerce_catalog_search.ai_search.SearchClient", return_value=client),
    ):
        result = await vector_search(
            query_text="headphones for gaming and streaming",
            filters={"brand": "Contoso"},
            top_k=3,
        )

    assert len(result) == 1
    assert result[0].sku == "SKU-101"
    assert result[0].enriched_fields["use_cases"] == ["gaming", "streaming"]
    assert client.search.await_count == 1


@pytest.mark.asyncio
async def test_hybrid_search_combines_text_and_vector_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_SEARCH_ENDPOINT", "https://example.search.windows.net")
    monkeypatch.setenv("AI_SEARCH_VECTOR_INDEX", "product_search_index")

    credential = Mock()
    credential.close = AsyncMock()

    client = Mock()
    client.close = AsyncMock()
    client.search = AsyncMock(
        return_value=_AsyncResults(
            [
                {
                    "sku": "SKU-202",
                    "@search.score": 0.9,
                    "complementary_products": ["SKU-204"],
                }
            ]
        )
    )

    with (
        patch("ecommerce_catalog_search.ai_search._resolve_credential", return_value=credential),
        patch("ecommerce_catalog_search.ai_search.SearchClient", return_value=client),
    ):
        result = await hybrid_search(
            query_text="wireless keyboard ergonomic",
            filters=None,
            top_k=5,
        )

    assert len(result) == 1
    assert result[0].sku == "SKU-202"
    assert result[0].enriched_fields["complementary_products"] == ["SKU-204"]


@pytest.mark.asyncio
async def test_multi_query_search_merges_dedupes_and_ranks() -> None:
    first = AISearchDocumentResult(
        sku="SKU-A",
        score=0.95,
        document={"sku": "SKU-A"},
        enriched_fields={"use_cases": ["daily"]},
    )
    second = AISearchDocumentResult(
        sku="SKU-B",
        score=0.9,
        document={"sku": "SKU-B"},
        enriched_fields={},
    )
    duplicate = AISearchDocumentResult(
        sku="SKU-A",
        score=0.8,
        document={"sku": "SKU-A"},
        enriched_fields={"use_cases": ["daily", "travel"]},
    )

    with patch(
        "ecommerce_catalog_search.ai_search.hybrid_search",
        new=AsyncMock(side_effect=[[first, second], [duplicate]]),
    ):
        merged = await multi_query_search(
            sub_queries=["travel laptop", "portable device"],
            filters={"category": "electronics"},
            top_k=3,
        )

    assert [item.sku for item in merged] == ["SKU-A", "SKU-B"]
