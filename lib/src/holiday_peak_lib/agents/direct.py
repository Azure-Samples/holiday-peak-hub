"""Direct-model invocation via MAF ``Agent`` (provider-agnostic).

This module is the runtime side of the *Mandatory MAF Invocation Policy*
amendment to ADR-005 (2026-05-10). The MAF :class:`agent_framework.Agent` runs
in-process inside the existing FastAPI handler. The agent's instructions, tools,
and model deployment reference are baked into the container image — no
portal-managed Foundry Agent record is required at runtime.

Drop-in replacement for :class:`FoundryAgentInvoker` at the
:class:`~holiday_peak_lib.agents.base_agent.ModelInvoker` boundary in
:meth:`BaseRetailAgent.invoke_model`. Differences:

- No portal-managed Foundry Agent record. The MAF ``Agent`` is constructed
  in-process at first call from ``instructions``, ``tools``, and a
  ``ChatClient``.
- Tool calling uses native MAF function-calling. The JSON-text tool-call parser
  used by ``FoundryAgentInvoker`` is intentionally not replicated; dict-schema
  tool definitions raise :class:`TypeError` rather than being silently injected
  into the system prompt.
- Provider-agnostic: pass ``chat_client_factory`` to swap providers
  (``FoundryChatClient``, ``OpenAIChatClient``, ``AzureOpenAIChatClient``).
- ``default_options={"store": False}`` — no server-side conversation state.
  Session continuity is via MAF :class:`AgentSession` (in-memory, per-request).

Single-architecture guardrail (from the inventory hosted-agent precedent,
commit ``4cf0e546``): a service must not ship a second entry point alongside
``main.py``. The MAF ``Agent`` constructed by this invoker lives inside the
existing FastAPI handler — there is no parallel runtime.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from time import perf_counter
from typing import Any, AsyncGenerator, Callable, NamedTuple

from agent_framework import Agent, AgentSession
from agent_framework import ChatOptions as _ChatOptions
from agent_framework import Message as MAFMessage
from azure.identity.aio import DefaultAzureCredential

from .base_agent import ModelTarget
from .foundry import FoundryAgentConfig, _maybe_await
from .provider_policy import normalize_messages as _normalize_messages

_logger = logging.getLogger(__name__)

_DEFAULT_DIRECT_INVOKE_TIMEOUT = float(os.getenv("AGENT_DIRECT_INVOKE_TIMEOUT_SECONDS", "55"))


ChatClientFactory = Callable[[FoundryAgentConfig], Any]


def _default_chat_client_factory(config: FoundryAgentConfig) -> Any:
    """Build a :class:`FoundryChatClient` from a :class:`FoundryAgentConfig`.

    Default factory used when no override is provided. Targets Foundry's
    Responses API. Provider-agnostic by design — callers may pass any factory
    that returns an object satisfying MAF's ``SupportsChatGetResponse``
    protocol (e.g., ``OpenAIChatClient``, ``AzureOpenAIChatClient``).
    """
    # Imported lazily so test environments without ``agent_framework_foundry``
    # installed can still exercise the rest of the invoker via mocks.
    from agent_framework_foundry import (  # pylint: disable=import-outside-toplevel
        FoundryChatClient,
    )

    if not config.deployment_name:
        raise ValueError(
            "DirectModelInvoker requires deployment_name on FoundryAgentConfig "
            "(env: MODEL_DEPLOYMENT_NAME_FAST / MODEL_DEPLOYMENT_NAME_RICH)."
        )
    credential = config.credential or DefaultAzureCredential()
    return FoundryChatClient(
        project_endpoint=config.endpoint,
        model=config.deployment_name,
        credential=credential,
    )


class _PreparedDirectInvocation(NamedTuple):
    """Extracted payload shared by streaming and non-streaming paths."""

    maf_messages: list[Any]
    runtime_tools: list[Any] | None
    normalized: list[dict[str, Any]]
    session: AgentSession | None
    reasoning_effort: str | None = None
    max_output_tokens: int | None = None


class DirectModelInvoker:
    """Invoke a model directly via MAF :class:`Agent`.

    Implements the same ``__call__`` contract as
    :class:`~holiday_peak_lib.agents.foundry.FoundryAgentInvoker` so call sites
    in :class:`BaseRetailAgent` are unchanged. Strategy dispatch:

    - ``stream=False`` (default) → awaits ``agent.run()`` and returns a dict.
    - ``stream=True`` → returns an :class:`AsyncGenerator` that yields text
      token deltas. Callers iterate with ``async for``.
    """

    def __init__(
        self,
        config: FoundryAgentConfig,
        *,
        instructions: str,
        tools: list[Callable[..., Any]] | None = None,
        chat_client_factory: ChatClientFactory | None = None,
        timeout: float | None = None,
        agent_name: str | None = None,
    ) -> None:
        self.config = config
        self._instructions = instructions
        self._static_tools = list(tools) if tools else None
        self._chat_client_factory = chat_client_factory or _default_chat_client_factory
        self._timeout = timeout if timeout is not None else _DEFAULT_DIRECT_INVOKE_TIMEOUT
        self._agent_name = agent_name or config.agent_name or "direct-agent"
        self._max_output_tokens = config.max_output_tokens
        self._client: Any = None
        self._agent: Agent | None = None

    def _ensure_agent(self) -> Agent:
        """Create or return the cached MAF ``Agent`` instance."""
        if self._agent is None:
            self._client = self._chat_client_factory(self.config)
            agent_kwargs: dict[str, Any] = {
                "client": self._client,
                "instructions": self._instructions,
                "name": self._agent_name,
                "default_options": {"store": False},
            }
            if self._static_tools:
                agent_kwargs["tools"] = self._static_tools
            self._agent = Agent(**agent_kwargs)
        return self._agent

    def _prepare_invocation(self, **kwargs: Any) -> _PreparedDirectInvocation:
        """Extract and normalize messages/tools/session from kwargs.

        Shared by ``__call__`` and ``_stream_impl`` to avoid duplicating
        message serialization and tool extraction.
        """
        messages_raw = kwargs.pop("messages", [])
        kwargs.pop("stream", None)
        tools_raw = kwargs.pop("tools", None)
        session_id = kwargs.pop("session_id", None)
        session_state = kwargs.pop("_foundry_session_state", None)
        reasoning_effort = kwargs.pop("reasoning_effort", None)
        max_tokens_override = kwargs.pop("max_output_tokens", None)
        # Discard transport-only kwargs not consumed by MAF.
        for _discard in (
            "model",
            "temperature",
            "top_p",
            "client",
            "thread_id",
            "conversation_id",
        ):
            kwargs.pop(_discard, None)

        # Restore AgentSession from prior state or create new one.
        session: AgentSession | None = None
        if isinstance(session_state, dict):
            try:
                session = AgentSession.from_dict(session_state)
            except (KeyError, TypeError, ValueError):
                pass
        if session is None and session_id:
            session = AgentSession(session_id=str(session_id))

        normalized = _normalize_messages(messages_raw)
        maf_messages: list[MAFMessage] = []
        for msg in normalized:
            raw_content = msg.get("content", "")
            if isinstance(raw_content, (dict, list)):
                raw_content = json.dumps(raw_content, default=str)
            maf_messages.append(
                MAFMessage(role=msg.get("role", "user"), contents=[raw_content])
            )

        # Resolve runtime tools: per-call override > static tools.
        # Direct-model path expects callables. Dict-schema tool definitions are
        # rejected — there is no JSON-text tool-call parser fallback in this
        # path (see ADR-005 2026-05-10 amendment).
        runtime_tools: list[Any] | None = self._static_tools
        if tools_raw is not None:
            if isinstance(tools_raw, dict):
                if tools_raw and all(callable(v) for v in tools_raw.values()):
                    runtime_tools = list(tools_raw.values())
                elif tools_raw:
                    raise TypeError(
                        "DirectModelInvoker requires callable tools; dict-schema "
                        "tool definitions are not supported. Pass Python callables "
                        "via AgentBuilder.with_tool(name, callable)."
                    )
            elif isinstance(tools_raw, (list, tuple)):
                if tools_raw and all(callable(t) for t in tools_raw):
                    runtime_tools = list(tools_raw)
                elif tools_raw:
                    raise TypeError(
                        "DirectModelInvoker requires callable tools; non-callable "
                        "entries found in tools list."
                    )

        return _PreparedDirectInvocation(
            maf_messages=maf_messages,
            runtime_tools=runtime_tools,
            normalized=normalized,
            session=session,
            reasoning_effort=reasoning_effort,
            max_output_tokens=max_tokens_override or self._max_output_tokens,
        )

    async def __call__(self, **kwargs: Any) -> dict[str, Any] | AsyncGenerator[str, None]:
        """Strategy dispatch entry point.

        - ``stream=False`` (default) → awaits a single response.
        - ``stream=True`` → returns an :class:`AsyncGenerator[str, None]`.
        """
        stream = kwargs.pop("stream", False)
        prep = self._prepare_invocation(**kwargs)
        if stream:
            return self._stream_impl(prep)
        return await self._request_response_impl(prep)

    async def _request_response_impl(
        self, prep: _PreparedDirectInvocation
    ) -> dict[str, Any]:
        """Non-streaming path: await a single :class:`AgentRunResponse`."""
        started = perf_counter()
        agent = self._ensure_agent()

        run_kwargs: dict[str, Any] = {"stream": False}
        if prep.runtime_tools is not None:
            run_kwargs["tools"] = prep.runtime_tools
        if prep.session is not None:
            run_kwargs["session"] = prep.session

        chat_options = self._build_chat_options(prep)
        if chat_options is not None:
            run_kwargs["options"] = chat_options

        try:
            response = await asyncio.wait_for(
                agent.run(prep.maf_messages, **run_kwargs),
                timeout=self._timeout,
            )
        except asyncio.TimeoutError:
            timeout_text = (
                "The request could not be completed within"
                " the allowed time. Please try a simpler"
                " query or retry shortly."
            )
            return {
                "content": timeout_text,
                "messages": [
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [
                            {"type": "output_text", "text": timeout_text}
                        ],
                    }
                ],
                "stream": False,
                "error": "timeout",
                "telemetry": self._build_telemetry(
                    started, prep.normalized, stream=False, outcome="timeout"
                ),
            }

        # Session continuity for multi-turn flows.
        updated_session_state: dict[str, Any] | None = None
        resp_session = getattr(response, "session", None)
        if resp_session is not None and hasattr(resp_session, "to_dict"):
            updated_session_state = resp_session.to_dict()
        elif prep.session is not None:
            updated_session_state = prep.session.to_dict()

        assistant_text = (
            response.text if hasattr(response, "text") else str(response)
        )

        # Prefer MAF's own serialization for messages when available.
        resp_messages = getattr(response, "messages", None)
        if (
            isinstance(resp_messages, list)
            and resp_messages
            and all(hasattr(m, "to_dict") for m in resp_messages)
        ):
            serialized_messages = [m.to_dict() for m in resp_messages]
        else:
            serialized_messages = []
            if assistant_text:
                serialized_messages.append(
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [
                            {"type": "output_text", "text": assistant_text}
                        ],
                    }
                )

        result: dict[str, Any] = {
            "content": assistant_text,
            "messages": serialized_messages,
            "stream": False,
            "telemetry": self._build_telemetry(
                started, prep.normalized, stream=False
            ),
        }

        response_id = getattr(response, "response_id", None)
        if response_id is not None:
            result["response_id"] = response_id

        usage = getattr(response, "usage_details", None)
        if usage is not None:
            result["usage"] = (
                usage.to_dict() if hasattr(usage, "to_dict") else usage
            )

        if updated_session_state is not None:
            # Same key name as FoundryAgentInvoker so call sites that already
            # relay session state for thread reuse keep working unchanged.
            result["_foundry_session_state"] = updated_session_state

        return result

    async def _stream_impl(
        self, prep: _PreparedDirectInvocation
    ) -> AsyncGenerator[str, None]:
        """Streaming path: yield text-token deltas.

        ``agent.run(stream=True)`` returns an async iterable, NOT a coroutine,
        so we guard with :func:`asyncio.timeout` instead of ``asyncio.wait_for``.

        MAF ``AgentResponseUpdate.text`` is *cumulative* — each update contains
        the full text assembled so far. We track ``prev_len`` and yield only
        the new portion (the delta).
        """
        agent = self._ensure_agent()

        run_kwargs: dict[str, Any] = {"stream": True}
        if prep.runtime_tools is not None:
            run_kwargs["tools"] = prep.runtime_tools
        if prep.session is not None:
            run_kwargs["session"] = prep.session

        chat_options = self._build_chat_options(prep)
        if chat_options is not None:
            run_kwargs["options"] = chat_options

        # ``Agent.run(stream=True)`` returns an async iterable, not a coroutine.
        # Pylint cannot narrow Agent.run's overload union on a literal
        # stream=True, hence the explicit suppression on the iteration line.
        # Mirrors the same call shape in ``FoundryAgentInvoker._stream_impl``.
        stream_response = agent.run(prep.maf_messages, **run_kwargs)

        prev_len = 0
        async with asyncio.timeout(self._timeout):
            # pylint: disable=not-an-iterable
            async for update in stream_response:
                text = update.text if hasattr(update, "text") else str(update)
                if len(text) > prev_len:
                    yield text[prev_len:]
                    prev_len = len(text)

    def _build_chat_options(
        self, prep: _PreparedDirectInvocation
    ) -> _ChatOptions | None:
        """Build a :class:`ChatOptions` payload for the underlying ``ChatClient``.

        Unlike portal-managed Foundry Agents, where ``reasoning_effort`` was an
        agent-DEFINITION parameter (set at version-creation time),
        ``FoundryChatClient`` exposes it as a runtime Responses API parameter.
        It is forwarded via :class:`ChatOptions` for forward compatibility.
        """
        kwargs: dict[str, Any] = {}
        if prep.max_output_tokens is not None:
            kwargs["max_output_tokens"] = prep.max_output_tokens
        if prep.reasoning_effort is not None:
            # MAF ChatOptions exposes a typed field on newer versions; older
            # versions surface unknown kwargs via additional_properties. Try
            # the typed field first, fall back to the bag.
            try:
                return _ChatOptions(
                    reasoning_effort=prep.reasoning_effort, **kwargs
                )
            except TypeError:
                kwargs["additional_properties"] = {
                    "reasoning_effort": prep.reasoning_effort
                }
        if not kwargs:
            return None
        return _ChatOptions(**kwargs)

    def _build_telemetry(
        self,
        started: float,
        normalized: list[dict[str, Any]],
        *,
        stream: bool,
        outcome: str = "success",
    ) -> dict[str, Any]:
        """Build a standard telemetry dict.

        The shape mirrors :meth:`FoundryAgentInvoker._build_telemetry` so that
        downstream telemetry consumers (Application Insights queries, the
        agent-traces endpoint) keep working unchanged. Only the ``runtime``
        marker differs (``maf-direct`` vs ``maf``).
        """
        telemetry: dict[str, Any] = {
            "endpoint": self.config.endpoint,
            "agent_name": self._agent_name,
            "deployment_name": self.config.deployment_name,
            "stream": stream,
            "messages_sent": len(normalized),
            "duration_ms": (perf_counter() - started) * 1000,
            "api_version": "responses",
            "runtime": "maf-direct",
        }
        if self._max_output_tokens is not None:
            telemetry["max_output_tokens"] = self._max_output_tokens
        if outcome != "success":
            telemetry["timeout_seconds"] = self._timeout
            telemetry["outcome"] = outcome
        return telemetry

    async def close(self) -> None:
        """Clean up cached client/credential resources."""
        # Close the credential only if we created it (i.e., the caller did
        # not provide one on the config).
        if self._client is not None and self.config.credential is None:
            client_credential = getattr(self._client, "_credential", None) or getattr(
                self._client, "credential", None
            )
            if client_credential is not None:
                close_method = getattr(client_credential, "close", None)
                if callable(close_method):
                    await _maybe_await(close_method())
        self._agent = None
        self._client = None


def build_direct_model_target(
    config: FoundryAgentConfig,
    *,
    instructions: str,
    tools: list[Callable[..., Any]] | None = None,
    chat_client_factory: ChatClientFactory | None = None,
) -> ModelTarget:
    """Create a :class:`ModelTarget` that invokes the model directly via MAF.

    Sibling of :func:`build_foundry_model_target`. No portal-managed agent
    record is required — the MAF ``Agent`` is constructed in-process from
    instructions and tools at first invocation.

    :param config: Foundry configuration carrying endpoint and deployment name.
    :param instructions: Persona/role text loaded from
        ``apps/<service>/prompts/instructions.md``. Baked into the container
        image; passed once at construction.
    :param tools: Optional list of Python callables registered as MAF tools.
        Native function-calling is used; no JSON-text fallback.
    :param chat_client_factory: Optional override for the underlying
        ``ChatClient``. Defaults to :class:`FoundryChatClient` (Foundry
        Responses API).
    :returns: A :class:`ModelTarget` wired to a :class:`DirectModelInvoker`.
    """
    config.apply_project_contract()
    invoker = DirectModelInvoker(
        config,
        instructions=instructions,
        tools=tools,
        chat_client_factory=chat_client_factory,
    )
    return ModelTarget(
        name=config.agent_name or config.deployment_name or "direct-model",
        model=config.deployment_name or "unknown",
        invoker=invoker,
        stream=config.stream,
        provider="maf-direct",
    )


__all__ = [
    "ChatClientFactory",
    "DirectModelInvoker",
    "build_direct_model_target",
]
