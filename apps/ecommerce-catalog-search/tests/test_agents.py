"""Unit tests for CatalogSearchAgent."""

import logging
from unittest.mock import AsyncMock, patch

import pytest
from ecommerce_catalog_search.adapters import AcpCatalogMapper, CatalogAdapters
from ecommerce_catalog_search.ai_search import AISearchSkuResult
from ecommerce_catalog_search.agents import CatalogSearchAgent
from holiday_peak_lib.agents.base_agent import AgentDependencies
from holiday_peak_lib.schemas.inventory import InventoryItem
from holiday_peak_lib.schemas.product import CatalogProduct


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
        mock_inventory_item = InventoryItem(
            sku="SKU-001", available=10, reserved=0, warehouse_id="WH1"
        )

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
        mock_inventory_item = InventoryItem(
            sku="SKU-001", available=10, reserved=0, warehouse_id="WH1"
        )

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
    async def test_handle_uses_ai_search_results(
        self, agent_dependencies, mock_catalog_product
    ):
        """Test configured AI Search path uses returned SKU order."""
        mock_inventory_item = InventoryItem(
            sku="SKU-001", available=10, reserved=0, warehouse_id="WH1"
        )

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
        mock_inventory_item = InventoryItem(
            sku="SKU-001", available=10, reserved=0, warehouse_id="WH1"
        )

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
        mock_inventory_item = InventoryItem(
            sku="SKU-001", available=10, reserved=0, warehouse_id="WH1"
        )

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
                and getattr(record, "fallback_reason", None)
                == "ai_search_transport_error"
                for record in caplog.records
            )
