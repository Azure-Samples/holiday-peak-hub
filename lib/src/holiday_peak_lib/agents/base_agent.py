"""Base agent abstraction with model selection and SDK integration points."""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Awaitable, Callable

try:
    from agent_framework import BaseAgent
except Exception:

    class BaseAgent:  # type: ignore[too-many-ancestors]
        """Fallback base to keep local/test imports resilient.

        Some CI environments can transiently resolve incompatible transitive
        observability dependencies for `agent_framework`, causing import-time
        failures before tests can run. This shim preserves importability for
        framework-independent tests.
        """

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            _ = args
            _ = kwargs


from holiday_peak_lib.utils.telemetry import get_foundry_tracer
from pydantic import BaseModel, ConfigDict, Field

from .provider_policy import (
    sanitize_messages_for_provider,
    should_use_local_routing_prompt,
)

ModelInvoker = Callable[..., Awaitable[dict[str, Any]]]

UPGRADE_TOKEN = "upgrade"


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
    memory_client: Any = None
    hot_memory: Any = None
    warm_memory: Any = None
    cold_memory: Any = None
    mcp_server: Any = None
    self_healing_kernel: Any = None
    slm: ModelTarget | None = None
    llm: ModelTarget | None = None
    complexity_threshold: float = 0.5
    enforce_foundry_prompt_governance: bool = True


class BaseRetailAgent(BaseAgent, ABC):
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

    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attribute access to the underlying config object.

        This reduces the need for repetitive property definitions that simply
        forward to ``self.config`` while preserving a flat attribute surface.
        """
        # Avoid recursion during initialization or when _config is missing
        config = self.__dict__.get("_config", None)
        if config is not None and hasattr(config, name):
            return getattr(config, name)
        raise AttributeError(f"{type(self).__name__!r} object has no attribute {name!r}")

    def __setattr__(self, name: str, value: Any) -> None:
        """Delegate setting unknown attributes to the config when appropriate.

        Core attributes and private names are always set on the instance itself.
        """
        if name in {"_config", "config"} or name.startswith("_"):
            super().__setattr__(name, value)
            return

        # If the attribute already exists on the instance, set it here
        if name in self.__dict__ or any(name in cls.__dict__ for cls in type(self).__mro__):
            super().__setattr__(name, value)
            return

        # Otherwise, try to set it on the config object if possible
        config = self.__dict__.get("_config", None)
        if config is not None and hasattr(config, name):
            setattr(config, name, value)
        else:
            # Fallback: create a normal attribute on the instance
            super().__setattr__(name, value)

    @property
    def router(self) -> Any | None:
        return self.config.router

    @router.setter
    def router(self, value: Any | None) -> None:
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
    def memory_client(self) -> Any:
        return self.config.memory_client

    @memory_client.setter
    def memory_client(self, value: Any) -> None:
        self.config.memory_client = value

    @property
    def hot_memory(self) -> Any:
        return self.config.hot_memory

    @hot_memory.setter
    def hot_memory(self, value: Any) -> None:
        self.config.hot_memory = value

    @property
    def warm_memory(self) -> Any:
        return self.config.warm_memory

    @warm_memory.setter
    def warm_memory(self, value: Any) -> None:
        self.config.warm_memory = value

    @property
    def cold_memory(self) -> Any:
        return self.config.cold_memory

    @cold_memory.setter
    def cold_memory(self, value: Any) -> None:
        self.config.cold_memory = value

    @property
    def mcp_server(self) -> Any:
        return self.config.mcp_server

    @mcp_server.setter
    def mcp_server(self, value: Any) -> None:
        self.config.mcp_server = value

    @property
    def self_healing_kernel(self) -> Any:
        return self.config.self_healing_kernel

    @self_healing_kernel.setter
    def self_healing_kernel(self, value: Any) -> None:
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

    def attach_memory(self, hot: Any, warm: Any, cold: Any) -> None:
        self.hot_memory = hot
        self.warm_memory = warm
        self.cold_memory = cold

    def attach_mcp(self, mcp_server: Any) -> None:
        self.mcp_server = mcp_server

    def attach_self_healing(self, self_healing_kernel: Any) -> None:
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

    def _get_foundry_tracer(self):
        service = self.service_name or type(self).__name__
        return get_foundry_tracer(service)

    def _trace_decision(self, decision: str, outcome: str, metadata: dict[str, Any]) -> None:
        try:
            self._get_foundry_tracer().trace_decision(
                decision=decision,
                outcome=outcome,
                metadata=metadata,
            )
        except (AttributeError, TypeError, ValueError, RuntimeError):
            return

    def _trace_tools(self, payload_tools: Any, outcome: str, metadata: dict[str, Any]) -> None:
        tool_names: list[str] = []
        if isinstance(payload_tools, dict):
            tool_names = [str(name) for name in payload_tools.keys()]
        elif isinstance(payload_tools, (list, tuple, set)):
            tool_names = [str(name) for name in payload_tools]
        elif payload_tools is not None:
            tool_names = [str(payload_tools)]

        if not tool_names:
            return

        tracer = self._get_foundry_tracer()
        for tool_name in tool_names:
            try:
                tracer.trace_tool_call(
                    tool_name=tool_name,
                    outcome=outcome,
                    metadata=metadata,
                )
            except (AttributeError, TypeError, ValueError, RuntimeError):
                continue

    def _assess_complexity(self, request: dict[str, Any]) -> float:
        """Crude complexity heuristic using token-ish count and tool hints.

        Returns a float in [0, 1]; higher means more complex and should route to LLM.
        """

        text = str(request.get("query") or request)
        word_score = min(len(text.split()) / 50.0, 1.0)
        tool_score = 0.2 if request.get("requires_multi_tool") else 0.0
        return min(word_score + tool_score, 1.0)

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
            "stream": kwargs.get("stream", target.stream),
            "tools": payload_tools,
        }
        started = perf_counter()
        outcome = "success"
        error_text: str | None = None
        try:
            result = await target.invoker(**payload)
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

        if self.slm and self.llm:
            return await self._evaluate_with_slm_routing(request, messages, payload_tools, **kwargs)

        return await self._direct_model_selection(request, messages, payload_tools, **kwargs)

    async def _evaluate_with_slm_routing(
        self,
        request: dict[str, Any],
        messages: Any,
        payload_tools: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evaluate request complexity with SLM and optionally upgrade to LLM."""

        if self.slm is None:
            raise RuntimeError("SLM target is required for routed model evaluation")

        if not should_use_local_routing_prompt(
            provider=self._shared_provider_for_routing(),
            enforce_prompt_governance=self.enforce_foundry_prompt_governance,
        ):
            self._trace_decision(
                decision="routing_strategy",
                outcome="provider_controlled",
                metadata={"enforce_prompt_governance": self.enforce_foundry_prompt_governance},
            )
            slm_result = await self.__invoke_target(self.slm, messages, payload_tools, **kwargs)
            if self.llm and self._assess_complexity(request) >= self.complexity_threshold:
                self._trace_decision(
                    decision="model_upgrade",
                    outcome="llm_by_complexity",
                    metadata={"complexity_threshold": self.complexity_threshold},
                )
                return await self.__invoke_target(self.llm, messages, payload_tools, **kwargs)
            return slm_result

        evaluation_prompt = (
            "Evaluate this request and identify the complexity. If the complexity is higher than "
            "medium, that is, if the request contains more than 2 steps to be fulfilled and needs "
            "different sources to be understood and processed, return a single word 'upgrade'.\n\n"
            f"Request: {request}"
        )
        evaluation_result = await self.__invoke_target(
            self.slm, evaluation_prompt, payload_tools, **kwargs
        )
        evaluation_text = ""
        if isinstance(evaluation_result, dict):
            evaluation_text = str(
                evaluation_result.get("response")
                or evaluation_result.get("content")
                or evaluation_result.get("message")
                or evaluation_result
            )

        if evaluation_text.strip().lower() == UPGRADE_TOKEN:
            if self.llm is None:
                raise RuntimeError("LLM target is required for model upgrade")
            self._trace_decision(
                decision="model_upgrade",
                outcome="llm_by_slm_upgrade",
                metadata={"upgrade_token": UPGRADE_TOKEN},
            )
            if isinstance(messages, list):
                upgraded_messages = [
                    {
                        "role": "system",
                        "content": "You must reason on the request before proceeding with the response.",
                    },
                    *messages,
                ]
            elif isinstance(messages, dict):
                upgraded_messages = [
                    {
                        "role": "system",
                        "content": "You must reason on the request before proceeding with the response.",
                    },
                    messages,
                ]
            else:
                upgraded_messages = (
                    "You must reason on the request before proceeding with the response.\n\n"
                    + str(messages)
                )
            return await self.__invoke_target(self.llm, upgraded_messages, payload_tools, **kwargs)

        self._trace_decision(
            decision="model_selection",
            outcome="slm",
            metadata={"reason": "no_upgrade"},
        )
        return await self.__invoke_target(self.slm, messages, payload_tools, **kwargs)

    async def _direct_model_selection(
        self,
        request: dict[str, Any],
        messages: Any,
        payload_tools: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Fallback path when SLM/LLM combo is not available: select a single model and invoke it."""

        target = self._select_model(request)
        self._trace_decision(
            decision="model_selection",
            outcome=target.name,
            metadata={"mode": "direct"},
        )
        return await self.__invoke_target(target, messages, payload_tools, **kwargs)

    @abstractmethod
    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle an incoming request."""
