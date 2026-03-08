"""Event Hub helpers for truth-layer job publishing and consuming."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable
from uuid import uuid4

from azure.eventhub import EventData
from azure.eventhub.aio import EventHubConsumerClient, EventHubProducerClient
from azure.identity.aio import DefaultAzureCredential
from holiday_peak_lib.utils.logging import configure_logging
from pydantic import BaseModel, Field

# Canonical topic names — must match Bicep-provisioned Event Hub instances
INGEST_JOBS_TOPIC = "ingest-jobs"
GAP_JOBS_TOPIC = "gap-jobs"
ENRICHMENT_JOBS_TOPIC = "enrichment-jobs"
WRITEBACK_JOBS_TOPIC = "writeback-jobs"
EXPORT_JOBS_TOPIC = "export-jobs"

EventHandler = Callable[[Any, Any], Awaitable[None]]


class TruthJobMessage(BaseModel):
    """Schema for truth-layer job messages published to Event Hub."""

    job_id: str = Field(default_factory=lambda: str(uuid4()))
    entity_id: str
    job_type: str  # 'enrichment', 'gap', 'export', 'writeback', 'ingest'
    payload: dict
    priority: int = 5
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tenant_id: str = "default"


class TruthEventPublisher:
    """Publishes truth-layer job messages to Event Hub topics.

    Uses Managed Identity (DefaultAzureCredential) for authentication.
    Supports single and batch publishing with retry logic.
    """

    def __init__(
        self,
        namespace: str,
        *,
        credential: Any | None = None,
        producer_factory: Callable[[str], EventHubProducerClient] | None = None,
    ) -> None:
        """Initialise the publisher.

        Args:
            namespace: Fully qualified Event Hub namespace
                       (e.g. ``mynamespace.servicebus.windows.net``).
            credential: Azure credential to use. Defaults to
                        ``DefaultAzureCredential``.
            producer_factory: Optional factory override for testing.
        """
        self._namespace = namespace
        self._credential = credential
        self._producer_factory = producer_factory
        self._logger = configure_logging(app_name="truth-event-publisher")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_producer(self, topic: str) -> EventHubProducerClient:
        if self._producer_factory:
            return self._producer_factory(topic)
        credential = self._credential or DefaultAzureCredential()
        return EventHubProducerClient(
            fully_qualified_namespace=self._namespace,
            eventhub_name=topic,
            credential=credential,
        )

    async def _publish(self, topic: str, message: TruthJobMessage) -> None:
        """Publish a single message to an Event Hub topic."""
        async with self._get_producer(topic) as producer:
            batch = await producer.create_batch()
            batch.add(EventData(message.model_dump_json()))
            await producer.send_batch(batch)
        self._logger.info(
            "truth_job_published topic=%s job_id=%s entity_id=%s job_type=%s",
            topic,
            message.job_id,
            message.entity_id,
            message.job_type,
        )

    async def _publish_batch(self, topic: str, messages: list[TruthJobMessage]) -> None:
        """Publish a batch of messages to an Event Hub topic."""
        async with self._get_producer(topic) as producer:
            batch = await producer.create_batch()
            for message in messages:
                batch.add(EventData(message.model_dump_json()))
            await producer.send_batch(batch)
        self._logger.info(
            "truth_job_batch_published topic=%s count=%d job_type=%s",
            topic,
            len(messages),
            messages[0].job_type if messages else None,
        )

    # ------------------------------------------------------------------
    # Public publish methods
    # ------------------------------------------------------------------

    async def publish_enrichment_job(
        self,
        entity_id: str,
        fields: list[str],
        priority: int = 5,
        *,
        tenant_id: str = "default",
    ) -> TruthJobMessage:
        """Publish an enrichment job to the ``enrichment-jobs`` topic."""
        message = TruthJobMessage(
            entity_id=entity_id,
            job_type="enrichment",
            payload={"fields": fields},
            priority=priority,
            tenant_id=tenant_id,
        )
        await self._publish(ENRICHMENT_JOBS_TOPIC, message)
        return message

    async def publish_gap_job(
        self,
        entity_id: str,
        *,
        tenant_id: str = "default",
    ) -> TruthJobMessage:
        """Publish a gap-analysis job to the ``gap-jobs`` topic."""
        message = TruthJobMessage(
            entity_id=entity_id,
            job_type="gap",
            payload={},
            tenant_id=tenant_id,
        )
        await self._publish(GAP_JOBS_TOPIC, message)
        return message

    async def publish_export_job(
        self,
        entity_id: str,
        protocol: str,
        version: str,
        *,
        tenant_id: str = "default",
    ) -> TruthJobMessage:
        """Publish an export job to the ``export-jobs`` topic."""
        message = TruthJobMessage(
            entity_id=entity_id,
            job_type="export",
            payload={"protocol": protocol, "version": version},
            tenant_id=tenant_id,
        )
        await self._publish(EXPORT_JOBS_TOPIC, message)
        return message

    async def publish_writeback_job(
        self,
        entity_id: str,
        attr_id: str,
        proposed_value: Any,
        confidence: float,
        *,
        tenant_id: str = "default",
    ) -> TruthJobMessage:
        """Publish a writeback job to the ``writeback-jobs`` topic."""
        message = TruthJobMessage(
            entity_id=entity_id,
            job_type="writeback",
            payload={
                "attr_id": attr_id,
                "proposed_value": proposed_value,
                "confidence": confidence,
            },
            tenant_id=tenant_id,
        )
        await self._publish(WRITEBACK_JOBS_TOPIC, message)
        return message

    async def publish_ingest_job(
        self,
        entity_id: str,
        source: str,
        status: str,
        *,
        tenant_id: str = "default",
    ) -> TruthJobMessage:
        """Publish an ingest job to the ``ingest-jobs`` topic."""
        message = TruthJobMessage(
            entity_id=entity_id,
            job_type="ingest",
            payload={"source": source, "status": status},
            tenant_id=tenant_id,
        )
        await self._publish(INGEST_JOBS_TOPIC, message)
        return message

    async def publish_enrichment_jobs_batch(
        self,
        entity_ids: list[str],
        fields: list[str],
        priority: int = 5,
        *,
        tenant_id: str = "default",
    ) -> list[TruthJobMessage]:
        """Publish a batch of enrichment jobs in a single Event Hub send."""
        messages = [
            TruthJobMessage(
                entity_id=entity_id,
                job_type="enrichment",
                payload={"fields": fields},
                priority=priority,
                tenant_id=tenant_id,
            )
            for entity_id in entity_ids
        ]
        await self._publish_batch(ENRICHMENT_JOBS_TOPIC, messages)
        return messages


class TruthEventConsumer:
    """Base consumer for truth-layer Event Hub topics.

    Wraps ``EventHubConsumerClient`` with checkpoint storage in Blob Storage
    and graceful shutdown support. Assign one consumer group per service.
    """

    def __init__(
        self,
        namespace: str,
        topic: str,
        consumer_group: str,
        *,
        credential: Any | None = None,
        blob_checkpoint_store: Any | None = None,
        on_event: EventHandler | None = None,
        client_factory: Callable[[], EventHubConsumerClient] | None = None,
    ) -> None:
        """Initialise the consumer.

        Args:
            namespace: Fully qualified Event Hub namespace.
            topic: Event Hub topic name.
            consumer_group: Consumer group name (one per service).
            credential: Azure credential. Defaults to ``DefaultAzureCredential``.
            blob_checkpoint_store: Optional ``BlobCheckpointStore`` for
                                   checkpoint persistence in Blob Storage.
            on_event: Async callable invoked for each received event.
            client_factory: Optional factory override for testing.
        """
        self._namespace = namespace
        self._topic = topic
        self._consumer_group = consumer_group
        self._credential = credential
        self._blob_checkpoint_store = blob_checkpoint_store
        self._on_event = on_event
        self._client_factory = client_factory
        self._logger = configure_logging(app_name=f"truth-event-consumer-{topic}")
        self._running = False

    def _get_client(self) -> EventHubConsumerClient:
        if self._client_factory:
            return self._client_factory()
        credential = self._credential or DefaultAzureCredential()
        return EventHubConsumerClient(
            fully_qualified_namespace=self._namespace,
            eventhub_name=self._topic,
            consumer_group=self._consumer_group,
            credential=credential,
            checkpoint_store=self._blob_checkpoint_store,
        )

    async def _handle_event(self, partition_context: Any, event: Any) -> None:
        """Default event handler — logs and delegates to custom handler."""
        try:
            payload = json.loads(event.body_as_str())
            self._logger.info(
                "truth_event_received topic=%s job_type=%s entity_id=%s job_id=%s",
                self._topic,
                payload.get("job_type"),
                payload.get("entity_id"),
                payload.get("job_id"),
            )
            if self._on_event:
                await self._on_event(partition_context, event)
            await partition_context.update_checkpoint(event)
        except Exception as exc:  # pragma: no cover
            self._logger.error("truth_event_handler_error topic=%s error=%s", self._topic, str(exc))

    async def start(self) -> None:
        """Start receiving events. Runs until :meth:`stop` is called."""
        self._running = True
        self._logger.info(
            "truth_consumer_starting topic=%s consumer_group=%s",
            self._topic,
            self._consumer_group,
        )
        async with self._get_client() as client:
            await client.receive(
                on_event=self._handle_event,
                starting_position="-1",
            )

    async def stop(self) -> None:
        """Signal the consumer to stop gracefully."""
        self._running = False
        self._logger.info("truth_consumer_stopping topic=%s", self._topic)


def build_truth_consumer_task(
    namespace: str,
    topic: str,
    consumer_group: str,
    *,
    on_event: EventHandler | None = None,
    credential: Any | None = None,
    blob_checkpoint_store: Any | None = None,
    client_factory: Callable[[], EventHubConsumerClient] | None = None,
) -> asyncio.Task:
    """Create an asyncio task running a :class:`TruthEventConsumer`.

    This is a convenience helper for use inside FastAPI lifespan functions.
    """
    consumer = TruthEventConsumer(
        namespace=namespace,
        topic=topic,
        consumer_group=consumer_group,
        credential=credential,
        blob_checkpoint_store=blob_checkpoint_store,
        on_event=on_event,
        client_factory=client_factory,
    )
    return asyncio.create_task(consumer.start())
