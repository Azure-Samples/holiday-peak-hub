"""Unit tests for SAPS4HANAConnector.

All HTTP calls are intercepted via httpx.MockTransport so no live SAP
system is required.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from holiday_peak_lib.adapters.base import AdapterError
from holiday_peak_lib.connectors.inventory_scm.sap_s4hana.auth import SAPS4HANAAuth
from holiday_peak_lib.connectors.inventory_scm.sap_s4hana.connector import SAPS4HANAConnector
from holiday_peak_lib.integrations.contracts import InventoryData, ProductData


# ---------------------------------------------------------------------------
# Mock transport builder
# ---------------------------------------------------------------------------


class _Routes:
    """Simple path-based request router for MockTransport."""

    def __init__(self) -> None:
        self._routes: list[tuple[str, str, httpx.Response]] = []

    def add(self, method: str, path_contains: str, response: httpx.Response) -> None:
        self._routes.append((method.upper(), path_contains, response))

    def handler(self, request: httpx.Request) -> httpx.Response:
        for method, fragment, response in self._routes:
            if request.method == method and fragment in str(request.url):
                return response
        return httpx.Response(404, json={"error": "not found"})


def _auth(api_key: str = "test-key") -> SAPS4HANAAuth:
    return SAPS4HANAAuth(api_key=api_key)


def _json_response(body: Any, status: int = 200) -> httpx.Response:
    return httpx.Response(status, json=body)


def _odata_list(items: list[dict]) -> dict:
    return {"value": items}


def _odata_single(item: dict) -> dict:
    return {"d": item}


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def stock_record():
    return {
        "Material": "MAT-001",
        "Plant": "1000",
        "StorageLocation": "0001",
        "MatlStkInAcctMod": "250",
        "QtyInTransit": "0",
        "QtyInQualityInspection": "0",
    }


@pytest.fixture()
def product_record():
    return {
        "Product": "SKU-001",
        "Brand": "TestBrand",
        "ProductGroup": "TOOLS",
        "CrossPlantStatus": "00",
        "to_Description": [{"Language": "EN", "ProductDescription": "Test Product"}],
    }


# ---------------------------------------------------------------------------
# get_inventory
# ---------------------------------------------------------------------------


class TestGetInventory:
    def _connector(self, records: list[dict]) -> SAPS4HANAConnector:
        routes = _Routes()
        routes.add("GET", "A_MatlStkInAcctMod", _json_response(_odata_list(records)))
        transport = httpx.MockTransport(routes.handler)
        return SAPS4HANAConnector(
            base_url="https://api.sap.example.com",
            auth=_auth(),
            transport=transport,
        )

    def test_returns_inventory_list(self, stock_record):
        import asyncio

        connector = self._connector([stock_record])
        result = asyncio.run(connector.get_inventory("MAT-001"))
        assert len(result) == 1
        assert isinstance(result[0], InventoryData)
        assert result[0].sku == "MAT-001"
        assert result[0].available_qty == 250

    def test_empty_response(self):
        import asyncio

        connector = self._connector([])
        result = asyncio.run(connector.get_inventory("MISSING"))
        assert result == []

    def test_http_error_raises_adapter_error(self):
        routes = _Routes()
        routes.add("GET", "A_MatlStkInAcctMod", httpx.Response(503, json={"error": "down"}))
        transport = httpx.MockTransport(routes.handler)
        connector = SAPS4HANAConnector(
            base_url="https://api.sap.example.com",
            auth=_auth(),
            transport=transport,
        )
        import asyncio

        with pytest.raises(AdapterError):
            asyncio.run(connector.get_inventory("MAT-001"))


# ---------------------------------------------------------------------------
# get_available_to_promise
# ---------------------------------------------------------------------------


class TestGetAvailableToPromise:
    def _connector(self, records: list[dict]) -> SAPS4HANAConnector:
        routes = _Routes()
        routes.add("GET", "A_MatlStkInAcctMod", _json_response(_odata_list(records)))
        return SAPS4HANAConnector(
            base_url="https://api.sap.example.com",
            auth=_auth(),
            transport=httpx.MockTransport(routes.handler),
        )

    def test_marks_fulfillable_locations(self, stock_record):
        import asyncio

        stock_record["MatlStkInAcctMod"] = "100"
        connector = self._connector([stock_record])
        atp = asyncio.run(connector.get_available_to_promise("MAT-001", 50))
        assert atp[0]["fulfillable"] is True

    def test_marks_non_fulfillable_locations(self, stock_record):
        import asyncio

        stock_record["MatlStkInAcctMod"] = "10"
        connector = self._connector([stock_record])
        atp = asyncio.run(connector.get_available_to_promise("MAT-001", 50))
        assert atp[0]["fulfillable"] is False


# ---------------------------------------------------------------------------
# reserve_inventory
# ---------------------------------------------------------------------------


class TestReserveInventory:
    def test_posts_purchase_order(self):
        import asyncio

        po_response = {"PurchaseOrder": "4500000001"}
        routes = _Routes()
        routes.add("POST", "A_PurchaseOrder", _json_response(po_response))
        connector = SAPS4HANAConnector(
            base_url="https://api.sap.example.com",
            auth=_auth(),
            transport=httpx.MockTransport(routes.handler),
        )
        result = asyncio.run(
            connector.reserve_inventory("MAT-001", "1000", 25, "REF-001")
        )
        assert result["reservation_id"] == "4500000001"
        assert result["sku"] == "MAT-001"
        assert result["quantity"] == 25

    def test_http_error_raises_adapter_error(self):
        import asyncio

        routes = _Routes()
        routes.add("POST", "A_PurchaseOrder", httpx.Response(400, json={"error": "bad"}))
        connector = SAPS4HANAConnector(
            base_url="https://api.sap.example.com",
            auth=_auth(),
            transport=httpx.MockTransport(routes.handler),
        )
        with pytest.raises(AdapterError):
            asyncio.run(connector.reserve_inventory("MAT-001", "1000", 25, "REF-001"))


# ---------------------------------------------------------------------------
# release_reservation
# ---------------------------------------------------------------------------


class TestReleaseReservation:
    def test_returns_true_on_success(self):
        import asyncio

        routes = _Routes()
        routes.add("DELETE", "A_PurchaseOrder", httpx.Response(204))
        connector = SAPS4HANAConnector(
            base_url="https://api.sap.example.com",
            auth=_auth(),
            transport=httpx.MockTransport(routes.handler),
        )
        result = asyncio.run(connector.release_reservation("4500000001"))
        assert result is True

    def test_returns_false_on_404(self):
        import asyncio

        routes = _Routes()
        routes.add("DELETE", "A_PurchaseOrder", httpx.Response(404))
        connector = SAPS4HANAConnector(
            base_url="https://api.sap.example.com",
            auth=_auth(),
            transport=httpx.MockTransport(routes.handler),
        )
        result = asyncio.run(connector.release_reservation("NONEXISTENT"))
        assert result is False


# ---------------------------------------------------------------------------
# get_replenishment_recommendations
# ---------------------------------------------------------------------------


class TestReplenishmentRecommendations:
    def _bin_record(self, sku: str, qty: int, reorder: int):
        return {
            "Product": sku,
            "Warehouse": "WH01",
            "StorageBin": "A-01",
            "StockQty": str(qty),
            "ReservedQty": "0",
            "ReorderThresholdQuantity": str(reorder),
        }

    def test_returns_below_reorder_items(self):
        import asyncio

        records = [
            self._bin_record("LOW-SKU", 5, 100),
            self._bin_record("OK-SKU", 200, 100),
        ]
        routes = _Routes()
        routes.add(
            "GET",
            "A_WarehouseStorageBinStock",
            _json_response(_odata_list(records)),
        )
        connector = SAPS4HANAConnector(
            base_url="https://api.sap.example.com",
            auth=_auth(),
            transport=httpx.MockTransport(routes.handler),
        )
        recs = asyncio.run(connector.get_replenishment_recommendations())
        assert len(recs) == 1
        assert recs[0]["sku"] == "LOW-SKU"
        assert recs[0]["suggested_order_qty"] == 95

    def test_empty_when_all_stock_ok(self):
        import asyncio

        records = [self._bin_record("OK-SKU", 500, 100)]
        routes = _Routes()
        routes.add(
            "GET",
            "A_WarehouseStorageBinStock",
            _json_response(_odata_list(records)),
        )
        connector = SAPS4HANAConnector(
            base_url="https://api.sap.example.com",
            auth=_auth(),
            transport=httpx.MockTransport(routes.handler),
        )
        recs = asyncio.run(connector.get_replenishment_recommendations())
        assert recs == []


# ---------------------------------------------------------------------------
# get_products / get_product
# ---------------------------------------------------------------------------


class TestGetProducts:
    def test_returns_product_list(self, product_record):
        import asyncio

        routes = _Routes()
        routes.add("GET", "A_Product", _json_response(_odata_list([product_record])))
        connector = SAPS4HANAConnector(
            base_url="https://api.sap.example.com",
            auth=_auth(),
            transport=httpx.MockTransport(routes.handler),
        )
        products = asyncio.run(connector.get_products())
        assert len(products) == 1
        assert isinstance(products[0], ProductData)
        assert products[0].sku == "SKU-001"

    def test_get_single_product(self, product_record):
        import asyncio

        routes = _Routes()
        routes.add("GET", "A_Product", _json_response({"d": product_record}))
        connector = SAPS4HANAConnector(
            base_url="https://api.sap.example.com",
            auth=_auth(),
            transport=httpx.MockTransport(routes.handler),
        )
        prod = asyncio.run(connector.get_product("SKU-001"))
        assert prod is not None
        assert prod.title == "Test Product"


# ---------------------------------------------------------------------------
# health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_healthy(self):
        import asyncio

        routes = _Routes()
        routes.add("GET", "A_Product", _json_response(_odata_list([])))
        connector = SAPS4HANAConnector(
            base_url="https://api.sap.example.com",
            auth=_auth(),
            transport=httpx.MockTransport(routes.handler),
        )
        result = asyncio.run(connector.health())
        assert result["ok"] is True

    def test_unhealthy_returns_error_info(self):
        import asyncio

        routes = _Routes()
        routes.add("GET", "A_Product", httpx.Response(503))
        connector = SAPS4HANAConnector(
            base_url="https://api.sap.example.com",
            auth=_auth(),
            transport=httpx.MockTransport(routes.handler),
        )
        result = asyncio.run(connector.health())
        assert result["ok"] is False
        assert "error" in result


# ---------------------------------------------------------------------------
# BaseAdapter hooks (generic OData pass-through)
# ---------------------------------------------------------------------------


class TestBaseAdapterHooks:
    def test_fetch_impl(self):
        import asyncio

        routes = _Routes()
        routes.add("GET", "A_Product", _json_response(_odata_list([{"Product": "P1"}])))
        connector = SAPS4HANAConnector(
            base_url="https://api.sap.example.com",
            auth=_auth(),
            transport=httpx.MockTransport(routes.handler),
        )
        result = asyncio.run(
            connector._fetch_impl({"endpoint": "/API_PRODUCT_SRV/A_Product"})
        )
        assert result[0]["Product"] == "P1"

    def test_upsert_impl(self):
        import asyncio

        routes = _Routes()
        routes.add("POST", "A_PurchaseOrder", _json_response({"PurchaseOrder": "12345"}))
        connector = SAPS4HANAConnector(
            base_url="https://api.sap.example.com",
            auth=_auth(),
            transport=httpx.MockTransport(routes.handler),
        )
        result = asyncio.run(
            connector._upsert_impl(
                {
                    "endpoint": "/API_PURCHASEORDER_PROCESS_SRV/A_PurchaseOrder",
                    "data": {"PurchaseOrderType": "NB"},
                }
            )
        )
        assert result["PurchaseOrder"] == "12345"
