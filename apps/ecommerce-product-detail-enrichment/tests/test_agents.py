"""Unit tests for ProductDetailEnrichmentAgent."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from ecommerce_product_detail_enrichment.adapters import (
    AcpContentAdapter,
    EnrichmentAdapters,
    ReviewAdapter,
    merge_product_enrichment,
)
from ecommerce_product_detail_enrichment.agents import ProductDetailEnrichmentAgent
from holiday_peak_lib.agents.base_agent import AgentDependencies
from holiday_peak_lib.schemas.inventory import InventoryContext, InventoryItem
from holiday_peak_lib.schemas.product import CatalogProduct


@pytest.fixture
def agent_config():
    """Create agent dependencies for testing."""
    return AgentDependencies(
        service_name="test-product-enrichment",
        router=None,
        tools={},
        slm=None,
        llm=None,
    )


class TestAcpContentAdapter:
    """Tests for AcpContentAdapter."""

    @pytest.mark.asyncio
    async def test_get_content_returns_enriched_data(self):
        """Test get_content returns enriched ACP data."""
        adapter = AcpContentAdapter()
        result = await adapter.get_content("SKU-001")

        assert result["sku"] == "SKU-001"
        assert "long_description" in result
        assert "features" in result
        assert len(result["features"]) > 0
        assert "media" in result


class TestReviewAdapter:
    """Tests for ReviewAdapter."""

    @pytest.mark.asyncio
    async def test_get_summary_returns_reviews(self):
        """Test get_summary returns review data."""
        adapter = ReviewAdapter()
        result = await adapter.get_summary("SKU-001")

        assert result["sku"] == "SKU-001"
        assert "rating" in result
        assert "review_count" in result
        assert "highlights" in result


class TestMergeProductEnrichment:
    """Tests for merge_product_enrichment function."""

    def test_merge_with_full_product(
        self, mock_catalog_product, mock_acp_content, mock_review_summary
    ):
        """Test merging with a full product."""
        result = merge_product_enrichment(
            mock_catalog_product, mock_acp_content, mock_review_summary
        )

        assert result["sku"] == "SKU-001"
        assert result["name"] == "Test Product"
        # ACP description should override
        assert result["description"] == "Rich, ACP-supplied product description."
        assert result["rating"] == 4.6
        assert result["review_count"] == 128
        assert "features" in result
        assert "media" in result
        assert "product" in result

    def test_merge_with_none_product(self, mock_acp_content, mock_review_summary):
        """Test merging when product is None."""
        result = merge_product_enrichment(None, mock_acp_content, mock_review_summary)

        assert result["sku"] == "SKU-001"
        assert result["description"] == "Rich, ACP-supplied product description."
        assert "features" in result
        assert "reviews" in result
        assert "name" not in result  # No product name when product is None


class TestProductDetailEnrichmentAgent:
    """Tests for ProductDetailEnrichmentAgent."""

    @pytest.mark.asyncio
    async def test_handle_enrichment_request(
        self,
        agent_config,
        mock_catalog_product,
        mock_inventory_context,
        mock_acp_content,
        mock_review_summary,
        mock_related_products,
    ):
        """Test handling an enrichment request."""
        with patch(
            "ecommerce_product_detail_enrichment.agents.build_enrichment_adapters"
        ) as mock_build:
            mock_products = AsyncMock()
            mock_products.get_product = AsyncMock(return_value=mock_catalog_product)
            mock_products.get_related = AsyncMock(return_value=mock_related_products)

            mock_inventory = AsyncMock()
            mock_inventory.build_inventory_context = AsyncMock(return_value=mock_inventory_context)

            mock_acp = AsyncMock()
            mock_acp.get_content = AsyncMock(return_value=mock_acp_content)

            mock_reviews = AsyncMock()
            mock_reviews.get_summary = AsyncMock(return_value=mock_review_summary)

            mock_build.return_value = EnrichmentAdapters(
                products=mock_products,
                inventory=mock_inventory,
                acp=mock_acp,
                reviews=mock_reviews,
            )

            agent = ProductDetailEnrichmentAgent(config=agent_config)
            result = await agent.handle({"sku": "SKU-001", "related_limit": 4})

            assert result["sku"] == "SKU-001"
            assert "description" in result
            assert "rating" in result
            assert "inventory" in result
            assert "related" in result
            assert len(result["related"]) == 2

    @pytest.mark.asyncio
    async def test_handle_missing_sku(self, agent_config):
        """Test handling request without sku returns error."""
        with patch(
            "ecommerce_product_detail_enrichment.agents.build_enrichment_adapters"
        ) as mock_build:
            mock_build.return_value = EnrichmentAdapters(
                products=AsyncMock(),
                inventory=AsyncMock(),
                acp=AsyncMock(),
                reviews=AsyncMock(),
            )

            agent = ProductDetailEnrichmentAgent(config=agent_config)
            result = await agent.handle({})

            assert "error" in result
            assert result["error"] == "sku is required"

    @pytest.mark.asyncio
    async def test_handle_product_not_found(self, agent_config):
        """Test handling when product is not found."""
        # Create ACP content with the requested SKU
        nonexistent_acp = {
            "sku": "NONEXISTENT",
            "long_description": "Enriched description for nonexistent product.",
            "features": ["Feature A"],
            "media": [],
        }
        nonexistent_review = {
            "sku": "NONEXISTENT",
            "rating": 0,
            "review_count": 0,
            "highlights": [],
        }

        with patch(
            "ecommerce_product_detail_enrichment.agents.build_enrichment_adapters"
        ) as mock_build:
            mock_products = AsyncMock()
            mock_products.get_product = AsyncMock(return_value=None)
            mock_products.get_related = AsyncMock(return_value=[])

            mock_inventory = AsyncMock()
            mock_inventory.build_inventory_context = AsyncMock(return_value=None)

            mock_acp = AsyncMock()
            mock_acp.get_content = AsyncMock(return_value=nonexistent_acp)

            mock_reviews = AsyncMock()
            mock_reviews.get_summary = AsyncMock(return_value=nonexistent_review)

            mock_build.return_value = EnrichmentAdapters(
                products=mock_products,
                inventory=mock_inventory,
                acp=mock_acp,
                reviews=mock_reviews,
            )

            agent = ProductDetailEnrichmentAgent(config=agent_config)
            result = await agent.handle({"sku": "NONEXISTENT"})

            # Should still return enrichment from ACP even if product not found
            assert result["sku"] == "NONEXISTENT"
            assert "description" in result

    @pytest.mark.asyncio
    async def test_handle_caches_to_hot_memory(
        self,
        agent_config,
        mock_catalog_product,
        mock_inventory_context,
        mock_acp_content,
        mock_review_summary,
    ):
        """Test that results are cached to hot memory."""
        mock_hot_memory = AsyncMock()
        mock_hot_memory.set = AsyncMock()

        with patch(
            "ecommerce_product_detail_enrichment.agents.build_enrichment_adapters"
        ) as mock_build:
            mock_products = AsyncMock()
            mock_products.get_product = AsyncMock(return_value=mock_catalog_product)
            mock_products.get_related = AsyncMock(return_value=[])

            mock_inventory = AsyncMock()
            mock_inventory.build_inventory_context = AsyncMock(return_value=mock_inventory_context)

            mock_acp = AsyncMock()
            mock_acp.get_content = AsyncMock(return_value=mock_acp_content)

            mock_reviews = AsyncMock()
            mock_reviews.get_summary = AsyncMock(return_value=mock_review_summary)

            mock_build.return_value = EnrichmentAdapters(
                products=mock_products,
                inventory=mock_inventory,
                acp=mock_acp,
                reviews=mock_reviews,
            )

            agent = ProductDetailEnrichmentAgent(config=agent_config)
            # Set hot memory via the property
            agent.hot_memory = mock_hot_memory

            await agent.handle({"sku": "SKU-001", "cache_ttl": 600})

            mock_hot_memory.set.assert_called_once()
            call_args = mock_hot_memory.set.call_args
            assert call_args.kwargs["key"] == "pdp:SKU-001"
            assert call_args.kwargs["ttl_seconds"] == 600
