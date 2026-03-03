"""Adapters for the Truth Ingestion service.

Provides:
- TruthStoreAdapter: Cosmos DB upsert/fetch for ProductStyle and ProductVariant.
- PIMConnector: Generic REST PIM connector wrapper.
- DAMConnector: Generic REST DAM connector wrapper.
- EventPublisher: Event Hub publisher for completeness-jobs and ingestion-notifications.
- IngestionAdapters: Aggregate container for all adapters.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Optional

import httpx


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------


@dataclass
class ProductStyle:
    """Canonical product style record stored in the truth layer."""

    entity_id: str
    name: str
    category: str
    brand: str
    description: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)
    source: str = "pim"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.entity_id,
            "entity_id": self.entity_id,
            "name": self.name,
            "category": self.category,
            "brand": self.brand,
            "description": self.description,
            "attributes": self.attributes,
            "source": self.source,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "record_type": "product_style",
        }


@dataclass
class ProductVariant:
    """Canonical product variant record stored in the truth layer."""

    entity_id: str
    style_id: str
    sku: str
    color: str = ""
    size: str = ""
    price: float = 0.0
    attributes: dict[str, Any] = field(default_factory=dict)
    assets: list[dict[str, Any]] = field(default_factory=list)
    source: str = "pim"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.entity_id,
            "entity_id": self.entity_id,
            "style_id": self.style_id,
            "sku": self.sku,
            "color": self.color,
            "size": self.size,
            "price": self.price,
            "attributes": self.attributes,
            "assets": self.assets,
            "source": self.source,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "record_type": "product_variant",
        }


@dataclass
class AuditEvent:
    """Audit trail entry for every ingestion state change."""

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entity_id: str = ""
    event_type: str = "ingestion"
    operation: str = "upsert"
    source: str = "truth-ingestion"
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.event_id,
            "entity_id": self.entity_id,
            "event_type": self.event_type,
            "operation": self.operation,
            "source": self.source,
            "timestamp": self.timestamp,
            "details": self.details,
        }


# ---------------------------------------------------------------------------
# Field mapping helpers
# ---------------------------------------------------------------------------


def apply_field_mapping(
    raw: dict[str, Any],
    field_mapping: dict[str, str],
) -> dict[str, Any]:
    """Map raw PIM fields to canonical field names using a configurable mapping.

    Keys in ``field_mapping`` are canonical names; values are source field names.
    Any unmapped keys from ``raw`` are preserved under their original name.
    """
    result: dict[str, Any] = {}
    mapped_source_keys: set[str] = set()

    for canonical, source_key in field_mapping.items():
        if source_key in raw:
            result[canonical] = raw[source_key]
            mapped_source_keys.add(source_key)

    for key, value in raw.items():
        if key not in mapped_source_keys and key not in result:
            result[key] = value

    return result


def map_pim_to_product_style(
    raw: dict[str, Any],
    field_mapping: Optional[dict[str, str]] = None,
) -> ProductStyle:
    """Convert a raw PIM payload to a canonical ProductStyle.

    The default field mapping covers common PIM field name conventions.
    """
    defaults: dict[str, str] = {
        "entity_id": "id",
        "name": "name",
        "category": "category",
        "brand": "brand",
        "description": "description",
    }
    mapping = {**defaults, **(field_mapping or {})}
    mapped = apply_field_mapping(raw, mapping)

    entity_id = str(mapped.get("entity_id") or mapped.get("id") or str(uuid.uuid4()))
    return ProductStyle(
        entity_id=entity_id,
        name=str(mapped.get("name", "")),
        category=str(mapped.get("category", "")),
        brand=str(mapped.get("brand", "")),
        description=str(mapped.get("description", "")),
        attributes={k: v for k, v in mapped.items()
                    if k not in {"entity_id", "id", "name", "category", "brand", "description"}},
        source=str(mapped.get("source", "pim")),
    )


def map_pim_to_product_variant(
    raw: dict[str, Any],
    style_id: str,
    field_mapping: Optional[dict[str, str]] = None,
) -> ProductVariant:
    """Convert a raw PIM variant payload to a canonical ProductVariant."""
    defaults: dict[str, str] = {
        "entity_id": "variant_id",
        "sku": "sku",
        "color": "color",
        "size": "size",
        "price": "price",
    }
    mapping = {**defaults, **(field_mapping or {})}
    mapped = apply_field_mapping(raw, mapping)

    entity_id = str(
        mapped.get("entity_id") or mapped.get("variant_id") or str(uuid.uuid4())
    )
    return ProductVariant(
        entity_id=entity_id,
        style_id=style_id,
        sku=str(mapped.get("sku", "")),
        color=str(mapped.get("color", "")),
        size=str(mapped.get("size", "")),
        price=float(mapped.get("price", 0.0)),
        attributes={k: v for k, v in mapped.items()
                    if k not in {
                        "entity_id", "variant_id", "sku", "color", "size", "price"
                    }},
        source=str(mapped.get("source", "pim")),
    )


# ---------------------------------------------------------------------------
# Truth store adapter (Cosmos DB)
# ---------------------------------------------------------------------------


class TruthStoreAdapter:
    """Adapter for upserting and fetching products from Cosmos DB truth store.

    Falls back gracefully to in-memory when Cosmos environment variables are absent,
    which is useful in local development and unit tests.
    """

    def __init__(self) -> None:
        self._cosmos_uri = os.getenv("COSMOS_ACCOUNT_URI")
        self._cosmos_db = os.getenv("COSMOS_DATABASE", "truth-store")
        self._cosmos_container = os.getenv("COSMOS_CONTAINER", "products")
        self._audit_container = os.getenv("COSMOS_AUDIT_CONTAINER", "audit-events")
        self._client: Any = None
        self._in_memory: dict[str, dict[str, Any]] = {}
        self._audit_store: list[dict[str, Any]] = []

    async def _get_container(self, container_name: str) -> Any:
        if not self._cosmos_uri:
            return None
        if self._client is None:
            from azure.cosmos.aio import CosmosClient  # pylint: disable=import-outside-toplevel
            from azure.identity.aio import DefaultAzureCredential  # pylint: disable=import-outside-toplevel
            credential = DefaultAzureCredential()
            self._client = CosmosClient(self._cosmos_uri, credential=credential)
        database = self._client.get_database_client(self._cosmos_db)
        return database.get_container_client(container_name)

    async def upsert_product_style(self, style: ProductStyle) -> dict[str, Any]:
        """Upsert a ProductStyle into the truth store. Idempotent by entity_id."""
        document = style.to_dict()
        container = await self._get_container(self._cosmos_container)
        if container is not None:
            await container.upsert_item(document)
        else:
            self._in_memory[style.entity_id] = document
        return document

    async def upsert_product_variant(self, variant: ProductVariant) -> dict[str, Any]:
        """Upsert a ProductVariant into the truth store. Idempotent by entity_id."""
        document = variant.to_dict()
        container = await self._get_container(self._cosmos_container)
        if container is not None:
            await container.upsert_item(document)
        else:
            self._in_memory[variant.entity_id] = document
        return document

    async def get_product_style(self, entity_id: str) -> Optional[dict[str, Any]]:
        """Fetch a ProductStyle by entity_id."""
        container = await self._get_container(self._cosmos_container)
        if container is not None:
            try:
                return await container.read_item(item=entity_id, partition_key=entity_id)
            except Exception:  # noqa: BLE001
                return None
        return self._in_memory.get(entity_id)

    async def write_audit_event(self, event: AuditEvent) -> None:
        """Append an audit event to the immutable audit trail."""
        document = event.to_dict()
        container = await self._get_container(self._audit_container)
        if container is not None:
            await container.upsert_item(document)
        else:
            self._audit_store.append(document)


# ---------------------------------------------------------------------------
# PIM connector
# ---------------------------------------------------------------------------


class PIMConnector:
    """Generic REST PIM connector.

    Reads from a configurable REST endpoint. Supports API-key and Bearer token auth.
    Falls back to returning an empty list when ``PIM_BASE_URL`` is not configured.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        field_mapping: Optional[dict[str, str]] = None,
        page_size: int = 100,
    ) -> None:
        self._base_url = base_url or os.getenv("PIM_BASE_URL", "")
        self._api_key = api_key or os.getenv("PIM_API_KEY", "")
        self._field_mapping = field_mapping or {}
        self._page_size = page_size

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def fetch_product(self, entity_id: str) -> Optional[dict[str, Any]]:
        """Fetch a single product by entity_id from the PIM."""
        if not self._base_url:
            return None
        url = f"{self._base_url.rstrip('/')}/products/{entity_id}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=self._headers())
            response.raise_for_status()
            return response.json()

    async def fetch_products_page(
        self, page: int = 1, page_size: Optional[int] = None
    ) -> list[dict[str, Any]]:
        """Fetch a paginated page of products from the PIM."""
        if not self._base_url:
            return []
        size = page_size or self._page_size
        url = f"{self._base_url.rstrip('/')}/products"
        params = {"page": page, "page_size": size}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self._headers(), params=params)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                return data
            return data.get("items") or data.get("products") or data.get("data") or []

    async def fetch_all_products(
        self, max_pages: int = 100
    ) -> list[dict[str, Any]]:
        """Fetch all products via paginated pull (up to max_pages)."""
        all_products: list[dict[str, Any]] = []
        for page in range(1, max_pages + 1):
            page_data = await self.fetch_products_page(page=page)
            if not page_data:
                break
            all_products.extend(page_data)
        return all_products

    def get_field_mapping(self) -> dict[str, str]:
        return self._field_mapping


# ---------------------------------------------------------------------------
# DAM connector
# ---------------------------------------------------------------------------


class DAMConnector:
    """Generic REST DAM (Digital Asset Management) connector.

    Falls back to returning empty assets when ``DAM_BASE_URL`` is not configured.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        self._base_url = base_url or os.getenv("DAM_BASE_URL", "")
        self._api_key = api_key or os.getenv("DAM_API_KEY", "")

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def fetch_assets(self, entity_id: str) -> list[dict[str, Any]]:
        """Fetch digital assets for a product entity_id from the DAM."""
        if not self._base_url:
            return []
        url = f"{self._base_url.rstrip('/')}/assets"
        params = {"entity_id": entity_id}
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=self._headers(), params=params)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                return data
            return data.get("assets") or data.get("items") or data.get("data") or []


# ---------------------------------------------------------------------------
# Event Hub publisher
# ---------------------------------------------------------------------------


class EventPublisher:
    """Publish messages to Azure Event Hub topics.

    Falls back to a no-op when ``EVENTHUB_CONNECTION_STRING`` is not configured.
    """

    def __init__(self, connection_string: Optional[str] = None) -> None:
        self._connection_string = connection_string or os.getenv("EVENTHUB_CONNECTION_STRING", "")

    async def publish(self, eventhub_name: str, payload: dict[str, Any]) -> None:
        """Send ``payload`` as a JSON event to the given Event Hub topic."""
        if not self._connection_string:
            return
        from azure.eventhub.aio import EventHubProducerClient  # pylint: disable=import-outside-toplevel
        from azure.eventhub import EventData  # pylint: disable=import-outside-toplevel
        async with EventHubProducerClient.from_connection_string(
            self._connection_string,
            eventhub_name=eventhub_name,
        ) as producer:
            batch = await producer.create_batch()
            batch.add(EventData(json.dumps(payload)))
            await producer.send_batch(batch)

    async def publish_completeness_job(
        self,
        entity_id: str,
        record_type: str = "product_style",
    ) -> None:
        await self.publish(
            "completeness-jobs",
            {
                "event_type": "completeness_job",
                "entity_id": entity_id,
                "record_type": record_type,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    async def publish_ingestion_notification(
        self,
        entity_id: str,
        operation: str = "upsert",
        source: str = "pim",
    ) -> None:
        await self.publish(
            "ingestion-notifications",
            {
                "event_type": "ingestion_notification",
                "entity_id": entity_id,
                "operation": operation,
                "source": source,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )


# ---------------------------------------------------------------------------
# Aggregate adapters container
# ---------------------------------------------------------------------------


@dataclass
class IngestionAdapters:
    """Container for all Truth Ingestion adapters."""

    truth_store: TruthStoreAdapter
    pim: PIMConnector
    dam: DAMConnector
    events: EventPublisher


def build_ingestion_adapters(
    *,
    truth_store: Optional[TruthStoreAdapter] = None,
    pim: Optional[PIMConnector] = None,
    dam: Optional[DAMConnector] = None,
    events: Optional[EventPublisher] = None,
) -> IngestionAdapters:
    """Create all ingestion adapters (uses env-based defaults when not provided)."""
    return IngestionAdapters(
        truth_store=truth_store or TruthStoreAdapter(),
        pim=pim or PIMConnector(),
        dam=dam or DAMConnector(),
        events=events or EventPublisher(),
    )


# ---------------------------------------------------------------------------
# Core ingestion logic
# ---------------------------------------------------------------------------


async def ingest_single_product(
    raw_product: dict[str, Any],
    adapters: IngestionAdapters,
    *,
    field_mapping: Optional[dict[str, str]] = None,
    variant_field_mapping: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    """Ingest one product: map → resolve assets → upsert → publish events.

    Returns a summary dict describing what was persisted.
    """
    mapping = field_mapping or adapters.pim.get_field_mapping()
    style = map_pim_to_product_style(raw_product, field_mapping=mapping)

    # Resolve DAM assets and attach to any variants
    assets = await adapters.dam.fetch_assets(style.entity_id)

    # Process variants if present
    raw_variants = raw_product.get("variants") or []
    persisted_variants: list[dict[str, Any]] = []
    for raw_variant in raw_variants:
        raw_variant_with_assets = {**raw_variant, "source": raw_product.get("source", "pim")}
        variant = map_pim_to_product_variant(
            raw_variant_with_assets,
            style_id=style.entity_id,
            field_mapping=variant_field_mapping,
        )
        variant.assets = assets
        persisted_variants.append(await adapters.truth_store.upsert_product_variant(variant))

    persisted_style = await adapters.truth_store.upsert_product_style(style)

    # Audit trail
    audit = AuditEvent(
        entity_id=style.entity_id,
        event_type="ingestion",
        operation="upsert",
        details={"source": style.source, "variant_count": len(persisted_variants)},
    )
    await adapters.truth_store.write_audit_event(audit)

    # Publish downstream events
    await asyncio.gather(
        adapters.events.publish_completeness_job(style.entity_id),
        adapters.events.publish_ingestion_notification(
            style.entity_id, source=style.source
        ),
    )

    return {
        "entity_id": style.entity_id,
        "style": persisted_style,
        "variants": persisted_variants,
        "assets_resolved": len(assets),
        "audit_event_id": audit.event_id,
    }


async def ingest_bulk_products(
    raw_products: list[dict[str, Any]],
    adapters: IngestionAdapters,
    *,
    concurrency: int = 5,
    field_mapping: Optional[dict[str, str]] = None,
) -> list[dict[str, Any]]:
    """Ingest multiple products with bounded concurrency."""
    semaphore = asyncio.Semaphore(concurrency)

    async def _ingest_one(raw: dict[str, Any]) -> dict[str, Any]:
        async with semaphore:
            try:
                return await ingest_single_product(
                    raw, adapters, field_mapping=field_mapping
                )
            except Exception as exc:  # noqa: BLE001
                entity_id = raw.get("id") or raw.get("entity_id", "unknown")
                return {"entity_id": entity_id, "error": str(exc)}

    tasks = [asyncio.create_task(_ingest_one(raw)) for raw in raw_products]
    return list(await asyncio.gather(*tasks))
