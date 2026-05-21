"""Tests for base agent functionality."""

import asyncio
import logging
import math
from unittest.mock import AsyncMock, Mock

import pytest
from holiday_peak_lib.agents.base_agent import (
    AgentDependencies,
    BaseRetailAgent,
    ModelTarget,
)
from holiday_peak_lib.agents.models import StreamingModelInvoker


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
        """Test complexity assessment for complex requests.

        Uses *varied* vocabulary plus reasoning verbs and a multi-tool
        hint — the previous version of this test used 100 repetitions
        of ``"word"`` which the new TTR-gated heuristic correctly
        treats as low-complexity regardless of length.
        """
        agent = SimpleTestAgent(config=agent_deps)
        request = {
            "query": (
                "compare and analyze the differences between these products and "
                "recommend the best one based on reviews and pricing"
            ),
            "requires_multi_tool": True,
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
            "query": (
                "compare and analyze the differences between these products and "
                "recommend the best one based on reviews and pricing"
            ),
            "requires_multi_tool": True,
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
    async def test_invoke_model_logs_provider_failure(self, caplog):
        """Provider failures emit an error log before propagating."""

        async def failing_invoker(**_kwargs):
            raise RuntimeError("provider down")

        slm = ModelTarget(name="slm", model="small", invoker=failing_invoker)
        deps = AgentDependencies(slm=slm, llm=None, service_name="critical-log-test")
        agent = SimpleTestAgent(config=deps)

        with caplog.at_level(logging.ERROR, logger="holiday_peak_lib.agents.base_agent"):
            with pytest.raises(RuntimeError, match="provider down"):
                await agent.invoke_model(
                    {"query": "hello"},
                    [{"role": "user", "content": "hello"}],
                )

        assert any(
            "agent_model_invocation_failed service=critical-log-test "
            "model=small error=provider down" in record.getMessage()
            for record in caplog.records
        )

    @pytest.mark.asyncio
    async def test_invoke_model_logs_provider_timeout(self, caplog):
        """Provider timeouts emit an error log and return the timeout fallback."""

        async def timeout_invoker(**_kwargs):
            raise asyncio.TimeoutError

        slm = ModelTarget(name="slm", model="small", invoker=timeout_invoker)
        deps = AgentDependencies(slm=slm, llm=None, service_name="critical-log-test")
        agent = SimpleTestAgent(config=deps)

        with caplog.at_level(logging.ERROR, logger="holiday_peak_lib.agents.base_agent"):
            result = await agent.invoke_model(
                {"query": "hello"},
                [{"role": "user", "content": "hello"}],
            )

        assert result["error"] == "timeout"
        assert any(
            "agent_model_invocation_timeout service=critical-log-test model=small"
            in record.getMessage()
            for record in caplog.records
        )

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
        """Governance opt-out preserves the caller's system prompt.

        With governance off, the caller's local system message must
        survive the round-trip. The framework still prepends a
        tier-framed routing hint as an additional system message — the
        caller's prompt stays first (so its weighting isn't disturbed)
        and the user turn stays last; the routing hint is inserted
        between them.
        """
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

        captured = captured_messages[0]
        assert captured[0] == {"role": "system", "content": "local prompt"}
        assert captured[-1] == {"role": "user", "content": "hello"}
        # Framework-injected routing hint slots between caller system
        # prompt and the user turn.
        assert captured[1]["role"] == "system"
        assert "routing" in captured[1]["content"].lower()

    @pytest.mark.asyncio
    async def test_invoke_model_surfaces_slm_routing_context(self):
        """SLM tier: kwargs metadata + system hint frame the SLM call.

        The invoker receives ``routing_*`` kwargs (canonical channel)
        and the model sees a tier-framed system hint instructing it to
        either answer or signal UPGRADE for escalation. An LLM target
        is paired so the upgrade clause is meaningful — the framework
        suppresses it when there is nowhere to escalate to.
        """
        captured = {}

        async def slm_invoker(**kwargs):
            captured.update(kwargs)
            return {"response": "ok"}

        async def llm_invoker(**_kwargs):  # pragma: no cover - not invoked here
            return {"response": "llm"}

        slm = ModelTarget(name="slm", model="small", invoker=slm_invoker)
        llm = ModelTarget(name="llm", model="large", invoker=llm_invoker)
        deps = AgentDependencies(slm=slm, llm=llm, complexity_threshold=0.5)
        agent = SimpleTestAgent(config=deps)

        await agent.invoke_model(
            {"query": "hi"},
            [{"role": "user", "content": "hi"}],
        )

        assert captured["routing_target_tier"] == "slm"
        assert captured["routing_threshold"] == 0.5
        assert isinstance(captured["routing_complexity"], float)
        assert 0.0 <= captured["routing_complexity"] <= 1.0
        assert "upgrade" in captured["routing_hint"].lower()

        # System hint reached the model via the messages channel too.
        msgs = captured["messages"]
        assert msgs[0]["role"] == "system"
        assert "slm" in msgs[0]["content"].lower()

    @pytest.mark.asyncio
    async def test_invoke_model_surfaces_llm_routing_context(self):
        """LLM tier: kwargs metadata + system hint encourage deliberate reasoning."""
        captured = {}

        async def slm_invoker(**_kwargs):  # pragma: no cover - never invoked
            return {"response": "slm"}

        async def llm_invoker(**kwargs):
            captured.update(kwargs)
            return {"response": "ok"}

        slm = ModelTarget(name="slm", model="small", invoker=slm_invoker)
        llm = ModelTarget(name="llm", model="large", invoker=llm_invoker)
        deps = AgentDependencies(slm=slm, llm=llm, complexity_threshold=0.2)
        agent = SimpleTestAgent(config=deps)

        await agent.invoke_model(
            {
                "query": (
                    "compare and analyze the differences between these "
                    "products and recommend the best one"
                ),
                "requires_multi_tool": True,
            },
            [{"role": "user", "content": "compare"}],
        )

        assert captured["routing_target_tier"] == "llm"
        assert captured["routing_complexity"] >= deps.complexity_threshold
        assert "reason" in captured["routing_hint"].lower()

        msgs = captured["messages"]
        assert msgs[0]["role"] == "system"
        assert "llm" in msgs[0]["content"].lower()

    @pytest.mark.asyncio
    async def test_foundry_governance_strips_hint_but_kwargs_survive(self):
        """Under Foundry governance the system hint is stripped, kwargs survive.

        Foundry-backed Responses targets own their system prompt at the
        provider boundary, so the messages-channel hint must not leak
        through. The kwargs channel still carries the routing metadata
        so adapters can plumb it into their provider-owned prompt.
        """
        captured = {}

        async def slm_invoker(**kwargs):
            captured.update(kwargs)
            return {"response": "ok"}

        async def llm_invoker(**_kwargs):  # pragma: no cover - not invoked here
            return {"response": "llm"}

        slm = ModelTarget(name="slm", model="small", invoker=slm_invoker, provider="foundry")
        llm = ModelTarget(name="llm", model="large", invoker=llm_invoker, provider="foundry")
        deps = AgentDependencies(
            slm=slm,
            llm=llm,
            complexity_threshold=0.5,
            enforce_foundry_prompt_governance=True,
        )
        agent = SimpleTestAgent(config=deps)

        await agent.invoke_model(
            {"query": "hi"},
            [{"role": "user", "content": "hi"}],
        )

        # Messages channel: governance stripped every system role.
        msgs = captured["messages"]
        assert all(m.get("role") != "system" for m in msgs)
        # Kwargs channel: routing metadata always reaches the adapter.
        assert captured["routing_target_tier"] == "slm"
        assert isinstance(captured["routing_complexity"], float)
        assert "upgrade" in captured["routing_hint"].lower()

    @pytest.mark.asyncio
    async def test_slm_upgrade_reply_escalates_to_llm(self):
        """SLM replying with the UPGRADE sentinel routes to the LLM.

        Closes the loop on the SLM hint: the hint promises an upgrade
        channel, and this is the runtime that honors it. The LLM call
        receives a fresh routing context (LLM-tier hint, no upgrade
        clause) and the final result reflects the LLM target.
        """
        invocations = []

        async def slm_invoker(**_kwargs):
            invocations.append("slm")
            return {"response": "UPGRADE"}

        captured_llm_msgs = []

        async def llm_invoker(**kwargs):
            invocations.append("llm")
            captured_llm_msgs.append(kwargs.get("messages"))
            return {"response": "llm answer"}

        slm = ModelTarget(name="slm", model="small", invoker=slm_invoker)
        llm = ModelTarget(name="llm", model="large", invoker=llm_invoker)
        deps = AgentDependencies(slm=slm, llm=llm, complexity_threshold=0.99)
        agent = SimpleTestAgent(config=deps)

        result = await agent.invoke_model(
            {"query": "hi"},
            [{"role": "user", "content": "hi"}],
        )

        assert invocations == ["slm", "llm"]
        assert result.get("_target") == "llm"

        # The LLM saw the LLM-tier hint, not the SLM one — messages were
        # rebuilt from the original caller messages.
        llm_msgs = captured_llm_msgs[0]
        assert llm_msgs[0]["role"] == "system"
        assert "llm" in llm_msgs[0]["content"].lower()
        assert "upgrade" not in llm_msgs[0]["content"].lower()

    @pytest.mark.asyncio
    async def test_slm_upgrade_with_reason_still_escalates(self):
        """UPGRADE on the first line escalates even when followed by a reason."""
        invocations = []

        async def slm_invoker(**_kwargs):
            invocations.append("slm")
            return {"response": "UPGRADE\nQuery needs multi-step reasoning."}

        async def llm_invoker(**_kwargs):
            invocations.append("llm")
            return {"response": "llm answer"}

        slm = ModelTarget(name="slm", model="small", invoker=slm_invoker)
        llm = ModelTarget(name="llm", model="large", invoker=llm_invoker)
        deps = AgentDependencies(slm=slm, llm=llm, complexity_threshold=0.99)
        agent = SimpleTestAgent(config=deps)

        result = await agent.invoke_model(
            {"query": "hi"},
            [{"role": "user", "content": "hi"}],
        )

        assert invocations == ["slm", "llm"]
        assert result.get("_target") == "llm"

    @pytest.mark.asyncio
    async def test_slm_normal_reply_does_not_escalate(self):
        """Passing mentions of 'upgrade' must not trigger escalation.

        Only ``UPGRADE`` as the first non-blank line is the sentinel;
        sentences that *mention* the word should pass through.
        """
        invocations = []

        async def slm_invoker(**_kwargs):
            invocations.append("slm")
            return {"response": "I can upgrade your plan; here are the tiers..."}

        async def llm_invoker(**_kwargs):  # pragma: no cover - should not be called
            invocations.append("llm")
            return {"response": "llm answer"}

        slm = ModelTarget(name="slm", model="small", invoker=slm_invoker)
        llm = ModelTarget(name="llm", model="large", invoker=llm_invoker)
        deps = AgentDependencies(slm=slm, llm=llm, complexity_threshold=0.99)
        agent = SimpleTestAgent(config=deps)

        result = await agent.invoke_model(
            {"query": "hi"},
            [{"role": "user", "content": "hi"}],
        )

        assert invocations == ["slm"]
        assert result.get("_target") == "slm"

    @pytest.mark.asyncio
    async def test_slm_upgrade_without_llm_returns_slm_reply(self):
        """With no LLM configured, the UPGRADE reply passes through.

        The framework suppresses the upgrade clause from the hint when
        no LLM is paired (so a well-behaved SLM won't even try), but
        defensive equivalence still holds: a stray ``UPGRADE`` reply
        must not crash the runtime — it is returned to the caller.
        """

        async def slm_invoker(**_kwargs):
            return {"response": "UPGRADE"}

        slm = ModelTarget(name="slm", model="small", invoker=slm_invoker)
        deps = AgentDependencies(slm=slm, llm=None, complexity_threshold=0.5)
        agent = SimpleTestAgent(config=deps)

        result = await agent.invoke_model(
            {"query": "hi"},
            [{"role": "user", "content": "hi"}],
        )

        assert result.get("_target") == "slm"
        assert result.get("response") == "UPGRADE"

    @pytest.mark.asyncio
    async def test_streaming_hint_omits_upgrade_clause(self):
        """Streaming SLM hint must not promise UPGRADE.

        The runtime cannot introspect a streamed reply without
        buffering, so the streaming path suppresses the upgrade clause
        to avoid promising a channel it can't honor.
        """
        captured_payloads = []

        class StreamingInvoker(StreamingModelInvoker):
            async def __call__(self, **kwargs):
                captured_payloads.append(kwargs)
                return self._stream_impl(kwargs)

            async def _stream_impl(self, _prep):  # type: ignore[override]
                for chunk in ("hello ", "world"):
                    yield chunk

        invoker = StreamingInvoker()
        slm = ModelTarget(name="slm", model="small", invoker=invoker)
        llm_invoker = AsyncMock()
        llm = ModelTarget(name="llm", model="large", invoker=llm_invoker)
        deps = AgentDependencies(slm=slm, llm=llm, complexity_threshold=0.5)
        agent = SimpleTestAgent(config=deps)

        chunks = [
            c
            async for c in agent.invoke_model_stream(
                {"query": "hi"},
                [{"role": "user", "content": "hi"}],
            )
        ]

        assert chunks == ["hello ", "world"]
        assert captured_payloads
        hint = captured_payloads[0].get("routing_hint", "")
        assert "slm" in hint.lower()
        assert "upgrade" not in hint.lower()

    @pytest.mark.asyncio
    async def test_payload_requests_logprobs_by_default(self):
        """Every ModelTarget invocation must request logprobs by default.

        The framework wants per-token confidence in the response for
        observability; ``ModelTarget.logprobs`` defaults to ``True`` so
        new configurations get this out-of-the-box.
        """
        captured = {}

        async def invoker(**kwargs):
            captured.update(kwargs)
            return {"response": "ok"}

        slm = ModelTarget(name="slm", model="small", invoker=invoker)
        deps = AgentDependencies(slm=slm, llm=None)
        agent = SimpleTestAgent(config=deps)

        await agent.invoke_model({"query": "hi"}, [{"role": "user", "content": "hi"}])

        assert captured.get("logprobs") is True
        # ``top_logprobs`` is opt-in even when ``logprobs`` is on.
        assert "top_logprobs" not in captured

    @pytest.mark.asyncio
    async def test_payload_omits_logprobs_when_target_disables(self):
        """Disabling logprobs on the target keeps the payload clean."""
        captured = {}

        async def invoker(**kwargs):
            captured.update(kwargs)
            return {"response": "ok"}

        slm = ModelTarget(name="slm", model="small", invoker=invoker, logprobs=False)
        deps = AgentDependencies(slm=slm, llm=None)
        agent = SimpleTestAgent(config=deps)

        await agent.invoke_model({"query": "hi"}, [{"role": "user", "content": "hi"}])

        assert "logprobs" not in captured
        assert "top_logprobs" not in captured

    @pytest.mark.asyncio
    async def test_top_logprobs_forwarded_to_payload(self):
        """``top_logprobs`` on the target reaches the invoker payload."""
        captured = {}

        async def invoker(**kwargs):
            captured.update(kwargs)
            return {"response": "ok"}

        slm = ModelTarget(name="slm", model="small", invoker=invoker, top_logprobs=5)
        deps = AgentDependencies(slm=slm, llm=None)
        agent = SimpleTestAgent(config=deps)

        await agent.invoke_model({"query": "hi"}, [{"role": "user", "content": "hi"}])

        assert captured.get("logprobs") is True
        assert captured.get("top_logprobs") == 5

    @pytest.mark.asyncio
    async def test_logprobs_summary_lands_in_telemetry(self, caplog):
        """OpenAI-shaped logprobs are summarized into ``_telemetry``.

        Headline numbers (count, mean, perplexity) also reach the
        ``agent_model_logprobs`` INFO log so ops can correlate model
        confidence with latency and outcomes.
        """

        async def invoker(**_kwargs):
            return {
                "response": "ok",
                "choices": [
                    {
                        "logprobs": {
                            "content": [
                                {"token": "hello", "logprob": -0.1},
                                {"token": " world", "logprob": -0.3},
                            ]
                        }
                    }
                ],
            }

        slm = ModelTarget(name="slm", model="small", invoker=invoker)
        deps = AgentDependencies(slm=slm, llm=None, service_name="obs-test")
        agent = SimpleTestAgent(config=deps)

        with caplog.at_level(logging.INFO, logger="holiday_peak_lib.agents.base_agent"):
            result = await agent.invoke_model({"query": "hi"}, [{"role": "user", "content": "hi"}])

        summary = result["_telemetry"]["logprobs_summary"]
        assert summary["count"] == 2
        assert summary["min"] == -0.3
        assert summary["max"] == -0.1
        # mean = -0.2 -> perplexity = exp(0.2)
        assert summary["mean"] == pytest.approx(-0.2)
        assert summary["perplexity"] == pytest.approx(math.exp(0.2))

        assert any(
            "agent_model_logprobs service=obs-test target=slm count=2" in record.getMessage()
            for record in caplog.records
        )

    @pytest.mark.asyncio
    async def test_logprobs_summary_handles_responses_api_shape(self):
        """Responses-API-shaped logprobs (``output[].content[].logprobs``).

        The framework can't know which transport the invoker uses, so
        the extractor must work on all three known shapes. This locks
        in the Responses-API path.
        """

        async def invoker(**_kwargs):
            return {
                "response": "ok",
                "output": [
                    {
                        "content": [
                            {
                                "text": "hi",
                                "logprobs": [
                                    {"token": "hi", "logprob": -0.05},
                                ],
                            }
                        ]
                    }
                ],
            }

        slm = ModelTarget(name="slm", model="small", invoker=invoker)
        deps = AgentDependencies(slm=slm, llm=None)
        agent = SimpleTestAgent(config=deps)

        result = await agent.invoke_model({"query": "hi"}, [{"role": "user", "content": "hi"}])

        summary = result["_telemetry"]["logprobs_summary"]
        assert summary["count"] == 1
        assert summary["mean"] == pytest.approx(-0.05)

    @pytest.mark.asyncio
    async def test_logprobs_summary_empty_when_provider_omits_them(self):
        """Providers may ignore the request - summary stays well-defined."""

        async def invoker(**_kwargs):
            return {"response": "ok"}

        slm = ModelTarget(name="slm", model="small", invoker=invoker)
        deps = AgentDependencies(slm=slm, llm=None)
        agent = SimpleTestAgent(config=deps)

        result = await agent.invoke_model({"query": "hi"}, [{"role": "user", "content": "hi"}])

        assert result["_telemetry"]["logprobs_summary"] == {"count": 0}

    @pytest.mark.asyncio
    async def test_payload_uses_responses_api_logprobs_shape_for_foundry(self):
        """Foundry targets emit the Responses-API ``include`` toggle.

        The Responses API does not accept a boolean ``logprobs`` field;
        the toggle is the presence of ``message.output_text.logprobs``
        in the ``include`` array. Sending ``logprobs: True`` to a
        Foundry Responses call is at best ignored and at worst rejected
        as an unknown parameter, so the framework must not emit it.
        """
        captured = {}

        async def invoker(**kwargs):
            captured.update(kwargs)
            return {"response": "ok"}

        slm = ModelTarget(name="slm", model="small", invoker=invoker, provider="foundry")
        deps = AgentDependencies(slm=slm, llm=None)
        agent = SimpleTestAgent(config=deps)

        await agent.invoke_model({"query": "hi"}, [{"role": "user", "content": "hi"}])

        assert captured.get("include") == ["message.output_text.logprobs"]
        # Chat-Completions toggle must NOT leak onto Responses-API
        # payloads - that's the whole point of the provider-aware
        # branch.
        assert "logprobs" not in captured
        # ``top_logprobs`` stays opt-in even on the Responses API.
        assert "top_logprobs" not in captured

    @pytest.mark.asyncio
    async def test_responses_api_include_extends_caller_provided_tokens(self):
        """Caller-supplied ``include`` tokens survive framework injection.

        Adapters that need other Responses-API include items (e.g.
        ``web_search_call.results``) pass them through ``kwargs``. The
        framework's logprobs token must be appended, not overwrite the
        caller's list.
        """
        captured = {}

        async def invoker(**kwargs):
            captured.update(kwargs)
            return {"response": "ok"}

        slm = ModelTarget(name="slm", model="small", invoker=invoker, provider="foundry")
        deps = AgentDependencies(slm=slm, llm=None)
        agent = SimpleTestAgent(config=deps)

        await agent.invoke_model(
            {"query": "hi"},
            [{"role": "user", "content": "hi"}],
            include=["web_search_call.results"],
        )

        assert captured.get("include") == [
            "web_search_call.results",
            "message.output_text.logprobs",
        ]

    @pytest.mark.asyncio
    async def test_responses_api_top_logprobs_forwarded(self):
        """``top_logprobs`` on Foundry targets reaches the Responses payload.

        The parameter has the same name and 0-20 range as Chat
        Completions, but it travels alongside the ``include`` toggle
        rather than the boolean ``logprobs`` flag.
        """
        captured = {}

        async def invoker(**kwargs):
            captured.update(kwargs)
            return {"response": "ok"}

        slm = ModelTarget(
            name="slm",
            model="small",
            invoker=invoker,
            provider="foundry",
            top_logprobs=3,
        )
        deps = AgentDependencies(slm=slm, llm=None)
        agent = SimpleTestAgent(config=deps)

        await agent.invoke_model({"query": "hi"}, [{"role": "user", "content": "hi"}])

        assert captured.get("include") == ["message.output_text.logprobs"]
        assert captured.get("top_logprobs") == 3
        assert "logprobs" not in captured

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
        )
        assert target.name == "test"
        assert target.model == "gpt-4"
        assert target.temperature == 0.7
        assert target.top_p == 0.9

    def test_model_target_defaults(self):
        """Test ModelTarget default values."""
        invoker = AsyncMock()
        target = ModelTarget(name="test", model="gpt-4", invoker=invoker)
        assert target.temperature == 0.2
        assert target.top_p == 0.9


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

        # When no hot memory, session_id passes through unchanged
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
        """Updated session state is persisted as a summary to Redis."""
        import asyncio
        import json

        async def invoker(**kwargs):
            return {
                "content": "computed result",
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

        # Allow background task to complete
        await asyncio.sleep(0)

        # Session summary stored in Redis via store_summary (background task)
        hot.set.assert_called_once()
        call_kwargs = hot.set.call_args[1]
        assert "session_summary:" in call_kwargs["key"]
        stored = json.loads(call_kwargs["value"])
        assert "page-abc" in stored["session_id"]
        assert stored["service"] == "default"

    @pytest.mark.asyncio
    async def test_session_state_loaded_from_hot_memory(self):
        """Cached session summary triggers continuation and loads Cosmos state."""
        import json
        import time

        captured_kwargs = {}

        async def invoker(**kwargs):
            captured_kwargs.update(kwargs)
            return {"content": "ok"}

        # Build a summary that matches the incoming request keywords
        summary = json.dumps(
            {
                "session_id": "page-abc",
                "service": "default",
                "entity_id": "page-abc",
                "topic_keywords": ["follow", "shipping", "update"],
                "message_count": 2,
                "last_epoch": time.time(),
                "summary_text": "prior response about shipping",
            }
        )

        slm = ModelTarget(name="slm", model="small", invoker=invoker)
        hot = AsyncMock()
        hot.get = AsyncMock(return_value=summary)
        hot.set = AsyncMock()
        warm = AsyncMock()
        warm.read = AsyncMock(
            return_value={
                "foundry_session_state": {
                    "type": "session",
                    "session_id": "page-abc",
                    "service_session_id": "foundry-thread-existing",
                    "state": {},
                },
            }
        )
        deps = AgentDependencies(slm=slm, llm=None, hot_memory=hot, warm_memory=warm)
        agent = SimpleTestAgent(config=deps)

        await agent.invoke_model(
            {"query": "follow up on shipping update", "session_id": "page-abc"},
            [{"role": "user", "content": "follow up on shipping update"}],
        )

        # Session continued — Foundry state loaded from Cosmos
        assert "_foundry_session_state" in captured_kwargs
        assert (
            captured_kwargs["_foundry_session_state"]["service_session_id"]
            == "foundry-thread-existing"
        )
