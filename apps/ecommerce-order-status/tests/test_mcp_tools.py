"""Unit tests for order status MCP tool registration."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from ecommerce_order_status.adapters import OrderStatusAdapters
from ecommerce_order_status.agents import register_mcp_tools
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer
from holiday_peak_lib.schemas.logistics import LogisticsContext, Shipment, ShipmentEvent


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
    shipment = Shipment(tracking_id="TRK-001", status="in_transit")
    event = ShipmentEvent(code="PICKED_UP", occurred_at="2026-03-02T00:00:00Z")
    context = LogisticsContext(shipment=shipment, events=[event])

    mock_logistics = AsyncMock()
    mock_logistics.build_logistics_context = AsyncMock(return_value=context)
    mock_logistics.get_events = AsyncMock(return_value=[event])

    mock_resolver = AsyncMock()
    mock_resolver.resolve_tracking_id = AsyncMock(return_value="TRK-001")

    agent = Mock()
    agent.adapters = OrderStatusAdapters(logistics=mock_logistics, resolver=mock_resolver)
    return agent


class TestMCPToolRegistration:
    def test_registers_order_status_tools(self, mock_mcp_server, mock_agent):
        with patch.dict("os.environ", {}, clear=False):
            register_mcp_tools(mock_mcp_server, mock_agent)

        assert "/order/status" in mock_mcp_server.tools
        assert "/order/events" in mock_mcp_server.tools


class TestMCPToolExecution:
    @pytest.mark.asyncio
    async def test_get_order_status_returns_acp_wrapper(self, mock_mcp_server, mock_agent):
        with patch.dict("os.environ", {}, clear=False):
            register_mcp_tools(mock_mcp_server, mock_agent)

        tool = mock_mcp_server.tools["/order/status"]
        result = await tool({"tracking_id": "TRK-001"})

        assert result["tracking_id"] == "TRK-001"
        assert "acp" in result
        assert result["acp"]["domain"] == "order_status"

    @pytest.mark.asyncio
    async def test_get_order_events_returns_acp_wrapper(self, mock_mcp_server, mock_agent):
        with patch.dict("os.environ", {}, clear=False):
            register_mcp_tools(mock_mcp_server, mock_agent)

        tool = mock_mcp_server.tools["/order/events"]
        result = await tool({"tracking_id": "TRK-001"})

        assert result["tracking_id"] == "TRK-001"
        assert "events" in result
        assert "acp" in result
        assert result["acp"]["domain"] == "order_status"

    @pytest.mark.asyncio
    async def test_get_order_events_requires_tracking_id(self, mock_mcp_server, mock_agent):
        with patch.dict("os.environ", {}, clear=False):
            register_mcp_tools(mock_mcp_server, mock_agent)

        tool = mock_mcp_server.tools["/order/events"]
        result = await tool({})

        assert result["error"] == "tracking_id is required"
