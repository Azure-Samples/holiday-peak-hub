"""Adapters for the Truth Enrichment service."""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass, field
from typing import Any, Optional

from azure.identity.aio import DefaultAzureCredential
from azure.storage.blob.aio import BlobServiceClient
from holiday_peak_lib.adapters.dam_image_analysis import DAMImageAnalysisAdapter
from holiday_peak_lib.self_healing import SelfHealingKernel
from holiday_peak_lib.utils import (
    PLATFORM_JOBS_EVENT_HUB_CONNECTION_STRING_ENV,
    PLATFORM_JOBS_EVENT_HUB_NAMESPACE_ENV,
)
from holiday_peak_lib.utils.logging import configure_logging
from holiday_peak_lib.utils.truth_event_hub import (
    TruthEventPublisher,
    build_truth_event_publisher_from_env,
)

logger = configure_logging(app_name="truth-enrichment")


class ProductStoreAdapter:
    """Read product records from the Cosmos DB truth store."""

    async def get_product(self, _entity_id: str) -> Optional[dict[str, Any]]:
        """Return a product dict by entity_id, or None when not found."""
        # In production this calls Cosmos DB; stubbed for local/test use.
        return None

    async def get_schema(self, _category: str) -> Optional[dict[str, Any]]:
        """Return a CategorySchema dict for the given category, or None."""
        return None


class BlobProductStoreAdapter(ProductStoreAdapter):
    """Read product records from Azure Blob Storage.

    Each product is stored as a JSON blob named ``{entity_id}.json``
    inside the configured container (env ``TRUTH_PRODUCT_BLOB_CONTAINER``,
    default ``products``).  Falls back to ``{entity_id}`` without extension
    when the ``.json`` variant is not found.
    """

    def __init__(
        self,
        account_url: str,
        container_name: str,
        *,
        schema_prefix: str = "_schemas/",
    ) -> None:
        self._account_url = account_url
        self._container_name = container_name
        self._schema_prefix = schema_prefix
        self._client: BlobServiceClient | None = None
        self._connect_lock = asyncio.Lock()

    async def _ensure_client(self) -> BlobServiceClient:
        if self._client is not None:
            return self._client
        async with self._connect_lock:
            if self._client is not None:
                return self._client
            credential = DefaultAzureCredential()
            self._client = BlobServiceClient(
                self._account_url,
                credential=credential,
            )
            return self._client

    async def _download_json(self, blob_name: str) -> dict[str, Any] | None:
        client = await self._ensure_client()
        container = client.get_container_client(self._container_name)
        try:
            blob_data = await container.download_blob(blob_name)
            raw = await blob_data.readall()
            return json.loads(raw)
        except (json.JSONDecodeError, KeyError, ValueError):
            logger.warning(
                "blob_product_parse_error blob=%s container=%s",
                blob_name,
                self._container_name,
            )
            return None
        except Exception:  # noqa: BLE001
            logger.debug(
                "blob_product_not_found blob=%s container=%s",
                blob_name,
                self._container_name,
            )
            return None

    async def get_product(self, entity_id: str) -> dict[str, Any] | None:
        result = await self._download_json(f"{entity_id}.json")
        if result is not None:
            return result
        return await self._download_json(entity_id)

    async def get_schema(self, category: str) -> dict[str, Any] | None:
        if not category:
            return None
        return await self._download_json(f"{self._schema_prefix}{category}.json")

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None


class ProposedAttributeStoreAdapter:
    """Write proposed attributes to the Cosmos DB `attributes_proposed` container."""

    async def upsert(self, proposed: dict[str, Any]) -> dict[str, Any]:
        """Persist a proposed attribute and return it."""
        logger.info(
            "proposed_attribute_upsert entity_id=%s field_name=%s status=%s",
            proposed.get("entity_id"),
            proposed.get("field_name"),
            proposed.get("status"),
        )
        return proposed

    async def get(self, _attribute_id: str) -> Optional[dict[str, Any]]:
        """Return a proposed attribute by id, or None."""
        return None


class TruthAttributeStoreAdapter:
    """Write approved attributes to the Cosmos DB `attributes_truth` container."""

    async def upsert(self, attribute: dict[str, Any]) -> dict[str, Any]:
        """Persist a truth attribute and return it."""
        logger.info(
            "truth_attribute_upsert entity_id=%s field_name=%s",
            attribute.get("entity_id"),
            attribute.get("field_name"),
        )
        return attribute


class AuditStoreAdapter:
    """Append audit events to the Cosmos DB `audit_events` container."""

    async def append(self, event: dict[str, Any]) -> dict[str, Any]:
        """Persist an audit event and return it."""
        logger.info(
            "audit_event_appended action=%s entity_id=%s",
            event.get("action"),
            event.get("entity_id"),
        )
        return event


class EventHubPublisher:
    """Publish messages to an Azure Event Hub topic."""

    def __init__(
        self,
        topic: str = "hitl-jobs",
        *,
        publisher: TruthEventPublisher | None = None,
        self_healing_kernel: SelfHealingKernel | None = None,
    ) -> None:
        self.topic = topic
        self._publisher = publisher or build_truth_event_publisher_from_env(
            service_name="truth-enrichment",
            namespace_env=PLATFORM_JOBS_EVENT_HUB_NAMESPACE_ENV,
            connection_string_env=PLATFORM_JOBS_EVENT_HUB_CONNECTION_STRING_ENV,
            self_healing_kernel=self_healing_kernel,
        )

    def attach_self_healing(self, self_healing_kernel: SelfHealingKernel | None) -> None:
        """Attach the app-owned self-healing kernel after bootstrap."""

        if hasattr(self._publisher, "self_healing_kernel"):
            self._publisher.self_healing_kernel = self_healing_kernel

    async def publish(self, payload: dict[str, Any]) -> None:
        """Send a message to the configured Event Hub topic."""
        payload_data = payload.get("data")
        data: dict[str, Any] = payload_data if isinstance(payload_data, dict) else {}
        entity_id = payload.get("entity_id") or data.get("entity_id")
        await self._publisher.publish_payload(
            self.topic,
            payload,
            metadata={
                "domain": "truth-enrichment",
                "entity_id": entity_id,
            },
            remediation_context={
                "preferred_action": "reset_messaging_publisher_bindings",
                "workflow": "hitl_review_dispatch",
                "target_topic": self.topic,
            },
        )


@dataclass
class EnrichmentAdapters:
    """Container for all Truth Enrichment service adapters."""

    products: ProductStoreAdapter = field(default_factory=ProductStoreAdapter)
    proposed: ProposedAttributeStoreAdapter = field(default_factory=ProposedAttributeStoreAdapter)
    truth: TruthAttributeStoreAdapter = field(default_factory=TruthAttributeStoreAdapter)
    audit: AuditStoreAdapter = field(default_factory=AuditStoreAdapter)
    dam: DAMImageAnalysisAdapter = field(default_factory=DAMImageAnalysisAdapter)
    image_analysis: DAMImageAnalysisAdapter | None = None
    hitl_publisher: EventHubPublisher = field(default_factory=EventHubPublisher)
    search_enrichment_publisher: EventHubPublisher | None = None

    def __post_init__(self) -> None:
        if self.image_analysis is not None:
            self.dam = self.image_analysis
        self.image_analysis = self.dam


def build_enrichment_adapters() -> EnrichmentAdapters:
    """Construct the default adapter set for the enrichment service."""
    max_images_raw = os.getenv("DAM_MAX_IMAGES", "4")
    try:
        max_images = max(1, int(max_images_raw))
    except ValueError:
        max_images = 4

    blob_account_url = (os.getenv("BLOB_ACCOUNT_URL") or "").strip()
    product_container = (os.getenv("TRUTH_PRODUCT_BLOB_CONTAINER") or "").strip()
    if blob_account_url and product_container:
        products: ProductStoreAdapter = BlobProductStoreAdapter(
            account_url=blob_account_url,
            container_name=product_container,
        )
        logger.info(
            "blob_product_store_enabled container=%s account=%s",
            product_container,
            blob_account_url,
        )
    else:
        products = ProductStoreAdapter()

    search_enrichment_publisher = EventHubPublisher(topic="search-enrichment-jobs")

    return EnrichmentAdapters(
        products=products,
        dam=DAMImageAnalysisAdapter(max_images=max_images),
        search_enrichment_publisher=search_enrichment_publisher,
    )
