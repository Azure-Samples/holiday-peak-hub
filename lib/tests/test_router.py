"""Tests for routing strategy."""

import pytest
from holiday_peak_lib.agents.orchestration.router import RoutingStrategy


class TestRoutingStrategy:
    """Test RoutingStrategy functionality."""

    def test_create_router(self):
        """Test creating a router instance."""
        router = RoutingStrategy()
        assert router is not None

    def test_register_handler(self):
        """Test registering a handler."""
        router = RoutingStrategy()
        handler = lambda x: x
        router.register("test_intent", handler)
        assert "test_intent" in router._routes

    def test_register_multiple_handlers(self):
        """Test registering multiple handlers."""
        router = RoutingStrategy()
        router.register("intent1", lambda x: x)
        router.register("intent2", lambda y: y)
        assert len(router._routes) == 2

    @pytest.mark.asyncio
    async def test_route_to_registered_handler(self):
        """Test routing to a registered handler."""
        router = RoutingStrategy()

        async def handler(payload):
            return {"result": payload["value"] * 2}

        router.register("multiply", handler)
        result = await router.route("multiply", {"value": 5})
        assert result["result"] == 10

    @pytest.mark.asyncio
    async def test_route_to_unknown_intent_raises(self):
        """Test routing to unknown intent raises KeyError."""
        router = RoutingStrategy()
        with pytest.raises(KeyError, match="No handler for intent"):
            await router.route("unknown", {})

    @pytest.mark.asyncio
    async def test_route_with_complex_payload(self):
        """Test routing with complex payload."""
        router = RoutingStrategy()

        async def complex_handler(payload):
            return {
                "user": payload["user"],
                "processed": True,
                "items": len(payload.get("items", [])),
            }

        router.register("process", complex_handler)
        payload = {"user": "test_user", "items": [1, 2, 3, 4, 5]}
        result = await router.route("process", payload)
        assert result["user"] == "test_user"
        assert result["processed"] is True
        assert result["items"] == 5

    @pytest.mark.asyncio
    async def test_route_handler_can_be_overwritten(self):
        """Test that handlers can be overwritten."""
        router = RoutingStrategy()

        async def handler1(payload):
            return {"version": 1}

        async def handler2(payload):
            return {"version": 2}

        router.register("test", handler1)
        result1 = await router.route("test", {})
        assert result1["version"] == 1

        router.register("test", handler2)
        result2 = await router.route("test", {})
        assert result2["version"] == 2

    @pytest.mark.asyncio
    async def test_route_with_async_handler(self):
        """Test routing with async handler."""
        router = RoutingStrategy()

        async def async_handler(payload):
            # Simulate async operation
            return {"async": True, "data": payload}

        router.register("async_op", async_handler)
        result = await router.route("async_op", {"test": "value"})
        assert result["async"] is True
        assert result["data"]["test"] == "value"

    @pytest.mark.asyncio
    async def test_route_preserves_payload(self):
        """Test that routing preserves original payload."""
        router = RoutingStrategy()

        async def passthrough_handler(payload):
            return payload

        router.register("passthrough", passthrough_handler)
        original = {"key": "value", "nested": {"data": [1, 2, 3]}}
        result = await router.route("passthrough", original)
        assert result == original

    @pytest.mark.asyncio
    async def test_route_supports_sync_handler(self):
        """Test routing works for synchronous handlers too."""
        router = RoutingStrategy()

        def sync_handler(payload):
            return {"value": payload["value"] + 1}

        router.register("sync", sync_handler)
        result = await router.route("sync", {"value": 41})
        assert result["value"] == 42

    @pytest.mark.asyncio
    async def test_slm_first_uses_slm_for_simple_payload(self):
        """Test SLM-first path keeps simple requests on SLM."""
        router = RoutingStrategy(complexity_threshold=0.7)

        async def slm_handler(payload):
            return {"target": "slm", "payload": payload}

        async def llm_handler(payload):
            return {"target": "llm", "payload": payload}

        router.register_model_handlers(
            "semantic",
            slm_handler=slm_handler,
            llm_handler=llm_handler,
        )

        result = await router.route("semantic", {"query": "simple lookup"})
        assert result["target"] == "slm"

    @pytest.mark.asyncio
    async def test_slm_first_upgrades_by_complexity(self):
        """Test SLM-first path escalates to LLM for complex payloads."""
        router = RoutingStrategy(complexity_threshold=0.3)

        async def slm_handler(payload):
            return {"target": "slm"}

        async def llm_handler(payload):
            return {"target": "llm"}

        router.register_model_handlers(
            "complex",
            slm_handler=slm_handler,
            llm_handler=llm_handler,
        )

        result = await router.route(
            "complex",
            {
                "query": "Please analyze this order history, compare against inventory trends, and build a multi-step recommendation plan",
                "requires_multi_tool": True,
            },
        )
        assert result["target"] == "llm"

    @pytest.mark.asyncio
    async def test_slm_first_upgrades_by_token(self):
        """Test SLM-first path escalates when SLM explicitly asks upgrade."""
        router = RoutingStrategy(complexity_threshold=0.9)

        async def slm_handler(payload):
            return {"response": "upgrade"}

        async def llm_handler(payload):
            return {"target": "llm"}

        router.register_model_handlers(
            "needs-upgrade",
            slm_handler=slm_handler,
            llm_handler=llm_handler,
        )

        result = await router.route("needs-upgrade", {"query": "short"})
        assert result["target"] == "llm"

    @pytest.mark.asyncio
    async def test_slm_first_without_llm_returns_slm(self):
        """Test SLM-only registration still returns SLM result."""
        router = RoutingStrategy(complexity_threshold=0.1)

        async def slm_handler(payload):
            return {"target": "slm"}

        router.register_model_handlers("slm-only", slm_handler=slm_handler)
        result = await router.route(
            "slm-only",
            {"query": "complex payload that would otherwise trigger upgrade"},
        )
        assert result["target"] == "slm"
