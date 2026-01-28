"""Agent builder using a simple Builder pattern."""
from typing import Any, Callable

from .base_agent import AgentDependencies, BaseRetailAgent, ModelTarget
from .foundry import FoundryAgentConfig, build_foundry_model_target
from .fastapi_mcp import FastAPIMCPServer
from .memory.hot import HotMemory
from .memory.warm import WarmMemory
from .memory.cold import ColdMemory
from .orchestration.router import RoutingStrategy


class AgentBuilder:
    """Fluent builder to assemble an agent with memory and routing."""

    def __init__(self) -> None:
        self._agent_class: type[BaseRetailAgent] | None = None
        self._router: RoutingStrategy | None = None
        self._hot_memory: HotMemory | None = None
        self._warm_memory: WarmMemory | None = None
        self._cold_memory: ColdMemory | None = None
        self._mcp_server: FastAPIMCPServer | None = None
        self._tools: dict[str, Callable[..., Any]] = {}
        self._slm: ModelTarget | None = None
        self._llm: ModelTarget | None = None
        self._complexity_threshold = 0.5

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

    def with_mcp(self, mcp_server: FastAPIMCPServer) -> "AgentBuilder":
        self._mcp_server = mcp_server
        return self

    def with_tool(self, name: str, handler: Callable[..., Any]) -> "AgentBuilder":
        self._tools[name] = handler
        return self

    def with_tools(self, tools: dict[str, Callable[..., Any]]) -> "AgentBuilder":
        self._tools.update(tools)
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

    def with_foundry_models(
        self,
        *,
        slm_config: FoundryAgentConfig | None = None,
        llm_config: FoundryAgentConfig | None = None,
        complexity_threshold: float = 0.5,
    ) -> "AgentBuilder":
        """Configure Foundry Agents for SLM/LLM targets via ModelTarget wrappers.

        Accepts optional configs for fast/slow (SLM/LLM) paths and builds the
        corresponding ``ModelTarget`` instances with telemetry-aware invokers.
        """

        self._slm = build_foundry_model_target(slm_config) if slm_config else None
        self._llm = build_foundry_model_target(llm_config) if llm_config else None
        self._complexity_threshold = complexity_threshold
        return self

    def build(self) -> BaseRetailAgent:
        if not self._agent_class:
            raise ValueError("Agent class is required")
        if not self._slm and not self._llm:
            raise ValueError("At least one model target (SLM or LLM) is required")
        deps = AgentDependencies(
            router=self._router or RoutingStrategy(),
            tools=self._tools,
            slm=self._slm,
            llm=self._llm,
            complexity_threshold=self._complexity_threshold,
        )
        agent = self._agent_class(config=deps)
        if any([self._hot_memory, self._warm_memory, self._cold_memory]):
            agent.attach_memory(self._hot_memory, self._warm_memory, self._cold_memory)
        if self._mcp_server:
            agent.attach_mcp(self._mcp_server)
        return agent
