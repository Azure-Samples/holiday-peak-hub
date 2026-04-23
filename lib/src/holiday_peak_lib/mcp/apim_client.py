"""APIM MCP discovery client for agent-to-agent tool invocations.

Follows ADR-031 (observability), ADR-035 (URL convention), and ADR-036 (governed interfaces).
"""

from __future__ import annotations

import logging
import os
import time
from inspect import isawaitable
from typing import Any, Awaitable, Callable

import httpx
from holiday_peak_lib.self_healing.models import FailureSignal, SurfaceType
from holiday_peak_lib.utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from holiday_peak_lib.utils.correlation import CORRELATION_HEADER, get_correlation_id
from pydantic import BaseModel

logger = logging.getLogger(__name__)

FailureCallback = Callable[[FailureSignal], Awaitable[Any] | Any]


class McpToolDescriptor(BaseModel):
    """Describes a discovered MCP tool."""

    service: str
    tool_name: str
    url: str


class McpInvocationResult(BaseModel):
    """Result of an MCP tool invocation."""

    success: bool
    status_code: int
    data: dict[str, Any] | None = None
    error: str | None = None
    latency_ms: float = 0.0


class ApimMcpClient:
    """Client for discovering and invoking MCP tools via the APIM gateway.

    Follows ADR-035 URL convention: ``POST /agents/{service}/mcp/{tool}``.

    Each target service gets its own :class:`CircuitBreaker` so that one
    failing agent does not block calls to others.
    """

    def __init__(
        self,
        *,
        apim_base_url: str,
        caller_service: str,
        timeout: float = 10.0,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        on_failure: FailureCallback | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._apim_base_url = apim_base_url.rstrip("/")
        self._caller_service = caller_service
        self._timeout = timeout
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._on_failure = on_failure
        self._transport = transport
        self._breakers: dict[str, CircuitBreaker] = {}

    def tool_url(self, service: str, tool_name: str) -> str:
        """Build APIM MCP tool URL following ADR-035 convention."""
        return f"{self._apim_base_url}/agents/{service}/mcp/{tool_name}"

    def _get_breaker(self, service: str) -> CircuitBreaker:
        """Get or create a circuit breaker for the target service."""
        if service not in self._breakers:
            self._breakers[service] = CircuitBreaker(
                name=f"apim-mcp:{service}",
                failure_threshold=self._failure_threshold,
                recovery_timeout=self._recovery_timeout,
            )
        return self._breakers[service]

    async def _emit_failure(
        self,
        *,
        target_service: str,
        tool_name: str,
        status_code: int | None,
        error: Exception,
    ) -> None:
        if self._on_failure is None:
            return
        signal = FailureSignal(
            service_name=self._caller_service,
            surface=SurfaceType.MCP,
            component=f"apim-mcp:{target_service}/{tool_name}",
            status_code=status_code,
            error_type=type(error).__name__,
            error_message=str(error),
            metadata={
                "caller_service": self._caller_service,
                "target_service": target_service,
                "tool_name": tool_name,
            },
        )
        try:
            result = self._on_failure(signal)
            if isawaitable(result):
                await result
        except (AttributeError, TypeError, ValueError, RuntimeError):
            return

    async def invoke(
        self,
        service: str,
        tool_name: str,
        payload: dict[str, Any] | None = None,
        *,
        extra_headers: dict[str, str] | None = None,
    ) -> McpInvocationResult:
        """Invoke an MCP tool on a target agent via APIM.

        Propagates correlation IDs, uses per-service circuit breakers,
        emits self-healing ``FailureSignal`` on errors, and logs
        structured observability fields per ADR-031.
        """
        url = self.tool_url(service, tool_name)
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "X-Caller-Service": self._caller_service,
        }
        correlation_id = get_correlation_id()
        if correlation_id:
            headers[CORRELATION_HEADER] = correlation_id
        if extra_headers:
            headers.update(extra_headers)

        breaker = self._get_breaker(service)
        start = time.monotonic()

        try:
            result = await breaker.call(self._do_request, url, payload, headers)
        except CircuitBreakerOpenError:
            latency_ms = (time.monotonic() - start) * 1000
            logger.warning(
                "apim_mcp_invoke circuit_open"
                " correlation_id=%s caller_service=%s target_service=%s"
                " tool_name=%s latency_ms=%.1f status=503",
                correlation_id,
                self._caller_service,
                service,
                tool_name,
                latency_ms,
            )
            return McpInvocationResult(
                success=False,
                status_code=503,
                error=f"Circuit open for {service}",
                latency_ms=latency_ms,
            )
        except httpx.TimeoutException:
            latency_ms = (time.monotonic() - start) * 1000
            logger.warning(
                "apim_mcp_invoke timeout"
                " correlation_id=%s caller_service=%s target_service=%s"
                " tool_name=%s latency_ms=%.1f status=504",
                correlation_id,
                self._caller_service,
                service,
                tool_name,
                latency_ms,
            )
            return McpInvocationResult(
                success=False,
                status_code=504,
                error=f"Timeout invoking {service}/{tool_name}",
                latency_ms=latency_ms,
            )
        except httpx.HTTPStatusError as exc:
            latency_ms = (time.monotonic() - start) * 1000
            logger.warning(
                "apim_mcp_invoke http_error"
                " correlation_id=%s caller_service=%s target_service=%s"
                " tool_name=%s latency_ms=%.1f status=%d error=%s",
                correlation_id,
                self._caller_service,
                service,
                tool_name,
                latency_ms,
                exc.response.status_code,
                str(exc),
            )
            return McpInvocationResult(
                success=False,
                status_code=exc.response.status_code,
                error=str(exc),
                latency_ms=latency_ms,
            )
        except httpx.HTTPError as exc:
            latency_ms = (time.monotonic() - start) * 1000
            logger.warning(
                "apim_mcp_invoke transport_error"
                " correlation_id=%s caller_service=%s target_service=%s"
                " tool_name=%s latency_ms=%.1f status=502 error=%s",
                correlation_id,
                self._caller_service,
                service,
                tool_name,
                latency_ms,
                str(exc),
            )
            return McpInvocationResult(
                success=False,
                status_code=502,
                error=str(exc),
                latency_ms=latency_ms,
            )

        latency_ms = (time.monotonic() - start) * 1000
        result.latency_ms = latency_ms

        if result.success:
            logger.info(
                "apim_mcp_invoke ok"
                " correlation_id=%s caller_service=%s target_service=%s"
                " tool_name=%s latency_ms=%.1f status=%d",
                correlation_id,
                self._caller_service,
                service,
                tool_name,
                latency_ms,
                result.status_code,
            )
        else:
            logger.warning(
                "apim_mcp_invoke error"
                " correlation_id=%s caller_service=%s target_service=%s"
                " tool_name=%s latency_ms=%.1f status=%d error=%s",
                correlation_id,
                self._caller_service,
                service,
                tool_name,
                latency_ms,
                result.status_code,
                result.error,
            )
        return result

    async def _do_request(
        self,
        url: str,
        payload: dict[str, Any] | None,
        headers: dict[str, str],
    ) -> McpInvocationResult:
        """Execute the HTTP POST and convert the response."""
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                response = await client.post(url, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            await self._emit_failure(
                target_service=self._extract_service(url),
                tool_name=self._extract_tool(url),
                status_code=504,
                error=exc,
            )
            raise
        except httpx.HTTPError as exc:
            await self._emit_failure(
                target_service=self._extract_service(url),
                tool_name=self._extract_tool(url),
                status_code=502,
                error=exc,
            )
            raise

        if response.is_success:
            return McpInvocationResult(
                success=True,
                status_code=response.status_code,
                data=response.json(),
            )

        error_exc = httpx.HTTPStatusError(
            message=f"HTTP {response.status_code}",
            request=response.request,
            response=response,
        )
        await self._emit_failure(
            target_service=self._extract_service(url),
            tool_name=self._extract_tool(url),
            status_code=response.status_code,
            error=error_exc,
        )
        raise error_exc

    @staticmethod
    def _extract_service(url: str) -> str:
        """Extract service name from an APIM MCP URL."""
        parts = url.split("/agents/")
        if len(parts) > 1:
            return parts[1].split("/")[0]
        return "unknown"

    @staticmethod
    def _extract_tool(url: str) -> str:
        """Extract tool name from an APIM MCP URL."""
        parts = url.split("/mcp/")
        if len(parts) > 1:
            return parts[1].split("/")[0].split("?")[0]
        return "unknown"


def create_apim_mcp_client(
    *,
    caller_service: str,
    apim_base_url: str | None = None,
    on_failure: FailureCallback | None = None,
) -> ApimMcpClient | None:
    """Create client from environment. Returns ``None`` if APIM base URL is not configured."""
    url = apim_base_url or os.environ.get("APIM_BASE_URL") or os.environ.get("AGENT_APIM_BASE_URL")
    if not url:
        return None
    return ApimMcpClient(
        apim_base_url=url,
        caller_service=caller_service,
        on_failure=on_failure,
    )
