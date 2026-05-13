"""Base agent abstraction with model selection and SDK integration points."""

import asyncio
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from time import perf_counter
from typing import Any, AsyncGenerator, Awaitable, Callable, cast

logger = logging.getLogger(__name__)

from agent_framework import BaseAgent
from holiday_peak_lib.agents.complexity import (
    UPGRADE_SENTINEL,
    assess_complexity,
    build_complexity_hint,
)

# Runtime imports for Pydantic model field resolution.
# Circular-import safe: none of these modules import base_agent.
from holiday_peak_lib.agents.memory.builder import MemoryClient
from holiday_peak_lib.agents.memory.cold import ColdMemory
from holiday_peak_lib.agents.memory.hot import HotMemory
from holiday_peak_lib.agents.memory.session_manager import (
    build_session_summary,
    persist_full_session,
    store_summary,
)
from holiday_peak_lib.agents.memory.warm import WarmMemory
from holiday_peak_lib.agents.orchestration.router import RoutingStrategy
from holiday_peak_lib.agents.telemetry_mixin import AgentTelemetryMixin
from holiday_peak_lib.mcp.server import FastAPIMCPServer
from holiday_peak_lib.self_healing import SelfHealingKernel
from pydantic import BaseModel, ConfigDict, Field

from .models import (
    ModelInvoker,
    ModelTarget,
    StreamingModelInvoker,
    build_logprobs_payload,
    extract_logprobs,
    extract_text_from_response,
    summarize_logprobs,
    supports_streaming,
)
from .provider_policy import normalize_messages, sanitize_messages_for_provider

# Public re-exports kept for module-level imports such as
# ``from holiday_peak_lib.agents.base_agent import ModelTarget`` that exist
# in older test fixtures. New code should import from ``.models`` directly
# or from the ``holiday_peak_lib.agents`` package re-export.
__all__ = [
    "AgentDependencies",
    "BaseRetailAgent",
    "ModelInvoker",
    "ModelTarget",
    "StreamingModelInvoker",
]

_DEFAULT_AGENT_INVOKE_TIMEOUT = float(os.getenv("AGENT_INVOKE_TIMEOUT_SECONDS", "90"))


class AgentDependencies(BaseModel):
    """Construction-time DTO for :class:`BaseRetailAgent`.

    Pydantic validates the shape once at build time. The agent then unpacks
    the values into its own instance attributes in ``__init__`` and *does
    not retain a reference* to this object — every subsequent access
    (``agent.slm``, ``agent.hot_memory``, …) is a single dict lookup, not a
    forwarded read through a descriptor or property.

    Infrastructure-shaped fields are typed ``Any | None`` so test code can
    construct dependencies with ``unittest.mock.AsyncMock`` without
    triggering ``isinstance`` validation under
    ``arbitrary_types_allowed=True``. The *real* static types live on the
    matching class-level annotations of :class:`BaseRetailAgent`, where
    Pyright/mypy enforce them at every read/write site.
    """

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


@dataclass(frozen=True, slots=True)
class _RoutingContext:
    """Bundled outputs of the routing decision for one invocation.

    Computing complexity and selecting a target are each cheap, but the
    framework needs both values at three different points (selection,
    tracing, hint construction). Bundling them eliminates the previous
    double-call to :func:`assess_complexity` and gives the streaming and
    non-streaming paths a single, typed handoff between routing and
    invocation.

    ``supports_upgrade`` is the truth-in-advertising bit: when ``True``
    the SLM hint promises an UPGRADE channel and the runtime must honor
    it. Streaming sets it ``False`` (no buffering, no mid-stream
    detection) and configurations with no LLM target leave it ``False``
    too (nowhere to escalate to).
    """

    target: ModelTarget
    complexity: float
    target_tier: str  # ``"slm"`` or ``"llm"``
    hint: str
    supports_upgrade: bool


class BaseRetailAgent(AgentTelemetryMixin, BaseAgent, ABC):
    """Common ingestion, routing, memory ops, and model selection.

    Configure two model targets (SLM/LLM or fast/slow) and the agent will choose
    based on a lightweight complexity heuristic. Pass SDK-specific invokers to
    keep this layer decoupled from the transport implementation.

    Dependencies arrive as an :class:`AgentDependencies` DTO and are unpacked
    into plain instance attributes — no property/descriptor indirection.
    Static types come from the class-level annotations below; Pyright/mypy
    use them for inference and they cost nothing at runtime.
    """

    # ------------------------------------------------------------------ #
    # Static type annotations for the dependency attributes.
    #
    # These are *type-only* declarations — they have no runtime values
    # (no ``= ...`` here). Concrete values are bound per-instance in
    # ``__init__``. Type checkers read these annotations to type
    # ``agent.hot_memory`` as ``HotMemory | None`` (etc.), even though
    # the underlying Pydantic field is ``Any | None`` for mock-friendliness.
    # ------------------------------------------------------------------ #
    router: RoutingStrategy | None
    tools: dict[str, Callable[..., Any]]
    service_name: str | None
    memory_client: MemoryClient | None
    hot_memory: HotMemory | None
    warm_memory: WarmMemory | None
    cold_memory: ColdMemory | None
    mcp_server: FastAPIMCPServer | None
    self_healing_kernel: SelfHealingKernel | None
    slm: ModelTarget | None
    llm: ModelTarget | None
    complexity_threshold: float
    enforce_foundry_prompt_governance: bool

    def __init__(self, config: AgentDependencies, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Unpack the DTO into plain instance attributes. After this the
        # ``config`` object is no longer referenced — there is nothing to
        # forward to and no per-access overhead beyond a normal attribute
        # lookup.
        self.router = config.router
        self.tools = config.tools
        self.service_name = config.service_name
        self.memory_client = config.memory_client
        self.hot_memory = config.hot_memory
        self.warm_memory = config.warm_memory
        self.cold_memory = config.cold_memory
        self.mcp_server = config.mcp_server
        self.self_healing_kernel = config.self_healing_kernel
        self.slm = config.slm
        self.llm = config.llm
        self.complexity_threshold = config.complexity_threshold
        self.enforce_foundry_prompt_governance = config.enforce_foundry_prompt_governance
        # Background task set for fire-and-forget memory operations.
        # Each agent is a stateful, long-lived object — tasks persist
        # across requests and are garbage-collected on completion.
        self._background_tasks: set[asyncio.Task[None]] = set()

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

    def _schedule_background(self, coro: Awaitable[None]) -> None:
        """Schedule a fire-and-forget background task for memory operations.

        The agent is a stateful long-lived object; background tasks run
        independently of the request path so memory persistence never
        impacts response latency.  Completed tasks are auto-removed via
        a done callback.
        """
        task = asyncio.ensure_future(coro)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    def background_cache_write(
        self, cache_key: str | None, value: Any, *, ttl_seconds: int = 300
    ) -> None:
        """Schedule a cache write as a background task (non-blocking).

        Agents call this instead of ``await cache_write(...)`` to return
        the response immediately while the Redis write completes in the
        background.
        """
        # Bind the narrowed reference *before* the closure: type-narrowing
        # from ``self.hot_memory is None`` is not preserved across closure
        # boundaries, so without this rebind the inner ``hot.set`` would be
        # statically typed as a method on ``Optional[HotMemory]`` and a future
        # contributor breaking the outer guard would only see the failure at
        # runtime. Capturing the narrowed local makes it impossible.
        hot = self.hot_memory
        if hot is None or cache_key is None or value is None:
            return

        async def _write() -> None:
            await hot.set(key=cache_key, value=value, ttl_seconds=ttl_seconds)

        self._schedule_background(_write())

    def memory_tool_definitions(self) -> dict[str, Callable[..., Any]]:
        """Return memory read/write as LLM-callable tool definitions.

        These tools allow the model to manage session/conversation memory
        directly, enabling a 'check memory first' strategy before deeper searches.
        """
        client = self.memory_client
        tools: dict[str, Callable[..., Any]] = {}
        if client is None:
            return tools

        async def memory_read(key: str) -> Any:
            """Read a value from the agent's tiered memory by key."""
            return await client.get(key)

        async def memory_write(key: str, value: Any) -> str:
            """Write a value to the agent's tiered memory."""
            await client.set(key, value)
            return "stored"

        tools["memory_read"] = memory_read
        tools["memory_write"] = memory_write
        return tools

    @staticmethod
    async def gather_adapters(*coros: Awaitable[Any]) -> list[Any]:
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

    def _select_model(
        self,
        request: dict[str, Any],
        *,
        complexity: float | None = None,
    ) -> ModelTarget:
        """Select SLM vs LLM based on heuristic and configuration.

        ``complexity`` is accepted as a keyword so callers that have
        already evaluated the heuristic (typically inside
        :meth:`_resolve_routing_context`) can hand the value in instead
        of paying for the work twice. When omitted, the heuristic runs
        on demand — preserving the public signature relied upon by
        existing tests.
        """

        if self.slm is None and self.llm is None:
            raise RuntimeError("No models configured on BaseRetailAgent")

        if complexity is None:
            complexity = self._assess_complexity(request)
        if self.llm and (complexity >= self.complexity_threshold or self.slm is None):
            return self.llm
        if self.slm:
            return self.slm
        if self.llm is not None:
            return self.llm
        # Defensive check: should not be reachable because of the initial guard.
        raise RuntimeError("Model selection failed: no suitable model available")

    def _make_routing_context(
        self,
        target: ModelTarget,
        complexity: float,
        *,
        supports_upgrade: bool = False,
    ) -> _RoutingContext:
        """Build a :class:`_RoutingContext` for an already-picked target.

        Factoring the tier-detection + hint-build pair here keeps the
        two callers (request/response and streaming) free of duplicated
        plumbing while preserving a single source of truth for how the
        ``target_tier`` label and the upgrade-capability bit are
        derived. ``supports_upgrade`` only takes effect for the SLM
        tier *and* when an LLM target exists — there is no point
        promising an upgrade channel the runtime can't follow through
        on.
        """
        tier = "slm" if target is self.slm else "llm"
        can_upgrade = supports_upgrade and tier == "slm" and self.llm is not None
        hint = build_complexity_hint(
            complexity=complexity,
            threshold=self.complexity_threshold,
            target_kind=tier,
            can_upgrade=can_upgrade,
        )
        return _RoutingContext(
            target=target,
            complexity=complexity,
            target_tier=tier,
            hint=hint,
            supports_upgrade=can_upgrade,
        )

    def _resolve_routing_context(self, request: dict[str, Any]) -> _RoutingContext:
        """Resolve target + complexity + hint for a request/response call.

        Computes the complexity score *once* and threads it into both
        :meth:`_select_model` (for the SLM/LLM decision) and the hint
        builder. Downstream tracing reads from the returned context, so
        ``_assess_complexity`` is never called more than once per
        invocation. The non-streaming path advertises the upgrade
        channel so :meth:`invoke_model` can act on an SLM-initiated
        ``UPGRADE`` reply.
        """
        complexity = self._assess_complexity(request)
        target = self._select_model(request, complexity=complexity)
        return self._make_routing_context(target, complexity, supports_upgrade=True)

    def _resolve_streaming_routing_context(self, request: dict[str, Any]) -> _RoutingContext:
        """Routing context for the streaming path (SLM-first, no escalation).

        :meth:`invoke_model_stream` always targets the SLM when one is
        configured; complexity-based escalation belongs to the
        request/response path. We still compute complexity so the model
        receives the same tier-framed hint as the non-streaming flow,
        but the upgrade clause is suppressed — the runtime cannot
        introspect a streamed reply without buffering, so we don't
        advertise a channel we can't honor.
        """
        target = self.slm or self.llm
        if target is None:
            raise RuntimeError("No models configured on BaseRetailAgent")
        complexity = self._assess_complexity(request)
        return self._make_routing_context(target, complexity, supports_upgrade=False)

    @staticmethod
    def _inject_routing_hint(messages: list[dict[str, Any]], hint: str) -> list[dict[str, Any]]:
        """Insert a system-role hint after the leading system prefix.

        The caller's persona prompt (typically at index 0) stays first
        — most providers weight the leading system message highest —
        and the routing context slides in immediately after it, before
        the conversation turns. For inputs that have no system prefix
        the hint becomes the first system message.
        """
        insert_at = 0
        for msg in messages:
            if isinstance(msg, dict) and str(msg.get("role", "")).lower() == "system":
                insert_at += 1
            else:
                break
        return [
            *messages[:insert_at],
            {"role": "system", "content": hint},
            *messages[insert_at:],
        ]

    def _apply_routing_context(
        self,
        messages: Any,
        kwargs: dict[str, Any],
        ctx: _RoutingContext,
    ) -> list[dict[str, Any]]:
        """Surface routing metadata to the invoker via both channels.

        * **kwargs channel** — ``routing_complexity`` / ``routing_threshold``
          / ``routing_target_tier`` / ``routing_hint`` are mutated onto
          the kwargs dict and reach every invoker unconditionally. This
          is the canonical channel: Foundry hosted-agent adapters that
          cannot accept runtime system messages still get the data and
          can plumb it through their portal-owned prompt.
        * **system-message channel** — the hint is inserted after the
          leading system prefix as a best-effort surface. It reaches
          non-Foundry providers directly; under Foundry governance the
          subsequent :func:`sanitize_messages_for_provider` call strips
          it, which is the right outcome (Foundry owns the prompt) and
          matches the kwargs channel's role as the source of truth.
        """
        kwargs["routing_complexity"] = ctx.complexity
        kwargs["routing_threshold"] = self.complexity_threshold
        kwargs["routing_target_tier"] = ctx.target_tier
        kwargs["routing_hint"] = ctx.hint
        return self._inject_routing_hint(normalize_messages(messages), ctx.hint)

    @staticmethod
    def _response_requests_upgrade(result: Any) -> bool:
        """Return ``True`` when the SLM's reply asks for runtime escalation.

        The SLM hint instructs the model to reply with the single token
        :data:`UPGRADE_SENTINEL` on its own line when it cannot handle
        the request. Detecting that is annoyingly shape-sensitive
        because different invokers return different envelopes — the
        Foundry-shaped ``messages[].content[].text`` structure read by
        :func:`extract_text_from_response`, but also flat ``response`` /
        ``content`` / ``text`` / ``output`` keys used by simpler
        adapters and test mocks. We probe all of them and treat a match
        as authoritative when the sentinel is the first non-blank line
        (so a passing mention like ``"I will upgrade my answer"`` does
        not trigger escalation).
        """
        if not isinstance(result, dict):
            return False
        candidates: list[str] = []
        structured = extract_text_from_response(result)
        if structured:
            candidates.append(structured)
        for key in ("response", "content", "text", "output"):
            value = result.get(key)
            if isinstance(value, str) and value:
                candidates.append(value)
        for text in candidates:
            stripped = text.strip()
            if not stripped:
                continue
            first_line = stripped.splitlines()[0].strip().upper()
            if first_line == UPGRADE_SENTINEL:
                return True
        return False

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
            "tools": payload_tools,
        }
        for key, value in build_logprobs_payload(target).items():
            if key == "include" and isinstance(payload.get("include"), list):
                existing = list(payload["include"])
                for token in value:
                    if token not in existing:
                        existing.append(token)
                payload["include"] = existing
            else:
                payload[key] = value
        started = perf_counter()
        outcome = "success"
        error_text: str | None = None
        logprob_summary: dict[str, Any] | None = None
        try:
            result = await target.invoker(**payload)
            if target.logprobs and isinstance(result, dict):
                logprob_summary = summarize_logprobs(extract_logprobs(result))
                mean_str = f"{logprob_summary['mean']:.4f}" if "mean" in logprob_summary else "n/a"
                perplexity_str = (
                    f"{logprob_summary['perplexity']:.4f}"
                    if "perplexity" in logprob_summary
                    else "n/a"
                )
                logger.info(
                    "agent_model_logprobs service=%s target=%s count=%d " "mean=%s perplexity=%s",
                    getattr(self, "service_name", "unknown"),
                    target.name,
                    logprob_summary.get("count", 0),
                    mean_str,
                    perplexity_str,
                )
        except asyncio.TimeoutError:
            outcome = "timeout"
            error_text = "Model invocation timed out"
            logger.error(
                "agent_model_invocation_timeout service=%s model=%s",
                getattr(self, "service_name", "unknown"),
                target.model,
            )
            raise
        except Exception as exc:
            outcome = "error"
            error_text = str(exc)
            logger.error(
                "agent_model_invocation_failed service=%s model=%s error=%s",
                getattr(self, "service_name", "unknown"),
                target.model,
                exc,
                exc_info=True,
            )
            raise
        finally:
            elapsed_ms = (perf_counter() - started) * 1000
            trace_metadata = {
                "elapsed_ms": elapsed_ms,
                # ``__invoke_target`` is the non-streaming request/response
                # path; the streaming path bypasses it entirely. Hard-coding
                # the value keeps the telemetry column stable for downstream
                # dashboards while removing a pointless dynamic lookup.
                "stream": False,
                "temperature": target.temperature,
                "top_p": target.top_p,
                "error": error_text,
                "logprobs_summary": logprob_summary,
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
                "stream": existing_meta.get("stream", False),
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
                "logprobs_summary": existing_meta.get("logprobs_summary", logprob_summary),
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

        # Smart session continuity: decide whether to continue an existing
        # Foundry thread or start fresh based on Redis summary + keyword overlap.
        # Sessions are stored in Cosmos (warm) with IDs matching Foundry's;
        # Redis holds only a compact summary for fast decision-making.
        from holiday_peak_lib.agents.memory.session_manager import (
            evaluate_session_continuity,
        )

        session_id = request.get("session_id") if isinstance(request, dict) else None
        _session_entity_id = session_id  # Used for post-invocation persistence
        _session_decision = None

        if session_id and "session_id" not in kwargs:
            _session_decision = await evaluate_session_continuity(
                self.hot_memory,
                self.warm_memory,
                request,
                service=self.service_name or "default",
                entity_id=session_id,
            )
            kwargs["session_id"] = _session_decision.session_id
            if _session_decision.foundry_session_state:
                kwargs["_foundry_session_state"] = _session_decision.foundry_session_state

        # Resolve routing once (target + complexity + tier-framed hint),
        # then surface the result through both the messages and kwargs
        # channels before sanitisation. Doing it before the sanitiser
        # lets Foundry governance strip the system hint while leaving
        # the kwargs untouched — the adapter can still plumb the data
        # into the portal-owned prompt. We keep a handle on the original
        # caller-supplied messages so an SLM-initiated upgrade can
        # rebuild the LLM prompt from a clean slate.
        ctx = self._resolve_routing_context(request)
        original_messages = messages
        messages = self._apply_routing_context(messages, kwargs, ctx)
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
            self._trace_decision(
                decision="routing_strategy",
                outcome=ctx.target.name,
                metadata={
                    "complexity": ctx.complexity,
                    "complexity_threshold": self.complexity_threshold,
                    "target_tier": ctx.target_tier,
                },
            )
            result = await asyncio.wait_for(
                self.__invoke_target(ctx.target, messages, payload_tools, **kwargs),
                timeout=_DEFAULT_AGENT_INVOKE_TIMEOUT,
            )

            # SLM-initiated escalation: when the SLM replied with the
            # UPGRADE sentinel, re-route to the LLM with a fresh
            # routing context built from the *original* caller
            # messages. This is the second leg of the two-stage routing
            # story — the heuristic catches obvious cases up front,
            # this branch catches the borderline ones it underestimated.
            # We rebuild from ``original_messages`` (rather than mutating
            # the SLM-prepared list) so the LLM never sees the SLM hint;
            # the kwargs ``routing_*`` entries get overwritten by the
            # second ``_apply_routing_context`` call.
            if (
                ctx.supports_upgrade
                and self.llm is not None
                and self._response_requests_upgrade(result)
            ):
                llm_ctx = self._make_routing_context(
                    self.llm, ctx.complexity, supports_upgrade=False
                )
                self._trace_decision(
                    decision="slm_upgrade",
                    outcome=llm_ctx.target.name,
                    metadata={
                        "complexity": ctx.complexity,
                        "complexity_threshold": self.complexity_threshold,
                        "from": ctx.target.name,
                        "to": llm_ctx.target.name,
                    },
                )
                upgraded_messages = self._apply_routing_context(original_messages, kwargs, llm_ctx)
                upgraded_messages = sanitize_messages_for_provider(
                    upgraded_messages,
                    provider=self._shared_provider_for_routing(),
                    enforce_prompt_governance=self.enforce_foundry_prompt_governance,
                )
                result = await asyncio.wait_for(
                    self.__invoke_target(
                        llm_ctx.target,
                        upgraded_messages,
                        payload_tools,
                        **kwargs,
                    ),
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

        # Persist session: summary → Redis, full state → Cosmos (matching Foundry ID).
        # Runs as a background task so memory I/O never adds latency to the response.
        if (
            _session_decision is not None
            and isinstance(result, dict)
            and result.get("_foundry_session_state")
        ):
            _used_session_id = _session_decision.session_id
            _messages_for_summary = messages if isinstance(messages, list) else []

            summary = build_session_summary(
                session_id=_used_session_id,
                service=self.service_name or "default",
                entity_id=_session_entity_id or "",
                messages=_messages_for_summary,
                result=result,
                prior_summary=None,
            )

            async def _persist_session() -> None:
                await store_summary(self.hot_memory, summary, ttl_seconds=1800)
                await persist_full_session(
                    self.warm_memory,
                    session_id=_used_session_id,
                    service=self.service_name or "default",
                    entity_id=_session_entity_id or "",
                    foundry_session_state=result["_foundry_session_state"],
                    messages=_messages_for_summary,
                    summary_text=summary.summary_text,
                )

            self._schedule_background(_persist_session())

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

        # Pick the streaming target up-front so we can decide between
        # the streaming branch and the non-streaming fallback before
        # paying for routing-context construction. The fallback path
        # delegates to ``invoke_model``, which performs its own routing
        # apply — doing it here too would double-inject the hint.
        early_target = self.slm or self.llm
        if early_target is None:
            raise RuntimeError("No models configured on BaseRetailAgent")

        self._trace_decision(
            decision="invoke_model_stream",
            outcome="start",
            metadata={
                "target": early_target.name,
                "supports_streaming": supports_streaming(early_target.invoker),
            },
        )

        if not supports_streaming(early_target.invoker):
            # Graceful degradation: yield the complete non-streaming response
            # as a single text chunk so callers always get an async generator.
            self._trace_decision(
                decision="invoke_model_stream",
                outcome="fallback_non_streaming",
                metadata={"target": early_target.name},
            )
            result = await self.invoke_model(request, messages, **kwargs)
            text = extract_text_from_response(result)
            if text:
                yield text
            return

        ctx = self._resolve_streaming_routing_context(request)
        messages = self._apply_routing_context(messages, kwargs, ctx)
        messages = sanitize_messages_for_provider(
            messages,
            provider=self._shared_provider_for_routing(),
            enforce_prompt_governance=self.enforce_foundry_prompt_governance,
        )

        payload = {
            **kwargs,
            "messages": messages,
            "model": ctx.target.model,
            "temperature": ctx.target.temperature,
            "top_p": ctx.target.top_p,
            # ``stream=True`` is the dispatch signal for invokers that
            # branch on it (see ``direct.py``: ``kwargs.pop("stream", False)``
            # selects ``_stream_impl`` vs ``__call__``). Without it the
            # real adapter would return a non-streaming dict and break
            # the ``async for`` consumer below.
            "stream": True,
            "tools": payload_tools,
        }
        # Mirror the non-streaming logprob payload contract on the
        # streaming path so adapters that honour it (Responses API
        # streams emit logprobs on ``ResponseTextDoneEvent``) receive
        # the same request keys. Capture of streamed logprobs is
        # handled in the chunk loop — see the streaming pipeline work
        # in :meth:`invoke_model_stream`.
        for key, value in build_logprobs_payload(ctx.target).items():
            if key == "include" and isinstance(payload.get("include"), list):
                existing = list(payload["include"])
                for token in value:
                    if token not in existing:
                        existing.append(token)
                payload["include"] = existing
            else:
                payload[key] = value

        # ``__call__`` with ``stream=True`` returns an ``AsyncGenerator[str, None]``
        # (see ``StreamingModelInvoker._stream_impl``). The static
        # ``ModelInvoker`` signature only documents the non-streaming
        # ``Awaitable[dict]`` shape, so we cast here to express the
        # streaming-path contract without widening the public type alias
        # (which would ripple through every non-streaming caller).
        stream_gen = cast(
            AsyncGenerator[str, None],
            await ctx.target.invoker(**payload),
        )
        async for chunk in stream_gen:
            yield chunk

    @abstractmethod
    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle an incoming request."""

    # ------------------------------------------------------------------ #
    # Foundry hosted-agent (Responses API) integration
    #
    # These two methods let an existing FastAPI service additionally serve
    # the Foundry Responses-protocol surface (``/v1/responses``) inside the
    # *same* uvicorn process — no second runtime, no parallel ``hosted_main.py``,
    # no extra port. They are additive: services that don't call
    # ``serve_hosted()`` retain their current behaviour.
    # ------------------------------------------------------------------ #

    async def hosted_request_from_text(self, text: str) -> dict[str, Any]:
        """Translate Responses-API free-form input text into the dict shape
        that this agent's ``handle()`` expects.

        Default implementation returns ``{"prompt": text}``. Services whose
        ``handle()`` requires structured fields (e.g. ``{"sku": "..."}``)
        should override this to parse them out of natural-language input.
        """
        return {"prompt": text}

    def serve_hosted(
        self,
        fastapi_app: Any,
        *,
        prefix: str = "/v1",
        request_translator: Callable[[str], Awaitable[dict[str, Any]]] | None = None,
    ) -> Any:
        """Mount this agent's Foundry Responses-protocol endpoints on the
        given FastAPI app.

        Single-process, single-runtime: the FastAPI app keeps owning
        ``/health``, ``/ready``, ``/mcp/*`` (registered before this call) and
        the mounted Starlette host server answers ``/{prefix}/responses``
        (matched after the direct routes because Starlette walks routes in
        registration order).

        Returns the constructed host server for tests / diagnostics.
        Raises ``ImportError`` if ``agent-framework-foundry-hosting`` is not
        installed in the active environment.
        """
        # Lazy import to avoid a circular dependency between base_agent.py
        # and hosted.py, and to keep the optional SDK out of import time.
        from .hosted import mount_hosted_agent  # pylint: disable=import-outside-toplevel

        return mount_hosted_agent(
            fastapi_app,
            self,
            prefix=prefix,
            request_translator=request_translator,
        )

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Auto-wrap concrete handle() implementations with entry/exit logging."""
        super().__init_subclass__(**kwargs)
        original_handle = cls.__dict__.get("handle")
        if original_handle is None:
            return

        async def _logged_handle(self: Any, request: dict[str, Any]) -> dict[str, Any]:
            svc = getattr(self, "service_name", cls.__name__)
            logger.info("agent_handle_entry service=%s", svc)
            started = perf_counter()
            try:
                result = await original_handle(self, request)
                elapsed = (perf_counter() - started) * 1000
                logger.info(
                    "agent_handle_success service=%s elapsed_ms=%.1f",
                    svc,
                    elapsed,
                )
                return result
            except Exception as exc:
                elapsed = (perf_counter() - started) * 1000
                logger.error(
                    "agent_handle_failed service=%s elapsed_ms=%.1f error=%s",
                    svc,
                    elapsed,
                    exc,
                    exc_info=True,
                )
                raise

        _logged_handle.__name__ = "handle"
        _logged_handle.__qualname__ = f"{cls.__qualname__}.handle"
        cls.handle = _logged_handle  # type: ignore[method-assign]
