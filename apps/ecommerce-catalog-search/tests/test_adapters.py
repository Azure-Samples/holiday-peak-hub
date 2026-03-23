"""Unit tests for catalog adapter strategy and CRUD-backed product adapter."""

import httpx
import pytest
from ecommerce_catalog_search.adapters import (
    CRUDCatalogProductAdapter,
    build_catalog_adapters,
)
from holiday_peak_lib.adapters.mock_adapters import MockProductAdapter


class TestBuildCatalogAdapters:
    """Strategy selection tests for adapter builder."""

    def test_build_catalog_adapters_uses_mock_when_crud_url_missing(self, monkeypatch):
        monkeypatch.delenv("CRUD_SERVICE_URL", raising=False)

        adapters = build_catalog_adapters()

        assert isinstance(adapters.products.adapter, MockProductAdapter)

    def test_build_catalog_adapters_uses_crud_adapter_when_crud_url_set(self, monkeypatch):
        monkeypatch.setenv("CRUD_SERVICE_URL", "http://crud-service")

        adapters = build_catalog_adapters()

        assert isinstance(adapters.products.adapter, CRUDCatalogProductAdapter)


class TestCrudCatalogProductAdapter:
    """Behavior tests for CRUD-backed adapter implementation."""

    @pytest.mark.asyncio
    async def test_crud_adapter_fetches_product_and_related(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/products/SKU-001":
                return httpx.Response(
                    200,
                    json={
                        "id": "SKU-001",
                        "name": "Trail Shoe",
                        "description": "Comfort running shoe",
                        "category_id": "footwear",
                        "price": 129.9,
                        "image_url": "https://example.com/p1.png",
                    },
                )
            if request.url.path == "/api/products" and request.url.params.get("category"):
                return httpx.Response(
                    200,
                    json=[
                        {
                            "id": "SKU-001",
                            "name": "Trail Shoe",
                            "category_id": "footwear",
                            "price": 129.9,
                        },
                        {
                            "id": "SKU-002",
                            "name": "Road Shoe",
                            "category_id": "footwear",
                            "price": 119.0,
                        },
                    ],
                )
            return httpx.Response(404, json={"detail": "not found"})

        adapter = CRUDCatalogProductAdapter(
            "http://crud-service",
            transport=httpx.MockTransport(handler),
        )
        adapters = build_catalog_adapters(
            product_connector=None,
            inventory_connector=None,
        )
        adapters.products.adapter = adapter

        product = await adapters.products.get_product("SKU-001")
        related = await adapters.products.get_related("SKU-001", limit=2)

        assert product is not None
        assert product.sku == "SKU-001"
        assert product.name == "Trail Shoe"
        assert related
        assert related[0].sku == "SKU-002"

    @pytest.mark.asyncio
    async def test_crud_adapter_degrades_gracefully_on_http_error(self):
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, json={"detail": "service unavailable"})

        adapter = CRUDCatalogProductAdapter(
            "http://crud-service",
            transport=httpx.MockTransport(handler),
        )
        adapters = build_catalog_adapters()
        adapters.products.adapter = adapter

        product = await adapters.products.get_product("SKU-001")
        related = await adapters.products.get_related("SKU-001", limit=2)

        assert product is None
        assert related == []
