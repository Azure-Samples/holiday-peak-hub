"""MCP adapter exposing CRUD operations as tools."""
from __future__ import annotations

from typing import Any

import httpx

from holiday_peak_lib.adapters.mcp_adapter import BaseMCPAdapter


class BaseCRUDAdapter(BaseMCPAdapter):
    """Adapter that exposes CRUD operations via MCP tools."""

    def __init__(
        self,
        crud_base_url: str,
        *,
        tool_prefix: str = "/crud",
        timeout: float = 5.0,
        headers: dict[str, str] | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        super().__init__(name="crud-adapter", tool_prefix=tool_prefix)
        self._crud_base_url = crud_base_url.rstrip("/")
        self._timeout = timeout
        self._headers = headers or {}
        self._transport = transport
        self._register_base_tools()

    def _register_base_tools(self) -> None:
        self.add_tool("/products/get", self._get_product)
        self.add_tool("/products/batch", self._get_products_batch)
        self.add_tool("/orders/update-status", self._update_order_status)
        self.add_tool("/inventory/get", self._get_inventory)
        self.add_tool("/tickets/create", self._create_ticket)

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        json_payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(
            base_url=self._crud_base_url,
            timeout=self._timeout,
            headers=self._headers,
            transport=self._transport,
        ) as client:
            response = await client.request(method, endpoint, json=json_payload, params=params)
            response.raise_for_status()
            return response.json()

    async def _get_product(self, payload: dict[str, Any]) -> dict[str, Any]:
        product_id = payload.get("product_id") or payload.get("sku")
        if not product_id:
            return {"error": "missing_field", "field": "product_id"}
        try:
            return await self._request("GET", f"/products/{product_id}")
        except httpx.HTTPError as exc:
            return {"error": "request_failed", "detail": str(exc)}

    async def _get_products_batch(self, payload: dict[str, Any]) -> dict[str, Any]:
        product_ids = payload.get("product_ids") or payload.get("ids")
        if not product_ids:
            return {"error": "missing_field", "field": "product_ids"}
        try:
            return await self._request(
                "POST",
                "/products/batch",
                json_payload={"ids": product_ids},
            )
        except httpx.HTTPError as exc:
            return {"error": "request_failed", "detail": str(exc)}

    async def _update_order_status(self, payload: dict[str, Any]) -> dict[str, Any]:
        order_id = payload.get("order_id")
        status = payload.get("status")
        if not order_id:
            return {"error": "missing_field", "field": "order_id"}
        if not status:
            return {"error": "missing_field", "field": "status"}
        metadata = payload.get("metadata")
        body: dict[str, Any] = {"status": status}
        if metadata is not None:
            body["metadata"] = metadata
        try:
            return await self._request("PATCH", f"/orders/{order_id}", json_payload=body)
        except httpx.HTTPError as exc:
            return {"error": "request_failed", "detail": str(exc)}

    async def _get_inventory(self, payload: dict[str, Any]) -> dict[str, Any]:
        sku = payload.get("sku")
        if not sku:
            return {"error": "missing_field", "field": "sku"}
        try:
            return await self._request("GET", f"/inventory/{sku}")
        except httpx.HTTPError as exc:
            return {"error": "request_failed", "detail": str(exc)}

    async def _create_ticket(self, payload: dict[str, Any]) -> dict[str, Any]:
        user_id = payload.get("user_id")
        subject = payload.get("subject")
        description = payload.get("description")
        if not user_id:
            return {"error": "missing_field", "field": "user_id"}
        if not subject:
            return {"error": "missing_field", "field": "subject"}
        if not description:
            return {"error": "missing_field", "field": "description"}
        try:
            return await self._request(
                "POST",
                "/tickets",
                json_payload={
                    "user_id": user_id,
                    "subject": subject,
                    "description": description,
                },
            )
        except httpx.HTTPError as exc:
            return {"error": "request_failed", "detail": str(exc)}
