"""Factory to create FastAPI + MCP service instances."""
import os
from typing import Callable, Optional

from fastapi import FastAPI

from holiday_peak_lib.agents import AgentBuilder, BaseRetailAgent, FoundryAgentConfig
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer
from holiday_peak_lib.agents.orchestration.router import RoutingStrategy
from holiday_peak_lib.agents.memory import HotMemory, WarmMemory, ColdMemory
from holiday_peak_lib.utils.logging import configure_logging, log_async_operation


def _build_foundry_config(agent_env: str, deployment_env: str) -> FoundryAgentConfig | None:
    endpoint = os.getenv("PROJECT_ENDPOINT") or os.getenv("FOUNDRY_ENDPOINT")
    project_name = os.getenv("PROJECT_NAME") or os.getenv("FOUNDRY_PROJECT_NAME")
    agent_id = os.getenv(agent_env)
    deployment = os.getenv(deployment_env)
    stream = (os.getenv("FOUNDRY_STREAM") or "").lower() in {"1", "true", "yes"}
    if not endpoint or not agent_id:
        return None
    return FoundryAgentConfig(
        endpoint=endpoint,
        agent_id=agent_id,
        deployment_name=deployment,
        project_name=project_name,
        stream=stream,
    )


def build_service_app(
    service_name: str,
    agent_class: type[BaseRetailAgent],
    *,
    hot_memory: HotMemory,
    warm_memory: WarmMemory,
    cold_memory: ColdMemory,
    slm_config: FoundryAgentConfig | None = None,
    llm_config: FoundryAgentConfig | None = None,
    mcp_setup: Optional[Callable[[FastAPIMCPServer, BaseRetailAgent], None]] = None,
) -> FastAPI:
    """Return a FastAPI app pre-wired with MCP and required memory tiers."""
    logger = configure_logging(app_name=service_name)
    app = FastAPI(title=service_name)

    mcp = FastAPIMCPServer(app)
    router = RoutingStrategy()
    router.register("default", lambda payload: payload)
    builder = (
        AgentBuilder()
        .with_agent(agent_class)
        .with_router(router)
        .with_memory(hot_memory, warm_memory, cold_memory)
        .with_mcp(mcp)
    )
    if slm_config is None and llm_config is None:
        slm_config = _build_foundry_config("FOUNDRY_AGENT_ID_FAST", "MODEL_DEPLOYMENT_NAME_FAST")
        llm_config = _build_foundry_config("FOUNDRY_AGENT_ID_RICH", "MODEL_DEPLOYMENT_NAME_RICH")
    if slm_config or llm_config:
        builder = builder.with_foundry_models(slm_config=slm_config, llm_config=llm_config)
    agent = builder.build()

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
