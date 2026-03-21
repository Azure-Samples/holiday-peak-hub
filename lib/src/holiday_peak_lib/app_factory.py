"""Factory to create FastAPI + MCP service instances."""

import os
from contextlib import asynccontextmanager
from typing import Any, AsyncContextManager, AsyncIterator, Callable

from fastapi import FastAPI, HTTPException
from holiday_peak_lib.agents import AgentBuilder, BaseRetailAgent, FoundryAgentConfig
from holiday_peak_lib.agents.foundry import (
    build_foundry_model_target,
    ensure_foundry_agent,
)
from holiday_peak_lib.agents.memory import ColdMemory, HotMemory, WarmMemory
from holiday_peak_lib.agents.orchestration.router import RoutingStrategy
from holiday_peak_lib.agents.prompt_loader import load_service_prompt_instructions
from holiday_peak_lib.app_factory_components.endpoints import register_standard_endpoints
from holiday_peak_lib.app_factory_components.foundry_lifecycle import (
    FoundryLifecycleManager,
    auto_ensure_on_startup_enabled,
    build_foundry_config,
    strict_foundry_mode_enabled,
)
from holiday_peak_lib.app_factory_components.middleware import register_correlation_middleware
from holiday_peak_lib.config import MemorySettings
from holiday_peak_lib.connectors.registry import ConnectorRegistry
from holiday_peak_lib.mcp.server import FastAPIMCPServer
from holiday_peak_lib.utils import (
    EventHubSubscription,
    create_eventhub_lifespan,
    get_foundry_tracer,
)
from holiday_peak_lib.utils.logging import configure_logging


def _build_foundry_config(agent_env: str, deployment_env: str) -> FoundryAgentConfig | None:
    """Backward-compatible alias for internal Foundry config builder."""
    return build_foundry_config(agent_env, deployment_env)


def create_standard_app(
    service_name: str,
    agent_class: type[BaseRetailAgent],
    *,
    mcp_setup: Callable[[FastAPIMCPServer, BaseRetailAgent], None] | None = None,
    subscriptions: list[EventHubSubscription] | None = None,
    handlers: dict[str, Any] | None = None,
) -> FastAPI:
    """Create a standard agent app with memory + default Foundry wiring."""
    memory_settings = MemorySettings()
    hot_memory = HotMemory(memory_settings.redis_url) if memory_settings.redis_url else None
    warm_memory = (
        WarmMemory(
            memory_settings.cosmos_account_uri,
            memory_settings.cosmos_database,
            memory_settings.cosmos_container,
        )
        if memory_settings.cosmos_account_uri
        else None
    )
    cold_memory = (
        ColdMemory(memory_settings.blob_account_url, memory_settings.blob_container)
        if memory_settings.blob_account_url
        else None
    )
    lifespan = None
    if subscriptions and handlers:
        lifespan = create_eventhub_lifespan(
            service_name=service_name,
            subscriptions=subscriptions,
            handlers=handlers,
        )

    return build_service_app(
        service_name,
        agent_class,
        hot_memory=hot_memory,
        warm_memory=warm_memory,
        cold_memory=cold_memory,
        mcp_setup=mcp_setup,
        lifespan=lifespan,
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
    mcp_setup: Callable[[FastAPIMCPServer, BaseRetailAgent], None] | None = None,
    lifespan: Callable[[FastAPI], AsyncContextManager[None]] | None = None,
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
    tracer = get_foundry_tracer(service_name)
    if hasattr(agent, "connector_registry"):
        agent.connector_registry = registry
    app.state.agent = agent
    strict_foundry_mode = strict_foundry_mode_enabled()
    foundry_ready = not strict_foundry_mode
    auto_ensure_on_startup = auto_ensure_on_startup_enabled(strict_foundry_mode=strict_foundry_mode)

    if hasattr(agent, "service_name"):
        agent.service_name = service_name
    if mcp_setup:
        mcp_setup(mcp, agent)
    default_instructions = load_service_prompt_instructions(service_name)

    register_correlation_middleware(app)

    async def _ensure_foundry_agent_proxy(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return await ensure_foundry_agent(*args, **kwargs)

    foundry_manager = FoundryLifecycleManager(
        service_name=service_name,
        agent=agent,
        slm_config=slm_config,
        llm_config=llm_config,
        ensure_foundry_agent_fn=_ensure_foundry_agent_proxy,
        build_foundry_model_target_fn=build_foundry_model_target,
    )

    @asynccontextmanager
    async def _service_lifespan(wrapped_app: FastAPI) -> AsyncIterator[None]:
        nonlocal foundry_ready
        if auto_ensure_on_startup:
            foundry_manager.ensure_foundry_agent_fn = ensure_foundry_agent
            results = await foundry_manager.ensure_startup_roles(default_instructions)

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

    async def ensure_agents(payload: dict | None = None) -> dict[str, Any]:
        nonlocal foundry_ready
        foundry_manager.ensure_foundry_agent_fn = ensure_foundry_agent
        body: dict = payload if isinstance(payload, dict) else {}
        fallback_instructions = load_service_prompt_instructions(service_name)
        role = str(body.get("role", "both")).lower()
        create_if_missing = bool(body.get("create_if_missing", True))
        instructions_raw = body.get("instructions")
        names_raw = body.get("names")
        models_raw = body.get("models")
        instructions: dict = instructions_raw if isinstance(instructions_raw, dict) else {}
        names: dict = names_raw if isinstance(names_raw, dict) else {}
        models: dict = models_raw if isinstance(models_raw, dict) else {}
        allow_instruction_override = (
            os.getenv("FOUNDRY_ALLOW_INSTRUCTION_OVERRIDE") or ""
        ).lower() in {
            "1",
            "true",
            "yes",
        }
        if instructions and not allow_instruction_override:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Instruction overrides are disabled. "
                    "Set FOUNDRY_ALLOW_INSTRUCTION_OVERRIDE=true to enable."
                ),
            )

        role_to_config = foundry_manager.role_to_config
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

            configured_name = (
                names.get(selected_role)
                or os.getenv(f"FOUNDRY_AGENT_NAME_{selected_role.upper()}")
                or f"{service_name}-{selected_role}"
            )
            configured_model = (
                models.get(selected_role)
                or config.deployment_name
                or build_foundry_config(
                    "FOUNDRY_AGENT_ID_FAST" if selected_role == "fast" else "FOUNDRY_AGENT_ID_RICH",
                    (
                        "MODEL_DEPLOYMENT_NAME_FAST"
                        if selected_role == "fast"
                        else "MODEL_DEPLOYMENT_NAME_RICH"
                    ),
                ).deployment_name
                if build_foundry_config(
                    "FOUNDRY_AGENT_ID_FAST" if selected_role == "fast" else "FOUNDRY_AGENT_ID_RICH",
                    (
                        "MODEL_DEPLOYMENT_NAME_FAST"
                        if selected_role == "fast"
                        else "MODEL_DEPLOYMENT_NAME_RICH"
                    ),
                )
                else ("gpt-5-nano" if selected_role == "fast" else "gpt-5")
            )

            ensure_result = await foundry_manager.ensure_role(
                selected_role=selected_role,
                config=config,
                instructions=(
                    instructions.get(selected_role)
                    if selected_role in instructions
                    else fallback_instructions
                ),
                create_if_missing=create_if_missing,
                name_override=str(configured_name),
                model_override=str(configured_model),
            )

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

    def _is_foundry_ready() -> bool:
        return foundry_ready

    def _set_foundry_ready(value: bool) -> None:
        nonlocal foundry_ready
        foundry_ready = value

    register_standard_endpoints(
        app,
        service_name=service_name,
        registry=registry,
        router=router,
        tracer=tracer,
        logger=logger,
        strict_foundry_mode=strict_foundry_mode,
        is_foundry_ready=_is_foundry_ready,
        set_foundry_ready=_set_foundry_ready,
        ensure_agents_handler=ensure_agents,
    )

    mcp.mount()
    return app
