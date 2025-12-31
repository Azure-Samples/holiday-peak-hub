"""Factory to create FastAPI + MCP service instances."""
from fastapi import FastAPI

from holiday_peak_lib.agents import AgentBuilder, BaseRetailAgent
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer
from holiday_peak_lib.agents.orchestration.router import RoutingStrategy
from holiday_peak_lib.agents.memory import HotMemory, WarmMemory, ColdMemory
from holiday_peak_lib.utils.logging import configure_logging, log_async_operation


def build_service_app(service_name: str) -> FastAPI:
    """Return a FastAPI app pre-wired with MCP and memory stubs."""
    logger = configure_logging(app_name=service_name)
    app = FastAPI(title=service_name)

    class ServiceAgent(BaseRetailAgent):
        async def handle(self, request):
            return {"service": service_name, "received": request}

    mcp = FastAPIMCPServer(app)
    router = RoutingStrategy()
    router.register("default", lambda payload: payload)
    agent = (
        AgentBuilder()
        .with_agent(ServiceAgent)
        .with_router(router)
        .with_memory(
            HotMemory("redis://localhost:6379"),
            WarmMemory("https://cosmos-account", "db", "container"),
            ColdMemory("https://storage-account", "container"),
        )
        .with_mcp(mcp)
        .build()
    )

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
