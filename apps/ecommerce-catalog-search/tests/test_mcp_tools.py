"""Unit tests for catalog search MCP tool registration."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from ecommerce_catalog_search.adapters import AcpCatalogMapper, CatalogAdapters
from ecommerce_catalog_search.agents import CatalogSearchAgent, register_mcp_tools
from holiday_peak_lib.agents.base_agent import AgentDependencies
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer
from holiday_peak_lib.schemas.truth import IntentClassification


@pytest.fixture(name="mock_mcp_server")
def fixture_mock_mcp_server():
    """Create a mock MCP server."""
    mcp = MagicMock(spec=FastAPIMCPServer)
    mcp.tools = {}

    def add_tool(path, handler):
        mcp.tools[path] = handler

    mcp.add_tool = add_tool
    return mcp


@pytest.fixture(name="mock_agent")
def fixture_mock_agent(mock_catalog_product, mock_inventory_item):
    """Create a mock agent with adapters."""
    mock_products = AsyncMock()
    mock_products.get_product = AsyncMock(return_value=mock_catalog_product)
    mock_products.get_related = AsyncMock(return_value=[])

    mock_inventory = AsyncMock()
    mock_inventory.get_item = AsyncMock(return_value=mock_inventory_item)

    agent = Mock()
    agent.adapters = CatalogAdapters(
        products=mock_products,
        inventory=mock_inventory,
        mapping=AcpCatalogMapper(),
    )
    return agent


class TestMCPToolRegistration:
    """Tests for MCP tool registration."""

    def test_registers_search_catalog_tool(self, mock_mcp_server, mock_agent):
        """Test that search catalog tool is registered."""
        with patch.dict("os.environ", {}, clear=False):
            register_mcp_tools(mock_mcp_server, mock_agent)

        assert "/catalog/search" in mock_mcp_server.tools

    def test_registers_product_details_tool(self, mock_mcp_server, mock_agent):
        """Test that product details tool is registered."""
        with patch.dict("os.environ", {}, clear=False):
            register_mcp_tools(mock_mcp_server, mock_agent)

        assert "/catalog/product" in mock_mcp_server.tools

    def test_registers_intent_tool(self, mock_mcp_server, mock_agent):
        """Test that intent classification MCP tool is registered."""
        with patch.dict("os.environ", {}, clear=False):
            register_mcp_tools(mock_mcp_server, mock_agent)

        assert "/catalog/intent" in mock_mcp_server.tools


class TestMCPToolExecution:
    """Tests for MCP tool execution."""

    @pytest.mark.asyncio
    async def test_search_catalog_returns_results(self, mock_mcp_server, mock_agent):
        """Test search catalog tool returns ACP-formatted results."""
        with patch.dict("os.environ", {}, clear=False):
            register_mcp_tools(mock_mcp_server, mock_agent)

        tool = mock_mcp_server.tools["/catalog/search"]
        result = await tool({"query": "test product", "limit": 5})

        assert "query" in result
        assert result["mode"] == "intelligent"
        assert "results" in result
        assert len(result["results"]) > 0
        # Verify ACP format
        assert "item_id" in result["results"][0]
        assert "title" in result["results"][0]
        assert "availability" in result["results"][0]

    @pytest.mark.asyncio
    async def test_search_catalog_empty_query(self, mock_mcp_server, mock_agent):
        """Test search catalog with empty query returns results based on default SKU."""
        # Note: The catalog search coerces empty query to SKU-1, so it may still return results
        mock_agent.adapters.products.get_product = AsyncMock(return_value=None)
        mock_agent.adapters.products.get_related = AsyncMock(return_value=[])

        with patch.dict("os.environ", {}, clear=False):
            register_mcp_tools(mock_mcp_server, mock_agent)

        tool = mock_mcp_server.tools["/catalog/search"]
        result = await tool({"query": ""})

        assert result["query"] == ""
        assert result["results"] == []

    @pytest.mark.asyncio
    async def test_search_catalog_accepts_intelligent_mode(self, mock_mcp_server, mock_agent):
        """Intelligent mode is accepted while keeping MCP contract stable."""
        with patch.dict("os.environ", {}, clear=False):
            register_mcp_tools(mock_mcp_server, mock_agent)

        tool = mock_mcp_server.tools["/catalog/search"]
        result = await tool({"query": "best travel backpack", "mode": "intelligent", "limit": 3})

        assert result["mode"] == "intelligent"
        assert "results" in result

    @pytest.mark.asyncio
    async def test_search_catalog_explicit_keyword_mode_is_preserved(
        self, mock_mcp_server, mock_agent
    ):
        """Explicit keyword mode must remain available for demos and compatibility."""
        with patch.dict("os.environ", {}, clear=False):
            register_mcp_tools(mock_mcp_server, mock_agent)

        tool = mock_mcp_server.tools["/catalog/search"]
        result = await tool({"query": "travel jacket", "mode": "keyword", "limit": 3})

        assert result["mode"] == "keyword"
        assert "results" in result

    @pytest.mark.asyncio
    async def test_get_product_details_returns_product(self, mock_mcp_server, mock_agent):
        """Test product details tool returns ACP-formatted product."""
        with patch.dict("os.environ", {}, clear=False):
            register_mcp_tools(mock_mcp_server, mock_agent)

        tool = mock_mcp_server.tools["/catalog/product"]
        result = await tool({"sku": "SKU-001"})

        assert "product" in result
        assert result["product"]["item_id"] == "SKU-001"

    @pytest.mark.asyncio
    async def test_get_product_details_requires_sku(self, mock_mcp_server, mock_agent):
        """Test product details tool requires sku parameter."""
        with patch.dict("os.environ", {}, clear=False):
            register_mcp_tools(mock_mcp_server, mock_agent)

        tool = mock_mcp_server.tools["/catalog/product"]
        result = await tool({})

        assert "error" in result
        assert result["error"] == "sku is required"

    @pytest.mark.asyncio
    async def test_get_product_details_not_found(self, mock_mcp_server, mock_agent):
        """Test product details tool handles not found."""
        mock_agent.adapters.products.get_product = AsyncMock(return_value=None)

        with patch.dict("os.environ", {}, clear=False):
            register_mcp_tools(mock_mcp_server, mock_agent)

        tool = mock_mcp_server.tools["/catalog/product"]
        result = await tool({"sku": "NONEXISTENT"})

        assert "error" in result
        assert result["error"] == "not_found"

    @pytest.mark.asyncio
    async def test_catalog_intent_tool_requires_query(self, mock_mcp_server, mock_agent):
        """Intent MCP tool validates required query payload."""
        with patch.dict("os.environ", {}, clear=False):
            register_mcp_tools(mock_mcp_server, mock_agent)

        tool = mock_mcp_server.tools["/catalog/intent"]
        result = await tool({})

        assert result["error"] == "query is required"

    @pytest.mark.asyncio
    async def test_catalog_intent_tool_returns_classification_for_real_agent(self, mock_mcp_server):
        """Intent MCP tool should call classify_intent when the bound agent supports it."""
        deps = AgentDependencies(
            service_name="test-catalog-search",
            router=None,
            tools={},
            slm=None,
            llm=None,
        )

        with patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build:
            mock_products = AsyncMock()
            mock_products.get_product = AsyncMock(return_value=None)
            mock_products.get_related = AsyncMock(return_value=[])
            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(return_value=None)
            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=AcpCatalogMapper(),
            )

            agent = CatalogSearchAgent(config=deps)
            with patch.object(
                agent,
                "classify_intent",
                new=AsyncMock(
                    return_value=IntentClassification(
                        intent="semantic_search",
                        confidence=0.82,
                        entities={"category": "audio"},
                    )
                ),
            ):
                with patch.dict("os.environ", {}, clear=False):
                    register_mcp_tools(mock_mcp_server, agent)

                tool = mock_mcp_server.tools["/catalog/intent"]
                result = await tool({"query": "headphones with long battery"})

        assert result["intent"]["intent"] == "semantic_search"
        assert result["intent"]["confidence"] == pytest.approx(0.82)
