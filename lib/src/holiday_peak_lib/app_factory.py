"""Factory to create FastAPI + MCP service instances."""

import os
from contextlib import asynccontextmanager
from typing import Any, AsyncContextManager, AsyncIterator, Callable, cast

from fastapi import FastAPI, HTTPException
from holiday_peak_lib.agents import AgentBuilder, BaseRetailAgent, FoundryAgentConfig
from holiday_peak_lib.agents.foundry import (
    build_foundry_model_target,
    ensure_foundry_agent,
)
from holiday_peak_lib.agents.memory import ColdMemory, HotMemory, WarmMemory
from holiday_peak_lib.agents.orchestration.router import RoutingStrategy
from holiday_peak_lib.agents.prompt_loader import load_service_prompt_instructions
from holiday_peak_lib.app_factory_components.endpoints import (
    EndpointContext,
    register_standard_endpoints,
)
from holiday_peak_lib.app_factory_components.foundry_lifecycle import (
    FoundryLifecycleManager,
    FoundryReadinessSnapshot,
    auto_ensure_on_startup_enabled,
    build_foundry_config,
    build_foundry_readiness_snapshot,
    exception_to_foundry_error_state,
    first_foundry_error_state,
    strict_foundry_mode_enabled,
)
from holiday_peak_lib.app_factory_components.middleware import register_correlation_middleware
from holiday_peak_lib.config import MemorySettings
from holiday_peak_lib.connectors.registry import ConnectorRegistry
from holiday_peak_lib.mcp.server import FastAPIMCPServer
from holiday_peak_lib.self_healing import SelfHealingKernel
from holiday_peak_lib.utils import (
    EventHubSubscription,
    create_eventhub_lifespan,
    get_foundry_tracer,
)
from holiday_peak_lib.utils.logging import configure_logging

_FALLBACK_INSTRUCTIONS_TEMPLATE = (
    "Structured instructions file not found for '{service_name}'. "
    "Use only provided request data, state missing fields, and avoid assumptions."
)


async def _fetch_key_vault_secret(vault_uri: str, secret_name: str) -> str:
    """Retrieve a secret from Azure Key Vault using managed identity."""
    from azure.identity.aio import DefaultAzureCredential  # pylint: disable=import-outside-toplevel
    from azure.keyvault.secrets.aio import SecretClient  # pylint: disable=import-outside-toplevel

    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=vault_uri, credential=credential)
    try:
        secret = await client.get_secret(secret_name)
        return secret.value
    finally:
        await client.close()
        await credential.close()


def _build_foundry_config(agent_env: str, deployment_env: str) -> FoundryAgentConfig | None:
    """Backward-compatible alias for internal Foundry config builder."""
    return build_foundry_config(agent_env, deployment_env)


def _runtime_foundry_config(config: FoundryAgentConfig | None) -> FoundryAgentConfig | None:
    """Return a Foundry config only when a resolvable runtime agent id is available.

    Foundry config may carry lookup-only references such as role names while the
    actual runtime agent id is still unresolved. We keep those configs for
    ensure/provision endpoints, but avoid binding them as callable SLM/LLM
    targets until a real runtime id is available.
    """
    if config is None:
        return None

    agent_id = str(config.runtime_agent_id or "").strip()
    if not agent_id or agent_id == "pending" or agent_id.endswith("-pending"):
        return None
    return config


def create_standard_app(
    service_name: str,
    agent_class: type[BaseRetailAgent],
    *,
    mcp_setup: Callable[[FastAPIMCPServer, BaseRetailAgent], None] | None = None,
    subscriptions: list[EventHubSubscription] | None = None,
    handlers: dict[str, Any] | None = None,
    require_foundry_readiness: bool = False,
    disable_tracing_without_foundry: bool = False,
) -> FastAPI:
    """Create a standard agent app with memory + default Foundry wiring.

    Foundry is preferred by default, but readiness enforcement is optional and
    controlled via ``require_foundry_readiness``.

    ``disable_tracing_without_foundry`` is a backward-compatible per-service
    hint. Core telemetry collection remains enabled so admin observability
    surfaces stay available even when Foundry targets are not bound.
    """
    self_healing_kernel = SelfHealingKernel.from_env(service_name)
    memory_settings = MemorySettings()
    resolved_redis_url = memory_settings.resolve_redis_url()
    hot_memory = HotMemory(resolved_redis_url) if resolved_redis_url else None
    warm_memory = (
        WarmMemory(
            memory_settings.cosmos_account_uri,
            memory_settings.cosmos_database,
            memory_settings.cosmos_container,
        )
        if (
            memory_settings.cosmos_account_uri
            and memory_settings.cosmos_database
            and memory_settings.cosmos_container
        )
        else None
    )
    cold_memory = (
        ColdMemory(memory_settings.blob_account_url, memory_settings.blob_container)
        if memory_settings.blob_account_url and memory_settings.blob_container
        else None
    )
    lifespan = None
    if subscriptions and handlers:
        eventhub_kwargs: dict[str, Any] = {}
        if self_healing_kernel is not None:
            eventhub_kwargs["self_healing_kernel"] = self_healing_kernel
            eventhub_kwargs["reconcile_on_error"] = self_healing_kernel.reconcile_on_messaging_error
        lifespan = create_eventhub_lifespan(
            service_name=service_name,
            subscriptions=subscriptions,
            handlers=handlers,
            **eventhub_kwargs,
        )

    return build_service_app(
        service_name,
        agent_class,
        hot_memory=hot_memory,
        warm_memory=warm_memory,
        cold_memory=cold_memory,
        memory_settings=memory_settings,
        mcp_setup=mcp_setup,
        lifespan=lifespan,
        self_healing_kernel=self_healing_kernel,
        require_foundry_readiness=require_foundry_readiness,
        disable_tracing_without_foundry=disable_tracing_without_foundry,
    )


def build_service_app(
    service_name: str,
    agent_class: type[BaseRetailAgent],
    *,
    hot_memory: HotMemory | None = None,
    warm_memory: WarmMemory | None = None,
    cold_memory: ColdMemory | None = None,
    memory_settings: MemorySettings | None = None,
    slm_config: FoundryAgentConfig | None = None,
    llm_config: FoundryAgentConfig | None = None,
    connector_registry: ConnectorRegistry | None = None,
    mcp_setup: Callable[[FastAPIMCPServer, BaseRetailAgent], None] | None = None,
    lifespan: Callable[[FastAPI], AsyncContextManager[None]] | None = None,
    self_healing_kernel: SelfHealingKernel | None = None,
    require_foundry_readiness: bool = False,
    disable_tracing_without_foundry: bool = False,
) -> FastAPI:
    """Return a FastAPI app pre-wired with MCP and required memory tiers.

    Args:
        require_foundry_readiness: When ``True``, ``/ready`` and invoke guards
            enforce Foundry runtime availability for this service.
        disable_tracing_without_foundry: Backward-compatible per-service hint.
            Core telemetry remains enabled for local/fallback execution paths.
    """
    logger = configure_logging(app_name=service_name)
    app = FastAPI(title=service_name)
    registry = connector_registry or ConnectorRegistry()
    app.state.connector_registry = registry
    healing_kernel = self_healing_kernel or SelfHealingKernel.from_env(service_name)
    app.state.self_healing_kernel = healing_kernel

    mcp = FastAPIMCPServer(app)
    if hasattr(mcp, "_on_failure"):
        setattr(mcp, "_on_failure", healing_kernel.handle_failure_signal)
    router = RoutingStrategy()
    builder = cast(
        AgentBuilder,
        (
            AgentBuilder()
            .with_agent(agent_class)
            .with_router(router)
            .with_memory(hot_memory, warm_memory, cold_memory)
            .with_mcp(mcp)
        ),
    )
    with_self_healing = getattr(builder, "with_self_healing", None)
    if callable(with_self_healing):
        maybe_builder = with_self_healing(healing_kernel)
        if isinstance(maybe_builder, AgentBuilder):
            builder = maybe_builder
    if slm_config is None and llm_config is None:
        slm_config = _build_foundry_config("FOUNDRY_AGENT_ID_FAST", "MODEL_DEPLOYMENT_NAME_FAST")
        llm_config = _build_foundry_config("FOUNDRY_AGENT_ID_RICH", "MODEL_DEPLOYMENT_NAME_RICH")

    runtime_slm_config = _runtime_foundry_config(slm_config)
    runtime_llm_config = _runtime_foundry_config(llm_config)
    if runtime_slm_config or runtime_llm_config:
        builder = builder.with_foundry_models(
            slm_config=runtime_slm_config,
            llm_config=runtime_llm_config,
        )

    unresolved_roles = []
    if slm_config and runtime_slm_config is None:
        unresolved_roles.append("fast")
    if llm_config and runtime_llm_config is None:
        unresolved_roles.append("rich")
    if unresolved_roles:
        logger.warning(
            "foundry_runtime_targets_disabled",
            extra={
                "service": service_name,
                "roles": unresolved_roles,
                "hint": (
                    "Set FOUNDRY_AGENT_ID_FAST/FOUNDRY_AGENT_ID_RICH (or role names) "
                    "or enable FOUNDRY_AUTO_ENSURE_ON_STARTUP to provision agents before invoke."
                ),
            },
        )

    agent = builder.build()
    if hasattr(agent, "connector_registry"):
        agent.connector_registry = registry
    app.state.agent = agent

    def _has_bound_foundry_target() -> bool:
        return bool(getattr(agent, "slm", None) or getattr(agent, "llm", None))

    def _sync_foundry_tracing_state() -> None:
        _ = disable_tracing_without_foundry
        get_foundry_tracer(service_name)

    tracer = get_foundry_tracer(service_name)

    configured_foundry_roles = tuple(
        role for role, config in (("fast", slm_config), ("rich", llm_config)) if config is not None
    )
    strict_foundry_mode = strict_foundry_mode_enabled() and bool(configured_foundry_roles)
    auto_ensure_on_startup = auto_ensure_on_startup_enabled(strict_foundry_mode=strict_foundry_mode)

    if hasattr(agent, "service_name"):
        agent.service_name = service_name
    if mcp_setup:
        mcp_setup(mcp, agent)
    default_instructions = load_service_prompt_instructions(service_name) or (
        _FALLBACK_INSTRUCTIONS_TEMPLATE.format(service_name=service_name)
    )

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

    last_foundry_error: dict[str, Any] | None = None

    def _current_foundry_readiness() -> FoundryReadinessSnapshot:
        return build_foundry_readiness_snapshot(
            agent=agent,
            slm_config=slm_config,
            llm_config=llm_config,
            require_foundry_readiness=require_foundry_readiness,
            strict_foundry_mode=strict_foundry_mode,
            auto_ensure_on_startup=auto_ensure_on_startup,
            last_error=last_foundry_error,
        )

    _UNSET = object()

    def _apply_foundry_error_state(
        error_state: dict[str, Any] | None | object = _UNSET,
    ) -> FoundryReadinessSnapshot:
        nonlocal last_foundry_error

        if error_state is not _UNSET:
            last_foundry_error = cast(dict[str, Any] | None, error_state)

        snapshot = _current_foundry_readiness()
        if snapshot.ready and last_foundry_error is not None:
            last_foundry_error = None
            snapshot = _current_foundry_readiness()

        _sync_foundry_tracing_state()
        return snapshot

    @asynccontextmanager
    async def _service_lifespan(wrapped_app: FastAPI) -> AsyncIterator[None]:
        # Resolve missing Azure Redis auth from Key Vault before serving traffic.
        if (
            memory_settings is not None
            and hot_memory is not None
            and memory_settings.key_vault_uri
            and memory_settings.redis_password_secret_name
            and memory_settings.redis_url_needs_password_resolution(hot_memory.url)
        ):
            try:
                redis_password = await _fetch_key_vault_secret(
                    memory_settings.key_vault_uri,
                    memory_settings.redis_password_secret_name,
                )
                new_url = memory_settings.resolve_redis_url(password=redis_password)
                if new_url and new_url != hot_memory.url:
                    hot_memory.url = new_url
                    hot_memory.client = None  # Force reconnect with new URL
                    logger.info("Redis password resolved from Key Vault")
            except Exception:  # pylint: disable=broad-exception-caught
                logger.warning(
                    "Redis password resolution from Key Vault failed; "
                    "hot memory may be unavailable",
                    exc_info=True,
                )

        if auto_ensure_on_startup:
            foundry_manager.ensure_foundry_agent_fn = ensure_foundry_agent
            try:
                results = await foundry_manager.ensure_startup_roles(default_instructions)
            except (AttributeError, ImportError, RuntimeError, TypeError, ValueError) as exc:
                snapshot = _apply_foundry_error_state(
                    exception_to_foundry_error_state(
                        exc,
                        status="startup_ensure_failed",
                    )
                )
                if strict_foundry_mode:
                    raise RuntimeError(
                        "Foundry auto-ensure failed for service "
                        f"'{service_name}': {snapshot.to_payload()}"
                    ) from exc
            else:
                startup_error = first_foundry_error_state(
                    results,
                    configured_roles=configured_foundry_roles,
                )
                snapshot = _apply_foundry_error_state(startup_error)

                if strict_foundry_mode and not snapshot.ready:
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
        foundry_manager.ensure_foundry_agent_fn = ensure_foundry_agent
        body: dict = payload if isinstance(payload, dict) else {}
        fallback_instructions = (
            load_service_prompt_instructions(service_name) or default_instructions
        )
        role = str(body.get("role", "both")).lower()
        create_if_missing = bool(body.get("create_if_missing", True))
        instructions_raw = body.get("instructions")
        names_raw = body.get("names")
        models_raw = body.get("models")
        instructions: dict[str, str] = (
            {str(key): value for key, value in instructions_raw.items() if isinstance(value, str)}
            if isinstance(instructions_raw, dict)
            else {}
        )
        names: dict[str, str] = (
            {str(key): value for key, value in names_raw.items() if isinstance(value, str)}
            if isinstance(names_raw, dict)
            else {}
        )
        models: dict[str, str] = (
            {str(key): value for key, value in models_raw.items() if isinstance(value, str)}
            if isinstance(models_raw, dict)
            else {}
        )
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
            role_agent_env = (
                "FOUNDRY_AGENT_ID_FAST" if selected_role == "fast" else "FOUNDRY_AGENT_ID_RICH"
            )
            role_deployment_env = (
                "MODEL_DEPLOYMENT_NAME_FAST"
                if selected_role == "fast"
                else "MODEL_DEPLOYMENT_NAME_RICH"
            )
            role_discovered_config = build_foundry_config(role_agent_env, role_deployment_env)
            configured_model = (
                models.get(selected_role)
                or config.deployment_name
                or (
                    role_discovered_config.deployment_name
                    if role_discovered_config is not None
                    else None
                )
                or ("gpt-5-nano" if selected_role == "fast" else "gpt-5")
            )

            selected_instructions = instructions.get(selected_role) or fallback_instructions

            try:
                ensure_result = await foundry_manager.ensure_role(
                    selected_role=selected_role,
                    config=config,
                    instructions=selected_instructions,
                    create_if_missing=create_if_missing,
                    name_override=str(configured_name),
                    model_override=str(configured_model),
                )
            except (AttributeError, ImportError, RuntimeError, TypeError, ValueError) as exc:
                _apply_foundry_error_state(
                    exception_to_foundry_error_state(
                        exc,
                        status="ensure_failed",
                        role=selected_role,
                    )
                )
                raise

            results[selected_role] = ensure_result

        configured_requested_roles = [
            selected_role
            for selected_role in selected_roles
            if role_to_config.get(selected_role) is not None
        ]

        resolved_roles = sum(
            1
            for selected_role, result in results.items()
            if selected_role in configured_requested_roles
            if bool(result.get("agent_id"))
            and result.get("status") in {"exists", "found_by_name", "created"}
        )
        ensure_error = first_foundry_error_state(
            results,
            configured_roles=configured_requested_roles,
        )
        snapshot = (
            _apply_foundry_error_state(ensure_error)
            if ensure_error is not None
            else _apply_foundry_error_state()
        )

        if (require_foundry_readiness or strict_foundry_mode) and not snapshot.ready:
            logger.warning(
                "foundry_strict_ensure_incomplete",
                extra={
                    "service": service_name,
                    "resolved_roles": resolved_roles,
                    "configured_roles": list(snapshot.configured_roles),
                    "configured_requested_roles": configured_requested_roles,
                    "unresolved_roles": list(snapshot.unresolved_roles),
                    "requested_roles": list(results.keys()),
                    "last_error": snapshot.last_error,
                },
            )

        return {
            "service": service_name,
            "strict_foundry_mode": strict_foundry_mode,
            "foundry_ready": snapshot.ready,
            "foundry": snapshot.to_payload(),
            "results": results,
        }

    def _is_foundry_ready() -> bool:
        return _current_foundry_readiness().ready

    def _set_foundry_ready(value: bool) -> None:
        if value:
            _apply_foundry_error_state(None)
            return
        _sync_foundry_tracing_state()

    def _requires_foundry_runtime_resolution() -> bool:
        return _current_foundry_readiness().runtime_resolution_required

    def _foundry_capabilities() -> dict[str, Any]:
        return _current_foundry_readiness().to_payload()

    endpoint_ctx = EndpointContext(
        service_name=service_name,
        registry=registry,
        router=router,
        tracer=tracer,
        logger=logger,
        strict_foundry_mode=strict_foundry_mode,
        require_foundry_readiness=require_foundry_readiness,
        is_foundry_ready=_is_foundry_ready,
        set_foundry_ready=_set_foundry_ready,
        requires_foundry_runtime_resolution=_requires_foundry_runtime_resolution,
        foundry_capabilities=_foundry_capabilities,
        ensure_agents_handler=ensure_agents,
        self_healing_kernel=healing_kernel,
    )

    register_standard_endpoints(app, ctx=endpoint_ctx)

    mcp.mount()
    return app
