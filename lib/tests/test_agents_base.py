"""Tests for base agent functionality."""
import pytest
from unittest.mock import AsyncMock, Mock
from holiday_peak_lib.agents.base_agent import (
    BaseRetailAgent,
    AgentDependencies,
    ModelTarget,
)


class SimpleTestAgent(BaseRetailAgent):
    """Minimal agent for testing."""

    async def handle(self, request: dict) -> dict:
        return {"status": "ok", "request": request}


@pytest.fixture
def model_invoker():
    """Mock model invoker."""
    async def invoker(**kwargs):
        return {
            "response": "test response",
            "content": "test content",
            "model": kwargs.get("model", "test-model"),
        }
    return invoker


@pytest.fixture
def slm_target(model_invoker):
    """Create a test SLM model target."""
    return ModelTarget(
        name="test-slm",
        model="gpt-4o-mini",
        invoker=model_invoker,
        temperature=0.2,
        top_p=0.9,
        stream=False,
    )


@pytest.fixture
def llm_target(model_invoker):
    """Create a test LLM model target."""
    return ModelTarget(
        name="test-llm",
        model="gpt-4o",
        invoker=model_invoker,
        temperature=0.5,
        top_p=0.95,
        stream=False,
    )


@pytest.fixture
def agent_deps(slm_target, llm_target):
    """Create agent dependencies."""
    return AgentDependencies(
        router=Mock(),
        tools={},
        service_name="test-service",
        slm=slm_target,
        llm=llm_target,
        complexity_threshold=0.5,
    )


class TestAgentDependencies:
    """Test AgentDependencies model."""

    def test_create_minimal_dependencies(self):
        """Test creating minimal dependencies."""
        deps = AgentDependencies()
        assert deps.router is None
        assert deps.tools == {}
        assert deps.service_name is None

    def test_create_full_dependencies(self, slm_target, llm_target):
        """Test creating full dependencies."""
        deps = AgentDependencies(
            router=Mock(),
            tools={"tool1": lambda x: x},
            service_name="test",
            slm=slm_target,
            llm=llm_target,
            complexity_threshold=0.7,
        )
        assert deps.service_name == "test"
        assert deps.complexity_threshold == 0.7
        assert deps.slm == slm_target
        assert deps.llm == llm_target


class TestBaseRetailAgent:
    """Test BaseRetailAgent functionality."""

    def test_agent_initialization(self, agent_deps):
        """Test agent initialization."""
        agent = SimpleTestAgent(config=agent_deps)
        assert agent.service_name == "test-service"
        assert agent.slm is not None
        assert agent.llm is not None

    def test_agent_property_setters(self, agent_deps):
        """Test agent property setters."""
        agent = SimpleTestAgent(config=agent_deps)
        agent.service_name = "new-service"
        assert agent.service_name == "new-service"
        
        new_tools = {"new_tool": lambda: None}
        agent.tools = new_tools
        assert agent.tools == new_tools

    @pytest.mark.asyncio
    async def test_handle_method(self, agent_deps):
        """Test agent handle method."""
        agent = SimpleTestAgent(config=agent_deps)
        result = await agent.handle({"test": "data"})
        assert result["status"] == "ok"
        assert result["request"]["test"] == "data"

    def test_assess_complexity_simple(self, agent_deps):
        """Test complexity assessment for simple requests."""
        agent = SimpleTestAgent(config=agent_deps)
        request = {"query": "short"}
        complexity = agent._assess_complexity(request)
        assert 0.0 <= complexity <= 1.0
        assert complexity < 0.5

    def test_assess_complexity_complex(self, agent_deps):
        """Test complexity assessment for complex requests."""
        agent = SimpleTestAgent(config=agent_deps)
        request = {
            "query": " ".join(["word"] * 100),
            "requires_multi_tool": True
        }
        complexity = agent._assess_complexity(request)
        assert complexity > 0.5

    def test_select_model_slm_for_simple(self, agent_deps):
        """Test model selection chooses SLM for simple requests."""
        agent = SimpleTestAgent(config=agent_deps)
        request = {"query": "simple query"}
        model = agent._select_model(request)
        assert model.name == "test-slm"

    def test_select_model_llm_for_complex(self, agent_deps):
        """Test model selection chooses LLM for complex requests."""
        agent = SimpleTestAgent(config=agent_deps)
        request = {
            "query": " ".join(["word"] * 100),
            "requires_multi_tool": True
        }
        model = agent._select_model(request)
        assert model.name == "test-llm"

    def test_select_model_no_models_raises(self):
        """Test model selection raises when no models configured."""
        deps = AgentDependencies(slm=None, llm=None)
        agent = SimpleTestAgent(config=deps)
        with pytest.raises(RuntimeError, match="No models configured"):
            agent._select_model({"query": "test"})

    @pytest.mark.asyncio
    async def test_invoke_model_with_slm_only(self, slm_target):
        """Test invoking model with only SLM."""
        deps = AgentDependencies(slm=slm_target, llm=None)
        agent = SimpleTestAgent(config=deps)
        result = await agent.invoke_model(
            {"query": "test"},
            "test message"
        )
        assert "response" in result or "content" in result
        assert result.get("_target") == "test-slm"

    @pytest.mark.asyncio
    async def test_invoke_model_with_routing(self, slm_target, llm_target):
        """Test invoking model with SLM to LLM routing."""
        # Mock invoker that returns upgrade for evaluation
        async def routing_invoker(**kwargs):
            messages = kwargs.get("messages", "")
            if "Evaluate this request" in str(messages):
                return {"response": "normal", "content": "normal"}
            return {"response": "test response", "content": "result"}
        
        slm = ModelTarget(
            name="slm", model="small", invoker=routing_invoker
        )
        llm = ModelTarget(
            name="llm", model="large", invoker=routing_invoker
        )
        deps = AgentDependencies(slm=slm, llm=llm)
        agent = SimpleTestAgent(config=deps)
        
        result = await agent.invoke_model(
            {"query": "simple query"},
            [{"role": "user", "content": "test"}]
        )
        assert result is not None

    def test_attach_memory(self, agent_deps):
        """Test attaching memory to agent."""
        agent = SimpleTestAgent(config=agent_deps)
        hot = Mock()
        warm = Mock()
        cold = Mock()
        agent.attach_memory(hot, warm, cold)
        assert agent.hot_memory == hot
        assert agent.warm_memory == warm
        assert agent.cold_memory == cold

    def test_attach_mcp(self, agent_deps):
        """Test attaching MCP server to agent."""
        agent = SimpleTestAgent(config=agent_deps)
        mcp = Mock()
        agent.attach_mcp(mcp)
        assert agent.mcp_server == mcp


class TestModelTarget:
    """Test ModelTarget dataclass."""

    def test_create_model_target(self):
        """Test creating a ModelTarget."""
        invoker = AsyncMock()
        target = ModelTarget(
            name="test",
            model="gpt-4",
            invoker=invoker,
            temperature=0.7,
            top_p=0.9,
            stream=True,
        )
        assert target.name == "test"
        assert target.model == "gpt-4"
        assert target.temperature == 0.7
        assert target.top_p == 0.9
        assert target.stream is True

    def test_model_target_defaults(self):
        """Test ModelTarget default values."""
        invoker = AsyncMock()
        target = ModelTarget(name="test", model="gpt-4", invoker=invoker)
        assert target.temperature == 0.2
        assert target.top_p == 0.9
        assert target.stream is False
