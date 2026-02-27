"""MCP adapter for external (3rd party) API integrations."""

from __future__ import annotations

from typing import Any

import httpx
from holiday_peak_lib.adapters.mcp_adapter import BaseMCPAdapter


class BaseExternalAPIAdapter(BaseMCPAdapter):
    """Base adapter for exposing 3rd party API calls as MCP tools."""

    def __init__(
        self,
        api_name: str,
        *,
        base_url: str,
        api_key: str | None = None,
        tool_prefix: str | None = None,
        timeout: float = 5.0,
        auth_header: str = "Authorization",
        auth_scheme: str = "Bearer",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        prefix = tool_prefix or f"/external/{api_name}"
        super().__init__(name=f"{api_name}-adapter", tool_prefix=prefix)
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._auth_header = auth_header
        self._auth_scheme = auth_scheme
        self._timeout = timeout
        self._transport = transport

    def add_api_tool(self, name: str, method: str, endpoint: str) -> None:
        """Register a tool that maps payload to an external API request."""

        async def handler(payload: dict[str, Any]) -> dict[str, Any]:
            json_payload = payload.get("json")
            params = payload.get("params")
            headers = payload.get("headers")
            return await self._request(
                method,
                endpoint,
                json_payload=json_payload,
                params=params,
                headers=headers,
            )

        self.add_tool(f"/{name}", handler)

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        json_payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        request_headers = dict(headers or {})
        if self._api_key:
            request_headers.setdefault(
                self._auth_header,
                f"{self._auth_scheme} {self._api_key}",
            )
        async with httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
            headers=request_headers,
            transport=self._transport,
        ) as client:
            response = await client.request(method, endpoint, json=json_payload, params=params)
            response.raise_for_status()
            return response.json()
