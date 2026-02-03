"""Unit tests for product detail enrichment MCP tool registration."""
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock

from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer
from holiday_peak_lib.schemas.inventory import InventoryContext, InventoryItem
from holiday_peak_lib.schemas.product import CatalogProduct

from ecommerce_product_detail_enrichment.agents import register_mcp_tools
from ecommerce_product_detail_enrichment.adapters import EnrichmentAdapters


@pytest.fixture
def mock_mcp_server():
    """Create a mock MCP server."""
    mcp = MagicMock(spec=FastAPIMCPServer)
    mcp.tools = {}

    def add_tool(path, handler):
        mcp.tools[path] = handler

    mcp.add_tool = add_tool
    return mcp


@pytest.fixture
def mock_agent(
    mock_catalog_product,
    mock_inventory_context,
    mock_acp_content,
    mock_review_summary,
    mock_related_products,
):
    """Create a mock agent with adapters."""
    mock_products = AsyncMock()
    mock_products.get_product = AsyncMock(return_value=mock_catalog_product)
    mock_products.get_related = AsyncMock(return_value=mock_related_products)

    mock_inventory = AsyncMock()
    mock_inventory.build_inventory_context = AsyncMock(
        return_value=mock_inventory_context
    )

    mock_acp = AsyncMock()
    mock_acp.get_content = AsyncMock(return_value=mock_acp_content)

    mock_reviews = AsyncMock()
    mock_reviews.get_summary = AsyncMock(return_value=mock_review_summary)

    agent = Mock()
    agent.adapters = EnrichmentAdapters(
        products=mock_products,
        inventory=mock_inventory,
        acp=mock_acp,
        reviews=mock_reviews,
    )
    return agent


class TestMCPToolRegistration:
    """Tests for MCP tool registration."""

    def test_registers_product_details_tool(self, mock_mcp_server, mock_agent):
        """Test that product details tool is registered."""
        with patch.dict("os.environ", {}, clear=False):
            register_mcp_tools(mock_mcp_server, mock_agent)

        assert "/product/detail" in mock_mcp_server.tools

    def test_registers_similar_products_tool(self, mock_mcp_server, mock_agent):
        """Test that similar products tool is registered."""
        with patch.dict("os.environ", {}, clear=False):
            register_mcp_tools(mock_mcp_server, mock_agent)

        assert "/product/similar" in mock_mcp_server.tools


class TestMCPToolExecution:
    """Tests for MCP tool execution."""

    @pytest.mark.asyncio
    async def test_get_product_details_returns_enriched_product(
        self, mock_mcp_server, mock_agent
    ):
        """Test product details tool returns enriched product data."""
        with patch.dict("os.environ", {}, clear=False):
            register_mcp_tools(mock_mcp_server, mock_agent)

        tool = mock_mcp_server.tools["/product/detail"]
        result = await tool({"sku": "SKU-001"})

        assert "enriched_product" in result
        assert result["enriched_product"]["sku"] == "SKU-001"
        assert "description" in result["enriched_product"]
        assert "rating" in result["enriched_product"]
        assert "inventory" in result["enriched_product"]
        assert "related" in result["enriched_product"]

    @pytest.mark.asyncio
    async def test_get_product_details_requires_sku(self, mock_mcp_server, mock_agent):
        """Test product details tool requires sku parameter."""
        with patch.dict("os.environ", {}, clear=False):
            register_mcp_tools(mock_mcp_server, mock_agent)

        tool = mock_mcp_server.tools["/product/detail"]
        result = await tool({})

        assert "error" in result
        assert result["error"] == "sku is required"

    @pytest.mark.asyncio
    async def test_get_similar_products_returns_related(
        self, mock_mcp_server, mock_agent
    ):
        """Test similar products tool returns related products."""
        with patch.dict("os.environ", {}, clear=False):
            register_mcp_tools(mock_mcp_server, mock_agent)

        tool = mock_mcp_server.tools["/product/similar"]
        result = await tool({"sku": "SKU-001", "limit": 4})

        assert "sku" in result
        assert "related" in result
        assert len(result["related"]) == 2

    @pytest.mark.asyncio
    async def test_get_similar_products_requires_sku(self, mock_mcp_server, mock_agent):
        """Test similar products tool requires sku parameter."""
        with patch.dict("os.environ", {}, clear=False):
            register_mcp_tools(mock_mcp_server, mock_agent)

        tool = mock_mcp_server.tools["/product/similar"]
        result = await tool({})

        assert "error" in result
        assert result["error"] == "sku is required"

    @pytest.mark.asyncio
    async def test_get_similar_products_respects_limit(
        self, mock_mcp_server, mock_agent
    ):
        """Test similar products tool respects limit parameter."""
        # Mock to return only 1 product when limit is 1
        mock_agent.adapters.products.get_related = AsyncMock(
            return_value=[
                CatalogProduct(
                    sku="SKU-002",
                    name="Related Product",
                    description="Desc",
                    price=50.0,
                    category="test",
                    brand="TestBrand",
                )
            ]
        )

        with patch.dict("os.environ", {}, clear=False):
            register_mcp_tools(mock_mcp_server, mock_agent)

        tool = mock_mcp_server.tools["/product/similar"]
        result = await tool({"sku": "SKU-001", "limit": 1})

        assert len(result["related"]) == 1
