"""Tests for memory namespace contract and compatibility reads."""

from unittest.mock import AsyncMock

import pytest
from holiday_peak_lib.agents.memory.namespace import (
    NamespaceContext,
    build_canonical_memory_key,
    read_hot_with_compatibility,
    resolve_namespace_context,
)


class TestNamespaceContract:
    """Tests for canonical namespace key generation."""

    def test_build_canonical_memory_key_shape(self):
        """Canonical keys include service, tenant, session, and logical key."""
        context = NamespaceContext(
            service="ecommerce-cart-intelligence",
            tenant_id="tenant-a",
            session_id="session-1",
        )

        key = build_canonical_memory_key(context, "cart")

        assert key == "v1|svc=ecommerce-cart-intelligence|ten=tenant-a|ses=session-1|key=cart"

    def test_collision_prevention_across_service_tenant_session(self):
        """Different service/tenant/session combinations produce unique keys."""
        key_service = build_canonical_memory_key(
            NamespaceContext("svc-a", "tenant-1", "session-1"),
            "shared-logical-key",
        )
        key_tenant = build_canonical_memory_key(
            NamespaceContext("svc-a", "tenant-2", "session-1"),
            "shared-logical-key",
        )
        key_session = build_canonical_memory_key(
            NamespaceContext("svc-a", "tenant-1", "session-2"),
            "shared-logical-key",
        )

        assert len({key_service, key_tenant, key_session}) == 3

    def test_resolve_namespace_context_with_defaults(self):
        """Namespace context falls back to defaults when values are absent."""
        context = resolve_namespace_context({}, "service-a")

        assert context.service == "service-a"
        assert context.tenant_id == "public"
        assert context.session_id == "anonymous"


class TestCompatibilityReads:
    """Tests for legacy compatibility read and promotion behavior."""

    @pytest.mark.asyncio
    async def test_compatibility_read_promotes_legacy_value(self):
        """When canonical misses and legacy hits, value is promoted to canonical."""
        hot_memory = AsyncMock()
        hot_memory.get = AsyncMock(side_effect=[None, {"legacy": True}])
        hot_memory.set = AsyncMock()

        result = await read_hot_with_compatibility(
            hot_memory,
            "v1|svc=svc-a|ten=tenant-1|ses=session-1|key=cart",
            ["cart:user-1"],
            ttl_seconds=600,
        )

        assert result == {"legacy": True}
        hot_memory.set.assert_awaited_once_with(
            key="v1|svc=svc-a|ten=tenant-1|ses=session-1|key=cart",
            value={"legacy": True},
            ttl_seconds=600,
        )

    @pytest.mark.asyncio
    async def test_compatibility_read_prefers_canonical(self):
        """Canonical key hit returns immediately without legacy read promotion."""
        hot_memory = AsyncMock()
        hot_memory.get = AsyncMock(return_value={"canonical": True})
        hot_memory.set = AsyncMock()

        result = await read_hot_with_compatibility(
            hot_memory,
            "v1|svc=svc-a|ten=tenant-1|ses=session-1|key=cart",
            ["cart:user-1"],
            ttl_seconds=600,
        )

        assert result == {"canonical": True}
        hot_memory.get.assert_awaited_once_with("v1|svc=svc-a|ten=tenant-1|ses=session-1|key=cart")
        hot_memory.set.assert_not_awaited()
