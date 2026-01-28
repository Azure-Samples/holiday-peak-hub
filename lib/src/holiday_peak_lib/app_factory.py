"""Factory to create FastAPI + MCP service instances."""
from typing import Callable, Optional

from fastapi import FastAPI

from holiday_peak_lib.agents import AgentBuilder, BaseRetailAgent
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer
from holiday_peak_lib.agents.orchestration.router import RoutingStrategy
from holiday_peak_lib.agents.memory import HotMemory, WarmMemory, ColdMemory
from holiday_peak_lib.utils.logging import configure_logging, log_async_operation


def build_service_app(
    service_name: str,
    agent_class: type[BaseRetailAgent],
    *,
    hot_memory: HotMemory,
    warm_memory: WarmMemory,
    cold_memory: ColdMemory,
    mcp_setup: Optional[Callable[[FastAPIMCPServer, BaseRetailAgent], None]] = None,
) -> FastAPI:
    """Return a FastAPI app pre-wired with MCP and required memory tiers."""
    logger = configure_logging(app_name=service_name)
    app = FastAPI(title=service_name)

    mcp = FastAPIMCPServer(app)
    router = RoutingStrategy()
    router.register("default", lambda payload: payload)
    agent = (
        AgentBuilder()
        .with_agent(agent_class)
        .with_router(router)
        .with_memory(hot_memory, warm_memory, cold_memory)
        .with_mcp(mcp)
        .build()
    )

    if hasattr(agent, "service_name"):
        agent.service_name = service_name
    if mcp_setup:
        mcp_setup(mcp, agent)

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": service_name}

    @app.post("/invoke")
    async def invoke(payload: dict):
        return await log_async_operation(
            logger,
            name="service.invoke",
            intent=service_name,
            func=lambda: agent.handle(payload),
            token_count=None,
            metadata={"payload_size": len(str(payload))},
        )

    mcp.mount()
    return app
