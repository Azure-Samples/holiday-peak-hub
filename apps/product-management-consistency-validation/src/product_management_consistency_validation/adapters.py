"""Adapters for the product consistency validation service."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from holiday_peak_lib.adapters.mock_adapters import MockProductAdapter
from holiday_peak_lib.adapters.product_adapter import ProductConnector
from holiday_peak_lib.schemas.product import CatalogProduct

from .completeness_engine import CategorySchema, GapReport


class CompletenessStorageAdapter:
    """Load category schemas and persist gap reports.

    In production, *cosmos_client* should be an ``azure.cosmos.aio.CosmosClient``
    instance.  When ``None`` (default) an in-memory mock is used so the service
    starts without Azure credentials in local / test environments.
    """

    def __init__(
        self,
        *,
        cosmos_client: Any = None,
        database: str = "truth",
        schemas_container: str = "schemas",
        completeness_container: str = "completeness",
    ) -> None:
        self._cosmos = cosmos_client
        self._database = database
        self._schemas_container = schemas_container
        self._completeness_container = completeness_container
        # In-memory fallbacks used when no Cosmos client is supplied
        self._schema_cache: dict[str, CategorySchema] = {}
        self._report_store: dict[str, dict[str, Any]] = {}

    def seed_schema(self, schema: CategorySchema) -> None:
        """Register an in-memory schema (useful for testing)."""
        self._schema_cache[schema.category_id] = schema

    async def get_schema(self, category_id: str) -> Optional[CategorySchema]:
        """Return the :class:`CategorySchema` for *category_id*.

        Tries Cosmos DB first; falls back to the in-memory cache.
        """
        if self._cosmos is not None:
            try:
                db = self._cosmos.get_database_client(self._database)
                container = db.get_container_client(self._schemas_container)
                item = await container.read_item(item=category_id, partition_key=category_id)
                return CategorySchema(**item)
            except Exception:  # noqa: BLE001
                pass
        return self._schema_cache.get(category_id)

    async def store_gap_report(self, report: GapReport) -> None:
        """Persist *report* to Cosmos DB (or in-memory store as fallback)."""
        doc = report.model_dump(mode="json")
        if self._cosmos is not None:
            try:
                db = self._cosmos.get_database_client(self._database)
                container = db.get_container_client(self._completeness_container)
                await container.upsert_item(doc)
                return
            except Exception:  # noqa: BLE001
                pass
        self._report_store[report.entity_id] = doc


@dataclass
class ProductConsistencyAdapters:
    """Container for product consistency validation adapters."""

    products: ProductConnector
    validator: "ProductConsistencyValidator"
    completeness: CompletenessStorageAdapter = field(default_factory=CompletenessStorageAdapter)


class ProductConsistencyValidator:
    """Validate product data for completeness and consistency."""

    async def validate(self, product: CatalogProduct) -> dict[str, Any]:
        issues = []
        if not product.name:
            issues.append("missing_name")
        if product.price is not None and product.price < 0:
            issues.append("negative_price")
        if product.price is not None and not product.currency:
            issues.append("missing_currency")
        if not product.image_url:
            issues.append("missing_image")
        return {
            "sku": product.sku,
            "issues": issues,
            "status": "invalid" if issues else "valid",
        }


def build_consistency_adapters(
    *,
    product_connector: Optional[ProductConnector] = None,
    completeness_adapter: Optional[CompletenessStorageAdapter] = None,
) -> ProductConsistencyAdapters:
    """Create adapters for product consistency validation workflows."""
    products = product_connector or ProductConnector(adapter=MockProductAdapter())
    validator = ProductConsistencyValidator()
    completeness = completeness_adapter or CompletenessStorageAdapter()
    return ProductConsistencyAdapters(
        products=products, validator=validator, completeness=completeness
    )
