"""Tests for routing strategy."""
import pytest
from unittest.mock import AsyncMock
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
                "items": len(payload.get("items", []))
            }
        
        router.register("process", complex_handler)
        payload = {
            "user": "test_user",
            "items": [1, 2, 3, 4, 5]
        }
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
