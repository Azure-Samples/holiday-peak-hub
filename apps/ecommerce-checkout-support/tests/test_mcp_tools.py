"""Unit tests for checkout support MCP tool registration."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from ecommerce_checkout_support.adapters import CheckoutAdapters
from ecommerce_checkout_support.agents import register_mcp_tools
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer
from holiday_peak_lib.schemas.inventory import InventoryContext, InventoryItem
from holiday_peak_lib.schemas.pricing import PriceContext, PriceEntry


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

    mock_pricing = AsyncMock()
    mock_pricing.build_price_context = AsyncMock(return_value=mock_pricing_ctx)

    mock_inventory = AsyncMock()
    mock_inventory.build_inventory_context = AsyncMock(return_value=mock_inventory_ctx)

    mock_validator = AsyncMock()
    mock_validator.validate = AsyncMock(return_value={"status": "ready", "issues": []})

    agent = Mock()
    agent.adapters = CheckoutAdapters(
        pricing=mock_pricing,
        inventory=mock_inventory,
        validator=mock_validator,
    )
    return agent


class TestMCPToolRegistration:
    """Tests for MCP tool registration."""

    def test_registers_validate_checkout_tool(self, mock_mcp_server, mock_agent):
        """Test that validate checkout tool is registered."""
        with patch.dict("os.environ", {}, clear=False):
            register_mcp_tools(mock_mcp_server, mock_agent)

        assert "/checkout/validate" in mock_mcp_server.tools

    def test_registers_pricing_tool(self, mock_mcp_server, mock_agent):
        """Test that pricing tool is registered."""
        with patch.dict("os.environ", {}, clear=False):
            register_mcp_tools(mock_mcp_server, mock_agent)

        assert "/checkout/pricing" in mock_mcp_server.tools

    def test_registers_inventory_tool(self, mock_mcp_server, mock_agent):
        """Test that inventory tool is registered."""
        with patch.dict("os.environ", {}, clear=False):
            register_mcp_tools(mock_mcp_server, mock_agent)

        assert "/checkout/inventory" in mock_mcp_server.tools


class TestMCPToolExecution:
    """Tests for MCP tool execution."""

    @pytest.mark.asyncio
    async def test_validate_checkout_returns_validation(self, mock_mcp_server, mock_agent):
        """Test validate checkout tool returns validation data."""
        with patch.dict("os.environ", {}, clear=False):
            register_mcp_tools(mock_mcp_server, mock_agent)

        tool = mock_mcp_server.tools["/checkout/validate"]
        result = await tool({"items": [{"sku": "SKU-001", "quantity": 1}]})

        assert "items" in result
        assert "validation" in result
        assert "acp" in result
        assert result["acp"]["domain"] == "checkout"

    @pytest.mark.asyncio
    async def test_get_pricing_returns_pricing(self, mock_mcp_server, mock_agent):
        """Test pricing tool returns pricing data."""
        with patch.dict("os.environ", {}, clear=False):
            register_mcp_tools(mock_mcp_server, mock_agent)

        tool = mock_mcp_server.tools["/checkout/pricing"]
        result = await tool({"sku": "SKU-001"})

        assert "pricing" in result
        assert result["pricing"]["sku"] == "SKU-001"
        assert "acp" in result
        assert result["acp"]["domain"] == "checkout"

    @pytest.mark.asyncio
    async def test_get_pricing_requires_sku(self, mock_mcp_server, mock_agent):
        """Test pricing tool requires sku parameter."""
        with patch.dict("os.environ", {}, clear=False):
            register_mcp_tools(mock_mcp_server, mock_agent)

        tool = mock_mcp_server.tools["/checkout/pricing"]
        result = await tool({})

        assert "error" in result
        assert result["error"] == "sku is required"

    @pytest.mark.asyncio
    async def test_get_inventory_returns_inventory(self, mock_mcp_server, mock_agent):
        """Test inventory tool returns inventory data."""
        with patch.dict("os.environ", {}, clear=False):
            register_mcp_tools(mock_mcp_server, mock_agent)

        tool = mock_mcp_server.tools["/checkout/inventory"]
        result = await tool({"sku": "SKU-001"})

        assert "inventory" in result
        assert result["inventory"]["item"]["sku"] == "SKU-001"
        assert "acp" in result
        assert result["acp"]["domain"] == "checkout"

    @pytest.mark.asyncio
    async def test_get_inventory_requires_sku(self, mock_mcp_server, mock_agent):
        """Test inventory tool requires sku parameter."""
        with patch.dict("os.environ", {}, clear=False):
            register_mcp_tools(mock_mcp_server, mock_agent)

        tool = mock_mcp_server.tools["/checkout/inventory"]
        result = await tool({})

        assert "error" in result
        assert result["error"] == "sku is required"
