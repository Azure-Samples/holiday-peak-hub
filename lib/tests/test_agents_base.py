"""Tests for base agent functionality."""

from unittest.mock import AsyncMock, Mock

import pytest
from holiday_peak_lib.agents.base_agent import (
    AgentDependencies,
    BaseRetailAgent,
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
        request = {"query": " ".join(["word"] * 100), "requires_multi_tool": True}
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
        request = {"query": " ".join(["word"] * 100), "requires_multi_tool": True}
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
        result = await agent.invoke_model({"query": "test"}, "test message")
        assert "response" in result or "content" in result
        assert result.get("_target") == "test-slm"

    @pytest.mark.asyncio
    async def test_invoke_model_with_routing(self, slm_target, llm_target):
        """Test invoking model routes simple requests to SLM."""

        deps = AgentDependencies(slm=slm_target, llm=llm_target)
        agent = SimpleTestAgent(config=deps)

        result = await agent.invoke_model(
            {"query": "simple query"}, [{"role": "user", "content": "test"}]
        )
        assert result is not None
        assert result.get("_target") == "test-slm"

    @pytest.mark.asyncio
    async def test_foundry_governance_strips_system_prompt(self):
        """Test Foundry governance strips local system prompts from messages."""
        captured_messages = []

        async def invoker(**kwargs):
            captured_messages.append(kwargs.get("messages"))
            return {"response": "ok"}

        slm = ModelTarget(name="slm", model="small", invoker=invoker, provider="foundry")
        deps = AgentDependencies(slm=slm, llm=None, enforce_foundry_prompt_governance=True)
        agent = SimpleTestAgent(config=deps)

        await agent.invoke_model(
            {"query": "hello"},
            [
                {"role": "system", "content": "local prompt"},
                {"role": "user", "content": "hello"},
            ],
        )

        assert captured_messages
        assert captured_messages[0] == [{"role": "user", "content": "hello"}]

    @pytest.mark.asyncio
    async def test_foundry_governance_uses_slm_first_then_llm_by_complexity(self):
        """Test Foundry governance routes complex requests directly to LLM (single call)."""
        invocation_order = []

        async def slm_invoker(**kwargs):
            invocation_order.append("slm")
            return {"response": "slm response"}

        async def llm_invoker(**kwargs):
            invocation_order.append("llm")
            return {"response": "llm response"}

        slm = ModelTarget(name="slm", model="small", invoker=slm_invoker, provider="foundry")
        llm = ModelTarget(name="llm", model="large", invoker=llm_invoker, provider="foundry")
        deps = AgentDependencies(
            slm=slm,
            llm=llm,
            complexity_threshold=0.2,
            enforce_foundry_prompt_governance=True,
        )
        agent = SimpleTestAgent(config=deps)

        result = await agent.invoke_model(
            {
                "query": "please analyze the full order history and provide multi-step recommendations",
                "requires_multi_tool": True,
            },
            [{"role": "user", "content": "request"}],
        )

        assert invocation_order == ["llm"]
        assert result.get("_target") == "llm"

    @pytest.mark.asyncio
    async def test_foundry_governance_can_be_disabled(self):
        """Test governance opt-out keeps local system messages untouched."""
        captured_messages = []

        async def invoker(**kwargs):
            captured_messages.append(kwargs.get("messages"))
            return {"response": "ok"}

        slm = ModelTarget(name="slm", model="small", invoker=invoker, provider="foundry")
        deps = AgentDependencies(slm=slm, llm=None, enforce_foundry_prompt_governance=False)
        agent = SimpleTestAgent(config=deps)

        original = [
            {"role": "system", "content": "local prompt"},
            {"role": "user", "content": "hello"},
        ]
        await agent.invoke_model({"query": "hello"}, original)
        assert captured_messages[0] == original

    @pytest.mark.asyncio
    async def test_tracing_pipeline_with_mock_tracer(self, slm_target):
        """Test tracing pipeline emits decision/model/tool events."""

        captured_events = []

        class _MockTracer:
            def trace_decision(self, **kwargs):
                captured_events.append(("decision", kwargs))

            def trace_model_invocation(self, **kwargs):
                captured_events.append(("model", kwargs))

            def trace_tool_call(self, **kwargs):
                captured_events.append(("tool", kwargs))

        deps = AgentDependencies(slm=slm_target, llm=None, service_name="trace-test")
        agent = SimpleTestAgent(config=deps)

        import holiday_peak_lib.agents.telemetry_mixin as telemetry_mixin_mod

        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(
            telemetry_mixin_mod, "get_foundry_tracer", lambda _service: _MockTracer()
        )
        try:
            await agent.invoke_model(
                {"query": "test"},
                "test message",
                tools={"inventory_lookup": lambda payload: payload},
            )
        finally:
            monkeypatch.undo()

        event_types = {event[0] for event in captured_events}
        assert "decision" in event_types
        assert "model" in event_types
        assert "tool" in event_types

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


class TestSessionThreading:
    """Test Foundry session threading through invoke_model."""

    @pytest.mark.asyncio
    async def test_session_id_forwarded_to_invoker(self):
        """session_id from request dict is forwarded to the invoker kwargs."""
        captured_kwargs = {}

        async def invoker(**kwargs):
            captured_kwargs.update(kwargs)
            return {"response": "ok"}

        slm = ModelTarget(name="slm", model="small", invoker=invoker)
        deps = AgentDependencies(slm=slm, llm=None)
        agent = SimpleTestAgent(config=deps)

        await agent.invoke_model(
            {"query": "hello", "session_id": "page-abc-123"},
            [{"role": "user", "content": "hello"}],
        )

        assert captured_kwargs.get("session_id") == "page-abc-123"

    @pytest.mark.asyncio
    async def test_no_session_id_when_absent(self):
        """No session_id is injected when absent from request."""
        captured_kwargs = {}

        async def invoker(**kwargs):
            captured_kwargs.update(kwargs)
            return {"response": "ok"}

        slm = ModelTarget(name="slm", model="small", invoker=invoker)
        deps = AgentDependencies(slm=slm, llm=None)
        agent = SimpleTestAgent(config=deps)

        await agent.invoke_model(
            {"query": "hello"},
            [{"role": "user", "content": "hello"}],
        )

        assert "session_id" not in captured_kwargs

    @pytest.mark.asyncio
    async def test_session_state_persisted_to_hot_memory(self):
        """Updated session state is persisted to Redis after invoke."""
        import json

        async def invoker(**kwargs):
            return {
                "response": "ok",
                "_foundry_session_state": {
                    "type": "session",
                    "session_id": "page-abc",
                    "service_session_id": "foundry-thread-new",
                    "state": {},
                },
            }

        slm = ModelTarget(name="slm", model="small", invoker=invoker)
        hot = AsyncMock()
        hot.get = AsyncMock(return_value=None)
        hot.set = AsyncMock()
        deps = AgentDependencies(slm=slm, llm=None, hot_memory=hot)
        agent = SimpleTestAgent(config=deps)

        await agent.invoke_model(
            {"query": "hello", "session_id": "page-abc"},
            [{"role": "user", "content": "hello"}],
        )

        hot.set.assert_called_once()
        call_args = hot.set.call_args
        assert call_args[0][0] == "foundry_session:page-abc"
        stored = json.loads(call_args[0][1])
        assert stored["service_session_id"] == "foundry-thread-new"

    @pytest.mark.asyncio
    async def test_session_state_loaded_from_hot_memory(self):
        """Cached session state is loaded from Redis and forwarded."""
        import json

        captured_kwargs = {}

        async def invoker(**kwargs):
            captured_kwargs.update(kwargs)
            return {"response": "ok"}

        cached_state = json.dumps(
            {
                "type": "session",
                "session_id": "page-abc",
                "service_session_id": "foundry-thread-existing",
                "state": {},
            }
        )

        slm = ModelTarget(name="slm", model="small", invoker=invoker)
        hot = AsyncMock()
        hot.get = AsyncMock(return_value=cached_state)
        hot.set = AsyncMock()
        deps = AgentDependencies(slm=slm, llm=None, hot_memory=hot)
        agent = SimpleTestAgent(config=deps)

        await agent.invoke_model(
            {"query": "follow-up", "session_id": "page-abc"},
            [{"role": "user", "content": "follow-up"}],
        )

        hot.get.assert_called_once_with("foundry_session:page-abc")
        assert "_foundry_session_state" in captured_kwargs
        assert (
            captured_kwargs["_foundry_session_state"]["service_session_id"]
            == "foundry-thread-existing"
        )
