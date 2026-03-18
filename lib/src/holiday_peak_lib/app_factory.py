"""Factory to create FastAPI + MCP service instances."""

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator, Callable, Optional

from fastapi import FastAPI, HTTPException
from holiday_peak_lib.agents import AgentBuilder, BaseRetailAgent, FoundryAgentConfig
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer
from holiday_peak_lib.agents.foundry import (
    build_foundry_model_target,
    ensure_foundry_agent,
)
from holiday_peak_lib.agents.memory import ColdMemory, HotMemory, WarmMemory
from holiday_peak_lib.agents.orchestration.router import RoutingStrategy
from holiday_peak_lib.connectors.registry import ConnectorRegistry
from holiday_peak_lib.utils.logging import configure_logging, log_async_operation

DEFAULT_FOUNDY_MODELS = {
    "fast": "gpt-5-nano",
    "rich": "gpt-5",
}


def _build_foundry_config(agent_env: str, deployment_env: str) -> FoundryAgentConfig | None:
    endpoint = os.getenv("PROJECT_ENDPOINT") or os.getenv("FOUNDRY_ENDPOINT")
    project_name = os.getenv("PROJECT_NAME") or os.getenv("FOUNDRY_PROJECT_NAME")
    role = "fast" if agent_env.endswith("FAST") else "rich"
    agent_id = os.getenv(agent_env)
    agent_name = os.getenv(f"FOUNDRY_AGENT_NAME_{role.upper()}")
    deployment = os.getenv(deployment_env) or DEFAULT_FOUNDY_MODELS[role]
    stream = (os.getenv("FOUNDRY_STREAM") or "").lower() in {"1", "true", "yes"}
    if not endpoint:
        return None
    return FoundryAgentConfig(
        endpoint=endpoint,
        agent_id=agent_id or agent_name or f"{role}-pending",
        agent_name=agent_name,
        deployment_name=deployment,
        project_name=project_name,
        stream=stream,
    )


def build_service_app(
    service_name: str,
    agent_class: type[BaseRetailAgent],
    *,
    hot_memory: HotMemory | None = None,
    warm_memory: WarmMemory | None = None,
    cold_memory: ColdMemory | None = None,
    slm_config: FoundryAgentConfig | None = None,
    llm_config: FoundryAgentConfig | None = None,
    connector_registry: ConnectorRegistry | None = None,
    mcp_setup: Optional[Callable[[FastAPIMCPServer, BaseRetailAgent], None]] = None,
    lifespan: Callable[[FastAPI], AsyncIterator[None]] | None = None,
) -> FastAPI:
    """Return a FastAPI app pre-wired with MCP and required memory tiers."""
    logger = configure_logging(app_name=service_name)
    app = FastAPI(title=service_name)
    registry = connector_registry or ConnectorRegistry()
    app.state.connector_registry = registry

    mcp = FastAPIMCPServer(app)
    router = RoutingStrategy()
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
    if hasattr(agent, "connector_registry"):
        agent.connector_registry = registry
    app.state.agent = agent
    strict_foundry_mode = (os.getenv("FOUNDRY_STRICT_ENFORCEMENT") or "").lower() in {
        "1",
        "true",
        "yes",
    }
    foundry_ready = not strict_foundry_mode
    auto_ensure_default = "true" if strict_foundry_mode else "false"
    auto_ensure_on_startup = (
        os.getenv("FOUNDRY_AUTO_ENSURE_ON_STARTUP") or auto_ensure_default
    ).lower() in {
        "1",
        "true",
        "yes",
    }

    if hasattr(agent, "service_name"):
        agent.service_name = service_name
    if mcp_setup:
        mcp_setup(mcp, agent)

    async def _ensure_role(selected_role: str, config: FoundryAgentConfig, service: str) -> dict:
        target_name = config.agent_name or f"{service}-{selected_role}"
        target_model = config.deployment_name or DEFAULT_FOUNDY_MODELS[selected_role]
        ensure_result = await ensure_foundry_agent(
            config,
            agent_name=target_name,
            create_if_missing=True,
            model=target_model,
        )
        ensured_id = ensure_result.get("agent_id")
        ensured_name = ensure_result.get("agent_name")
        if ensured_id:
            config.agent_id = str(ensured_id)
        if ensured_name:
            config.agent_name = str(ensured_name)

        if config.agent_id:
            model_target = build_foundry_model_target(config)
            if selected_role == "fast":
                agent.slm = model_target
            else:
                agent.llm = model_target

        return ensure_result

    @asynccontextmanager
    async def _service_lifespan(wrapped_app: FastAPI) -> AsyncIterator[None]:
        nonlocal foundry_ready
        if auto_ensure_on_startup:
            results: dict[str, dict] = {}
            role_to_config: dict[str, FoundryAgentConfig | None] = {
                "fast": slm_config,
                "rich": llm_config,
            }
            for selected_role, config in role_to_config.items():
                if config is None:
                    continue
                results[selected_role] = await _ensure_role(selected_role, config, service_name)

            foundry_ready = all(
                result.get("status") in {"exists", "found_by_name", "created"}
                and bool(result.get("agent_id") or result.get("agent_name"))
                for result in results.values()
            )

            if strict_foundry_mode and not foundry_ready:
                raise RuntimeError(
                    f"Foundry auto-ensure failed for service '{service_name}': {results}"
                )

        if lifespan is not None:
            async with lifespan(wrapped_app):
                yield
        else:
            yield

    app.router.lifespan_context = _service_lifespan
    router.register("default", agent.handle)

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "service": service_name,
            "integrations_registered": await registry.count(),
        }

    @app.get("/integrations")
    async def integrations():
        return {
            "service": service_name,
            "domains": await registry.list_domains(),
            "health": await registry.health(),
        }

    @app.get("/ready")
    async def ready():
        """Readiness probe — returns 503 when Foundry agents aren't provisioned
        and strict enforcement is enabled. K8s readinessProbe should use this
        endpoint so traffic is only routed to pods that are fully operational."""
        if strict_foundry_mode and not foundry_ready:
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "not_ready",
                    "service": service_name,
                    "reason": "Foundry agents not provisioned. "
                    "Call POST /foundry/agents/ensure or set FOUNDRY_AUTO_ENSURE_ON_STARTUP=true.",
                },
            )
        return {
            "status": "ready",
            "service": service_name,
            "foundry_ready": foundry_ready,
            "integrations_registered": await registry.count(),
        }

    @app.post("/invoke")
    async def invoke(payload: dict):
        if strict_foundry_mode and not foundry_ready:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Strict Foundry enforcement is enabled and no Foundry target is ready. "
                    "Call POST /foundry/agents/ensure first."
                ),
            )

        intent = str(payload.get("intent", "default"))
        request_payload = payload.get("payload", payload)
        if not isinstance(request_payload, dict):
            request_payload = {"query": str(request_payload)}

        return await log_async_operation(
            logger,
            name="service.invoke",
            intent=intent,
            func=lambda: router.route(intent, request_payload),
            token_count=None,
            metadata={
                "payload_size": len(str(request_payload)),
                "service": service_name,
            },
        )

    @app.post("/foundry/agents/ensure")
    async def ensure_agents(payload: dict | None = None):
        nonlocal foundry_ready
        body = payload or {}
        role = str(body.get("role", "both")).lower()
        create_if_missing = bool(body.get("create_if_missing", True))
        instructions = (
            body.get("instructions") if isinstance(body.get("instructions"), dict) else {}
        )
        names = body.get("names") if isinstance(body.get("names"), dict) else {}
        models = body.get("models") if isinstance(body.get("models"), dict) else {}

        role_to_config: dict[str, FoundryAgentConfig | None] = {
            "fast": slm_config,
            "rich": llm_config,
        }
        selected_roles = ["fast", "rich"] if role == "both" else [role]
        results: dict[str, dict] = {}

        for selected_role in selected_roles:
            if selected_role not in role_to_config:
                raise HTTPException(status_code=400, detail=f"Unsupported role '{selected_role}'")

            config = role_to_config[selected_role]
            if config is None:
                results[selected_role] = {
                    "status": "not_configured",
                    "agent_id": None,
                    "created": False,
                }
                continue

            default_name = f"{service_name}-{selected_role}"
            configured_name = names.get(selected_role) or os.getenv(
                f"FOUNDRY_AGENT_NAME_{selected_role.upper()}"
            )
            config.agent_name = str(configured_name or default_name)
            config.deployment_name = str(
                models.get(selected_role)
                or config.deployment_name
                or DEFAULT_FOUNDY_MODELS[selected_role]
            )

            ensure_result = await ensure_foundry_agent(
                config,
                agent_name=config.agent_name,
                instructions=instructions.get(selected_role),
                create_if_missing=create_if_missing,
                model=config.deployment_name,
            )

            ensured_id = ensure_result.get("agent_id")
            ensured_name = ensure_result.get("agent_name")
            if ensured_id:
                config.agent_id = str(ensured_id)
            if ensured_name:
                config.agent_name = str(ensured_name)

            if config.agent_id:
                model_target = build_foundry_model_target(config)
                if selected_role == "fast":
                    agent.slm = model_target
                else:
                    agent.llm = model_target

            results[selected_role] = ensure_result

        if strict_foundry_mode:
            foundry_ready = any(
                bool(result.get("agent_id"))
                and result.get("status") in {"exists", "found_by_name", "created"}
                for result in results.values()
            )

        return {
            "service": service_name,
            "strict_foundry_mode": strict_foundry_mode,
            "foundry_ready": foundry_ready,
            "results": results,
        }

    mcp.mount()
    return app
