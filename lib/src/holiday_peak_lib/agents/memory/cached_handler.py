"""Cached handler utilities for agents with hot-memory integration.

Provides a reusable pattern for request-level caching that any agent can
adopt with minimal boilerplate.  The pattern:

1. Resolve namespace context from the request.
2. Check hot cache for existing result.
3. On cache hit → return immediately.
4. On cache miss → execute the handler logic.
5. Store result in hot cache with configurable TTL.
6. Inject ``session_id`` into the request for Foundry session threading.

Usage in an agent::

    from holiday_peak_lib.agents.memory.cached_handler import (
        CacheConfig,
        resolve_cache_key,
        try_cache_read,
        cache_write,
    )

    async def handle(self, request):
        cache_cfg = CacheConfig(service=self.service_name, entity_prefix="order")
        cache_key = resolve_cache_key(request, cache_cfg)
        cached = await try_cache_read(self.hot_memory, cache_key)
        if cached is not None:
            return cached
        # ... do work ...
        await cache_write(self.hot_memory, cache_key, result, cache_cfg.ttl_seconds)
        return result
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .namespace import (
    NamespaceContext,
    build_canonical_memory_key,
    read_hot_with_compatibility,
    resolve_namespace_context,
)


@dataclass(frozen=True)
class CacheConfig:
    """Configuration for cached handler behavior."""

    service: str
    entity_prefix: str
    ttl_seconds: int = 300
    entity_key_field: str = "entity_id"
    session_key_field: str = "session_id"
    fallback_entity_fields: tuple[str, ...] = ("sku", "order_id", "user_id", "shipment_id")


def resolve_cache_key(
    request: dict[str, Any],
    config: CacheConfig,
) -> str | None:
    """Resolve a canonical cache key from the request.

    Returns None if no identifiable entity is found in the request.
    """
    entity_id = request.get(config.entity_key_field)
    if not entity_id:
        for field in config.fallback_entity_fields:
            entity_id = request.get(field)
            if entity_id:
                break
    if not entity_id:
        return None

    namespace_context = resolve_namespace_context(
        request,
        config.service,
        session_fallback=str(entity_id),
    )
    return build_canonical_memory_key(
        namespace_context,
        f"{config.entity_prefix}:{entity_id}",
    )


async def try_cache_read(
    hot_memory: Any | None,
    cache_key: str | None,
    *,
    legacy_keys: list[str] | None = None,
    ttl_seconds: int = 300,
) -> Any | None:
    """Attempt to read from hot cache. Returns None on miss or if memory unavailable."""
    if hot_memory is None or cache_key is None:
        return None
    return await read_hot_with_compatibility(
        hot_memory,
        cache_key,
        legacy_keys or [],
        ttl_seconds=ttl_seconds,
    )


async def cache_write(
    hot_memory: Any | None,
    cache_key: str | None,
    value: Any,
    ttl_seconds: int = 300,
) -> None:
    """Write a result to hot cache if memory is available."""
    if hot_memory is None or cache_key is None or value is None:
        return
    await hot_memory.set(key=cache_key, value=value, ttl_seconds=ttl_seconds)


def inject_session_id(request: dict[str, Any], config: CacheConfig) -> dict[str, Any]:
    """Ensure request contains a session_id for Foundry session threading.

    If the request already has a session_id, it is preserved. Otherwise,
    a deterministic session_id is derived from the entity identifier to
    enable conversation continuity across multiple invoke_model calls
    within the same handle() execution.
    """
    if request.get(config.session_key_field):
        return request

    entity_id = request.get(config.entity_key_field)
    if not entity_id:
        for field in config.fallback_entity_fields:
            entity_id = request.get(field)
            if entity_id:
                break
    if entity_id:
        request = {**request, config.session_key_field: f"{config.service}:{entity_id}"}
    return request
