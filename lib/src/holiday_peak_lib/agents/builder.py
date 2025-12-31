"""Agent builder using a simple Builder pattern."""
from typing import Any, Callable, Dict, Optional

from agent_framework import Agent

from .base_agent import BaseRetailAgent
from .fastapi_mcp import FastAPIMCPServer
from .memory.hot import HotMemory
from .memory.warm import WarmMemory
from .memory.cold import ColdMemory
from .orchestration.router import RoutingStrategy


class AgentBuilder:
    """Fluent builder to assemble an agent with memory and routing."""

    def __init__(self) -> None:
        self._agent_class: Optional[type[BaseRetailAgent]] = None
        self._router: Optional[RoutingStrategy] = None
        self._hot_memory: Optional[HotMemory] = None
        self._warm_memory: Optional[WarmMemory] = None
        self._cold_memory: Optional[ColdMemory] = None
        self._mcp_server: Optional[FastAPIMCPServer] = None
        self._tools: Dict[str, Callable[..., Any]] = {}

    def with_agent(self, agent_class: type[BaseRetailAgent]) -> "AgentBuilder":
        self._agent_class = agent_class
        return self

    def with_router(self, router: RoutingStrategy) -> "AgentBuilder":
        self._router = router
        return self

    def with_memory(self, hot: HotMemory, warm: WarmMemory, cold: ColdMemory) -> "AgentBuilder":
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

    def build(self) -> Agent:
        if not self._agent_class:
            raise ValueError("Agent class is required")
        router = self._router or RoutingStrategy()
        agent = self._agent_class(router=router, tools=self._tools)
        if self._hot_memory and self._warm_memory and self._cold_memory:
            agent.attach_memory(self._hot_memory, self._warm_memory, self._cold_memory)
        if self._mcp_server:
            agent.attach_mcp(self._mcp_server)
        return agent
