"""Tests for recommendation-agent capability hosted by search enrichment."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from holiday_peak_lib.agents.base_agent import AgentDependencies
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer
from search_enrichment_agent.adapters import ApprovedTruthAdapter, SearchEnrichmentAdapters
from search_enrichment_agent.agents import SearchEnrichmentAgent, register_mcp_tools
from search_enrichment_agent.recommendations import (
    ComposeRecommendationsRequest,
    RankRecommendationsRequest,
    RecommendationCandidate,
    RecommendationCandidatesRequest,
    RecommendationEngine,
    RecommendationEvidence,
    RecommendationOrchestrator,
)

pytestmark = pytest.mark.usefixtures("mock_foundry_readiness")


def _build_client() -> TestClient:
    from search_enrichment_agent.main import app

    return TestClient(app)


def _agent_config_without_models() -> AgentDependencies:
    return AgentDependencies(
        service_name="search-enrichment-agent-test",
        router=None,
        tools={},
        slm=None,
        llm=None,
    )


def test_engine_builds_candidates_from_product_correlations() -> None:
    engine = RecommendationEngine()
    request = RecommendationCandidatesRequest(
        tenant_id="tenant-1",
        seed_skus=["SKU-SHOE"],
        max_candidates=5,
    )

    candidates = engine.build_correlated_candidates(
        request=request,
        seed_products={
            "SKU-SHOE": {
                "sku": "SKU-SHOE",
                "name": "Trail Shoe",
                "category": "footwear",
                "complementary_products": ["SKU-SOCK"],
                "substitute_products": ["SKU-BOOT"],
            }
        },
    )

    assert [candidate.sku for candidate in candidates] == ["SKU-SOCK", "SKU-BOOT"]
    assert candidates[0].reason_codes == ["complementary_product"]
    assert candidates[0].evidence[0].source == "complement"


def test_rank_boosts_intent_overlap_and_penalizes_cart_items() -> None:
    engine = RecommendationEngine()
    response = engine.rank(
        RankRecommendationsRequest(
            tenant_id="tenant-1",
            session_id="session-1",
            intent="trail running socks",
            cart_skus=["SKU-IN-CART"],
            candidates=[
                RecommendationCandidate(
                    sku="SKU-SOCK",
                    score=0.55,
                    reason_codes=["complementary_product"],
                    evidence=[
                        RecommendationEvidence(
                            source="complement",
                            reason="Trail running complement",
                            weight=0.12,
                        )
                    ],
                ),
                RecommendationCandidate(sku="SKU-IN-CART", score=0.9),
            ],
        )
    )

    assert response[0].sku == "SKU-SOCK"
    assert "intent_overlap" in response[0].reason_codes
    assert "already_in_cart" in response[1].reason_codes


@pytest.mark.asyncio
async def test_orchestrator_composes_ui_ready_cards_with_product_context() -> None:
    adapters = SearchEnrichmentAdapters(
        approved_truth=ApprovedTruthAdapter(
            seeded_truth={
                "SKU-SOCK": {
                    "sku": "SKU-SOCK",
                    "name": "Trail Sock",
                    "category": "footwear",
                    "price": 14.99,
                    "images": ["https://example.test/sock.png"],
                    "in_stock": True,
                }
            }
        )
    )
    orchestrator = RecommendationOrchestrator(adapters, RecommendationEngine())

    response = await orchestrator.compose(
        ComposeRecommendationsRequest(
            tenant_id="tenant-1",
            ranked_items=[RecommendationCandidate(sku="SKU-SOCK", score=0.8)],
        )
    )

    assert response.ready_for_ui is True
    assert response.cards[0].display.title == "Trail Sock"
    assert response.cards[0].display.availability == "available"
    assert response.cards[0].display.price == 14.99


def test_recommendation_rest_endpoints_are_registered() -> None:
    client = _build_client()

    candidates_response = client.post(
        "/recommendations/candidates",
        json={"tenant_id": "tenant-1", "candidate_skus": ["SKU-REC"]},
    )
    assert candidates_response.status_code == 200
    assert candidates_response.json()["status"] == "ready"

    rank_response = client.post(
        "/recommendations/rank",
        json={
            "tenant_id": "tenant-1",
            "intent": "gift",
            "candidates": [{"sku": "SKU-REC", "score": 0.5}],
        },
    )
    assert rank_response.status_code == 200
    assert rank_response.json()["ranked"][0]["sku"] == "SKU-REC"

    compose_response = client.post(
        "/recommendations/compose",
        json={"tenant_id": "tenant-1", "ranked_items": [{"sku": "SKU-REC", "score": 0.5}]},
    )
    assert compose_response.status_code == 200
    assert compose_response.json()["ready_for_ui"] is True

    status_response = client.get("/models/status")
    assert status_response.status_code == 200
    assert status_response.json()["service"] == "recommendation-agent"
    assert status_response.json()["hosted_by"] == "search-enrichment-agent"


@pytest.mark.asyncio
async def test_recommendation_mcp_tools_are_registered() -> None:
    mcp = Mock(spec=FastAPIMCPServer)
    mcp.tools = {}

    def add_tool(path, handler):  # noqa: ANN001
        mcp.tools[path] = handler

    mcp.add_tool = add_tool
    adapters = SearchEnrichmentAdapters()

    with patch(
        "search_enrichment_agent.agents.build_search_enrichment_adapters",
        return_value=adapters,
    ):
        agent = SearchEnrichmentAgent(config=_agent_config_without_models())
        register_mcp_tools(mcp, agent)

    assert "/recommendations/candidates" in mcp.tools
    assert "/recommendations/rank" in mcp.tools
    assert "/recommendations/compose" in mcp.tools
    assert "/recommendations/feedback" in mcp.tools
    assert "/recommendations/explain" in mcp.tools
    assert "/models/status" in mcp.tools

    candidates = await mcp.tools["/recommendations/candidates"](
        {"tenant_id": "tenant-1", "candidate_skus": ["SKU-REC"]}
    )

    assert candidates["status"] == "ready"
    assert candidates["candidates"][0]["sku"] == "SKU-REC"
