"""Adapters for the Truth Enrichment service."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

from holiday_peak_lib.adapters import AdapterError, BaseAdapter
from holiday_peak_lib.utils.logging import configure_logging

logger = configure_logging(app_name="truth-enrichment")


class ProductStoreAdapter:
    """Read product records from the Cosmos DB truth store."""

    async def get_product(self, entity_id: str) -> Optional[dict[str, Any]]:
        """Return a product dict by entity_id, or None when not found."""
        # In production this calls Cosmos DB; stubbed for local/test use.
        return None

    async def get_schema(self, category: str) -> Optional[dict[str, Any]]:
        """Return a CategorySchema dict for the given category, or None."""
        return None


class _DAMConnectorProxy:
    """Thin proxy over DAM endpoint used by image-analysis enrichment."""

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None) -> None:
        self._base_url = base_url or os.getenv("DAM_BASE_URL", "")
        self._api_key = api_key or os.getenv("DAM_API_KEY", "")

    async def fetch_assets(self, entity_id: str) -> list[dict[str, Any]]:
        if not self._base_url:
            return []
        import httpx

        url = f"{self._base_url.rstrip('/')}/assets"
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers, params={"entity_id": entity_id})
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                return data
            return data.get("assets") or data.get("items") or data.get("data") or []


class DAMImageAnalysisAdapter(BaseAdapter):
    """Analyze product images from DAM and return proposed attribute values."""

    def __init__(
        self,
        *,
        dam_connector: Any | None = None,
        vision_invoker: Callable[..., Awaitable[dict[str, Any]]] | None = None,
        max_images: int = 4,
    ) -> None:
        super().__init__(
            max_calls=8,
            per_seconds=1.0,
            cache_ttl=15.0,
            retries=2,
            timeout=12.0,
            circuit_breaker_threshold=3,
            circuit_reset_seconds=20.0,
        )
        self._dam_connector = dam_connector or _DAMConnectorProxy()
        self._vision_invoker = vision_invoker
        self._max_images = max_images

    def set_vision_invoker(
        self, vision_invoker: Callable[..., Awaitable[dict[str, Any]]] | None
    ) -> None:
        self._vision_invoker = vision_invoker

    async def analyze_attribute_from_images(
        self,
        *,
        entity_id: str,
        field_name: str,
        product: dict[str, Any],
        field_definition: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        try:
            records = await self.fetch(
                {
                    "entity_id": entity_id,
                    "field_name": field_name,
                    "product": product,
                    "field_definition": field_definition or {},
                }
            )
            first = list(records)[0] if records else None
            return first or self._fallback("no_assets", field_name)
        except AdapterError as exc:
            logger.warning(
                "dam_image_analysis_unavailable entity_id=%s field_name=%s error=%s",
                entity_id,
                field_name,
                str(exc),
            )
            return self._fallback("adapter_failure", field_name)

    async def _connect_impl(self, **kwargs: Any) -> None:
        return None

    async def _fetch_impl(self, query: dict[str, Any]) -> list[dict[str, Any]]:
        entity_id = str(query.get("entity_id", ""))
        field_name = str(query.get("field_name", ""))
        product = query.get("product") or {}
        field_definition = query.get("field_definition") or {}

        assets = await self._dam_connector.fetch_assets(entity_id)
        image_urls = self._extract_image_urls(assets)
        if not image_urls:
            return [self._fallback("no_assets", field_name)]
        if self._vision_invoker is None:
            return [self._fallback("no_foundry_invoker", field_name)]

        messages = self._build_vision_messages(
            product=product,
            field_name=field_name,
            field_definition=field_definition,
            image_urls=image_urls,
        )
        vision_raw = await self._vision_invoker(
            request={"entity_id": entity_id, "field_name": field_name, "source": "image_analysis"},
            messages=messages,
        )
        parsed = self._parse_vision_response(vision_raw)
        parsed.setdefault("metadata", {})
        parsed["metadata"] = {
            **parsed["metadata"],
            "source": "image_analysis",
            "assets_count": len(image_urls),
            "assets": image_urls,
        }
        return [parsed]

    async def _upsert_impl(self, payload: dict[str, Any]) -> Optional[dict[str, Any]]:
        return payload

    async def _delete_impl(self, identifier: str) -> bool:
        return True

    def _extract_image_urls(self, assets: list[dict[str, Any]]) -> list[str]:
        urls: list[str] = []
        for asset in assets:
            url = asset.get("url") or asset.get("asset_url") or asset.get("cdn_url")
            if not url:
                continue
            urls.append(str(url))
            if len(urls) >= self._max_images:
                break
        return urls

    def _cache_key(self, query: dict[str, Any]) -> tuple:
        return (
            ("entity_id", str(query.get("entity_id", ""))),
            ("field_name", str(query.get("field_name", ""))),
        )

    def _build_vision_messages(
        self,
        *,
        product: dict[str, Any],
        field_name: str,
        field_definition: dict[str, Any],
        image_urls: list[str],
    ) -> list[dict[str, Any]]:
        field_hint = (
            f"type={field_definition.get('type', 'string')}; "
            f"description={field_definition.get('description', '')}"
        )
        prompt = {
            "instruction": (
                "Infer the missing product attribute from the provided product context and image URLs. "
                "Return JSON only with keys: value, confidence, evidence, metadata."
            ),
            "field_name": field_name,
            "field_hint": field_hint,
            "product": product,
            "image_urls": image_urls,
        }
        return [
            {
                "role": "system",
                "content": "You are a vision enrichment assistant for product catalog data.",
            },
            {"role": "user", "content": str(prompt)},
        ]

    def _parse_vision_response(self, raw: Any) -> dict[str, Any]:
        if isinstance(raw, dict) and "value" in raw:
            return {
                "value": raw.get("value"),
                "confidence": float(raw.get("confidence", 0.0)),
                "evidence": str(raw.get("evidence", "image analysis")),
                "metadata": raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {},
            }
        return {
            "value": None,
            "confidence": 0.0,
            "evidence": "vision response unavailable",
            "metadata": {"source": "image_analysis", "fallback_reason": "invalid_vision_response"},
        }

    def _fallback(self, reason: str, field_name: str) -> dict[str, Any]:
        return {
            "value": None,
            "confidence": 0.0,
            "evidence": f"image analysis unavailable for {field_name}",
            "metadata": {"source": "image_analysis", "fallback_reason": reason},
        }

class ProposedAttributeStoreAdapter:
    """Write proposed attributes to the Cosmos DB `attributes_proposed` container."""

    async def upsert(self, proposed: dict[str, Any]) -> dict[str, Any]:
        """Persist a proposed attribute and return it."""
        logger.info(
            "proposed_attribute_upsert",
            entity_id=proposed.get("entity_id"),
            field_name=proposed.get("field_name"),
            status=proposed.get("status"),
        )
        return proposed

    async def get(self, attribute_id: str) -> Optional[dict[str, Any]]:
        """Return a proposed attribute by id, or None."""
        return None


class TruthAttributeStoreAdapter:
    """Write approved attributes to the Cosmos DB `attributes_truth` container."""

    async def upsert(self, attribute: dict[str, Any]) -> dict[str, Any]:
        """Persist a truth attribute and return it."""
        logger.info(
            "truth_attribute_upsert",
            entity_id=attribute.get("entity_id"),
            field_name=attribute.get("field_name"),
        )
        return attribute


class AuditStoreAdapter:
    """Append audit events to the Cosmos DB `audit_events` container."""

    async def append(self, event: dict[str, Any]) -> dict[str, Any]:
        """Persist an audit event and return it."""
        logger.info(
            "audit_event_appended", action=event.get("action"), entity_id=event.get("entity_id")
        )
        return event


class EventHubPublisher:
    """Publish messages to an Azure Event Hub topic."""

    def __init__(self, topic: str = "hitl-jobs") -> None:
        self.topic = topic
        self._connection_string = os.getenv("EVENT_HUB_CONNECTION_STRING")

    async def publish(self, payload: dict[str, Any]) -> None:
        """Send a message to the configured Event Hub topic."""
        if not self._connection_string:
            logger.info(
                "eventhub_publish_skipped_no_connection",
                topic=self.topic,
                entity_id=payload.get("entity_id"),
            )
            return
        try:
            import json

            from azure.eventhub import EventData
            from azure.eventhub.aio import EventHubProducerClient

            async with EventHubProducerClient.from_connection_string(
                self._connection_string, eventhub_name=self.topic
            ) as producer:
                batch = await producer.create_batch()
                batch.add(EventData(json.dumps(payload)))
                await producer.send_batch(batch)
                logger.info(
                    "eventhub_published", topic=self.topic, entity_id=payload.get("entity_id")
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("eventhub_publish_failed", topic=self.topic, error=str(exc))


@dataclass
class EnrichmentAdapters:
    """Container for all Truth Enrichment service adapters."""

    products: ProductStoreAdapter = field(default_factory=ProductStoreAdapter)
    proposed: ProposedAttributeStoreAdapter = field(default_factory=ProposedAttributeStoreAdapter)
    truth: TruthAttributeStoreAdapter = field(default_factory=TruthAttributeStoreAdapter)
    audit: AuditStoreAdapter = field(default_factory=AuditStoreAdapter)
    image_analysis: DAMImageAnalysisAdapter = field(default_factory=DAMImageAnalysisAdapter)
    hitl_publisher: EventHubPublisher = field(default_factory=EventHubPublisher)


def build_enrichment_adapters() -> EnrichmentAdapters:
    """Construct the default adapter set for the enrichment service."""
    return EnrichmentAdapters()
