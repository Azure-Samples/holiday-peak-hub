"""Tests for agent builder."""
import pytest
from unittest.mock import Mock, AsyncMock
from holiday_peak_lib.agents.builder import AgentBuilder
from holiday_peak_lib.agents.base_agent import BaseRetailAgent, ModelTarget
from holiday_peak_lib.agents.orchestration.router import RoutingStrategy
from holiday_peak_lib.agents.memory.hot import HotMemory
from holiday_peak_lib.agents.memory.warm import WarmMemory
from holiday_peak_lib.agents.memory.cold import ColdMemory


class SampleAgent(BaseRetailAgent):
    """Test agent implementation."""

    async def handle(self, request: dict) -> dict:
        return {"result": "ok"}


@pytest.fixture
def model_invoker():
    """Mock model invoker."""
    async def invoker(**kwargs):
        return {"response": "test"}
    return invoker


@pytest.fixture
def mock_hot_memory(mock_redis_client, monkeypatch):
    """Mock hot memory."""
    memory = HotMemory("redis://localhost:6379")
    monkeypatch.setattr(memory, "client", mock_redis_client)
    return memory


@pytest.fixture
def mock_warm_memory(mock_cosmos_client, monkeypatch):
    """Mock warm memory."""
    memory = WarmMemory(
        account_uri="https://test.documents.azure.com",
        database="test",
        container="test"
    )
    monkeypatch.setattr(memory, "client", mock_cosmos_client)
    return memory


@pytest.fixture
def mock_cold_memory(mock_blob_client, monkeypatch):
    """Mock cold memory."""
    memory = ColdMemory(
        account_url="https://test.blob.core.windows.net",
        container_name="test"
    )
    monkeypatch.setattr(memory, "client", mock_blob_client)
    return memory


class SampleAgentBuilder:
    """Test AgentBuilder functionality."""

    def test_create_builder(self):
        """Test creating a builder instance."""
        builder = AgentBuilder()
        assert builder is not None

    def test_with_agent(self):
        """Test setting agent class."""
        builder = AgentBuilder()
        result = builder.with_agent(SampleAgent)
        assert result is builder  # fluent interface

    def test_with_router(self):
        """Test setting router."""
        builder = AgentBuilder()
        router = RoutingStrategy()
        result = builder.with_router(router)
        assert result is builder

    def test_with_memory(self, mock_hot_memory, mock_warm_memory, mock_cold_memory):
        """Test setting memory layers."""
        builder = AgentBuilder()
        result = builder.with_memory(
            mock_hot_memory,
            mock_warm_memory,
            mock_cold_memory
        )
        assert result is builder

    def test_with_tool(self):
        """Test adding a single tool."""
        builder = AgentBuilder()
        handler = lambda x: x
        result = builder.with_tool("test_tool", handler)
        assert result is builder

    def test_with_tools(self):
        """Test adding multiple tools."""
        builder = AgentBuilder()
        tools = {
            "tool1": lambda x: x,
            "tool2": lambda y: y
        }
        result = builder.with_tools(tools)
        assert result is builder

    def test_with_models(self, model_invoker):
        """Test setting model targets."""
        builder = AgentBuilder()
        slm = ModelTarget(name="slm", model="small", invoker=model_invoker)
        llm = ModelTarget(name="llm", model="large", invoker=model_invoker)
        result = builder.with_models(slm=slm, llm=llm, complexity_threshold=0.6)
        assert result is builder

    def test_build_minimal_agent(self, model_invoker):
        """Test building agent with minimal configuration."""
        slm = ModelTarget(name="slm", model="test", invoker=model_invoker)
        builder = AgentBuilder()
        agent = builder.with_agent(SampleAgent).with_models(slm=slm).build()
        assert isinstance(agent, SampleAgent)
        assert agent.slm is not None

    def test_build_full_agent(
        self,
        model_invoker,
        mock_hot_memory,
        mock_warm_memory,
        mock_cold_memory
    ):
        """Test building agent with full configuration."""
        slm = ModelTarget(name="slm", model="small", invoker=model_invoker)
        llm = ModelTarget(name="llm", model="large", invoker=model_invoker)
        router = RoutingStrategy()
        tools = {"test": lambda x: x}
        
        builder = AgentBuilder()
        agent = (
            builder
            .with_agent(SampleAgent)
            .with_router(router)
            .with_memory(mock_hot_memory, mock_warm_memory, mock_cold_memory)
            .with_tools(tools)
            .with_models(slm=slm, llm=llm)
            .build()
        )
        
        assert isinstance(agent, SampleAgent)
        assert agent.hot_memory is not None
        assert agent.warm_memory is not None
        assert agent.cold_memory is not None
        assert len(agent.tools) == 1

    def test_build_without_agent_raises(self):
        """Test building without agent class raises error."""
        builder = AgentBuilder()
        with pytest.raises(ValueError, match="Agent class is required"):
            builder.build()

    def test_build_without_models_raises(self):
        """Test building without models raises error."""
        builder = AgentBuilder()
        with pytest.raises(ValueError, match="At least one model target"):
            builder.with_agent(SampleAgent).build()

    def test_with_mcp(self):
        """Test setting MCP server."""
        builder = AgentBuilder()
        mcp = Mock()
        result = builder.with_mcp(mcp)
        assert result is builder

    def test_build_with_mcp(self, model_invoker):
        """Test building agent with MCP server."""
        slm = ModelTarget(name="slm", model="test", invoker=model_invoker)
        mcp = Mock()
        builder = AgentBuilder()
        agent = (
            builder
            .with_agent(SampleAgent)
            .with_models(slm=slm)
            .with_mcp(mcp)
            .build()
        )
        assert agent.mcp_server == mcp

    @pytest.mark.asyncio
    async def test_built_agent_handles_request(self, model_invoker):
        """Test that built agent can handle requests."""
        slm = ModelTarget(name="slm", model="test", invoker=model_invoker)
        builder = AgentBuilder()
        agent = builder.with_agent(SampleAgent).with_models(slm=slm).build()
        result = await agent.handle({"test": "data"})
        assert result["result"] == "ok"


class TestBuilderChaining:
    """Test builder method chaining."""

    def test_chain_all_methods(self, model_invoker):
        """Test chaining all builder methods."""
        slm = ModelTarget(name="slm", model="test", invoker=model_invoker)
        router = RoutingStrategy()
        
        builder = AgentBuilder()
        agent = (
            builder
            .with_agent(SampleAgent)
            .with_router(router)
            .with_tool("tool1", lambda x: x)
            .with_tools({"tool2": lambda y: y})
            .with_models(slm=slm)
            .build()
        )
        
        assert isinstance(agent, SampleAgent)
        assert len(agent.tools) == 2

    def test_order_independence(self, model_invoker):
        """Test that method call order doesn't matter."""
        slm = ModelTarget(name="slm", model="test", invoker=model_invoker)
        
        # Build in one order
        builder1 = AgentBuilder()
        agent1 = (
            builder1
            .with_models(slm=slm)
            .with_agent(SampleAgent)
            .build()
        )
        
        # Build in different order
        builder2 = AgentBuilder()
        agent2 = (
            builder2
            .with_agent(SampleAgent)
            .with_models(slm=slm)
            .build()
        )
        
        assert isinstance(agent1, SampleAgent)
        assert isinstance(agent2, SampleAgent)
