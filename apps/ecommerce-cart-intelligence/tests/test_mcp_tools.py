"""Unit tests for cart intelligence MCP tool registration."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from ecommerce_cart_intelligence.adapters import CartAdapters, CartAnalyticsAdapter
from ecommerce_cart_intelligence.agents import CartIntelligenceAgent, register_mcp_tools
from holiday_peak_lib.agents.base_agent import AgentDependencies
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer
from holiday_peak_lib.schemas.inventory import InventoryContext, InventoryItem
from holiday_peak_lib.schemas.pricing import PriceContext, PriceEntry
from holiday_peak_lib.schemas.product import CatalogProduct, ProductContext


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
def mock_agent():
    """Create a mock agent with adapters."""
    mock_product_ctx = ProductContext(
        sku="SKU-001",
        product=CatalogProduct(
            sku="SKU-001",
            name="Test Product",
            description="Test Desc",
            amount=50.0,
            category="electronics",
            brand="TestBrand",
        ),
        related=[],
    )
    mock_pricing_ctx = PriceContext(
        sku="SKU-001",
        active=PriceEntry(sku="SKU-001", amount=50.0, currency="USD", promotional=True),
        offers=[],
    )
    mock_inventory_ctx = InventoryContext(
        sku="SKU-001",
        item=InventoryItem(sku="SKU-001", available=20, reserved=0, warehouse_id="WH1"),
        warehouses=[],
    )

    mock_products = AsyncMock()
    mock_products.build_product_context = AsyncMock(return_value=mock_product_ctx)

    mock_pricing = AsyncMock()
    mock_pricing.build_price_context = AsyncMock(return_value=mock_pricing_ctx)

    mock_inventory = AsyncMock()
    mock_inventory.build_inventory_context = AsyncMock(return_value=mock_inventory_ctx)

    mock_analytics = AsyncMock()
    mock_analytics.estimate_abandonment_risk = AsyncMock(
        return_value={"risk_score": 0.15, "drivers": []}
    )

    agent = Mock()
    agent.adapters = CartAdapters(
        products=mock_products,
        pricing=mock_pricing,
        inventory=mock_inventory,
        analytics=mock_analytics,
    )
    return agent


class TestMCPToolRegistration:
    """Tests for MCP tool registration."""

    def test_registers_cart_context_tool(self, mock_mcp_server, mock_agent):
        """Test that cart context tool is registered."""
        with patch.dict("os.environ", {}, clear=False):
            register_mcp_tools(mock_mcp_server, mock_agent)

        assert "/cart/context" in mock_mcp_server.tools

    def test_registers_abandonment_risk_tool(self, mock_mcp_server, mock_agent):
        """Test that abandonment risk tool is registered."""
        with patch.dict("os.environ", {}, clear=False):
            register_mcp_tools(mock_mcp_server, mock_agent)

        assert "/cart/abandonment-risk" in mock_mcp_server.tools

    def test_registers_recommendations_tool(self, mock_mcp_server, mock_agent):
        """Test that recommendations tool is registered."""
        with patch.dict("os.environ", {}, clear=False):
            register_mcp_tools(mock_mcp_server, mock_agent)

        assert "/cart/recommendations" in mock_mcp_server.tools


class TestMCPToolExecution:
    """Tests for MCP tool execution."""

    @pytest.mark.asyncio
    async def test_get_cart_context_returns_data(self, mock_mcp_server, mock_agent):
        """Test cart context tool returns expected data."""
        with patch.dict("os.environ", {}, clear=False):
            register_mcp_tools(mock_mcp_server, mock_agent)

        tool = mock_mcp_server.tools["/cart/context"]
        result = await tool({"items": [{"sku": "SKU-001", "quantity": 1}]})

        assert "items" in result
        assert "product_contexts" in result
        assert "pricing_contexts" in result
        assert "inventory_contexts" in result
        assert "acp" in result
        assert result["acp"]["domain"] == "cart"

    @pytest.mark.asyncio
    async def test_get_abandonment_risk_returns_risk(self, mock_mcp_server, mock_agent):
        """Test abandonment risk tool returns risk data."""
        with patch.dict("os.environ", {}, clear=False):
            register_mcp_tools(mock_mcp_server, mock_agent)

        tool = mock_mcp_server.tools["/cart/abandonment-risk"]
        result = await tool({"items": [{"sku": "SKU-001", "quantity": 1}]})

        assert "items" in result
        assert "abandonment_risk" in result
        assert "risk_score" in result["abandonment_risk"]
        assert "acp" in result
        assert result["acp"]["domain"] == "cart"

    @pytest.mark.asyncio
    async def test_recommend_actions_returns_actions(self, mock_mcp_server, mock_agent):
        """Test recommendations tool returns actions."""
        with patch.dict("os.environ", {}, clear=False):
            register_mcp_tools(mock_mcp_server, mock_agent)

        tool = mock_mcp_server.tools["/cart/recommendations"]
        result = await tool({"items": [{"sku": "SKU-001", "quantity": 1}]})

        assert "items" in result
        assert "abandonment_risk" in result
        assert "recommended_actions" in result
        assert len(result["recommended_actions"]) > 0
        assert "acp" in result
        assert result["acp"]["domain"] == "cart"

    @pytest.mark.asyncio
    async def test_cart_context_empty_items(self, mock_mcp_server, mock_agent):
        """Test cart context with empty items."""
        with patch.dict("os.environ", {}, clear=False):
            register_mcp_tools(mock_mcp_server, mock_agent)

        tool = mock_mcp_server.tools["/cart/context"]
        result = await tool({"items": []})

        assert result["items"] == []
        assert result["product_contexts"] == []
