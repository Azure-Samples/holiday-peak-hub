"""Truth Store Cosmos DB adapter for Product Graph CRUD operations.

Provides :class:`TruthStoreAdapter` — the data-access layer for all
truth-layer services.  It extends :class:`~holiday_peak_lib.adapters.base.BaseAdapter`
to inherit rate limiting, caching, retries, and circuit breaking, while adding
domain-specific operations across the nine Product Graph containers.

Design decisions:
- ``azure.cosmos.aio.CosmosClient`` for fully async I/O.
- ``DefaultAzureCredential`` for Managed Identity auth (no shared keys).
- Idempotent upserts keyed on ``id`` + partition key.
- Explicit 429 retry-after handling on top of the base resilience layer.
- 404 responses are surfaced as ``None`` (not raised) for predictable callers.
"""

import asyncio
import logging
from typing import Any, Optional

from azure.cosmos.aio import CosmosClient
from azure.cosmos.exceptions import CosmosHttpResponseError, CosmosResourceNotFoundError
from azure.identity import DefaultAzureCredential

from holiday_peak_lib.adapters.base import AdapterError, BaseAdapter
from holiday_peak_lib.truth.models import (
    AuditEvent,
    CategorySchema,
    MappingDocument,
    ProductStyle,
    ProposedAttribute,
    TenantConfig,
    TruthAttribute,
)
from holiday_peak_lib.utils.logging import configure_logging

logger = configure_logging()

_DEFAULT_CONTAINERS: dict[str, str] = {
    "products": "products",
    "attributes_truth": "attributes_truth",
    "attributes_proposed": "attributes_proposed",
    "assets": "assets",
    "evidence": "evidence",
    "schemas": "schemas",
    "mappings": "mappings",
    "audit": "audit",
    "config": "config",
}

_MAX_COSMOS_RETRIES = 3


class TruthStoreAdapter(BaseAdapter):
    """Cosmos DB adapter for all Product Graph containers.

    Manages CRUD operations across the truth-layer containers with:

    - Managed Identity authentication via ``DefaultAzureCredential``
    - Idempotent upserts keyed on ``id`` + partition key
    - Automatic retry on 429 (rate-limit) responses with ``Retry-After`` header
    - Consistent error handling: 404 → ``None``, other errors → :class:`AdapterError`

    Example::

        adapter = TruthStoreAdapter(
            account_uri="https://my-cosmos.documents.azure.com:443/",
            database="truth",
        )
        await adapter.connect()
        style = await adapter.get_product("style-1", category_id="CAT-1")

    """

    def __init__(
        self,
        account_uri: str,
        database: str,
        *,
        containers: Optional[dict[str, str]] = None,
        connection_limit: Optional[int] = None,
        client_kwargs: Optional[dict[str, Any]] = None,
        **adapter_kwargs: Any,
    ) -> None:
        super().__init__(**adapter_kwargs)
        self.account_uri = account_uri
        self.database = database
        self.containers: dict[str, str] = containers or dict(_DEFAULT_CONTAINERS)
        self._connection_limit = connection_limit
        self._client_kwargs: dict[str, Any] = client_kwargs or {}
        self.client: Optional[CosmosClient] = None

    # ------------------------------------------------------------------
    # BaseAdapter abstract hooks
    # ------------------------------------------------------------------

    async def _connect_impl(self, **kwargs: Any) -> None:
        credential = DefaultAzureCredential()
        merged = dict(self._client_kwargs)
        if self._connection_limit is not None:
            merged["connection_limit"] = self._connection_limit
        self.client = CosmosClient(self.account_uri, credential, **merged)
        logger.info(
            "TruthStoreAdapter connected to %s database=%s",
            self.account_uri,
            self.database,
        )

    async def _fetch_impl(self, query: dict[str, Any]) -> list[dict[str, Any]]:
        container_name = query.get("_container")
        partition_key = query.get("_partition_key")
        sql = query.get("_sql")
        params = query.get("_params")

        if not container_name:
            raise AdapterError("_container is required in query")
        if not sql:
            raise AdapterError("_sql is required in query")

        container = self._get_container(container_name)
        items: list[dict[str, Any]] = []
        async for item in container.query_items(
            query=sql,
            parameters=params,
            partition_key=partition_key,
        ):
            items.append(item)
        return items

    async def _upsert_impl(self, payload: dict[str, Any]) -> Optional[dict[str, Any]]:
        container_name = payload.pop("_container", None)
        if not container_name:
            raise AdapterError("_container is required in payload")
        container = self._get_container(container_name)
        return await container.upsert_item(payload)

    async def _delete_impl(self, identifier: str) -> bool:
        parts = identifier.split(":", 2)
        if len(parts) != 3:
            raise AdapterError(
                "identifier must be formatted as 'container:item_id:partition_key'"
            )
        container_name, item_id, partition_key = parts
        container = self._get_container(container_name)
        try:
            await container.delete_item(item_id, partition_key=partition_key)
        except CosmosResourceNotFoundError:
            return False
        except CosmosHttpResponseError as exc:
            raise AdapterError(f"Cosmos delete failed: {exc}") from exc
        return True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_container(self, name: str):
        if self.client is None:
            raise AdapterError("Not connected. Call connect() first.")
        container_name = self.containers.get(name)
        if not container_name:
            raise AdapterError(f"Unknown container key: '{name}'")
        db = self.client.get_database_client(self.database)
        return db.get_container_client(container_name)

    async def _ensure_connected(self) -> None:
        if self.client is None:
            await self.connect()

    async def _cosmos_call(self, func, *args, **kwargs) -> Any:
        """Execute a Cosmos operation with 429 retry-after handling."""
        last_exc: Optional[Exception] = None
        for attempt in range(_MAX_COSMOS_RETRIES + 1):
            try:
                return await func(*args, **kwargs)
            except CosmosResourceNotFoundError:
                return None
            except CosmosHttpResponseError as exc:
                if exc.status_code == 429 and attempt < _MAX_COSMOS_RETRIES:
                    retry_after_ms = 1000.0
                    try:
                        headers = getattr(exc, "headers", None) or {}
                        retry_after_ms = float(
                            headers.get("x-ms-retry-after-ms", 1000)
                        )
                    except (TypeError, ValueError):
                        pass
                    logger.warning(
                        "Cosmos 429 throttle (attempt %d/%d), retrying in %.0f ms",
                        attempt + 1,
                        _MAX_COSMOS_RETRIES,
                        retry_after_ms,
                    )
                    await asyncio.sleep(retry_after_ms / 1000.0)
                    last_exc = exc
                    continue
                raise AdapterError(f"Cosmos operation failed: {exc}") from exc
        raise AdapterError("Cosmos operation failed after retries") from last_exc

    # ------------------------------------------------------------------
    # Products
    # ------------------------------------------------------------------

    async def upsert_product(self, style: ProductStyle) -> ProductStyle:
        """Upsert a :class:`~holiday_peak_lib.truth.models.ProductStyle` document."""
        await self._ensure_connected()
        item = style.model_dump(mode="json", by_alias=True)
        container = self._get_container("products")
        result = await self._cosmos_call(container.upsert_item, item)
        return ProductStyle.model_validate(result)

    async def get_product(
        self, entity_id: str, category_id: str
    ) -> Optional[ProductStyle]:
        """Retrieve a product style by ID and partition key."""
        await self._ensure_connected()
        container = self._get_container("products")
        result = await self._cosmos_call(
            container.read_item, entity_id, partition_key=category_id
        )
        if result is None:
            return None
        return ProductStyle.model_validate(result)

    async def list_products(
        self,
        category_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ProductStyle]:
        """Paginated listing of product styles within a category."""
        await self._ensure_connected()
        container = self._get_container("products")
        sql = (
            "SELECT * FROM c WHERE c.categoryId = @categoryId"
            " OFFSET @offset LIMIT @limit"
        )
        params = [
            {"name": "@categoryId", "value": category_id},
            {"name": "@offset", "value": offset},
            {"name": "@limit", "value": limit},
        ]
        items: list[ProductStyle] = []
        async for item in container.query_items(
            query=sql, parameters=params, partition_key=category_id
        ):
            items.append(ProductStyle.model_validate(item))
        return items

    # ------------------------------------------------------------------
    # Truth Attributes
    # ------------------------------------------------------------------

    async def upsert_truth_attribute(self, attr: TruthAttribute) -> TruthAttribute:
        """Upsert an official approved attribute."""
        await self._ensure_connected()
        item = attr.model_dump(mode="json", by_alias=True)
        container = self._get_container("attributes_truth")
        result = await self._cosmos_call(container.upsert_item, item)
        return TruthAttribute.model_validate(result)

    async def get_truth_attributes(self, entity_id: str) -> list[TruthAttribute]:
        """Return all official attributes for a given entity."""
        await self._ensure_connected()
        container = self._get_container("attributes_truth")
        sql = "SELECT * FROM c WHERE c.entityId = @entityId"
        params = [{"name": "@entityId", "value": entity_id}]
        items: list[TruthAttribute] = []
        async for item in container.query_items(
            query=sql, parameters=params, partition_key=entity_id
        ):
            items.append(TruthAttribute.model_validate(item))
        return items

    # ------------------------------------------------------------------
    # Proposed Attributes
    # ------------------------------------------------------------------

    async def upsert_proposed_attribute(
        self, attr: ProposedAttribute
    ) -> ProposedAttribute:
        """Write or update an AI-proposed attribute."""
        await self._ensure_connected()
        item = attr.model_dump(mode="json", by_alias=True)
        container = self._get_container("attributes_proposed")
        result = await self._cosmos_call(container.upsert_item, item)
        return ProposedAttribute.model_validate(result)

    async def get_proposed_attributes(
        self,
        entity_id: str,
        status: Optional[str] = None,
    ) -> list[ProposedAttribute]:
        """Return proposed attributes for an entity, optionally filtered by status."""
        await self._ensure_connected()
        container = self._get_container("attributes_proposed")
        if status:
            sql = (
                "SELECT * FROM c"
                " WHERE c.entityId = @entityId AND c.status = @status"
            )
            params = [
                {"name": "@entityId", "value": entity_id},
                {"name": "@status", "value": status},
            ]
        else:
            sql = "SELECT * FROM c WHERE c.entityId = @entityId"
            params = [{"name": "@entityId", "value": entity_id}]
        items: list[ProposedAttribute] = []
        async for item in container.query_items(
            query=sql, parameters=params, partition_key=entity_id
        ):
            items.append(ProposedAttribute.model_validate(item))
        return items

    async def update_proposed_status(
        self, attr_id: str, entity_id: str, status: str
    ) -> Optional[ProposedAttribute]:
        """Approve or reject a proposed attribute by updating its status."""
        await self._ensure_connected()
        container = self._get_container("attributes_proposed")
        existing = await self._cosmos_call(
            container.read_item, attr_id, partition_key=entity_id
        )
        if existing is None:
            return None
        existing["status"] = status
        result = await self._cosmos_call(container.upsert_item, existing)
        return ProposedAttribute.model_validate(result)

    # ------------------------------------------------------------------
    # Schemas
    # ------------------------------------------------------------------

    async def get_schema(self, category_id: str) -> Optional[CategorySchema]:
        """Load the category schema definition."""
        await self._ensure_connected()
        container = self._get_container("schemas")
        result = await self._cosmos_call(
            container.read_item, category_id, partition_key=category_id
        )
        if result is None:
            return None
        return CategorySchema.model_validate(result)

    async def upsert_schema(self, schema_doc: CategorySchema) -> CategorySchema:
        """Upload or update a category schema."""
        await self._ensure_connected()
        item = schema_doc.model_dump(mode="json", by_alias=True)
        container = self._get_container("schemas")
        result = await self._cosmos_call(container.upsert_item, item)
        return CategorySchema.model_validate(result)

    # ------------------------------------------------------------------
    # Mappings
    # ------------------------------------------------------------------

    async def get_mapping(
        self, protocol: str, version: str
    ) -> Optional[MappingDocument]:
        """Load a canonical-to-protocol field mapping document."""
        await self._ensure_connected()
        container = self._get_container("mappings")
        item_id = f"{protocol}:{version}"
        result = await self._cosmos_call(
            container.read_item, item_id, partition_key=version
        )
        if result is None:
            return None
        return MappingDocument.model_validate(result)

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    async def write_audit(self, event: AuditEvent) -> AuditEvent:
        """Append an immutable audit event."""
        await self._ensure_connected()
        item = event.model_dump(mode="json", by_alias=True)
        container = self._get_container("audit")
        result = await self._cosmos_call(container.upsert_item, item)
        return AuditEvent.model_validate(result)

    async def query_audit(
        self,
        entity_id: str,
        action: Optional[str] = None,
        limit: int = 50,
    ) -> list[AuditEvent]:
        """Return audit events for an entity, optionally filtered by action."""
        await self._ensure_connected()
        container = self._get_container("audit")
        if action:
            sql = (
                "SELECT * FROM c"
                " WHERE c.entityId = @entityId AND c.action = @action"
                " ORDER BY c._ts DESC OFFSET 0 LIMIT @limit"
            )
            params = [
                {"name": "@entityId", "value": entity_id},
                {"name": "@action", "value": action},
                {"name": "@limit", "value": limit},
            ]
        else:
            sql = (
                "SELECT * FROM c WHERE c.entityId = @entityId"
                " ORDER BY c._ts DESC OFFSET 0 LIMIT @limit"
            )
            params = [
                {"name": "@entityId", "value": entity_id},
                {"name": "@limit", "value": limit},
            ]
        items: list[AuditEvent] = []
        async for item in container.query_items(
            query=sql, parameters=params, partition_key=entity_id
        ):
            items.append(AuditEvent.model_validate(item))
        return items

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    async def upsert_config(self, config: TenantConfig) -> TenantConfig:
        """Create or update tenant configuration."""
        await self._ensure_connected()
        item = config.model_dump(mode="json", by_alias=True)
        container = self._get_container("config")
        result = await self._cosmos_call(container.upsert_item, item)
        return TenantConfig.model_validate(result)

    async def get_config(self, tenant_id: str) -> Optional[TenantConfig]:
        """Load tenant configuration by tenant ID."""
        await self._ensure_connected()
        container = self._get_container("config")
        result = await self._cosmos_call(
            container.read_item, tenant_id, partition_key=tenant_id
        )
        if result is None:
            return None
        return TenantConfig.model_validate(result)
