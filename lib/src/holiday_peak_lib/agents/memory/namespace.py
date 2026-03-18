"""Namespace helpers for memory key isolation and legacy compatibility reads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Protocol

NAMESPACE_VERSION = "v1"
DEFAULT_TENANT_ID = "public"
DEFAULT_SESSION_ID = "anonymous"


class HotMemoryProtocol(Protocol):
    """Protocol for hot-memory compatibility read/write operations."""

    async def get(self, key: str) -> Any: ...

    async def set(self, key: str, value: Any, ttl_seconds: int = 900) -> None: ...


@dataclass(frozen=True)
class NamespaceContext:
    """Canonical namespace context for memory key generation."""

    service: str
    tenant_id: str
    session_id: str


def resolve_namespace_context(
    request: Mapping[str, Any],
    service_name: str,
    *,
    default_tenant_id: str = DEFAULT_TENANT_ID,
    default_session_id: str = DEFAULT_SESSION_ID,
    session_fallback: str | None = None,
) -> NamespaceContext:
    """Build namespace context from request payload with safe defaults."""

    tenant_id = _clean_token(
        request.get("tenant_id") or request.get("tenant") or default_tenant_id,
        fallback=default_tenant_id,
    )
    session_id = _clean_token(
        request.get("session_id")
        or request.get("session")
        or session_fallback
        or default_session_id,
        fallback=default_session_id,
    )
    service = _clean_token(service_name, fallback="unknown-service")
    return NamespaceContext(service=service, tenant_id=tenant_id, session_id=session_id)


def build_canonical_memory_key(context: NamespaceContext, logical_key: str) -> str:
    """Build canonical memory key including service, tenant, and session."""

    key_token = _clean_token(logical_key, fallback="unknown-key")
    return (
        f"{NAMESPACE_VERSION}"
        f"|svc={context.service}"
        f"|ten={context.tenant_id}"
        f"|ses={context.session_id}"
        f"|key={key_token}"
    )


async def read_hot_with_compatibility(
    hot_memory: HotMemoryProtocol,
    canonical_key: str,
    legacy_keys: Iterable[str],
    *,
    ttl_seconds: int,
) -> Any:
    """Read canonical key first, then fallback to legacy keys and promote."""

    canonical_value = await hot_memory.get(canonical_key)
    if canonical_value is not None:
        return canonical_value

    for legacy_key in legacy_keys:
        legacy_value = await hot_memory.get(legacy_key)
        if legacy_value is None:
            continue
        await hot_memory.set(
            key=canonical_key,
            value=legacy_value,
            ttl_seconds=ttl_seconds,
        )
        return legacy_value
    return None


def _clean_token(value: Any, *, fallback: str) -> str:
    text = str(value).strip() if value is not None else ""
    text = text.replace("|", "_")
    return text or fallback
