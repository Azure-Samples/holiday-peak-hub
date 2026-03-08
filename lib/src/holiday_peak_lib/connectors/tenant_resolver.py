"""Tenant context resolution and tenant-aware connector caching."""

from __future__ import annotations

import asyncio
from contextvars import ContextVar, Token
from typing import Awaitable, Callable

from fastapi import Request
from holiday_peak_lib.connectors.registry import ConnectorRegistry
from holiday_peak_lib.connectors.tenant_config import TenantConfigStore, normalize_tenant_id
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response


class TenantContext(BaseModel):
    """Context propagated for multi-tenant request handling."""

    tenant_id: str
    source: str
    request_id: str | None = None


TenantContextResolver = Callable[
    [Request], Awaitable[TenantContext | str | None] | TenantContext | str | None
]


_tenant_context_var: ContextVar[TenantContext | None] = ContextVar(
    "tenant_context",
    default=None,
)


def get_current_tenant_context() -> TenantContext | None:
    """Return tenant context for the current async execution context."""
    return _tenant_context_var.get()


def set_current_tenant_context(context: TenantContext) -> Token[TenantContext | None]:
    """Set tenant context and return contextvar token for cleanup."""
    return _tenant_context_var.set(context)


def reset_current_tenant_context(token: Token[TenantContext | None]) -> None:
    """Reset tenant context using a token captured by ``set_current_tenant_context``."""
    _tenant_context_var.reset(token)


class TenantResolver:
    """Resolve tenant identity from request headers/query/defaults."""

    def __init__(
        self,
        *,
        header_name: str = "x-tenant-id",
        query_param: str = "tenant_id",
        default_tenant: str | None = None,
        custom_resolver: TenantContextResolver | None = None,
    ) -> None:
        self._header_name = header_name
        self._query_param = query_param
        self._default_tenant = default_tenant
        self._custom_resolver = custom_resolver

    async def resolve(self, request: Request) -> TenantContext:
        """Resolve tenant context from request metadata."""
        if self._custom_resolver is not None:
            custom = self._custom_resolver(request)
            resolved = await custom if asyncio.iscoroutine(custom) else custom
            if isinstance(resolved, TenantContext):
                resolved.tenant_id = normalize_tenant_id(resolved.tenant_id)
                return resolved
            if isinstance(resolved, str) and resolved.strip():
                return TenantContext(
                    tenant_id=normalize_tenant_id(resolved),
                    source="custom",
                    request_id=request.headers.get("x-request-id"),
                )

        header_value = request.headers.get(self._header_name)
        if header_value and header_value.strip():
            return TenantContext(
                tenant_id=normalize_tenant_id(header_value),
                source="header",
                request_id=request.headers.get("x-request-id"),
            )

        query_value = request.query_params.get(self._query_param)
        if query_value and query_value.strip():
            return TenantContext(
                tenant_id=normalize_tenant_id(query_value),
                source="query",
                request_id=request.headers.get("x-request-id"),
            )

        if self._default_tenant and self._default_tenant.strip():
            return TenantContext(
                tenant_id=normalize_tenant_id(self._default_tenant),
                source="default",
                request_id=request.headers.get("x-request-id"),
            )

        raise ValueError(
            f"Unable to resolve tenant context. Provide '{self._header_name}' header "
            f"or '{self._query_param}' query parameter."
        )


class TenantContextMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that resolves and propagates tenant context."""

    def __init__(self, app, tenant_resolver: TenantResolver) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self._tenant_resolver = tenant_resolver

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        try:
            context = await self._tenant_resolver.resolve(request)
        except ValueError as exc:
            return JSONResponse(status_code=400, content={"detail": str(exc)})
        request.state.tenant_context = context

        token = set_current_tenant_context(context)
        try:
            return await call_next(request)
        finally:
            reset_current_tenant_context(token)


class TenantConnectorResolver:
    """Resolve tenant-scoped connectors with per-instance pooling cache."""

    def __init__(
        self,
        *,
        registry: ConnectorRegistry,
        config_store: TenantConfigStore,
        tenant_resolver: TenantResolver | None = None,
    ) -> None:
        self._registry = registry
        self._config_store = config_store
        self._tenant_resolver = tenant_resolver or TenantResolver()
        self._connector_cache: dict[str, object] = {}
        self._lock = asyncio.Lock()

    async def resolve_context(self, request: Request) -> TenantContext:
        """Resolve tenant context from an HTTP request."""
        return await self._tenant_resolver.resolve(request)

    async def get_connector(self, tenant_id: str, domain: str) -> object:
        """Get or create tenant/domain connector and cache it for pooling reuse."""
        runtime = await self._config_store.resolve_connector_runtime_config(tenant_id, domain)

        async with self._lock:
            cached = self._connector_cache.get(runtime.cache_key)
            if cached is not None:
                return cached

            existing = await self._registry.get_runtime(runtime.cache_key)
            if existing is not None:
                self._connector_cache[runtime.cache_key] = existing
                return existing

            created = await self._registry.create(
                runtime.domain,
                vendor=runtime.vendor,
                name=runtime.cache_key,
                init_kwargs=runtime.init_kwargs,
            )
            self._connector_cache[runtime.cache_key] = created
            return created

    async def get_connector_from_request(self, request: Request, domain: str) -> object:
        """Resolve tenant from request and return connector for requested domain."""
        context = await self.resolve_context(request)
        return await self.get_connector(context.tenant_id, domain)
