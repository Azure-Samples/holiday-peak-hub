"""Tests for the Foundry hosted-agent FastAPI mount adapter.

These tests cover the *translation logic* (free-form text -> handle dict ->
AgentResponse) without requiring the optional
``agent-framework-foundry-hosting`` package to be installed. End-to-end
mount tests live under ``.tmp/probe_mount.py`` and the planned
``inventory-health-check`` integration test once the SDK is available in
the lib venv.
"""

from __future__ import annotations

from typing import Any

import pytest
from agent_framework import Content, Message
from holiday_peak_lib.agents.base_agent import AgentDependencies, BaseRetailAgent
from holiday_peak_lib.agents.hosted import (
    _extract_text_from_handle_result,
    _extract_user_text,
    _HostedAgentRunAdapter,
)


class _RecordingAgent(BaseRetailAgent):
    """Minimal agent that records the request its ``handle`` was given."""

    def __init__(self) -> None:
        super().__init__(AgentDependencies(service_name="recording-agent"))
        self.last_request: dict[str, Any] | None = None
        self.next_response: dict[str, Any] = {"text": "hello-from-handle"}

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        self.last_request = request
        return self.next_response


class _MessageLike:
    def __init__(
        self,
        *,
        role: str | None = "user",
        contents: list[Any] | None = None,
        content: Any = None,
        text: str | None = None,
        input_value: Any = None,
    ) -> None:
        self.role = role
        self.contents = contents
        self.content = content
        self.text = text
        self.input = input_value


def test_extract_user_text_pulls_last_text_message() -> None:
    msgs = [
        Message(role="user", contents=[Content(type="text", text="earlier")]),
        Message(
            role="user",
            contents=[Content(type="text", text="latest input text")],
        ),
    ]
    assert _extract_user_text(msgs) == "latest input text"


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        (_MessageLike(content="plain object content"), "plain object content"),
        (
            _MessageLike(content=[{"type": "input_text", "text": "object part"}]),
            "object part",
        ),
        ({"role": "user", "content": "plain dict content"}, "plain dict content"),
        (
            {"role": "user", "content": [{"type": "input_text", "text": "dict part"}]},
            "dict part",
        ),
        (_MessageLike(role=None, text="object direct text"), "object direct text"),
        ({"text": "dict direct text"}, "dict direct text"),
        ({"input": "direct input text"}, "direct input text"),
        (
            {
                "input": [
                    {"role": "user", "content": "earlier nested input"},
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": "latest nested input"}],
                    },
                ]
            },
            "latest nested input",
        ),
    ],
)
def test_extract_user_text_handles_common_maf_and_openai_shapes(
    message: Any, expected: str
) -> None:
    assert _extract_user_text(message) == expected


def test_extract_user_text_prefers_most_recent_user_message() -> None:
    messages = [
        {"role": "user", "content": "older user text"},
        {"role": "assistant", "content": "assistant text should be ignored"},
        {"role": "user", "content": "latest user text"},
    ]
    assert _extract_user_text(messages) == "latest user text"


def test_extract_user_text_skips_later_non_user_messages() -> None:
    messages = [
        {"role": "user", "content": "latest user text"},
        {"role": "assistant", "content": "assistant text should be ignored"},
    ]
    assert _extract_user_text(messages) == "latest user text"


def test_extract_user_text_handles_empty_inputs() -> None:
    assert _extract_user_text(None) == ""
    assert _extract_user_text([]) == ""


def test_extract_text_from_handle_result_prefers_known_keys() -> None:
    assert _extract_text_from_handle_result({"text": "t-value"}) == "t-value"
    assert _extract_text_from_handle_result({"response": "r-value"}) == "r-value"
    assert _extract_text_from_handle_result({"summary": "s-value"}) == "s-value"


def test_extract_text_from_handle_result_walks_nested_messages() -> None:
    payload = {
        "messages": [
            {
                "role": "assistant",
                "content": [{"type": "text", "text": "deep-nested"}],
            }
        ]
    }
    assert _extract_text_from_handle_result(payload) == "deep-nested"


def test_extract_text_from_handle_result_falls_back_to_json() -> None:
    out = _extract_text_from_handle_result({"unknown_field": 42})
    assert "unknown_field" in out and "42" in out


@pytest.mark.asyncio
async def test_default_request_translator_passes_prompt() -> None:
    agent = _RecordingAgent()
    request = await agent.hosted_request_from_text("free form input")
    assert request == {"prompt": "free form input"}


@pytest.mark.asyncio
async def test_hosted_run_adapter_round_trips_text() -> None:
    agent = _RecordingAgent()

    async def translator(text: str) -> dict[str, Any]:
        return {"prompt": text, "kind": "translated"}

    adapter = _HostedAgentRunAdapter(agent, translator)
    response = await adapter.run(messages=[Message(role="user", contents=["check me"])])

    assert agent.last_request == {"prompt": "check me", "kind": "translated"}
    assert response.messages and response.messages[0].contents
    text = getattr(response.messages[0].contents[0], "text", None)
    assert text == "hello-from-handle"


@pytest.mark.asyncio
async def test_hosted_run_adapter_streams_single_update() -> None:
    """``run(stream=True)`` must return an async iterator (NOT a coroutine).

    Foundry's ``ResponsesHostServer`` calls
    ``async for update in agent.run(stream=True, ...):`` without awaiting
    first — so the dispatcher MUST return an async iterator directly.
    Marking ``run`` as ``async def`` would always return a coroutine and
    fail with ``TypeError: 'async for' requires an object with __aiter__``.
    This test pins the streaming contract that powers the Foundry portal
    Playground (which always sets ``stream=True``).
    """
    from agent_framework import AgentResponseUpdate

    agent = _RecordingAgent()

    async def translator(text: str) -> dict[str, Any]:
        return {"prompt": text, "kind": "translated"}

    adapter = _HostedAgentRunAdapter(agent, translator)

    iterator = adapter.run(messages=[Message(role="user", contents=["stream me"])], stream=True)

    # MUST be an async iterator, not a coroutine.
    assert hasattr(iterator, "__aiter__"), (
        "run(stream=True) must return an async iterator so the host server "
        "can `async for update in agent.run(...)` it directly"
    )

    updates = [item async for item in iterator]

    assert len(updates) == 1, "Single-chunk streaming adapter emits one update"
    update = updates[0]
    assert isinstance(update, AgentResponseUpdate)
    assert update.role == "assistant"
    assert update.contents and len(update.contents) == 1
    text = getattr(update.contents[0], "text", None)
    assert text == "hello-from-handle"
    # Translator was called and ``handle()`` received the translated request.
    assert agent.last_request == {"prompt": "stream me", "kind": "translated"}


@pytest.mark.asyncio
async def test_hosted_run_adapter_non_streaming_returns_awaitable() -> None:
    """``run(stream=False)`` must return an awaitable (not an async iterator).

    The non-streaming Foundry path does ``response = await agent.run(...)``,
    so the dispatcher must return a coroutine/awaitable that resolves to an
    :class:`AgentResponse`.
    """
    agent = _RecordingAgent()

    async def translator(text: str) -> dict[str, Any]:
        return {"prompt": text}

    adapter = _HostedAgentRunAdapter(agent, translator)
    awaitable = adapter.run(messages=[Message(role="user", contents=["once"])])

    # The non-streaming path returns a coroutine; awaiting it yields an
    # AgentResponse. It must NOT be async-iterable (that's the streaming
    # path's contract).
    assert hasattr(awaitable, "__await__")
    response = await awaitable
    assert response.messages and response.messages[0].contents


def test_serve_hosted_raises_clear_error_when_sdk_missing(monkeypatch) -> None:
    """If ``agent-framework-foundry-hosting`` is unavailable, the helper
    must raise an actionable ``ImportError`` rather than a generic one.
    """
    import builtins

    real_import = builtins.__import__

    def _blocked_import(name, *args, **kwargs):
        if name == "agent_framework_foundry_hosting":
            raise ImportError("blocked for test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _blocked_import)

    agent = _RecordingAgent()

    class _StubApp:
        def mount(self, *args, **kwargs):  # pragma: no cover - never reached
            raise AssertionError("mount should not be called when SDK missing")

    with pytest.raises(ImportError, match="agent-framework-foundry-hosting"):
        agent.serve_hosted(_StubApp())


# ---------------------------------------------------------------------------
# Optional integration test: only runs when the preview SDK is installed.
# Keeps the suite green without the SDK while exercising the real mount when
# operators do install it (e.g. in a Foundry-hosted-pilot track).
# ---------------------------------------------------------------------------


def test_serve_hosted_mounts_responses_routes_when_sdk_present() -> None:
    pytest.importorskip("agent_framework_foundry_hosting")
    from fastapi import FastAPI

    agent = _RecordingAgent()
    app = FastAPI()

    # Default prefix is empty so the container exposes ``/responses`` directly,
    # matching the path that the Foundry gateway routes to after stripping
    # the public ``/openai/v1/`` segment.
    host_server = agent.serve_hosted(app)

    paths = {
        getattr(r, "path", None) or getattr(r, "path_format", None) for r in host_server.routes
    }
    paths.discard(None)
    assert "/responses" in paths
    # FastAPI mount appended at the end of the route list.
    mounted = [r for r in app.router.routes if getattr(r, "path", "") == ""]
    assert mounted, "ResponsesHostServer should be mounted on the FastAPI app"


def test_serve_hosted_honors_explicit_prefix_when_sdk_present() -> None:
    pytest.importorskip("agent_framework_foundry_hosting")
    from fastapi import FastAPI

    agent = _RecordingAgent()
    app = FastAPI()

    host_server = agent.serve_hosted(app, prefix="/v1")

    paths = {
        getattr(r, "path", None) or getattr(r, "path_format", None) for r in host_server.routes
    }
    paths.discard(None)
    assert "/v1/responses" in paths
