"""Tests for ApimMcpClient — APIM MCP discovery client."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest
from holiday_peak_lib.mcp.apim_client import (
    ApimMcpClient,
    McpInvocationResult,
    McpToolDescriptor,
    create_apim_mcp_client,
)
from holiday_peak_lib.self_healing.models import FailureSignal
from holiday_peak_lib.utils.correlation import clear_correlation_id, set_correlation_id

APIM_BASE = "https://apim.example.com"
CALLER = "crm-profile-aggregation"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_transport(
    status_code: int = 200,
    json_body: dict[str, Any] | None = None,
    *,
    raise_timeout: bool = False,
) -> httpx.MockTransport:
    """Return an httpx.MockTransport that returns a fixed response."""

    def handler(request: httpx.Request) -> httpx.Response:
        if raise_timeout:
            raise httpx.ReadTimeout("simulated timeout")
        body = json_body if json_body is not None else {}
        return httpx.Response(status_code, json=body)

    return httpx.MockTransport(handler)


def _make_client(
    transport: httpx.AsyncBaseTransport | None = None,
    on_failure: Any = None,
    **kwargs: Any,
) -> ApimMcpClient:
    defaults: dict[str, Any] = {
        "apim_base_url": APIM_BASE,
        "caller_service": CALLER,
        "timeout": 5.0,
        "failure_threshold": 3,
        "recovery_timeout": 10.0,
    }
    defaults.update(kwargs)
    return ApimMcpClient(
        **defaults,
        on_failure=on_failure,
        transport=transport,
    )


# ---------------------------------------------------------------------------
# 1. URL construction
# ---------------------------------------------------------------------------


class TestToolUrl:
    def test_basic_url(self) -> None:
        client = _make_client()
        url = client.tool_url("cart-intelligence", "get_recommendations")
        assert url == f"{APIM_BASE}/agents/cart-intelligence/mcp/get_recommendations"

    def test_trailing_slash_stripped(self) -> None:
        client = _make_client(apim_base_url=f"{APIM_BASE}/")
        url = client.tool_url("svc", "tool")
        assert url == f"{APIM_BASE}/agents/svc/mcp/tool"


# ---------------------------------------------------------------------------
# 2. Successful invocation
# ---------------------------------------------------------------------------


class TestSuccessfulInvocation:
    @pytest.mark.asyncio
    async def test_returns_success_result(self) -> None:
        body = {"items": [1, 2, 3]}
        transport = _mock_transport(200, body)
        client = _make_client(transport=transport)

        result = await client.invoke("cart", "get_items", {"user_id": "u1"})

        assert result.success is True
        assert result.status_code == 200
        assert result.data == body
        assert result.error is None

    @pytest.mark.asyncio
    async def test_empty_payload_sends_null_json(self) -> None:
        transport = _mock_transport(200, {"ok": True})
        client = _make_client(transport=transport)

        result = await client.invoke("svc", "tool")

        assert result.success is True


# ---------------------------------------------------------------------------
# 3. HTTP error handling
# ---------------------------------------------------------------------------


class TestHttpErrorHandling:
    @pytest.mark.asyncio
    async def test_4xx_returns_failure(self) -> None:
        transport = _mock_transport(422, {"detail": "bad payload"})
        client = _make_client(transport=transport)

        result = await client.invoke("svc", "validate", {"x": 1})

        assert result.success is False
        assert result.status_code == 422

    @pytest.mark.asyncio
    async def test_5xx_returns_failure(self) -> None:
        transport = _mock_transport(500, {"error": "internal"})
        client = _make_client(transport=transport)

        result = await client.invoke("svc", "tool")

        assert result.success is False
        assert result.status_code == 500


# ---------------------------------------------------------------------------
# 4. Correlation ID propagation
# ---------------------------------------------------------------------------


class TestCorrelationId:
    @pytest.mark.asyncio
    async def test_correlation_id_included_in_headers(self) -> None:
        captured_headers: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured_headers.update(dict(request.headers))
            return httpx.Response(200, json={})

        transport = httpx.MockTransport(handler)
        client = _make_client(transport=transport)

        cid = set_correlation_id("test-cid-abc")
        try:
            await client.invoke("svc", "tool")
        finally:
            clear_correlation_id()

        assert captured_headers.get("x-correlation-id") == cid

    @pytest.mark.asyncio
    async def test_no_correlation_header_when_unset(self) -> None:
        captured_headers: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured_headers.update(dict(request.headers))
            return httpx.Response(200, json={})

        transport = httpx.MockTransport(handler)
        client = _make_client(transport=transport)

        clear_correlation_id()
        await client.invoke("svc", "tool")

        assert "x-correlation-id" not in captured_headers


# ---------------------------------------------------------------------------
# 5. Circuit breaker integration
# ---------------------------------------------------------------------------


class TestCircuitBreaker:
    @pytest.mark.asyncio
    async def test_per_service_breakers(self) -> None:
        transport = _mock_transport(200, {})
        client = _make_client(transport=transport)

        await client.invoke("svc-a", "tool")
        await client.invoke("svc-b", "tool")

        assert "svc-a" in client._breakers
        assert "svc-b" in client._breakers
        assert client._breakers["svc-a"] is not client._breakers["svc-b"]

    @pytest.mark.asyncio
    async def test_circuit_open_returns_503(self) -> None:
        transport = _mock_transport(500, {"error": "fail"})
        client = _make_client(transport=transport, failure_threshold=2)

        # Trip the breaker
        await client.invoke("svc", "tool")
        await client.invoke("svc", "tool")

        # Now circuit should be open
        result = await client.invoke("svc", "tool")
        assert result.success is False
        assert result.status_code == 503
        assert "Circuit open" in (result.error or "")


# ---------------------------------------------------------------------------
# 6. Self-healing signal emission
# ---------------------------------------------------------------------------


class TestSelfHealingSignal:
    @pytest.mark.asyncio
    async def test_failure_signal_emitted_on_http_error(self) -> None:
        signals: list[FailureSignal] = []

        def on_fail(sig: FailureSignal) -> None:
            signals.append(sig)

        transport = _mock_transport(500, {"error": "boom"})
        client = _make_client(transport=transport, on_failure=on_fail)

        result = await client.invoke("target-svc", "broken_tool")

        assert result.success is False
        assert len(signals) == 1
        sig = signals[0]
        assert sig.service_name == CALLER
        assert sig.surface == "mcp"
        assert "target-svc" in sig.component
        assert "broken_tool" in sig.component
        assert sig.status_code == 500

    @pytest.mark.asyncio
    async def test_async_failure_callback(self) -> None:
        signals: list[FailureSignal] = []
        callback = AsyncMock(side_effect=lambda sig: signals.append(sig))

        transport = _mock_transport(500, {"error": "fail"})
        client = _make_client(transport=transport, on_failure=callback)

        await client.invoke("svc", "tool")

        callback.assert_called_once()
        assert len(signals) == 1


# ---------------------------------------------------------------------------
# 7. Timeout handling
# ---------------------------------------------------------------------------


class TestTimeoutHandling:
    @pytest.mark.asyncio
    async def test_timeout_returns_504(self) -> None:
        transport = _mock_transport(raise_timeout=True)
        client = _make_client(transport=transport)

        result = await client.invoke("svc", "tool")

        assert result.success is False
        assert result.status_code == 504
        assert "Timeout" in (result.error or "")
        assert result.latency_ms > 0

    @pytest.mark.asyncio
    async def test_timeout_emits_failure_signal(self) -> None:
        signals: list[FailureSignal] = []

        def on_fail(sig: FailureSignal) -> None:
            signals.append(sig)

        transport = _mock_transport(raise_timeout=True)
        client = _make_client(transport=transport, on_failure=on_fail)

        result = await client.invoke("svc", "tool")

        assert result.success is False
        assert len(signals) == 1
        assert signals[0].status_code == 504


# ---------------------------------------------------------------------------
# 8. Factory function
# ---------------------------------------------------------------------------


class TestFactory:
    def test_returns_client_with_explicit_url(self) -> None:
        client = create_apim_mcp_client(
            caller_service=CALLER,
            apim_base_url="https://gw.example.com",
        )
        assert client is not None
        assert isinstance(client, ApimMcpClient)

    def test_returns_none_without_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("APIM_BASE_URL", raising=False)
        monkeypatch.delenv("AGENT_APIM_BASE_URL", raising=False)

        client = create_apim_mcp_client(caller_service=CALLER)
        assert client is None

    def test_reads_apim_base_url_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("APIM_BASE_URL", "https://env.example.com")
        monkeypatch.delenv("AGENT_APIM_BASE_URL", raising=False)

        client = create_apim_mcp_client(caller_service=CALLER)
        assert client is not None

    def test_reads_agent_apim_base_url_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("APIM_BASE_URL", raising=False)
        monkeypatch.setenv("AGENT_APIM_BASE_URL", "https://agent-env.example.com")

        client = create_apim_mcp_client(caller_service=CALLER)
        assert client is not None


# ---------------------------------------------------------------------------
# 9. Latency measurement
# ---------------------------------------------------------------------------


class TestLatency:
    @pytest.mark.asyncio
    async def test_latency_ms_populated(self) -> None:
        transport = _mock_transport(200, {"ok": True})
        client = _make_client(transport=transport)

        result = await client.invoke("svc", "tool")

        assert result.latency_ms > 0


# ---------------------------------------------------------------------------
# 10. Extra headers
# ---------------------------------------------------------------------------


class TestExtraHeaders:
    @pytest.mark.asyncio
    async def test_extra_headers_merged(self) -> None:
        captured_headers: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured_headers.update(dict(request.headers))
            return httpx.Response(200, json={})

        transport = httpx.MockTransport(handler)
        client = _make_client(transport=transport)

        await client.invoke(
            "svc",
            "tool",
            extra_headers={"X-Custom": "value123"},
        )

        assert captured_headers.get("x-custom") == "value123"
        assert captured_headers.get("x-caller-service") == CALLER


# ---------------------------------------------------------------------------
# 11. McpToolDescriptor model
# ---------------------------------------------------------------------------


class TestMcpToolDescriptor:
    def test_serialization(self) -> None:
        desc = McpToolDescriptor(
            service="cart",
            tool_name="get_items",
            url="https://apim.example.com/agents/cart/mcp/get_items",
        )
        data = desc.model_dump()
        assert data["service"] == "cart"
        assert data["tool_name"] == "get_items"
        assert "/agents/cart/mcp/get_items" in data["url"]
