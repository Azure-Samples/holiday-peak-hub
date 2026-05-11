"""Factory to create FastAPI + MCP service instances."""

import os
from contextlib import asynccontextmanager
from typing import Any, AsyncContextManager, AsyncIterator, Callable, cast

from fastapi import FastAPI
from holiday_peak_lib.agents import AgentBuilder, BaseRetailAgent, FoundryAgentConfig
from holiday_peak_lib.agents.memory import ColdMemory, HotMemory, WarmMemory
from holiday_peak_lib.agents.orchestration.router import RoutingStrategy
from holiday_peak_lib.agents.prompt_loader import (
    load_service_prompt_catalog,
    load_service_prompt_instructions,
    prompt_instructions_sha256,
)
from holiday_peak_lib.app_factory_components.endpoints import (
    EndpointContext,
    register_standard_endpoints,
)
from holiday_peak_lib.app_factory_components.foundry_lifecycle import (
    FoundryReadinessSnapshot,
    build_foundry_config,
    build_foundry_readiness_snapshot,
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


def create_standard_app(
    service_name: str,
    agent_class: type[BaseRetailAgent],
    *,
    mcp_setup: Callable[[FastAPIMCPServer, BaseRetailAgent], None] | None = None,
    subscriptions: list[EventHubSubscription] | None = None,
    handlers: dict[str, Any] | None = None,
    require_foundry_readiness: bool = False,
    disable_tracing_without_foundry: bool = False,
    use_direct_model: bool | None = None,
) -> FastAPI:
    """Create a standard agent app with memory + default Foundry wiring.

    Foundry is preferred by default, but readiness enforcement is optional and
    controlled via ``require_foundry_readiness``.

    ``disable_tracing_without_foundry`` is a backward-compatible per-service
    hint. Core telemetry collection remains enabled so admin observability
    surfaces stay available even when Foundry targets are not bound.

    ``use_direct_model`` switches the model wiring to the direct-model path
    (in-process MAF ``Agent`` + ``FoundryChatClient`` over Responses API)
    introduced by the ADR-005 2026-05-10 amendment. When ``None`` (default),
    the value is read from the ``HOLIDAY_PEAK_DIRECT_MODEL`` environment
    variable. Pass ``True`` to opt a service into the pilot regardless of env.
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
        use_direct_model=use_direct_model,
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
    use_direct_model: bool | None = None,
) -> FastAPI:
    """Return a FastAPI app pre-wired with MCP and required memory tiers.

    Args:
        require_foundry_readiness: When ``True``, ``/ready`` and invoke guards
            enforce Foundry runtime availability for this service.
        disable_tracing_without_foundry: Backward-compatible per-service hint.
            Core telemetry remains enabled for local/fallback execution paths.
        use_direct_model: When ``True``, wires SLM/LLM targets through
            :class:`~holiday_peak_lib.agents.direct.DirectModelInvoker`
            (in-process MAF ``Agent`` + ``FoundryChatClient``) instead of the
            portal-managed Foundry Agent path. ``None`` (default) falls back to
            the ``HOLIDAY_PEAK_DIRECT_MODEL`` environment variable.
    """
    logger = configure_logging(app_name=service_name)
    root_path = os.getenv("ROOT_PATH", "")
    app = FastAPI(title=service_name, root_path=root_path)
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

    # Resolve the model-wiring strategy:
    # Direct-model invocation is the canonical path post-2026-05-10
    # (ADR-005 amendment). The legacy portal-agent ModelInvoker path was
    # removed in Wave 4a of the cutover. ``use_direct_model`` is preserved
    # on the signature for backward compatibility but is now effectively a
    # no-op: model wiring always uses :class:`DirectModelInvoker` (in-process
    # MAF ``Agent`` + ``FoundryChatClient`` over Responses API). Requires
    # only a ``deployment_name`` on each config.
    _ = use_direct_model  # signature kept for backward compatibility
    _ = os.getenv("HOLIDAY_PEAK_DIRECT_MODEL", "")  # env-var read for telemetry parity

    direct_slm = slm_config if slm_config and slm_config.deployment_name else None
    direct_llm = llm_config if llm_config and llm_config.deployment_name else None
    if direct_slm or direct_llm:
        instructions = load_service_prompt_instructions(service_name) or (
            _FALLBACK_INSTRUCTIONS_TEMPLATE.format(service_name=service_name)
        )
        builder = builder.with_direct_models(
            instructions=instructions,
            slm_config=direct_slm,
            llm_config=direct_llm,
        )
        logger.info(
            "direct_model_targets_bound",
            extra={
                "service": service_name,
                "fast_deployment": direct_slm.deployment_name if direct_slm else None,
                "rich_deployment": direct_llm.deployment_name if direct_llm else None,
                "runtime": "maf-direct",
            },
        )

    unresolved_roles = []
    if slm_config and direct_slm is None:
        unresolved_roles.append("fast")
    if llm_config and direct_llm is None:
        unresolved_roles.append("rich")
    if unresolved_roles:
        logger.warning(
            "direct_model_targets_disabled",
            extra={
                "service": service_name,
                "roles": unresolved_roles,
                "hint": (
                    "Set MODEL_DEPLOYMENT_NAME_FAST / MODEL_DEPLOYMENT_NAME_RICH "
                    "for direct-model invocation."
                ),
            },
        )

    agent = builder.build()
    if hasattr(agent, "connector_registry"):
        agent.connector_registry = registry
    app.state.agent = agent

    def _sync_foundry_tracing_state() -> None:
        _ = disable_tracing_without_foundry
        get_foundry_tracer(service_name)

    tracer = get_foundry_tracer(service_name)

    # Suppress azure-ai-projects SDK internal telemetry instrumentor when
    # no real OpenTelemetry exporter is configured. The SDK crashes with
    # AttributeError on NonRecordingSpan.attributes (GH-946).
    if not os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING") and not os.getenv(
        "AZURE_TRACING_ENABLED"
    ):
        os.environ.setdefault("AZURE_TRACING_ENABLED", "false")

    configured_foundry_roles = tuple(
        role for role, config in (("fast", slm_config), ("rich", llm_config)) if config is not None
    )
    strict_foundry_mode = strict_foundry_mode_enabled() and bool(configured_foundry_roles)

    if hasattr(agent, "service_name"):
        agent.service_name = service_name
    if mcp_setup:
        mcp_setup(mcp, agent)
    default_instructions = load_service_prompt_instructions(service_name) or (
        _FALLBACK_INSTRUCTIONS_TEMPLATE.format(service_name=service_name)
    )

    def _prompt_catalog_provider() -> list[dict[str, Any]]:
        catalog = load_service_prompt_catalog(service_name)
        if catalog:
            return catalog

        return [
            {
                "name": "instructions.md",
                "content": default_instructions,
                "sha": prompt_instructions_sha256(default_instructions),
                "last_modified": None,
            }
        ]

    def _mcp_tool_descriptions_provider() -> list[dict[str, Any]]:
        descriptions: list[dict[str, Any]] = []
        for path, details in sorted(mcp.tool_metadata.items()):
            metadata = details.get("metadata")
            metadata_record = metadata if isinstance(metadata, dict) else {}
            descriptions.append(
                {
                    "name": str(details.get("name") or path.lstrip("/")),
                    "path": path,
                    "description": str(
                        metadata_record.get("description")
                        or metadata_record.get("summary")
                        or "No description provided."
                    ),
                    "input_schema_ref": details.get("input_schema_ref"),
                    "output_schema_ref": details.get("output_schema_ref"),
                    "input_schema": details.get("input_schema"),
                    "output_schema": details.get("output_schema"),
                    "metadata": metadata_record,
                }
            )
        return descriptions

    register_correlation_middleware(app)

    def _current_foundry_readiness() -> FoundryReadinessSnapshot:
        _sync_foundry_tracing_state()
        return build_foundry_readiness_snapshot(
            agent=agent,
            slm_config=slm_config,
            llm_config=llm_config,
            require_foundry_readiness=require_foundry_readiness,
            strict_foundry_mode=strict_foundry_mode,
            last_error=None,
        )

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

        if lifespan is not None:
            async with lifespan(wrapped_app):
                yield
        else:
            yield

    app.router.lifespan_context = _service_lifespan
    router.register("default", agent.handle)

    def _is_foundry_ready() -> bool:
        return _current_foundry_readiness().ready

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
        requires_foundry_runtime_resolution=_requires_foundry_runtime_resolution,
        foundry_capabilities=_foundry_capabilities,
        self_healing_kernel=healing_kernel,
        prompt_catalog_provider=_prompt_catalog_provider,
        mcp_tool_descriptions_provider=_mcp_tool_descriptions_provider,
    )

    register_standard_endpoints(app, ctx=endpoint_ctx)

    mcp.mount()
    return app
