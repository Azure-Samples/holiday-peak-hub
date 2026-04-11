from __future__ import annotations

import logging
from unittest.mock import AsyncMock, patch

import pytest
from ecommerce_catalog_search.agents import CatalogSearchAgent
from ecommerce_catalog_search.ai_search import AISearchDocumentResult, AISearchSkuResult
from holiday_peak_lib.schemas.truth import IntentClassification

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]


async def test_simple_keyword_query_uses_keyword_path(
    agent_config_without_models,
    build_catalog_harness,
    catalog_product,
) -> None:
    harness = build_catalog_harness(products_by_sku={"SKU-100": catalog_product})

    with (
        patch(
            "ecommerce_catalog_search.agents.build_catalog_adapters", return_value=harness.adapters
        ),
        patch(
            "ecommerce_catalog_search.agents.search_catalog_skus_detailed",
            return_value=AISearchSkuResult(skus=["SKU-100"]),
        ) as mock_ai_lookup,
        patch("ecommerce_catalog_search.agents.multi_query_search") as mock_multi,
    ):
        agent = CatalogSearchAgent(config=agent_config_without_models)
        result = await agent.handle({"query": "explorer headphones", "limit": 5, "mode": "keyword"})

    assert result["mode"] == "keyword"
    assert result["results"][0]["item_id"] == "SKU-100"
    mock_ai_lookup.assert_awaited_once_with(query="explorer headphones", limit=5)
    mock_multi.assert_not_awaited()


async def test_complex_query_uses_intelligent_path_with_intent_and_hybrid_search(
    agent_config_without_models,
    build_catalog_harness,
    catalog_product,
) -> None:
    harness = build_catalog_harness(products_by_sku={"SKU-100": catalog_product})
    ranked_results = [
        AISearchDocumentResult(
            sku="SKU-100",
            score=0.99,
            document={"sku": "SKU-100"},
            enriched_fields={
                "use_cases": ["travel", "commute"],
                "enriched_description": "Adaptive noise cancellation for commuting and travel.",
            },
        )
    ]

    with (
        patch(
            "ecommerce_catalog_search.agents.build_catalog_adapters", return_value=harness.adapters
        ),
        patch(
            "ecommerce_catalog_search.agents.search_catalog_skus_detailed",
            return_value=AISearchSkuResult(skus=[]),
        ),
        patch(
            "ecommerce_catalog_search.agents.multi_query_search",
            new=AsyncMock(return_value=ranked_results),
        ) as mock_multi,
    ):
        agent = CatalogSearchAgent(config=agent_config_without_models)
        with (
            patch.object(agent, "_assess_complexity", return_value=0.94),
            patch.object(
                agent,
                "classify_intent",
                new=AsyncMock(
                    return_value=IntentClassification(
                        intent="semantic_search",
                        confidence=0.92,
                        entities={
                            "use_case": "travel",
                            "features": ["noise cancellation", "wireless"],
                        },
                    )
                ),
            ),
        ):
            result = await agent.handle(
                {
                    "query": "best wireless headphones for long flights",
                    "limit": 5,
                    "mode": "intelligent",
                }
            )

    assert result["mode"] == "intelligent"
    assert result["intent"]["intent"] == "semantic_search"
    assert result["results"][0]["item_id"] == "SKU-100"
    mock_multi.assert_awaited_once()
    assert mock_multi.await_count > 0
    await_kwargs = mock_multi.await_args_list[-1].kwargs
    assert await_kwargs is not None
    called_sub_queries = await_kwargs["sub_queries"]
    assert "best wireless headphones for long flights" in called_sub_queries
    assert "travel" in called_sub_queries
    assert "noise cancellation" in called_sub_queries


async def test_use_case_intent_matches_include_use_cases(
    agent_config_without_models,
    build_catalog_harness,
    catalog_product,
) -> None:
    harness = build_catalog_harness(products_by_sku={"SKU-100": catalog_product})

    with (
        patch(
            "ecommerce_catalog_search.agents.build_catalog_adapters", return_value=harness.adapters
        ),
        patch(
            "ecommerce_catalog_search.agents.search_catalog_skus_detailed",
            return_value=AISearchSkuResult(skus=[]),
        ),
        patch(
            "ecommerce_catalog_search.agents.multi_query_search",
            new=AsyncMock(
                return_value=[
                    AISearchDocumentResult(
                        sku="SKU-100",
                        score=0.88,
                        document={"sku": "SKU-100"},
                        enriched_fields={"use_cases": ["office", "remote work"]},
                    )
                ]
            ),
        ),
    ):
        agent = CatalogSearchAgent(config=agent_config_without_models)
        with (
            patch.object(agent, "_assess_complexity", return_value=0.88),
            patch.object(
                agent,
                "classify_intent",
                new=AsyncMock(
                    return_value=IntentClassification(
                        intent="use_case_search",
                        confidence=0.9,
                        entities={"use_case": "office"},
                    )
                ),
            ),
        ):
            result = await agent.handle(
                {
                    "query": "headphones for office calls",
                    "limit": 3,
                    "mode": "intelligent",
                }
            )

    first = result["results"][0]
    assert first["use_cases"] == ["office", "remote work"]
    assert first["extended_attributes"]["use_cases"] == ["office", "remote work"]


async def test_complementary_resolution_includes_readable_related_products(
    agent_config_without_models,
    build_catalog_harness,
    catalog_product,
) -> None:
    harness = build_catalog_harness(products_by_sku={"SKU-100": catalog_product})

    with (
        patch(
            "ecommerce_catalog_search.agents.build_catalog_adapters", return_value=harness.adapters
        ),
        patch(
            "ecommerce_catalog_search.agents.search_catalog_skus_detailed",
            return_value=AISearchSkuResult(skus=[]),
        ),
        patch(
            "ecommerce_catalog_search.agents.multi_query_search",
            new=AsyncMock(
                return_value=[
                    AISearchDocumentResult(
                        sku="SKU-100",
                        score=0.87,
                        document={"sku": "SKU-100"},
                        enriched_fields={
                            "complementary_products": [
                                "Travel Case",
                                "Premium Carry Sleeve",
                            ]
                        },
                    )
                ]
            ),
        ),
    ):
        agent = CatalogSearchAgent(config=agent_config_without_models)
        with (
            patch.object(agent, "_assess_complexity", return_value=0.9),
            patch.object(
                agent,
                "classify_intent",
                new=AsyncMock(
                    return_value=IntentClassification(
                        intent="complementary_search",
                        confidence=0.86,
                        entities={"category": "accessories"},
                    )
                ),
            ),
        ):
            result = await agent.handle(
                {
                    "query": "what accessories go with these headphones",
                    "limit": 3,
                    "mode": "intelligent",
                }
            )

    related = result["results"][0]["complementary_products"]
    assert related == ["Travel Case", "Premium Carry Sleeve"]
    assert all(isinstance(item, str) and len(item.strip().split()) >= 1 for item in related)


async def test_indexer_lag_returns_no_results(
    agent_config_without_models, build_catalog_harness
) -> None:
    harness = build_catalog_harness(products_by_sku={}, default_product=None, related_products=[])

    with (
        patch(
            "ecommerce_catalog_search.agents.build_catalog_adapters", return_value=harness.adapters
        ),
        patch(
            "ecommerce_catalog_search.agents.search_catalog_skus_detailed",
            return_value=AISearchSkuResult(skus=[]),
        ),
    ):
        agent = CatalogSearchAgent(config=agent_config_without_models)
        result = await agent.handle({"query": "new arrivals from 5 minutes ago", "limit": 5})

    assert result["mode"] == "intelligent"
    assert result["results"] == []


async def test_ai_search_unavailable_uses_fallback_path(
    agent_config_without_models,
    build_catalog_harness,
    catalog_product,
    caplog,
    monkeypatch,
) -> None:
    # Disable strict mode so the fallback path is exercised regardless of
    # CI environment (KUBERNETES_SERVICE_HOST may enable strict mode by default).
    monkeypatch.setenv("CATALOG_SEARCH_REQUIRE_AI_SEARCH", "false")

    harness = build_catalog_harness(default_product=catalog_product, related_products=[])
    harness.products.search = AsyncMock(return_value=[catalog_product])

    caplog.set_level(logging.WARNING, logger="ecommerce_catalog_search.agents")

    with (
        patch(
            "ecommerce_catalog_search.agents.build_catalog_adapters", return_value=harness.adapters
        ),
        patch(
            "ecommerce_catalog_search.agents.search_catalog_skus_detailed",
            return_value=AISearchSkuResult(skus=[], fallback_reason="ai_search_transport_error"),
        ),
    ):
        agent = CatalogSearchAgent(config=agent_config_without_models)
        result = await agent.handle({"query": "explorer headphones", "limit": 4})

    assert result["results"]
    assert result["results"][0]["item_id"] == "SKU-100"
    assert any(
        record.msg == "catalog_search_fallback_path"
        and getattr(record, "fallback_reason", None) == "ai_search_transport_error"
        for record in caplog.records
    )
