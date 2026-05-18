"""Foundry hosted-agent runtime adapter.

This module wraps a :class:`~holiday_peak_lib.agents.base_agent.BaseRetailAgent`
in the Microsoft Agent Framework ``SupportsAgentRun`` protocol and mounts the
preview ``ResponsesHostServer`` Starlette app inside an existing FastAPI
service so that:

* the same FastAPI process keeps serving ``/health``, ``/ready``, ``/mcp/*``,
  etc. (the AKS-friendly surface), AND
* the ``/{prefix}/responses`` endpoints are exposed for Azure AI Foundry's
  Hosted Agents runtime (the portal-indexed surface).

Single process, single ``uvicorn`` listener, single port. No second runtime,
no parallel ``hosted_main.py``, no separate port 8088. The dual-runtime
guardrail in ADR-005 (2026-05-10) targets the multi-process / multi-port
shape — this helper is its compliant alternative.

Prefix policy: the Foundry gateway translates the public endpoint
``{project_endpoint}/agents/{name}/endpoint/protocols/openai/v1/responses``
into the container-local path ``/responses`` (per the Foundry hosted-agent
deploy reference). The mount default is therefore the empty prefix so the
container answers ``/responses`` directly. Tests and local probes that need
the legacy ``/v1/responses`` layout can pass ``prefix="/v1"`` explicitly.

Usage in a service ``main.py``::

    app = create_standard_app(...)
    app.state.agent.serve_hosted(app)

The lazy import of ``agent_framework_foundry_hosting`` keeps the dependency
optional: services that have not yet migrated continue to work unchanged.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, AsyncIterator, Awaitable, Callable

from agent_framework import AgentResponse, AgentResponseUpdate, Content, Message

if TYPE_CHECKING:  # pragma: no cover - typing only
    from fastapi import FastAPI

    from .base_agent import BaseRetailAgent

logger = logging.getLogger(__name__)


RequestTranslator = Callable[[str], Awaitable[dict[str, Any]]]
"""Async callable that converts free-form Responses-API input text into the
service-specific request dict expected by ``BaseRetailAgent.handle()``.

Default implementation (provided on ``BaseRetailAgent``) returns
``{"prompt": text}``. Services with structured ``handle()`` schemas should
override ``BaseRetailAgent.hosted_request_from_text`` to extract the right
fields.
"""


class _HostedAgentRunAdapter:
    """Minimal ``SupportsAgentRun`` implementation that delegates to a
    :class:`BaseRetailAgent`.

    The Foundry ``ResponsesHostServer`` calls
    ``agent.run(messages, *, stream, session, **kwargs)`` with two distinct
    contracts depending on ``stream`` (verified against
    ``agent_framework_foundry_hosting==1.0.0a260507`` in
    ``agent_framework_foundry_hosting/_responses.py``):

    * ``stream=False`` — ``response = await agent.run(...)`` expects an
      :class:`AgentResponse` (with ``.messages`` of ``Message`` objects).
    * ``stream=True`` — ``async for update in agent.run(...):`` iterates
      :class:`AgentResponseUpdate` items whose ``.contents`` are passed to
      a tracker that emits SSE events. The Foundry portal Playground
      always sets ``stream=True``.

    Because the same call site must return *either* a coroutine *or* an
    async iterator, ``run`` is intentionally a synchronous dispatcher.
    Marking it ``async def`` would always return a coroutine and break the
    streaming path with ``TypeError: 'async for' requires an object with
    __aiter__``.

    Retail agents implement ``handle(request: dict) -> dict`` (unary). This
    adapter currently emits the full reply as a single
    :class:`AgentResponseUpdate` chunk in the streaming path; richer
    incremental streaming via ``invoke_model_stream`` is a follow-up.
    """

    def __init__(
        self,
        agent: "BaseRetailAgent",
        request_translator: RequestTranslator,
    ) -> None:
        self._agent = agent
        self._translate = request_translator
        # Surface attributes the host server inspects.
        self.id = getattr(agent, "id", None) or getattr(agent, "service_name", None) or "agent"
        self.name = getattr(agent, "service_name", None) or self.id
        self.description = getattr(agent, "description", None) or self.name
        self.context_providers = getattr(agent, "context_providers", []) or []
        # ``middleware`` is read by the host server only when present.
        self.middleware = getattr(agent, "middleware", []) or []

    def run(
        self,
        messages: Any = None,
        *,
        stream: bool = False,
        session: Any = None,
        **kwargs: Any,
    ) -> "Awaitable[AgentResponse] | AsyncIterator[AgentResponseUpdate]":
        """Dispatch on ``stream`` to satisfy the dual ``SupportsAgentRun``
        contract used by ``ResponsesHostServer``.

        ``session`` and ``kwargs`` are part of the protocol but the current
        adapter does not consume them — Foundry-side session state is
        managed by the host server, and we do not yet pass extra client
        kwargs through to ``handle()``.
        """
        _ = session, kwargs
        if stream:
            return self._run_streaming(messages)
        return self._run_once(messages)

    async def _run_once(self, messages: Any) -> AgentResponse:
        """Non-streaming path: collect the unary reply and return one
        :class:`AgentResponse`.
        """
        reply_text = await self._invoke_handle(messages)
        reply = Message(role="assistant", contents=[reply_text])
        return AgentResponse(messages=[reply], agent_id=self.id)

    async def _run_streaming(self, messages: Any) -> AsyncIterator[AgentResponseUpdate]:
        """Streaming path: yield a single :class:`AgentResponseUpdate`
        chunk carrying the full text reply.

        The retail agents' ``handle()`` is unary, so we cannot emit
        incremental tokens yet. Emitting one well-formed update is
        sufficient for the Foundry host's SSE tracker to render the reply
        and terminate the stream cleanly; richer per-token streaming via
        ``invoke_model_stream`` is tracked as a follow-up.
        """
        reply_text = await self._invoke_handle(messages)
        yield AgentResponseUpdate(
            contents=[Content(type="text", text=reply_text)],
            role="assistant",
            agent_id=self.id,
        )

    async def _invoke_handle(self, messages: Any) -> str:
        """Shared translation + dispatch + extraction used by both paths."""
        text = _extract_user_text(messages)
        request = await self._translate(text)
        try:
            result = await self._agent.handle(request)
        except Exception:
            logger.exception(
                "hosted_run_handle_failed service=%s",
                getattr(self._agent, "service_name", self.name),
            )
            raise
        return _extract_text_from_handle_result(result)

    def create_session(self, *, session_id: str | None = None) -> Any:
        # Delegate to the wrapped agent (BaseAgent provides this from agent_framework).
        return self._agent.create_session(session_id=session_id)

    def get_session(self, service_session_id: str, *, session_id: str | None = None) -> Any:
        return self._agent.get_session(service_session_id, session_id=session_id)


def _extract_user_text(messages: Any) -> str:
    """Pull the most recent user-message text from a MAF message sequence."""
    if not messages:
        return ""
    seq = messages if isinstance(messages, (list, tuple)) else [messages]
    for msg in reversed(seq):
        for content in getattr(msg, "contents", None) or []:
            text = getattr(content, "text", None)
            if text:
                return str(text)
    return ""


def _extract_text_from_handle_result(result: Any) -> str:
    """Pick the natural-language field from a ``handle()`` dict, or fall
    back to a JSON-serialised payload so no data is silently dropped.
    """
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        for key in ("text", "response", "answer", "summary", "content", "message"):
            value = result.get(key)
            if isinstance(value, str) and value:
                return value
        # Some services wrap text inside ``messages: [{content: [...]}]``
        nested = result.get("messages")
        if isinstance(nested, list):
            for msg in nested:
                if isinstance(msg, dict):
                    parts = msg.get("content")
                    if isinstance(parts, list):
                        for part in parts:
                            text = part.get("text") if isinstance(part, dict) else None
                            if isinstance(text, str) and text:
                                return text
        return json.dumps(result, default=str, ensure_ascii=False)
    return json.dumps(result, default=str, ensure_ascii=False)


def mount_hosted_agent(
    fastapi_app: "FastAPI",
    agent: "BaseRetailAgent",
    *,
    prefix: str = "",
    request_translator: RequestTranslator | None = None,
) -> Any:
    """Mount the Foundry Responses-protocol surface on an existing FastAPI app.

    Args:
        fastapi_app: The FastAPI application that already serves ``/health``,
            ``/ready``, ``/mcp/*``, etc. (typically the one returned by
            :func:`holiday_peak_lib.create_standard_app`). Direct routes
            registered on this app take precedence over the mounted host
            server because Starlette matches in registration order.
        agent: The :class:`BaseRetailAgent` instance whose ``handle()`` will
            answer Foundry hosted-agent invocations.
        prefix: URL prefix for the Responses protocol routes
            (``/{prefix}/responses``). Defaults to ``""`` so the container
            answers ``/responses`` directly — the Foundry gateway translates
            the public ``/openai/v1/responses`` path before reaching the
            container. Pass ``"/v1"`` only for legacy probes that need the
            prior layout.
        request_translator: Optional async callable that converts the
            Responses-API free-form input string into the service-specific
            request dict for ``handle()``. When ``None``, falls back to
            ``agent.hosted_request_from_text`` (defined on ``BaseRetailAgent``).

    Returns:
        The constructed ``ResponsesHostServer`` (a Starlette ASGI app),
        already mounted onto ``fastapi_app``. Returned for tests and
        diagnostics.

    Raises:
        ImportError: If the optional ``agent-framework-foundry-hosting``
            package is not installed in the active environment. Install via
            ``pip install --pre agent-framework-foundry-hosting``.
    """
    try:
        # Lazy import keeps this an *optional* dependency. Services that
        # have not migrated to hosted mode incur no cost.
        from agent_framework_foundry_hosting import (  # pylint: disable=import-outside-toplevel
            ResponsesHostServer,
        )
    except ImportError as exc:  # pragma: no cover - exercised at runtime only
        raise ImportError(
            "agent-framework-foundry-hosting is required to mount Foundry "
            "hosted-agent endpoints. Install with "
            "`pip install --pre agent-framework-foundry-hosting`."
        ) from exc

    translator = request_translator or _default_translator(agent)
    adapter = _HostedAgentRunAdapter(agent, translator)
    host_server = ResponsesHostServer(adapter, prefix=prefix)
    fastapi_app.mount("/", host_server)
    logger.info(
        "hosted_agent_mounted service=%s prefix=%s",
        getattr(agent, "service_name", adapter.name),
        prefix,
    )
    return host_server


def _default_translator(agent: "BaseRetailAgent") -> RequestTranslator:
    """Build a translator that delegates to ``agent.hosted_request_from_text``.

    Defined as a function rather than a lambda so the closure carries a clear
    name in tracebacks.
    """

    async def _translate(text: str) -> dict[str, Any]:
        return await agent.hosted_request_from_text(text)

    return _translate
