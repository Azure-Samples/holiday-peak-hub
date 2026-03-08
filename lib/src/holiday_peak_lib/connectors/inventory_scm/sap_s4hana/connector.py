"""SAP S/4HANA connector for Inventory & Supply Chain Management.

Extends :class:`BaseAdapter` for resilience (rate limiting, retries, circuit
breaker, caching) and implements :class:`InventoryConnectorBase` to satisfy
the canonical inventory interface.

OData endpoints used
--------------------
GET  /API_PRODUCT_SRV/A_Product
GET  /API_MATERIAL_STOCK_SRV/A_MatlStkInAcctMod
POST /API_PURCHASEORDER_PROCESS_SRV/A_PurchaseOrder
GET  /API_WAREHOUSE_LOC_STOCK/A_WarehouseStorageBinStock
"""

from __future__ import annotations

import os
from typing import Any, Iterable, Optional

import httpx
from holiday_peak_lib.adapters.base import AdapterError, BaseAdapter
from holiday_peak_lib.connectors.inventory_scm.sap_s4hana.auth import SAPS4HANAAuth
from holiday_peak_lib.connectors.inventory_scm.sap_s4hana.mappings import (
    map_material_stock_to_inventory,
    map_product_to_product_data,
    map_warehouse_bin_stock_to_inventory,
)
from holiday_peak_lib.integrations.contracts import (
    InventoryConnectorBase,
    InventoryData,
    ProductData,
)

_DEFAULT_PAGE_SIZE = 100
_ODATA_JSON_HEADERS = {"Accept": "application/json"}


class SAPS4HANAConnector(BaseAdapter, InventoryConnectorBase):
    """Connector for SAP S/4HANA REST/OData v4 APIs.

    Authentication
    --------------
    Configure via environment variables (see :mod:`auth`).  API key takes
    precedence; OAuth 2.0 client credentials are used as fallback.

    Environment variables
    ---------------------
    SAP_S4HANA_BASE_URL      API base URL (required)
    SAP_S4HANA_TOKEN_URL     OAuth 2.0 token endpoint
    SAP_S4HANA_CLIENT_ID     OAuth 2.0 client ID
    SAP_S4HANA_CLIENT_SECRET OAuth 2.0 client secret
    SAP_S4HANA_API_KEY       API key
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        auth: SAPS4HANAAuth | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        **adapter_kwargs: Any,
    ) -> None:
        super().__init__(**adapter_kwargs)
        self._base_url = (base_url or os.environ.get("SAP_S4HANA_BASE_URL", "")).rstrip("/")
        self._auth = auth or SAPS4HANAAuth(transport=transport)
        self._transport = transport

    # ------------------------------------------------------------------
    # BaseAdapter hooks
    # ------------------------------------------------------------------

    async def _connect_impl(self, **kwargs: Any) -> None:
        """Verify connectivity by calling the health check endpoint."""
        await self.health()

    async def _fetch_impl(self, query: dict[str, Any]) -> Iterable[dict[str, Any]]:
        """Execute a generic OData GET request.

        Parameters in *query*
        ---------------------
        endpoint : str   Relative path (required)
        params   : dict  OData query params ($filter, $top, etc.)
        """
        endpoint: str = query.get("endpoint", "")
        params: dict[str, Any] = dict(query.get("params") or {})
        return await self._odata_get(endpoint, params=params)

    async def _upsert_impl(self, payload: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Execute a generic OData POST request.

        Keys in *payload*
        -----------------
        endpoint : str   Relative path (required)
        data     : dict  JSON body
        """
        endpoint: str = payload.get("endpoint", "")
        data: dict[str, Any] = dict(payload.get("data") or {})
        return await self._odata_post(endpoint, data=data)

    async def _delete_impl(self, identifier: str) -> bool:
        """Execute a DELETE request; *identifier* is the relative URL path."""
        headers = await self._auth.get_headers()
        headers.update(_ODATA_JSON_HEADERS)
        async with httpx.AsyncClient(
            base_url=self._base_url,
            headers=headers,
            transport=self._transport,
        ) as client:
            response = await client.delete(identifier)
            if response.status_code == 404:
                return False
            response.raise_for_status()
            return True

    # ------------------------------------------------------------------
    # InventoryConnectorBase implementation
    # ------------------------------------------------------------------

    async def get_inventory(
        self,
        sku: str,
        location_id: str | None = None,
    ) -> list[InventoryData]:
        """Fetch stock levels for *sku*, optionally filtered by *location_id*.

        Calls ``/API_MATERIAL_STOCK_SRV/A_MatlStkInAcctMod``.
        """
        odata_filter = f"Material eq '{sku}'"
        if location_id:
            odata_filter += f" and Plant eq '{location_id}'"

        records = await self._odata_get(
            "/API_MATERIAL_STOCK_SRV/A_MatlStkInAcctMod",
            params={"$filter": odata_filter, "$format": "json"},
        )
        return [map_material_stock_to_inventory(r) for r in records]

    async def get_available_to_promise(self, sku: str, quantity: int) -> list[dict]:
        """Return locations that can fulfil *quantity* units of *sku*.

        Reads unrestricted stock across all plants, then filters to those
        with sufficient available quantity.
        """
        all_inventory = await self.get_inventory(sku)
        return [
            {
                "location_id": inv.location_id,
                "location_name": inv.location_name,
                "available_qty": inv.available_qty,
                "fulfillable": inv.available_qty >= quantity,
            }
            for inv in all_inventory
        ]

    async def reserve_inventory(
        self,
        sku: str,
        location_id: str,
        quantity: int,
        reference_id: str,
    ) -> dict:
        """Create a soft reservation by posting a purchase order.

        Posts to ``/API_PURCHASEORDER_PROCESS_SRV/A_PurchaseOrder``.
        """
        body = {
            "PurchaseOrderType": "NB",
            "PurchasingOrganization": location_id,
            "PurchasingGroup": "001",
            "to_PurchaseOrderItem": {
                "results": [
                    {
                        "PurchaseOrderItem": "00010",
                        "Material": sku,
                        "Plant": location_id,
                        "OrderQuantity": str(quantity),
                        "PurchaseOrderItemText": f"Reservation {reference_id}",
                    }
                ]
            },
        }
        result = await self._odata_post(
            "/API_PURCHASEORDER_PROCESS_SRV/A_PurchaseOrder",
            data=body,
        )
        return {
            "reservation_id": result.get("PurchaseOrder") if result else None,
            "sku": sku,
            "location_id": location_id,
            "quantity": quantity,
            "reference_id": reference_id,
            "raw": result,
        }

    async def release_reservation(self, reservation_id: str) -> bool:
        """Release a purchase order / reservation by its SAP document number."""
        path = f"/API_PURCHASEORDER_PROCESS_SRV/A_PurchaseOrder('{reservation_id}')"
        return await self.delete(path)

    async def get_replenishment_recommendations(
        self,
        location_id: str | None = None,
    ) -> list[dict]:
        """Return items whose stock has fallen below the reorder threshold.

        Reads bin-level stock via
        ``/API_WAREHOUSE_LOC_STOCK/A_WarehouseStorageBinStock``
        and filters those where available quantity < reorder point.
        """
        params: dict[str, Any] = {"$format": "json"}
        if location_id:
            params["$filter"] = f"Warehouse eq '{location_id}'"

        records = await self._odata_get(
            "/API_WAREHOUSE_LOC_STOCK/A_WarehouseStorageBinStock",
            params=params,
        )
        recommendations = []
        for record in records:
            inv = map_warehouse_bin_stock_to_inventory(record)
            if inv.reorder_point is not None and inv.available_qty < inv.reorder_point:
                recommendations.append(
                    {
                        "sku": inv.sku,
                        "location_id": inv.location_id,
                        "available_qty": inv.available_qty,
                        "reorder_point": inv.reorder_point,
                        "suggested_order_qty": inv.reorder_point - inv.available_qty,
                    }
                )
        return recommendations

    # ------------------------------------------------------------------
    # Additional product helpers (not in base contract, exposed for agents)
    # ------------------------------------------------------------------

    async def get_products(
        self,
        *,
        category: str | None = None,
        modified_since: str | None = None,
        top: int = _DEFAULT_PAGE_SIZE,
        skip: int = 0,
    ) -> list[ProductData]:
        """List products from ``/API_PRODUCT_SRV/A_Product``.

        Parameters
        ----------
        category:       OData $filter by ProductGroup
        modified_since: ISO-8601 datetime string for LastChangeDate filter
        top:            OData $top (page size)
        skip:           OData $skip (offset)
        """
        filters: list[str] = []
        if category:
            filters.append(f"ProductGroup eq '{category}'")
        if modified_since:
            filters.append(f"LastChangeDate gt '{modified_since}'")

        params: dict[str, Any] = {
            "$top": top,
            "$skip": skip,
            "$format": "json",
            "$expand": "to_Description",
        }
        if filters:
            params["$filter"] = " and ".join(filters)

        records = await self._odata_get("/API_PRODUCT_SRV/A_Product", params=params)
        return [map_product_to_product_data(r) for r in records]

    async def get_product(self, sku: str) -> ProductData | None:
        """Fetch a single product by SKU from ``/API_PRODUCT_SRV/A_Product``."""
        records = await self._odata_get(
            f"/API_PRODUCT_SRV/A_Product('{sku}')",
            params={"$format": "json", "$expand": "to_Description"},
        )
        if not records:
            return None
        return map_product_to_product_data(records[0])

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    async def health(self) -> dict[str, Any]:
        """Ping SAP by fetching a single product record."""
        try:
            headers = await self._auth.get_headers()
            headers.update(_ODATA_JSON_HEADERS)
            async with httpx.AsyncClient(
                base_url=self._base_url,
                headers=headers,
                transport=self._transport,
                timeout=5.0,
            ) as client:
                response = await client.get(
                    "/API_PRODUCT_SRV/A_Product",
                    params={"$top": "1", "$format": "json"},
                )
                response.raise_for_status()
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Private HTTP helpers
    # ------------------------------------------------------------------

    async def _odata_get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Perform an OData GET and return the value array."""
        headers = await self._auth.get_headers()
        headers.update(_ODATA_JSON_HEADERS)
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                headers=headers,
                transport=self._transport,
            ) as client:
                response = await client.get(path, params=params)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise AdapterError(
                f"SAP S/4HANA GET {path} failed: {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            raise AdapterError(f"SAP S/4HANA request error for {path}: {exc}") from exc

        body = response.json()
        # OData v4 returns {"value": [...]}; single entity returns the dict directly
        if "value" in body:
            return body["value"]
        if "d" in body:
            # OData v2 compatibility
            inner = body["d"]
            if "results" in inner:
                return inner["results"]
            return [inner]
        return [body]

    async def _odata_post(
        self,
        path: str,
        *,
        data: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Perform an OData POST and return the created entity."""
        headers = await self._auth.get_headers()
        headers.update(_ODATA_JSON_HEADERS)
        headers["Content-Type"] = "application/json"
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                headers=headers,
                transport=self._transport,
            ) as client:
                response = await client.post(path, json=data)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise AdapterError(
                f"SAP S/4HANA POST {path} failed: {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            raise AdapterError(f"SAP S/4HANA request error for {path}: {exc}") from exc

        if not response.content:
            return None
        body = response.json()
        # Unwrap OData envelope when present
        if "d" in body:
            return body["d"]
        return body
