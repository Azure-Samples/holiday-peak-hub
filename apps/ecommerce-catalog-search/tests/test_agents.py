"""Unit tests for CatalogSearchAgent."""

import logging
from unittest.mock import AsyncMock, patch

import pytest
from ecommerce_catalog_search.adapters import AcpCatalogMapper, CatalogAdapters
from ecommerce_catalog_search.agents import CatalogSearchAgent
from ecommerce_catalog_search.ai_search import AISearchDocumentResult, AISearchSkuResult
from holiday_peak_lib.agents.base_agent import AgentDependencies
from holiday_peak_lib.schemas.inventory import InventoryItem
from holiday_peak_lib.schemas.product import CatalogProduct
from holiday_peak_lib.schemas.truth import IntentClassification


@pytest.fixture(name="agent_dependencies")
def fixture_agent_dependencies():
    """Create agent dependencies for testing."""
    return AgentDependencies(
        service_name="test-catalog-search",
        router=None,
        tools={},
        slm=None,
        llm=None,
    )


class TestAcpCatalogMapper:
    """Tests for AcpCatalogMapper."""

    def test_to_acp_product_full_product(self, mock_catalog_product):
        """Test mapping a full product to ACP format."""
        mapper = AcpCatalogMapper()
        result = mapper.to_acp_product(mock_catalog_product, availability="in_stock")

        assert result["item_id"] == "SKU-001"
        assert result["title"] == "Test Product"
        assert result["brand"] == "TestBrand"
        assert result["availability"] == "in_stock"
        assert result["price"] == "99.99 usd"
        assert result["is_eligible_search"] is True
        assert result["is_eligible_checkout"] is True
        assert "url" in result
        assert "image_url" in result

    def test_to_acp_product_minimal_product(self):
        """Test mapping a minimal product to ACP format."""
        mapper = AcpCatalogMapper()
        product = CatalogProduct(
            sku="MIN-001",
            name="Minimal Product",
            description=None,
            price=None,
            category="uncategorized",
            brand=None,
        )
        result = mapper.to_acp_product(product, availability="out_of_stock")

        assert result["item_id"] == "MIN-001"
        assert result["title"] == "Minimal Product"
        assert result["description"] == ""
        assert result["brand"] == ""
        assert result["price"] == "0.00 usd"
        assert result["availability"] == "out_of_stock"
        # Should use placeholder image
        assert "placeholder" in result["image_url"]

    def test_to_acp_product_custom_currency(self, mock_catalog_product):
        """Test mapping with custom currency."""
        mapper = AcpCatalogMapper()
        result = mapper.to_acp_product(
            mock_catalog_product, availability="in_stock", currency="eur"
        )

        assert result["price"] == "99.99 eur"


class TestCatalogSearchAgent:
    """Tests for CatalogSearchAgent."""

    @pytest.mark.asyncio
    async def test_handle_search_query(self, agent_dependencies, mock_catalog_product):
        """Test handling a search query."""
        mock_inventory_item = InventoryItem(sku="SKU-001", available=10, reserved=0)

        with patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build:
            mock_products = AsyncMock()
            mock_products.get_product = AsyncMock(return_value=mock_catalog_product)
            mock_products.get_related = AsyncMock(return_value=[])

            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(return_value=mock_inventory_item)

            mock_mapping = AcpCatalogMapper()

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=mock_mapping,
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            result = await agent.handle({"query": "test product", "limit": 5})

            assert result["service"] == "test-catalog-search"
            assert result["query"] == "test product"
            assert "results" in result
            assert len(result["results"]) == 1
            # Verify ACP format
            assert result["results"][0]["item_id"] == "SKU-001"

    @pytest.mark.asyncio
    async def test_handle_empty_query(self, agent_dependencies):
        """Test handling an empty search query."""
        with patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build:
            mock_products = AsyncMock()
            mock_products.get_product = AsyncMock(return_value=None)
            mock_products.get_related = AsyncMock(return_value=[])

            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(return_value=None)
            mock_mapping = AcpCatalogMapper()

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=mock_mapping,
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            result = await agent.handle({"query": "", "limit": 5})

            assert result["service"] == "test-catalog-search"
            assert result["query"] == ""
            assert result["results"] == []

    @pytest.mark.asyncio
    async def test_handle_respects_limit(self, agent_dependencies, mock_catalog_products):
        """Test that search respects limit parameter."""
        mock_inventory_item = InventoryItem(sku="SKU-001", available=10, reserved=0)

        with patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build:
            mock_products = AsyncMock()
            mock_products.get_product = AsyncMock(return_value=mock_catalog_products[0])
            mock_products.get_related = AsyncMock(return_value=[])

            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(return_value=mock_inventory_item)

            mock_mapping = AcpCatalogMapper()

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=mock_mapping,
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            result = await agent.handle({"query": "test", "limit": 1})

            assert len(result["results"]) == 1

    @pytest.mark.asyncio
    async def test_handle_uses_ai_search_results(self, agent_dependencies, mock_catalog_product):
        """Test configured AI Search path uses returned SKU order."""
        mock_inventory_item = InventoryItem(sku="SKU-001", available=10, reserved=0)

        with (
            patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build,
            patch("ecommerce_catalog_search.agents.search_catalog_skus_detailed") as mock_search,
        ):
            mock_search.return_value = AISearchSkuResult(skus=["SKU-001"])

            mock_products = AsyncMock()
            mock_products.get_product = AsyncMock(return_value=mock_catalog_product)
            mock_products.get_related = AsyncMock(return_value=[])

            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(return_value=mock_inventory_item)

            mock_mapping = AcpCatalogMapper()

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=mock_mapping,
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            result = await agent.handle({"query": "running shoes", "limit": 5})

            assert len(result["results"]) == 1
            assert result["results"][0]["item_id"] == "SKU-001"
            mock_search.assert_awaited_once_with(query="running shoes", limit=5)
            mock_products.get_related.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_handle_falls_back_when_ai_search_empty(
        self, agent_dependencies, mock_catalog_product
    ):
        """Test fallback path remains active when AI Search has no hits."""
        mock_inventory_item = InventoryItem(sku="SKU-001", available=10, reserved=0)

        with (
            patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build,
            patch("ecommerce_catalog_search.agents.search_catalog_skus_detailed") as mock_search,
        ):
            mock_search.return_value = AISearchSkuResult(skus=[])

            mock_products = AsyncMock()
            mock_products.get_product = AsyncMock(return_value=mock_catalog_product)
            mock_products.get_related = AsyncMock(return_value=[])

            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(return_value=mock_inventory_item)

            mock_mapping = AcpCatalogMapper()

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=mock_mapping,
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            result = await agent.handle({"query": "fallback query", "limit": 3})

            assert len(result["results"]) == 1
            mock_search.assert_awaited_once_with(query="fallback query", limit=3)
            mock_products.get_related.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handle_logs_fallback_reason_when_ai_search_degraded(
        self, agent_dependencies, mock_catalog_product, caplog
    ):
        """Test fallback reason from AI Search degradation is logged by caller path."""
        mock_inventory_item = InventoryItem(sku="SKU-001", available=10, reserved=0)

        with (
            patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build,
            patch("ecommerce_catalog_search.agents.search_catalog_skus_detailed") as mock_search,
        ):
            mock_search.return_value = AISearchSkuResult(
                skus=[],
                fallback_reason="ai_search_transport_error",
            )

            mock_products = AsyncMock()
            mock_products.get_product = AsyncMock(return_value=mock_catalog_product)
            mock_products.get_related = AsyncMock(return_value=[])

            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(return_value=mock_inventory_item)

            mock_mapping = AcpCatalogMapper()

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=mock_mapping,
            )

            caplog.set_level(logging.WARNING, logger="ecommerce_catalog_search.agents")

            agent = CatalogSearchAgent(config=agent_dependencies)
            await agent.handle({"query": "fallback query", "limit": 3})

            assert any(
                record.msg == "catalog_search_fallback_path"
                and getattr(record, "fallback_reason", None) == "ai_search_transport_error"
                for record in caplog.records
            )

    @pytest.mark.asyncio
    async def test_handle_intelligent_mode_falls_back_on_low_confidence(
        self, agent_dependencies, mock_catalog_product
    ):
        """Intelligent mode should degrade to keyword path when confidence is low."""
        mock_inventory_item = InventoryItem(sku="SKU-001", available=10, reserved=0)

        with (
            patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build,
            patch("ecommerce_catalog_search.agents.search_catalog_skus_detailed") as mock_search,
            patch("ecommerce_catalog_search.agents.multi_query_search") as mock_multi,
        ):
            mock_search.return_value = AISearchSkuResult(skus=["SKU-001"])

            mock_products = AsyncMock()
            mock_products.get_product = AsyncMock(return_value=mock_catalog_product)
            mock_products.get_related = AsyncMock(return_value=[])

            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(return_value=mock_inventory_item)

            mock_mapping = AcpCatalogMapper()

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=mock_mapping,
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            with (
                patch.object(agent, "_assess_complexity", return_value=1.0),
                patch.object(
                    agent,
                    "classify_intent",
                    new=AsyncMock(
                        return_value=IntentClassification(
                            intent="semantic_search",
                            confidence=0.45,
                            entities={"category": "electronics"},
                        )
                    ),
                ),
            ):
                result = await agent.handle(
                    {"query": "show me travel accessories", "limit": 5, "mode": "intelligent"}
                )

            assert len(result["results"]) == 1
            assert result["results"][0]["item_id"] == "SKU-001"
            mock_multi.assert_not_awaited()
            mock_search.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handle_intelligent_mode_runs_multi_query_and_merges_enrichment(
        self, agent_dependencies, mock_catalog_product
    ):
        """Intelligent mode should use multi-query retrieval and surface enriched fields."""
        mock_inventory_item = InventoryItem(sku="SKU-001", available=10, reserved=0)

        with (
            patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build,
            patch("ecommerce_catalog_search.agents.search_catalog_skus_detailed") as mock_search,
            patch("ecommerce_catalog_search.agents.multi_query_search") as mock_multi,
        ):
            mock_search.return_value = AISearchSkuResult(skus=[])
            mock_multi.return_value = [
                AISearchDocumentResult(
                    sku="SKU-001",
                    score=0.98,
                    document={"sku": "SKU-001"},
                    enriched_fields={
                        "use_cases": ["travel", "commute"],
                        "complementary_products": ["SKU-321"],
                        "substitute_products": ["SKU-654"],
                        "enriched_description": "Noise-canceling headphones for travel.",
                    },
                )
            ]

            mock_products = AsyncMock()
            mock_products.get_product = AsyncMock(return_value=mock_catalog_product)
            mock_products.get_related = AsyncMock(return_value=[])

            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(return_value=mock_inventory_item)

            mock_mapping = AcpCatalogMapper()

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=mock_mapping,
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            with (
                patch.object(agent, "_assess_complexity", return_value=0.95),
                patch.object(
                    agent,
                    "classify_intent",
                    new=AsyncMock(
                        return_value=IntentClassification(
                            intent="semantic_search",
                            confidence=0.91,
                            entities={"category": "audio", "keywords": ["travel"]},
                        )
                    ),
                ),
            ):
                result = await agent.handle(
                    {"query": "best headphones for travel", "limit": 5, "mode": "intelligent"}
                )

            first = result["results"][0]
            assert first["item_id"] == "SKU-001"
            assert first["use_cases"] == ["travel", "commute"]
            assert first["complementary_products"] == ["SKU-321"]
            assert first["substitute_products"] == ["SKU-654"]
            assert "extended_attributes" in first
            assert first["extended_attributes"]["enriched_description"].startswith(
                "Noise-canceling"
            )
            mock_multi.assert_awaited_once()

    def test_build_sub_queries_from_intent_entities(self, agent_dependencies):
        """Private sub-query builder should include deduped intent entities."""
        with patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build:
            mock_build.return_value = CatalogAdapters(
                products=AsyncMock(),
                inventory=AsyncMock(),
                mapping=AcpCatalogMapper(),
            )
            agent = CatalogSearchAgent(config=agent_dependencies)

        intent = IntentClassification(
            intent="semantic_search",
            confidence=0.9,
            entities={
                "category": "audio",
                "features": ["wireless", "noise cancellation"],
                "keywords": ["wireless", "travel"],
            },
        )
        sub_queries = agent.build_sub_queries("best travel headphones", intent)

        assert "best travel headphones" in sub_queries
        assert "audio" in sub_queries
        assert "wireless" in sub_queries
        assert sub_queries.count("wireless") == 1

    def test_merge_results_dedupes_and_prefers_richer_enrichment(self, agent_dependencies):
        """Private merger should dedupe by SKU and keep richest enriched payload."""
        with patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build:
            mock_build.return_value = CatalogAdapters(
                products=AsyncMock(),
                inventory=AsyncMock(),
                mapping=AcpCatalogMapper(),
            )
            agent = CatalogSearchAgent(config=agent_dependencies)

        first = AISearchDocumentResult(
            sku="SKU-1",
            score=0.82,
            document={"sku": "SKU-1"},
            enriched_fields={"use_cases": ["travel"]},
        )
        second = AISearchDocumentResult(
            sku="SKU-2",
            score=0.9,
            document={"sku": "SKU-2"},
            enriched_fields={},
        )
        duplicate_richer = AISearchDocumentResult(
            sku="SKU-1",
            score=0.8,
            document={"sku": "SKU-1"},
            enriched_fields={
                "use_cases": ["travel", "office"],
                "enriched_description": "Versatile headset.",
            },
        )

        merged = agent.merge_results([[first, second], [duplicate_richer]], limit=5)

        assert [item.sku for item in merged][:2] == ["SKU-1", "SKU-2"]
        assert merged[0].enriched_fields["enriched_description"] == "Versatile headset."
