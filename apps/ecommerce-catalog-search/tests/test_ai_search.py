"""Focused tests for AI Search fallback telemetry and reason signaling."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, Mock, patch

import pytest
from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ServiceRequestError,
)
from ecommerce_catalog_search.ai_search import (
    AISearchDocumentResult,
    AISearchIndexStatus,
    AISearchSkuResult,
    ai_search_required_runtime_enabled,
    get_catalog_index_status,
    hybrid_search,
    multi_query_search,
    search_catalog_skus,
    search_catalog_skus_detailed,
    seed_catalog_index_from_crud,
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


def test_ai_search_required_runtime_defaults_to_aks_detection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CATALOG_SEARCH_REQUIRE_AI_SEARCH", raising=False)
    monkeypatch.setenv("KUBERNETES_SERVICE_HOST", "10.0.0.1")
    assert ai_search_required_runtime_enabled() is True

    monkeypatch.delenv("KUBERNETES_SERVICE_HOST", raising=False)
    assert ai_search_required_runtime_enabled() is False


def test_ai_search_required_runtime_respects_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KUBERNETES_SERVICE_HOST", "10.0.0.1")
    monkeypatch.setenv("CATALOG_SEARCH_REQUIRE_AI_SEARCH", "false")
    assert ai_search_required_runtime_enabled() is False

    monkeypatch.setenv("CATALOG_SEARCH_REQUIRE_AI_SEARCH", "true")
    assert ai_search_required_runtime_enabled() is True


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
async def test_get_catalog_index_status_reports_empty_index(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_SEARCH_ENDPOINT", "https://example.search.windows.net")
    monkeypatch.setenv("AI_SEARCH_INDEX", "catalog")

    credential = Mock()
    credential.close = AsyncMock()

    client = Mock()
    client.search = AsyncMock(return_value=_AsyncResults([]))
    client.close = AsyncMock()

    with (
        patch("ecommerce_catalog_search.ai_search._resolve_credential", return_value=credential),
        patch("ecommerce_catalog_search.ai_search.SearchClient", return_value=client),
    ):
        status = await get_catalog_index_status()

    assert status == AISearchIndexStatus(
        configured=True,
        reachable=True,
        non_empty=False,
        reason="ai_search_index_empty",
    )


@pytest.mark.asyncio
async def test_seed_catalog_index_from_crud_succeeds_when_documents_indexed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_SEARCH_ENDPOINT", "https://example.search.windows.net")
    monkeypatch.setenv("AI_SEARCH_INDEX", "catalog")

    products = [
        {
            "sku": "SKU-100",
            "name": "Running Jacket",
            "description": "Breathable jacket",
            "category": "apparel",
            "brand": "Contoso",
            "price": 89.99,
        },
        {
            "sku": "SKU-200",
            "name": "Trail Shoes",
            "description": "All-terrain shoe",
            "category": "footwear",
            "brand": "Contoso",
            "price": 129.99,
        },
    ]

    with (
        patch(
            "ecommerce_catalog_search.ai_search._fetch_seed_products_from_crud",
            new=AsyncMock(return_value=(products, None)),
        ) as mock_fetch,
        patch(
            "ecommerce_catalog_search.ai_search.upsert_catalog_documents",
            new=AsyncMock(return_value=True),
        ) as mock_upsert,
        patch(
            "ecommerce_catalog_search.ai_search.get_catalog_index_status",
            new=AsyncMock(
                return_value=AISearchIndexStatus(
                    configured=True,
                    reachable=True,
                    non_empty=True,
                )
            ),
        ) as mock_status,
    ):
        result = await seed_catalog_index_from_crud(max_attempts=1, batch_size=10)

    assert result.success is True
    assert result.attempt_count == 1
    assert result.seeded_documents == 2
    mock_fetch.assert_awaited_once_with(10)
    mock_upsert.assert_awaited_once()
    mock_status.assert_awaited_once()


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
async def test_vector_search_sends_no_select_restriction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AI Search queries must not include a $select clause so the index schema never blocks results."""
    monkeypatch.setenv("AI_SEARCH_ENDPOINT", "https://example.search.windows.net")
    monkeypatch.setenv("AI_SEARCH_VECTOR_INDEX", "product_search_index")

    credential = Mock()
    credential.close = AsyncMock()

    client = Mock()
    client.close = AsyncMock()
    client.search = AsyncMock(
        return_value=_AsyncResults(
            [{"sku": "SKU-303", "@search.score": 1.0, "title": "Trail Jacket"}]
        )
    )

    with (
        patch("ecommerce_catalog_search.ai_search._resolve_credential", return_value=credential),
        patch("ecommerce_catalog_search.ai_search.SearchClient", return_value=client),
    ):
        result = await vector_search(
            query_text="outdoor jacket",
            filters=None,
            top_k=2,
        )

    assert [item.sku for item in result] == ["SKU-303"]
    assert client.search.await_count == 1
    call_kwargs = client.search.await_args_list[0].kwargs
    assert "select" not in call_kwargs


@pytest.mark.asyncio
async def test_vector_search_returns_all_document_fields_for_model_filtering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """All fields returned by the index are available on the document for model-side filtering."""
    monkeypatch.setenv("AI_SEARCH_ENDPOINT", "https://example.search.windows.net")
    monkeypatch.setenv("AI_SEARCH_VECTOR_INDEX", "product_search_index")

    credential = Mock()
    credential.close = AsyncMock()

    document = {
        "sku": "SKU-101",
        "@search.score": 0.95,
        "title": "Merino Wool Base Layer",
        "description": "Lightweight thermal layer for cold weather.",
        "category": "clothing",
        "brand": "Contoso",
        "price": "49.99 usd",
    }
    client = Mock()
    client.close = AsyncMock()
    client.search = AsyncMock(return_value=_AsyncResults([document]))

    with (
        patch(
            "ecommerce_catalog_search.ai_search._resolve_credential",
            return_value=Mock(close=AsyncMock()),
        ),
        patch("ecommerce_catalog_search.ai_search.SearchClient", return_value=client),
    ):
        result = await vector_search(
            query_text="warm clothing for winter travel",
            filters=None,
            top_k=3,
        )

    assert len(result) == 1
    assert result[0].sku == "SKU-101"
    assert result[0].document["title"] == "Merino Wool Base Layer"
    assert result[0].document["category"] == "clothing"
    assert result[0].document["price"] == "49.99 usd"


@pytest.mark.asyncio
async def test_vector_search_returns_empty_on_http_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_SEARCH_ENDPOINT", "https://example.search.windows.net")
    monkeypatch.setenv("AI_SEARCH_VECTOR_INDEX", "product_search_index")

    credential = Mock()
    credential.close = AsyncMock()

    client = Mock()
    client.close = AsyncMock()
    client.search = AsyncMock(
        side_effect=HttpResponseError(message="Query syntax error in filter expression")
    )

    with (
        patch("ecommerce_catalog_search.ai_search._resolve_credential", return_value=credential),
        patch("ecommerce_catalog_search.ai_search.SearchClient", return_value=client),
    ):
        result = await vector_search(
            query_text="wireless headset",
            filters=None,
            top_k=2,
        )

    assert result == []
    assert client.search.await_count == 1


@pytest.mark.asyncio
async def test_vector_search_returns_empty_on_permission_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_SEARCH_ENDPOINT", "https://example.search.windows.net")
    monkeypatch.setenv("AI_SEARCH_VECTOR_INDEX", "product_search_index")

    forbidden_error = HttpResponseError(message="Access denied")
    forbidden_error.status_code = 403

    client = Mock()
    client.close = AsyncMock()
    client.search = AsyncMock(side_effect=forbidden_error)

    with (
        patch(
            "ecommerce_catalog_search.ai_search._resolve_credential",
            return_value=Mock(close=AsyncMock()),
        ),
        patch("ecommerce_catalog_search.ai_search.SearchClient", return_value=client),
    ):
        result = await vector_search(
            query_text="wireless headset",
            filters=None,
            top_k=2,
        )

    assert result == []
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
