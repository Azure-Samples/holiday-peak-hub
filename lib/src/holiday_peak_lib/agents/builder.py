"""Agent builder using a simple Builder pattern."""

from typing import Any, Callable

from holiday_peak_lib.evaluation.models import EvalConfig
from holiday_peak_lib.mcp.server import FastAPIMCPServer

from .base_agent import AgentDependencies, BaseRetailAgent, ModelTarget
from .direct import ChatClientFactory, build_direct_model_target
from .foundry import FoundryAgentConfig
from .memory.builder import MemoryBuilder
from .memory.cold import ColdMemory
from .memory.hot import HotMemory
from .memory.warm import WarmMemory
from .orchestration.router import RoutingStrategy


class AgentBuilder:
    """Fluent builder to assemble an agent with memory and routing."""

    def __init__(self) -> None:
        self._agent_class: type[BaseRetailAgent] | None = None
        self._router: RoutingStrategy | None = None
        self._hot_memory: HotMemory | None = None
        self._warm_memory: WarmMemory | None = None
        self._cold_memory: ColdMemory | None = None
        self._memory_builder: MemoryBuilder | None = None
        self._mcp_server: FastAPIMCPServer | None = None
        self._self_healing_kernel: Any = None
        self._tools: dict[str, Callable[..., Any]] = {}
        self._slm: ModelTarget | None = None
        self._llm: ModelTarget | None = None
        self._complexity_threshold = 0.5
        self._evaluation_config: EvalConfig | None = None

    def with_agent(self, agent_class: type[BaseRetailAgent]) -> "AgentBuilder":
        self._agent_class = agent_class
        return self

    def with_router(self, router: RoutingStrategy) -> "AgentBuilder":
        self._router = router
        return self

    def with_memory(
        self,
        hot: HotMemory | None,
        warm: WarmMemory | None,
        cold: ColdMemory | None,
    ) -> "AgentBuilder":
        self._hot_memory = hot
        self._warm_memory = warm
        self._cold_memory = cold
        return self

    def with_memory_builder(self, memory_builder: MemoryBuilder) -> "AgentBuilder":
        self._memory_builder = memory_builder
        return self

    def with_mcp(self, mcp_server: FastAPIMCPServer) -> "AgentBuilder":
        self._mcp_server = mcp_server
        return self

    def with_self_healing(self, self_healing_kernel: Any) -> "AgentBuilder":
        self._self_healing_kernel = self_healing_kernel
        return self

    def with_tool(self, name: str, handler: Callable[..., Any]) -> "AgentBuilder":
        self._tools[name] = handler
        return self

    def with_tools(self, tools: dict[str, Callable[..., Any]]) -> "AgentBuilder":
        self._tools.update(tools)
        return self

    def with_evaluation(self, config: EvalConfig) -> "AgentBuilder":
        self._evaluation_config = config
        return self

    def with_models(
        self,
        *,
        slm: ModelTarget | None = None,
        llm: ModelTarget | None = None,
        complexity_threshold: float = 0.5,
    ) -> "AgentBuilder":
        self._slm = slm
        self._llm = llm
        self._complexity_threshold = complexity_threshold
        return self

    def with_direct_models(
        self,
        *,
        instructions: str,
        slm_config: FoundryAgentConfig | None = None,
        llm_config: FoundryAgentConfig | None = None,
        complexity_threshold: float = 0.5,
        chat_client_factory: ChatClientFactory | None = None,
    ) -> "AgentBuilder":
        """Configure direct-model targets for SLM/LLM via MAF ``Agent``.

        Sibling of :meth:`with_foundry_models` implementing the *Mandatory MAF
        Invocation Policy* amendment to ADR-005 (2026-05-10). The MAF ``Agent``
        is constructed in-process from ``instructions`` and the registered
        callable tools — no portal-managed Foundry Agent record is required.

        :param instructions: Persona/role text loaded from
            ``apps/<service>/prompts/instructions.md``. Identical for SLM and
            LLM targets (same agent persona; different model deployment).
        :param slm_config: Foundry config carrying the fast deployment name.
        :param llm_config: Foundry config carrying the rich deployment name.
        :param complexity_threshold: Routing threshold passed to
            :class:`AgentDependencies`.
        :param chat_client_factory: Optional override for the underlying
            ``ChatClient``. Defaults to ``FoundryChatClient`` (Foundry
            Responses API). Pass an alternate factory to use OpenAI,
            Azure OpenAI, or any other provider that satisfies MAF's
            ``SupportsChatGetResponse`` protocol.
        """

        # Tools registered via ``with_tool``/``with_tools`` are forwarded to
        # the in-process MAF ``Agent`` so native function-calling works.
        runtime_tools = list(self._tools.values()) if self._tools else None

        self._slm = (
            build_direct_model_target(
                slm_config,
                instructions=instructions,
                tools=runtime_tools,
                chat_client_factory=chat_client_factory,
            )
            if slm_config
            else None
        )
        self._llm = (
            build_direct_model_target(
                llm_config,
                instructions=instructions,
                tools=runtime_tools,
                chat_client_factory=chat_client_factory,
            )
            if llm_config
            else None
        )
        self._complexity_threshold = complexity_threshold
        return self

    def build(self) -> BaseRetailAgent:
        if not self._agent_class:
            raise ValueError("Agent class is required")
        if not self._slm and not self._llm:
            import logging

            logging.getLogger("holiday_peak_lib.agents.builder").warning(
                "No model target configured — agent starts in degraded mode"
            )
        deps = AgentDependencies(
            router=self._router or RoutingStrategy(),
            tools=self._tools,
            self_healing_kernel=self._self_healing_kernel,
            slm=self._slm,
            llm=self._llm,
            complexity_threshold=self._complexity_threshold,
            evaluation_config=self._evaluation_config,
        )
        agent = self._agent_class(config=deps)
        if self._memory_builder:
            if any([self._hot_memory, self._warm_memory, self._cold_memory]):
                self._memory_builder.with_hot(self._hot_memory).with_warm(
                    self._warm_memory
                ).with_cold(self._cold_memory)
            memory_client = self._memory_builder.build()
            agent.memory_client = memory_client
            agent.attach_memory(memory_client.hot, memory_client.warm, memory_client.cold)
        elif any([self._hot_memory, self._warm_memory, self._cold_memory]):
            agent.attach_memory(self._hot_memory, self._warm_memory, self._cold_memory)
        if self._mcp_server:
            agent.attach_mcp(self._mcp_server)
        if self._self_healing_kernel is not None:
            agent.attach_self_healing(self._self_healing_kernel)
        return agent
