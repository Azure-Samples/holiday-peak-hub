"""Unit tests for Truth HITL MCP tool registration and behavior."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock

import pytest
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer
from truth_hitl.adapters import build_hitl_adapters
from truth_hitl.agents import register_mcp_tools
from truth_hitl.review_manager import ReviewItem


@pytest.fixture
def mock_mcp_server() -> MagicMock:
    """Create a mock MCP server that captures registered tools."""
    mcp = MagicMock(spec=FastAPIMCPServer)
    mcp.tools = {}

    def add_tool(path, handler):
        mcp.tools[path] = handler

    mcp.add_tool = add_tool
    return mcp


@pytest.fixture
def mock_agent() -> Mock:
    """Create an agent stub with a review manager preloaded with one item."""
    adapters = build_hitl_adapters()
    adapters.review_manager.enqueue(
        ReviewItem(
            entity_id="prod-001",
            attr_id="attr-001",
            field_name="color",
            proposed_value="Midnight Blue",
            confidence=0.93,
            current_value="Blue",
            source="ai",
            proposed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            product_title="Winter Jacket",
            category_label="Apparel",
            original_data={"color": "Blue"},
            enriched_data={"color": "Midnight Blue"},
            reasoning="Consistent with DAM image and title",
            source_assets=[{"asset_id": "dam-777", "kind": "image"}],
            source_type="dam",
        )
    )

    agent = Mock()
    agent.adapters = adapters
    return agent


class TestMCPToolRegistration:
    def test_registers_review_get_proposal_tool(self, mock_mcp_server, mock_agent):
        register_mcp_tools(mock_mcp_server, mock_agent)
        assert "/review/get_proposal" in mock_mcp_server.tools


class TestMCPToolExecution:
    @pytest.mark.asyncio
    async def test_get_proposal_returns_full_enrichment_context(self, mock_mcp_server, mock_agent):
        register_mcp_tools(mock_mcp_server, mock_agent)
        tool = mock_mcp_server.tools["/review/get_proposal"]

        result = await tool({"entity_id": "prod-001", "attr_id": "attr-001"})

        assert result["entity_id"] == "prod-001"
        assert result["proposal"]["original_data"] == {"color": "Blue"}
        assert result["proposal"]["enriched_data"] == {"color": "Midnight Blue"}
        assert result["proposal"]["reasoning"] == "Consistent with DAM image and title"
        assert result["proposal"]["source_assets"] == [{"asset_id": "dam-777", "kind": "image"}]
        assert result["proposal"]["source_type"] == "dam"

    @pytest.mark.asyncio
    async def test_get_proposal_requires_entity_id(self, mock_mcp_server, mock_agent):
        register_mcp_tools(mock_mcp_server, mock_agent)
        tool = mock_mcp_server.tools["/review/get_proposal"]

        result = await tool({})

        assert result["error"] == "entity_id is required"

    @pytest.mark.asyncio
    async def test_get_proposal_returns_none_for_missing_proposal(
        self, mock_mcp_server, mock_agent
    ):
        register_mcp_tools(mock_mcp_server, mock_agent)
        tool = mock_mcp_server.tools["/review/get_proposal"]

        result = await tool({"entity_id": "unknown"})

        assert result["entity_id"] == "unknown"
        assert result["proposal"] is None
