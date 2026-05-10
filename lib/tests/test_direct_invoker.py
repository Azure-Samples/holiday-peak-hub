"""Tests for the direct-model invoker (MAF Agent + pluggable ChatClient)."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from holiday_peak_lib.agents.base_agent import ModelTarget
from holiday_peak_lib.agents.direct import (
    DirectModelInvoker,
    _default_chat_client_factory,
    build_direct_model_target,
)
from holiday_peak_lib.agents.foundry import FoundryAgentConfig

TEST_PROJECT_NAME = "test-project"
TEST_PROJECT_ENDPOINT = (
    f"https://test.services.ai.azure.com/api/projects/{TEST_PROJECT_NAME}"
)


def _make_config(*, deployment: str | None = "gpt-5-fast") -> FoundryAgentConfig:
    """Build a minimally-valid FoundryAgentConfig for direct-model invocation."""
    return FoundryAgentConfig(
        endpoint=TEST_PROJECT_ENDPOINT,
        agent_id="pending",
        agent_name="test-agent",
        deployment_name=deployment,
    )


def _make_run_response(text: str = "ok", *, usage: dict | None = None) -> Any:
    """Build a fake AgentRunResponse-like object with the attributes the
    invoker reads."""
    response = MagicMock()
    response.text = text
    response.messages = []
    response.session = None
    response.response_id = None
    if usage is not None:
        usage_obj = MagicMock()
        usage_obj.to_dict.return_value = usage
        response.usage_details = usage_obj
    else:
        response.usage_details = None
    return response


class _StubAgent:
    """Stub for ``agent_framework.Agent`` capturing run() inputs."""

    def __init__(self, response: Any | None = None) -> None:
        self._response = response or _make_run_response()
        self.run_calls: list[dict[str, Any]] = []
        self.constructor_kwargs: dict[str, Any] = {}

    async def run(self, messages: Any, **kwargs: Any) -> Any:
        self.run_calls.append({"messages": messages, **kwargs})
        return self._response


class _StreamUpdate:
    """Stub for ``AgentResponseUpdate`` used in streaming tests."""

    def __init__(self, text: str) -> None:
        self.text = text


class _StreamingStubAgent:
    """Stub agent whose run() returns an async iterable of cumulative updates."""

    def __init__(self, deltas: list[str]) -> None:
        # Build cumulative texts ("Hel", "Hell", "Hello").
        self._cumulative: list[str] = []
        running = ""
        for delta in deltas:
            running += delta
            self._cumulative.append(running)
        self.run_calls: list[dict[str, Any]] = []

    def run(self, messages: Any, **kwargs: Any):  # noqa: ANN201 - intentional async gen
        self.run_calls.append({"messages": messages, **kwargs})

        async def _gen():
            for text in self._cumulative:
                yield _StreamUpdate(text)

        return _gen()


# ---------------------------------------------------------------------------
# DirectModelInvoker — non-streaming
# ---------------------------------------------------------------------------


class TestDirectModelInvokerNonStreaming:
    """Non-streaming path: __call__(stream=False) returns a dict."""

    @pytest.mark.asyncio
    async def test_returns_response_dict_with_telemetry(self):
        stub_agent = _StubAgent(_make_run_response("hello world"))
        invoker = DirectModelInvoker(
            _make_config(),
            instructions="You are a test agent.",
            chat_client_factory=lambda _cfg: MagicMock(),
        )
        invoker._agent = stub_agent  # bypass _ensure_agent

        result = await invoker(messages=[{"role": "user", "content": "hi"}])

        assert isinstance(result, dict)
        assert result["content"] == "hello world"
        assert result["stream"] is False
        assert result["telemetry"]["runtime"] == "maf-direct"
        assert result["telemetry"]["agent_name"] == "test-agent"
        assert result["telemetry"]["deployment_name"] == "gpt-5-fast"
        assert result["telemetry"]["messages_sent"] == 1

    @pytest.mark.asyncio
    async def test_normalizes_dict_message_content_to_json(self):
        """Dict/list message content is JSON-serialized before reaching MAF."""
        stub_agent = _StubAgent(_make_run_response("ok"))
        invoker = DirectModelInvoker(
            _make_config(),
            instructions="x",
            chat_client_factory=lambda _cfg: MagicMock(),
        )
        invoker._agent = stub_agent

        await invoker(
            messages=[{"role": "user", "content": {"sku": "ABC123"}}]
        )

        sent = stub_agent.run_calls[0]["messages"]
        assert len(sent) == 1
        # MAFMessage stores the content under .contents
        contents = sent[0].contents
        # JSON-serialized dict
        assert any('"sku"' in str(c) for c in contents)

    @pytest.mark.asyncio
    async def test_callable_tools_forwarded_to_agent_run(self):
        """List of callables is forwarded as ``tools=`` on agent.run()."""
        stub_agent = _StubAgent()
        invoker = DirectModelInvoker(
            _make_config(),
            instructions="x",
            chat_client_factory=lambda _cfg: MagicMock(),
        )
        invoker._agent = stub_agent

        async def my_tool(**_: Any) -> dict:
            return {"ok": True}

        await invoker(messages=[{"role": "user", "content": "hi"}], tools=[my_tool])

        assert stub_agent.run_calls[0]["tools"] == [my_tool]

    @pytest.mark.asyncio
    async def test_dict_callable_tools_forwarded_as_list(self):
        """Dict-of-callables is converted to a list before reaching MAF."""
        stub_agent = _StubAgent()
        invoker = DirectModelInvoker(
            _make_config(),
            instructions="x",
            chat_client_factory=lambda _cfg: MagicMock(),
        )
        invoker._agent = stub_agent

        async def tool_a(**_: Any) -> dict:
            return {}

        async def tool_b(**_: Any) -> dict:
            return {}

        await invoker(
            messages=[{"role": "user", "content": "hi"}],
            tools={"a": tool_a, "b": tool_b},
        )

        forwarded = stub_agent.run_calls[0]["tools"]
        assert tool_a in forwarded and tool_b in forwarded

    @pytest.mark.asyncio
    async def test_dict_schema_tools_rejected(self):
        """Dict-schema tool definitions raise TypeError (no JSON-prompt fallback)."""
        invoker = DirectModelInvoker(
            _make_config(),
            instructions="x",
            chat_client_factory=lambda _cfg: MagicMock(),
        )
        invoker._agent = _StubAgent()

        with pytest.raises(TypeError, match="callable tools"):
            await invoker(
                messages=[{"role": "user", "content": "hi"}],
                tools={"foo": {"type": "function", "function": {"name": "foo"}}},
            )

    @pytest.mark.asyncio
    async def test_session_continuity_round_trip(self):
        """Session state is restored on input and surfaced back on output."""
        from agent_framework import AgentSession

        # Stub response carries a session whose to_dict identifies it.
        response = _make_run_response("hi")
        session_obj = MagicMock()
        session_obj.to_dict.return_value = {"session_id": "sess-123"}
        response.session = session_obj

        stub_agent = _StubAgent(response)
        invoker = DirectModelInvoker(
            _make_config(),
            instructions="x",
            chat_client_factory=lambda _cfg: MagicMock(),
        )
        invoker._agent = stub_agent

        result = await invoker(
            messages=[{"role": "user", "content": "hi"}],
            session_id="sess-123",
        )

        # Session was constructed and forwarded
        forwarded_session = stub_agent.run_calls[0].get("session")
        assert isinstance(forwarded_session, AgentSession)
        # And surfaced back to the caller for thread reuse
        assert result["_foundry_session_state"] == {"session_id": "sess-123"}

    @pytest.mark.asyncio
    async def test_max_output_tokens_propagated_to_chat_options(self):
        """``max_output_tokens`` becomes a runtime ChatOptions field."""
        stub_agent = _StubAgent()
        config = _make_config()
        config.max_output_tokens = 800
        invoker = DirectModelInvoker(
            config,
            instructions="x",
            chat_client_factory=lambda _cfg: MagicMock(),
        )
        invoker._agent = stub_agent

        await invoker(messages=[{"role": "user", "content": "hi"}])

        options = stub_agent.run_calls[0]["options"]
        # ``ChatOptions`` is a TypedDict on this MAF version, so isinstance
        # checks aren't usable; assert the field shape instead.
        assert options is not None
        assert options.get("max_output_tokens") == 800

    @pytest.mark.asyncio
    async def test_timeout_returns_graceful_fallback(self):
        """asyncio.TimeoutError surfaces as a structured response."""
        slow_agent = MagicMock()

        async def _slow_run(*_args: Any, **_kwargs: Any) -> Any:
            await asyncio.sleep(10)
            return _make_run_response("never")

        slow_agent.run = _slow_run

        invoker = DirectModelInvoker(
            _make_config(),
            instructions="x",
            chat_client_factory=lambda _cfg: MagicMock(),
            timeout=0.05,
        )
        invoker._agent = slow_agent

        result = await invoker(messages=[{"role": "user", "content": "hi"}])

        assert isinstance(result, dict)
        assert result["error"] == "timeout"
        assert "could not be completed" in result["content"]
        assert result["telemetry"]["outcome"] == "timeout"

    @pytest.mark.asyncio
    async def test_transport_only_kwargs_discarded(self):
        """``model``, ``temperature``, ``top_p`` etc. are stripped before agent.run()."""
        stub_agent = _StubAgent()
        invoker = DirectModelInvoker(
            _make_config(),
            instructions="x",
            chat_client_factory=lambda _cfg: MagicMock(),
        )
        invoker._agent = stub_agent

        await invoker(
            messages=[{"role": "user", "content": "hi"}],
            model="gpt-5",
            temperature=0.1,
            top_p=0.95,
            client="should-not-leak",
        )

        forwarded = stub_agent.run_calls[0]
        for forbidden in ("model", "temperature", "top_p", "client"):
            assert forbidden not in forwarded


# ---------------------------------------------------------------------------
# DirectModelInvoker — streaming
# ---------------------------------------------------------------------------


class TestDirectModelInvokerStreaming:
    """Streaming path: __call__(stream=True) returns AsyncGenerator[str, None]."""

    @pytest.mark.asyncio
    async def test_streaming_yields_token_deltas(self):
        """Cumulative MAF updates are yielded as incremental deltas."""
        stub_agent = _StreamingStubAgent(["He", "llo", " world"])
        invoker = DirectModelInvoker(
            _make_config(),
            instructions="x",
            chat_client_factory=lambda _cfg: MagicMock(),
        )
        invoker._agent = stub_agent

        gen = await invoker(
            messages=[{"role": "user", "content": "hi"}], stream=True
        )

        deltas = [delta async for delta in gen]
        assert deltas == ["He", "llo", " world"]
        # And stream=True was forwarded to agent.run
        assert stub_agent.run_calls[0]["stream"] is True


# ---------------------------------------------------------------------------
# build_direct_model_target — factory shape
# ---------------------------------------------------------------------------


class TestBuildDirectModelTarget:
    """The factory must return a ModelTarget whose invoker is DirectModelInvoker."""

    def test_returns_model_target_with_maf_direct_provider(self):
        target = build_direct_model_target(
            _make_config(),
            instructions="You are a test agent.",
            chat_client_factory=lambda _cfg: MagicMock(),
        )

        assert isinstance(target, ModelTarget)
        assert target.provider == "maf-direct"
        assert target.model == "gpt-5-fast"
        assert isinstance(target.invoker, DirectModelInvoker)

    def test_propagates_tools_into_invoker(self):
        async def my_tool(**_: Any) -> dict:
            return {}

        target = build_direct_model_target(
            _make_config(),
            instructions="x",
            tools=[my_tool],
            chat_client_factory=lambda _cfg: MagicMock(),
        )

        assert target.invoker._static_tools == [my_tool]

    def test_default_factory_requires_deployment_name(self):
        """Without deployment_name the default factory fails fast."""
        config = _make_config(deployment=None)

        with pytest.raises(ValueError, match="deployment_name"):
            _default_chat_client_factory(config)
