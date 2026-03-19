"""MCP adapter exposing CRUD operations as tools."""

from __future__ import annotations

from typing import Any

import httpx
from holiday_peak_lib.adapters.mcp_adapter import BaseMCPAdapter
from holiday_peak_lib.utils.correlation import CORRELATION_HEADER, get_correlation_id


class BaseCRUDAdapter(BaseMCPAdapter):
    """Adapter that exposes CRUD operations via MCP tools."""

    def __init__(
        self,
        crud_base_url: str,
        *,
        api_prefix: str = "/api",
        tool_prefix: str = "/crud",
        timeout: float = 5.0,
        headers: dict[str, str] | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        super().__init__(name="crud-adapter", tool_prefix=tool_prefix)
        self._crud_base_url = crud_base_url.rstrip("/")
        self._api_prefix = api_prefix.rstrip("/")
        self._timeout = timeout
        self._headers = headers or {}
        self._transport = transport
        self._register_base_tools()

    def _register_base_tools(self) -> None:
        self.add_tool("/products/get", self._get_product)
        self.add_tool("/products/list", self._list_products)
        self.add_tool("/products/batch", self._get_products_batch)
        self.add_tool("/orders/get", self._get_order)
        self.add_tool("/orders/list", self._list_orders)
        self.add_tool("/orders/cancel", self._cancel_order)
        self.add_tool("/orders/update-status", self._update_order_status)
        self.add_tool("/cart/get", self._get_cart)
        self.add_tool("/cart/recommendations", self._get_cart_recommendations)
        self.add_tool("/users/me", self._get_current_user)
        self.add_tool("/inventory/get", self._get_inventory)
        self.add_tool("/tickets/create", self._create_ticket)

    def _endpoint(self, relative: str) -> str:
        if not relative.startswith("/"):
            relative = f"/{relative}"
        return f"{self._api_prefix}{relative}"

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        json_payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        headers = dict(self._headers)
        correlation_id = get_correlation_id()
        if correlation_id:
            headers[CORRELATION_HEADER] = correlation_id

        async with httpx.AsyncClient(
            base_url=self._crud_base_url,
            timeout=self._timeout,
            headers=headers,
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
            return await self._request("GET", self._endpoint(f"/products/{product_id}"))
        except httpx.HTTPError as exc:
            return {"error": "request_failed", "detail": str(exc)}

    async def _list_products(self, payload: dict[str, Any]) -> dict[str, Any]:
        params = payload.get("params")
        if not isinstance(params, dict):
            params = {"limit": int(payload.get("limit", 20))}
        try:
            products = await self._request("GET", self._endpoint("/products"), params=params)
            return {"items": products}
        except httpx.HTTPError as exc:
            return {"error": "request_failed", "detail": str(exc)}

    async def _get_products_batch(self, payload: dict[str, Any]) -> dict[str, Any]:
        product_ids = payload.get("product_ids") or payload.get("ids")
        if not product_ids:
            return {"error": "missing_field", "field": "product_ids"}
        items: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        for product_id in product_ids:
            result = await self._get_product({"product_id": product_id})
            if isinstance(result, dict) and result.get("error"):
                errors.append({"product_id": product_id, "error": result})
            else:
                items.append(result)
        return {"items": items, "errors": errors}

    async def _get_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        order_id = payload.get("order_id")
        if not order_id:
            return {"error": "missing_field", "field": "order_id"}
        try:
            return await self._request("GET", self._endpoint(f"/orders/{order_id}"))
        except httpx.HTTPError as exc:
            return {"error": "request_failed", "detail": str(exc)}

    async def _list_orders(self, payload: dict[str, Any]) -> dict[str, Any]:
        params = payload.get("params") if isinstance(payload.get("params"), dict) else None
        try:
            orders = await self._request("GET", self._endpoint("/orders"), params=params)
            return {"items": orders}
        except httpx.HTTPError as exc:
            return {"error": "request_failed", "detail": str(exc)}

    async def _cancel_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        order_id = payload.get("order_id")
        if not order_id:
            return {"error": "missing_field", "field": "order_id"}
        try:
            return await self._request("PATCH", self._endpoint(f"/orders/{order_id}/cancel"))
        except httpx.HTTPError as exc:
            return {"error": "request_failed", "detail": str(exc)}

    async def _update_order_status(self, payload: dict[str, Any]) -> dict[str, Any]:
        order_id = payload.get("order_id")
        status = payload.get("status")
        if not order_id:
            return {"error": "missing_field", "field": "order_id"}
        if not status:
            return {"error": "missing_field", "field": "status"}
        status_normalized = str(status).lower()
        if status_normalized not in {"cancel", "cancelled", "canceled"}:
            return {
                "error": "unsupported_operation",
                "detail": "CRUD API supports order cancellation via /orders/{id}/cancel only.",
                "supported_statuses": ["cancel", "cancelled", "canceled"],
            }
        return await self._cancel_order({"order_id": order_id})

    async def _get_cart(self, payload: dict[str, Any]) -> dict[str, Any]:
        params = payload.get("params") if isinstance(payload.get("params"), dict) else None
        try:
            return await self._request("GET", self._endpoint("/cart"), params=params)
        except httpx.HTTPError as exc:
            return {"error": "request_failed", "detail": str(exc)}

    async def _get_cart_recommendations(self, payload: dict[str, Any]) -> dict[str, Any]:
        params = payload.get("params") if isinstance(payload.get("params"), dict) else None
        try:
            return await self._request(
                "GET",
                self._endpoint("/cart/recommendations"),
                params=params,
            )
        except httpx.HTTPError as exc:
            return {"error": "request_failed", "detail": str(exc)}

    async def _get_current_user(self, payload: dict[str, Any]) -> dict[str, Any]:
        params = payload.get("params") if isinstance(payload.get("params"), dict) else None
        try:
            return await self._request("GET", self._endpoint("/users/me"), params=params)
        except httpx.HTTPError as exc:
            return {"error": "request_failed", "detail": str(exc)}

    async def _get_inventory(self, payload: dict[str, Any]) -> dict[str, Any]:
        sku = payload.get("sku")
        if not sku:
            return {"error": "missing_field", "field": "sku"}
        try:
            product = await self._request("GET", self._endpoint(f"/products/{sku}"))
            return {
                "sku": sku,
                "inventory": (product.get("inventory") if isinstance(product, dict) else None),
                "source": "products",
            }
        except httpx.HTTPError:
            return {
                "error": "unsupported_operation",
                "detail": "No dedicated inventory endpoint in CRUD API.",
            }

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
        return {
            "error": "unsupported_operation",
            "detail": "CRUD API currently exposes tickets read endpoints only (/api/staff/tickets).",
            "requested": {
                "user_id": user_id,
                "subject": subject,
                "description": description,
            },
        }
