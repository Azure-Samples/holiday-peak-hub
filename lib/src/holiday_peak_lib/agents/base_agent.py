"""Base agent abstraction with model selection and SDK integration points."""

import asyncio
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from time import perf_counter
from typing import Any, AsyncGenerator, Awaitable, Callable

from agent_framework import BaseAgent
from holiday_peak_lib.agents.complexity import assess_complexity

# Runtime imports for Pydantic model field resolution.
# Circular-import safe: none of these modules import base_agent.
from holiday_peak_lib.agents.memory.builder import MemoryClient
from holiday_peak_lib.agents.memory.cold import ColdMemory
from holiday_peak_lib.agents.memory.hot import HotMemory
from holiday_peak_lib.agents.memory.warm import WarmMemory
from holiday_peak_lib.agents.orchestration.router import RoutingStrategy
from holiday_peak_lib.agents.telemetry_mixin import AgentTelemetryMixin
from holiday_peak_lib.mcp.server import FastAPIMCPServer
from holiday_peak_lib.self_healing import SelfHealingKernel
from pydantic import BaseModel, ConfigDict, Field

from .provider_policy import sanitize_messages_for_provider

ModelInvoker = Callable[..., Awaitable[dict[str, Any]]]


class StreamingModelInvoker:
    """Protocol-style interface for invokers that support streaming.

    Pattern: Strategy — invokers implement ``__call__`` as the single entry
    point.  When ``stream=True`` is passed, ``__call__`` dispatches to the
    private ``_stream_impl`` method and returns an ``AsyncGenerator``.
    ``_supports_streaming()`` checks for this method's presence.
    """

    def _stream_impl(  # noqa: ARG002
        self,
        prep: Any,
    ) -> AsyncGenerator[str, None]:
        """Yield text token deltas from a streaming model call."""
        raise NotImplementedError  # pragma: no cover


def _supports_streaming(invoker: Any) -> bool:
    """Check whether an invoker's ``__call__`` supports ``stream=True``.\n\n    Convention: invokers that support streaming implement a ``_stream_impl``\n    method.  ``__call__`` dispatches to it when ``stream=True``.\n"""
    return callable(getattr(invoker, "_stream_impl", None))


def _extract_text_from_response(result: dict[str, Any]) -> str:
    """Extract concatenated assistant text from a model response dict.

    # No GoF pattern applies — simple data extraction utility.
    """
    parts: list[str] = []
    for msg in result.get("messages", []):
        for content in msg.get("content", []):
            if isinstance(content, dict):
                text = content.get("text", "")
                if text:
                    parts.append(text)
    return "".join(parts)


_DEFAULT_AGENT_INVOKE_TIMEOUT = float(os.getenv("AGENT_INVOKE_TIMEOUT_SECONDS", "90"))


@dataclass
class ModelTarget:
    """Represents a specific model deployment plus its invoker.

    The ``invoker`` is an async callable that receives ``messages`` (list or str),
    optional ``tools``, and any extra kwargs. This keeps the base class agnostic
    of the concrete SDK (Azure AI Agents, Chat Completions, etc.).
    """

    name: str
    model: str
    invoker: ModelInvoker
    temperature: float = 0.2
    top_p: float = 0.9
    stream: bool = False
    provider: str | None = None


class AgentDependencies(BaseModel):
    """Dependency container for DI via property/setter."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    router: Any | None = None
    tools: dict[str, Callable[..., Any]] = Field(default_factory=dict)
    service_name: str | None = None
    memory_client: Any | None = None
    hot_memory: Any | None = None
    warm_memory: Any | None = None
    cold_memory: Any | None = None
    mcp_server: Any | None = None
    self_healing_kernel: Any | None = None
    slm: ModelTarget | None = None
    llm: ModelTarget | None = None
    complexity_threshold: float = 0.5
    enforce_foundry_prompt_governance: bool = True


class BaseRetailAgent(AgentTelemetryMixin, BaseAgent, ABC):
    """Common ingestion, routing, memory ops, and model selection.

    Configure two model targets (SLM/LLM or fast/slow) and the agent will choose
    based on a lightweight complexity heuristic. Pass SDK-specific invokers to
    keep this layer decoupled from the transport implementation.

    Initializes a per-instance pydantic config in ``__init__`` (after calling
    ``BaseAgent.__init__``); inject dependencies via the ``config`` property or
    the provided setters.
    """

    def __init__(self, config: AgentDependencies, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # store the configuration object directly
        self._config = config

    @property
    def config(self) -> AgentDependencies:
        return self._config

    @config.setter
    def config(self, deps: AgentDependencies) -> None:
        self._config = deps

    @property
    def router(self) -> RoutingStrategy | None:
        return self.config.router

    @router.setter
    def router(self, value: RoutingStrategy | None) -> None:
        self.config.router = value

    @property
    def tools(self) -> dict[str, Callable[..., Any]]:
        return self.config.tools

    @tools.setter
    def tools(self, value: dict[str, Callable[..., Any]]) -> None:
        self.config.tools = value

    @property
    def service_name(self) -> str | None:
        return self.config.service_name

    @service_name.setter
    def service_name(self, value: str | None) -> None:
        self.config.service_name = value

    @property
    def memory_client(self) -> MemoryClient | None:
        return self.config.memory_client

    @memory_client.setter
    def memory_client(self, value: MemoryClient | None) -> None:
        self.config.memory_client = value

    @property
    def hot_memory(self) -> HotMemory | None:
        return self.config.hot_memory

    @hot_memory.setter
    def hot_memory(self, value: HotMemory | None) -> None:
        self.config.hot_memory = value

    @property
    def warm_memory(self) -> WarmMemory | None:
        return self.config.warm_memory

    @warm_memory.setter
    def warm_memory(self, value: WarmMemory | None) -> None:
        self.config.warm_memory = value

    @property
    def cold_memory(self) -> ColdMemory | None:
        return self.config.cold_memory

    @cold_memory.setter
    def cold_memory(self, value: ColdMemory | None) -> None:
        self.config.cold_memory = value

    @property
    def mcp_server(self) -> FastAPIMCPServer | None:
        return self.config.mcp_server

    @mcp_server.setter
    def mcp_server(self, value: FastAPIMCPServer | None) -> None:
        self.config.mcp_server = value

    @property
    def self_healing_kernel(self) -> SelfHealingKernel | None:
        return self.config.self_healing_kernel

    @self_healing_kernel.setter
    def self_healing_kernel(self, value: SelfHealingKernel | None) -> None:
        self.config.self_healing_kernel = value

    @property
    def slm(self) -> ModelTarget | None:
        return self.config.slm

    @slm.setter
    def slm(self, value: ModelTarget | None) -> None:
        self.config.slm = value

    @property
    def llm(self) -> ModelTarget | None:
        return self.config.llm

    @llm.setter
    def llm(self, value: ModelTarget | None) -> None:
        self.config.llm = value

    @property
    def complexity_threshold(self) -> float:
        return self.config.complexity_threshold

    @complexity_threshold.setter
    def complexity_threshold(self, value: float) -> None:
        self.config.complexity_threshold = value

    @property
    def enforce_foundry_prompt_governance(self) -> bool:
        return self.config.enforce_foundry_prompt_governance

    @enforce_foundry_prompt_governance.setter
    def enforce_foundry_prompt_governance(self, value: bool) -> None:
        self.config.enforce_foundry_prompt_governance = value

    def _shared_provider_for_routing(self) -> str | None:
        """Return provider name only when SLM/LLM routing targets share one provider."""

        if self.slm is None:
            return None
        slm_provider = self.slm.provider
        if self.llm is None:
            return slm_provider
        if slm_provider and self.llm.provider and slm_provider == self.llm.provider:
            return slm_provider
        return None

    def attach_memory(
        self,
        hot: HotMemory | None,
        warm: WarmMemory | None,
        cold: ColdMemory | None,
    ) -> None:
        self.hot_memory = hot
        self.warm_memory = warm
        self.cold_memory = cold

    def attach_mcp(self, mcp_server: FastAPIMCPServer) -> None:
        self.mcp_server = mcp_server

    def attach_self_healing(self, self_healing_kernel: SelfHealingKernel) -> None:
        self.self_healing_kernel = self_healing_kernel

    def memory_tool_definitions(self) -> dict[str, Callable[..., Any]]:
        """Return memory read/write as LLM-callable tool definitions.

        These tools allow the model to manage session/conversation memory
        directly, enabling a 'check memory first' strategy before deeper searches.
        """
        tools: dict[str, Callable[..., Any]] = {}
        if self.memory_client is None:
            return tools

        async def memory_read(key: str) -> Any:
            """Read a value from the agent's tiered memory by key."""
            return await self.memory_client.get(key)

        async def memory_write(key: str, value: Any) -> str:
            """Write a value to the agent's tiered memory."""
            await self.memory_client.set(key, value)
            return "stored"

        tools["memory_read"] = memory_read
        tools["memory_write"] = memory_write
        return tools

    @staticmethod
    async def gather_adapters(*coros: Awaitable[Any]) -> tuple[Any, ...]:
        """Execute multiple adapter/MCP coroutines in parallel.

        Provides a framework-level entry point so agents can dispatch
        concurrent adapter and MCP calls without manually importing asyncio::

            product, pricing, inventory = await self.gather_adapters(
                self.adapters.products.build_product_context(sku),
                self.adapters.pricing.build_price_context(sku),
                self.adapters.inventory.build_inventory_context(sku),
            )
        """
        return await asyncio.gather(*coros)

    def _assess_complexity(self, request: dict[str, Any]) -> float:
        """Delegate to shared complexity heuristic."""
        return assess_complexity(request)

    def _select_model(self, request: dict[str, Any]) -> ModelTarget:
        """Select SLM vs LLM based on heuristic and configuration."""

        if self.slm is None and self.llm is None:
            raise RuntimeError("No models configured on BaseRetailAgent")

        complexity = self._assess_complexity(request)
        if self.llm and (complexity >= self.complexity_threshold or self.slm is None):
            return self.llm
        if self.slm:
            return self.slm
        if self.llm is not None:
            return self.llm
        # Defensive check: should not be reachable because of the initial guard.
        raise RuntimeError("Model selection failed: no suitable model available")

    async def __invoke_target(
        self,
        target: ModelTarget,
        payload_messages: Any,
        payload_tools: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        payload = {
            **kwargs,
            "messages": payload_messages,
            "model": target.model,
            "temperature": target.temperature,
            "top_p": target.top_p,
            # Always stream=False here — this is the request/response path
            # that expects a dict back.  The streaming path goes through
            # invoke_model_stream() which passes stream=True explicitly.
            "stream": False,
            "tools": payload_tools,
        }
        started = perf_counter()
        outcome = "success"
        error_text: str | None = None
        try:
            result = await target.invoker(**payload)
        except asyncio.TimeoutError:
            outcome = "timeout"
            error_text = "Model invocation timed out"
            raise
        except Exception as exc:
            outcome = "error"
            error_text = str(exc)
            raise
        finally:
            elapsed_ms = (perf_counter() - started) * 1000
            trace_metadata = {
                "elapsed_ms": elapsed_ms,
                "stream": payload.get("stream", target.stream),
                "temperature": target.temperature,
                "top_p": target.top_p,
                "error": error_text,
            }
            try:
                # Derive model_tier from config
                model_tier = "unknown"
                if self.slm and target.name == self.slm.name:
                    model_tier = "slm"
                elif self.llm and target.name == self.llm.name:
                    model_tier = "llm"

                self._get_foundry_tracer().trace_model_invocation(
                    model=target.model,
                    target=target.name,
                    outcome=outcome,
                    model_tier=model_tier,
                    metadata=trace_metadata,
                )
                # Tools are traced with model outcome when they participated
                # in the invocation; individual tool execution tracking
                # is handled at the adapter/handler level.
                self._trace_tools(payload_tools, outcome, trace_metadata)
            except (AttributeError, TypeError, ValueError, RuntimeError):
                pass

        if isinstance(result, dict):
            existing_meta: dict[str, Any] = {}
            for key in ("_telemetry", "telemetry"):
                cand = result.get(key)
                if isinstance(cand, dict):
                    existing_meta.update(cand)

            telemetry = {
                **existing_meta,
                "elapsed_ms": existing_meta.get("elapsed_ms", elapsed_ms),
                "target": existing_meta.get("target", target.name),
                "model": existing_meta.get("model", target.model),
                "stream": existing_meta.get("stream", payload.get("stream", target.stream)),
                "temperature": existing_meta.get("temperature", target.temperature),
                "top_p": existing_meta.get("top_p", target.top_p),
                "tools": existing_meta.get(
                    "tools",
                    (
                        list(payload_tools.keys())
                        if isinstance(payload_tools, dict)
                        else payload_tools
                    ),
                ),
            }

            result.setdefault("_target", target.name)
            result.setdefault("_model", target.model)
            result["_telemetry"] = telemetry

        return result

    async def invoke_model(
        self, request: dict[str, Any], messages: Any, **kwargs: Any
    ) -> dict[str, Any]:
        """Invoke a model with SLM-first routing and optional LLM upgrade.

        Routing rules:
        1) Always evaluate with the SLM using the provided routing prompt.
        2) If the SLM returns ``upgrade``, re-run the original request on the LLM,
           adding a reasoning directive to the system prompt.
        3) Otherwise, execute the original request on the SLM.

        ``messages`` is SDK-dependent (chat messages list, prompt string, etc.).
        Additional kwargs are forwarded to the invoker (e.g., tools, metadata).
        """

        payload_tools = kwargs.get("tools") or (self.tools if self.tools else None)

        # Thread Foundry session for page-level conversation reuse.
        # When a ``session_id`` is present in the request, we load the
        # persisted session state from hot memory (Redis) and forward it
        # through kwargs so the invoker can resume the Foundry thread.
        session_id = request.get("session_id") if isinstance(request, dict) else None
        if session_id and "session_id" not in kwargs:
            kwargs["session_id"] = session_id
            if self.hot_memory is not None and "_foundry_session_state" not in kwargs:
                cached_state = await self.hot_memory.get(f"foundry_session:{session_id}")
                if cached_state:
                    try:
                        import json as _json

                        kwargs["_foundry_session_state"] = _json.loads(cached_state)
                    except (TypeError, ValueError):
                        pass

        messages = sanitize_messages_for_provider(
            messages,
            provider=self._shared_provider_for_routing(),
            enforce_prompt_governance=self.enforce_foundry_prompt_governance,
        )
        self._trace_decision(
            decision="invoke_model",
            outcome="start",
            metadata={
                "has_slm": bool(self.slm),
                "has_llm": bool(self.llm),
                "complexity_threshold": self.complexity_threshold,
            },
        )

        try:
            target = self._select_model(request)
            self._trace_decision(
                decision="routing_strategy",
                outcome=target.name,
                metadata={
                    "complexity": self._assess_complexity(request),
                    "complexity_threshold": self.complexity_threshold,
                },
            )
            result = await asyncio.wait_for(
                self.__invoke_target(target, messages, payload_tools, **kwargs),
                timeout=_DEFAULT_AGENT_INVOKE_TIMEOUT,
            )
        except asyncio.TimeoutError:
            self._trace_decision(
                decision="invoke_model",
                outcome="timeout",
                metadata={"timeout_seconds": _DEFAULT_AGENT_INVOKE_TIMEOUT},
            )
            return {
                "error": "timeout",
                "message": "The agent could not complete the request within the allowed time.",
                "_telemetry": {
                    "outcome": "timeout",
                    "timeout_seconds": _DEFAULT_AGENT_INVOKE_TIMEOUT,
                },
            }

        # Persist updated Foundry session state to hot memory so
        # subsequent requests in the same page-level thread can resume.
        if (
            session_id
            and self.hot_memory is not None
            and isinstance(result, dict)
            and result.get("_foundry_session_state")
        ):
            import json as _json

            _session_ttl = 1800  # 30 min idle TTL per page thread
            await self.hot_memory.set(
                f"foundry_session:{session_id}",
                _json.dumps(result["_foundry_session_state"]),
                ttl_seconds=_session_ttl,
            )

        return result

    async def invoke_model_stream(
        self,
        request: dict[str, Any],
        messages: Any,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Streaming counterpart of ``invoke_model``.

        Yields text token chunks from the underlying model invoker.
        Falls back to a single-yield non-streaming call when the invoker
        does not support the ``StreamingModelInvoker`` protocol.

        Pattern: Strategy — delegates to the invoker's ``invoke_stream``
        when available, otherwise falls back to the non-streaming path.
        """
        payload_tools = kwargs.get("tools") or (self.tools if self.tools else None)
        messages = sanitize_messages_for_provider(
            messages,
            provider=self._shared_provider_for_routing(),
            enforce_prompt_governance=self.enforce_foundry_prompt_governance,
        )

        # Use SLM when available (matches provider_controlled path)
        target = self.slm or self.llm
        if target is None:
            raise RuntimeError("No models configured on BaseRetailAgent")

        self._trace_decision(
            decision="invoke_model_stream",
            outcome="start",
            metadata={
                "target": target.name,
                "supports_streaming": _supports_streaming(target.invoker),
            },
        )

        if not _supports_streaming(target.invoker):
            # Graceful degradation: yield the complete non-streaming response
            # as a single text chunk so callers always get an async generator.
            self._trace_decision(
                decision="invoke_model_stream",
                outcome="fallback_non_streaming",
                metadata={"target": target.name},
            )
            result = await self.invoke_model(request, messages, **kwargs)
            text = _extract_text_from_response(result)
            if text:
                yield text
            return

        payload = {
            **kwargs,
            "messages": messages,
            "model": target.model,
            "temperature": target.temperature,
            "top_p": target.top_p,
            "stream": True,
            "tools": payload_tools,
        }

        # __call__ with stream=True returns an AsyncGenerator
        stream_gen = await target.invoker(**payload)
        async for chunk in stream_gen:
            yield chunk

    @abstractmethod
    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle an incoming request."""
