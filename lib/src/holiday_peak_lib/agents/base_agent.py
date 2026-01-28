"""Base agent abstraction with model selection and SDK integration points."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Awaitable, Callable
from time import perf_counter

from agent_framework import BaseAgent
from pydantic import BaseModel, ConfigDict, Field


ModelInvoker = Callable[..., Awaitable[dict[str, Any]]]


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


class AgentDependencies(BaseModel):
    """Dependency container for DI via property/setter."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    router: Any | None = None
    tools: dict[str, Callable[..., Any]] = Field(default_factory=dict)
    service_name: str | None = None
    hot_memory: Any = None
    warm_memory: Any = None
    cold_memory: Any = None
    mcp_server: Any = None
    slm: ModelTarget | None = None
    llm: ModelTarget | None = None
    complexity_threshold: float = 0.5


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
        self._config = config

    @property
    def config(self) -> AgentDependencies:
        return self._config

    @config.setter
    def config(self, deps: AgentDependencies) -> None:
        self._config = deps

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

    def attach_memory(self, hot: Any, warm: Any, cold: Any) -> None:
        self.hot_memory = hot
        self.warm_memory = warm
        self.cold_memory = cold

    def attach_mcp(self, mcp_server: Any) -> None:
        self.mcp_server = mcp_server

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
        return self.llm  # type: ignore[return-value]

    async def invoke_model(self, request: dict[str, Any], messages: Any, **kwargs: Any) -> dict[str, Any]:
        """Invoke the selected model via its SDK-specific invoker.

        ``messages`` is SDK-dependent (chat messages list, prompt string, etc.).
        Additional kwargs are forwarded to the invoker (e.g., tools, metadata).
        """

        target = self._select_model(request)
        payload_tools = kwargs.get("tools") or (self.tools if self.tools else None)
        payload = {
            **kwargs,
            "messages": messages,
            "model": target.model,
            "temperature": target.temperature,
            "top_p": target.top_p,
            "stream": kwargs.get("stream", target.stream),
            "tools": payload_tools,
        }
        started = perf_counter()
        result = await target.invoker(**payload)
        elapsed_ms = (perf_counter() - started) * 1000

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
                "tools": existing_meta.get("tools", list(payload_tools.keys()) if isinstance(payload_tools, dict) else payload_tools),
            }

            result.setdefault("_target", target.name)
            result.setdefault("_model", target.model)
            result["_telemetry"] = telemetry

        return result

    @abstractmethod
    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle an incoming request."""
