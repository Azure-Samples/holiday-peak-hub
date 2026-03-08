"""Tests for truth-layer Event Hub helpers."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from holiday_peak_lib.utils.truth_event_hub import (
    ENRICHMENT_JOBS_TOPIC,
    EXPORT_JOBS_TOPIC,
    GAP_JOBS_TOPIC,
    INGEST_JOBS_TOPIC,
    WRITEBACK_JOBS_TOPIC,
    TruthEventConsumer,
    TruthEventPublisher,
    TruthJobMessage,
    build_truth_consumer_task,
)

# ---------------------------------------------------------------------------
# Helpers / fakes
# ---------------------------------------------------------------------------


def _make_producer_factory(batch_mock: MagicMock) -> MagicMock:
    """Return a factory that yields a fake EventHubProducerClient."""
    producer = AsyncMock()
    producer.__aenter__ = AsyncMock(return_value=producer)
    producer.__aexit__ = AsyncMock(return_value=False)
    producer.create_batch = AsyncMock(return_value=batch_mock)
    producer.send_batch = AsyncMock()

    factory = MagicMock(return_value=producer)
    return factory, producer


class FakePartitionContext:
    def __init__(self) -> None:
        self.checkpoints = 0

    async def update_checkpoint(self, event) -> None:  # noqa: ANN001
        self.checkpoints += 1


class FakeEvent:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def body_as_str(self) -> str:
        return json.dumps(self._payload)


class FakeConsumerClient:
    """Fake EventHubConsumerClient that fires one event then returns."""

    def __init__(self, partition_context: FakePartitionContext, event: FakeEvent) -> None:
        self._partition_context = partition_context
        self._event = event

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False

    async def receive(self, *, on_event, starting_position="-1"):  # noqa: ANN001
        await on_event(self._partition_context, self._event)


# ---------------------------------------------------------------------------
# TruthJobMessage tests
# ---------------------------------------------------------------------------


class TestTruthJobMessage:
    def test_defaults(self):
        msg = TruthJobMessage(entity_id="e1", job_type="enrichment", payload={})
        assert msg.entity_id == "e1"
        assert msg.job_type == "enrichment"
        assert msg.priority == 5
        assert msg.tenant_id == "default"
        assert len(msg.job_id) == 36  # UUID format

    def test_custom_fields(self):
        msg = TruthJobMessage(
            entity_id="e2",
            job_type="export",
            payload={"key": "val"},
            priority=1,
            tenant_id="acme",
        )
        assert msg.priority == 1
        assert msg.tenant_id == "acme"
        assert msg.payload == {"key": "val"}

    def test_json_serialisable(self):
        msg = TruthJobMessage(entity_id="e3", job_type="gap", payload={})
        data = json.loads(msg.model_dump_json())
        assert data["entity_id"] == "e3"


# ---------------------------------------------------------------------------
# TruthEventPublisher tests
# ---------------------------------------------------------------------------


class TestTruthEventPublisher:
    """Unit tests for TruthEventPublisher — all I/O is mocked."""

    @pytest.mark.asyncio
    async def test_publish_enrichment_job(self):
        batch = MagicMock()
        factory, producer = _make_producer_factory(batch)

        publisher = TruthEventPublisher("ns.servicebus.windows.net", producer_factory=factory)
        msg = await publisher.publish_enrichment_job("prod-1", ["title", "desc"], priority=3)

        factory.assert_called_once_with(ENRICHMENT_JOBS_TOPIC)
        producer.create_batch.assert_called_once()
        batch.add.assert_called_once()
        producer.send_batch.assert_called_once_with(batch)
        assert msg.job_type == "enrichment"
        assert msg.entity_id == "prod-1"
        assert msg.payload["fields"] == ["title", "desc"]
        assert msg.priority == 3

    @pytest.mark.asyncio
    async def test_publish_gap_job(self):
        batch = MagicMock()
        factory, producer = _make_producer_factory(batch)

        publisher = TruthEventPublisher("ns.servicebus.windows.net", producer_factory=factory)
        msg = await publisher.publish_gap_job("prod-2")

        factory.assert_called_once_with(GAP_JOBS_TOPIC)
        assert msg.job_type == "gap"
        assert msg.entity_id == "prod-2"

    @pytest.mark.asyncio
    async def test_publish_export_job(self):
        batch = MagicMock()
        factory, producer = _make_producer_factory(batch)

        publisher = TruthEventPublisher("ns.servicebus.windows.net", producer_factory=factory)
        msg = await publisher.publish_export_job("prod-3", protocol="GS1", version="3.1")

        factory.assert_called_once_with(EXPORT_JOBS_TOPIC)
        assert msg.job_type == "export"
        assert msg.payload == {"protocol": "GS1", "version": "3.1"}

    @pytest.mark.asyncio
    async def test_publish_writeback_job(self):
        batch = MagicMock()
        factory, producer = _make_producer_factory(batch)

        publisher = TruthEventPublisher("ns.servicebus.windows.net", producer_factory=factory)
        msg = await publisher.publish_writeback_job(
            "prod-4", attr_id="color", proposed_value="red", confidence=0.72
        )

        factory.assert_called_once_with(WRITEBACK_JOBS_TOPIC)
        assert msg.job_type == "writeback"
        assert msg.payload["confidence"] == 0.72
        assert msg.payload["attr_id"] == "color"

    @pytest.mark.asyncio
    async def test_publish_ingest_job(self):
        batch = MagicMock()
        factory, producer = _make_producer_factory(batch)

        publisher = TruthEventPublisher("ns.servicebus.windows.net", producer_factory=factory)
        msg = await publisher.publish_ingest_job("prod-5", source="erp", status="success")

        factory.assert_called_once_with(INGEST_JOBS_TOPIC)
        assert msg.job_type == "ingest"
        assert msg.payload == {"source": "erp", "status": "success"}

    @pytest.mark.asyncio
    async def test_publish_enrichment_jobs_batch(self):
        batch = MagicMock()
        factory, producer = _make_producer_factory(batch)

        publisher = TruthEventPublisher("ns.servicebus.windows.net", producer_factory=factory)
        msgs = await publisher.publish_enrichment_jobs_batch(["e1", "e2", "e3"], fields=["title"])

        factory.assert_called_once_with(ENRICHMENT_JOBS_TOPIC)
        producer.send_batch.assert_called_once()
        assert len(msgs) == 3
        assert all(m.job_type == "enrichment" for m in msgs)
        assert [m.entity_id for m in msgs] == ["e1", "e2", "e3"]

    @pytest.mark.asyncio
    async def test_publish_with_tenant_id(self):
        batch = MagicMock()
        factory, _ = _make_producer_factory(batch)

        publisher = TruthEventPublisher("ns.servicebus.windows.net", producer_factory=factory)
        msg = await publisher.publish_gap_job("prod-6", tenant_id="tenant-abc")
        assert msg.tenant_id == "tenant-abc"


# ---------------------------------------------------------------------------
# TruthEventConsumer tests
# ---------------------------------------------------------------------------


class TestTruthEventConsumer:
    @pytest.mark.asyncio
    async def test_consumer_invokes_handler_and_checkpoints(self):
        ctx = FakePartitionContext()
        event = FakeEvent(
            {"job_id": "jid", "entity_id": "e1", "job_type": "enrichment", "payload": {}}
        )
        handler_calls = {"count": 0}

        async def on_event(partition_context, ev):  # noqa: ANN001
            handler_calls["count"] += 1

        consumer = TruthEventConsumer(
            namespace="ns.servicebus.windows.net",
            topic=ENRICHMENT_JOBS_TOPIC,
            consumer_group="svc-enrichment",
            on_event=on_event,
            client_factory=lambda: FakeConsumerClient(ctx, event),
        )
        await consumer.start()

        assert handler_calls["count"] == 1
        assert ctx.checkpoints == 1

    @pytest.mark.asyncio
    async def test_consumer_default_handler_no_custom_callback(self):
        ctx = FakePartitionContext()
        event = FakeEvent({"job_id": "jid", "entity_id": "e2", "job_type": "gap", "payload": {}})

        consumer = TruthEventConsumer(
            namespace="ns.servicebus.windows.net",
            topic=GAP_JOBS_TOPIC,
            consumer_group="svc-gap",
            client_factory=lambda: FakeConsumerClient(ctx, event),
        )
        await consumer.start()

        assert ctx.checkpoints == 1

    @pytest.mark.asyncio
    async def test_consumer_stop(self):
        consumer = TruthEventConsumer(
            namespace="ns.servicebus.windows.net",
            topic=ENRICHMENT_JOBS_TOPIC,
            consumer_group="svc-enrichment",
        )
        await consumer.stop()
        assert not consumer._running


# ---------------------------------------------------------------------------
# build_truth_consumer_task helper test
# ---------------------------------------------------------------------------


class TestBuildTruthConsumerTask:
    @pytest.mark.asyncio
    async def test_returns_asyncio_task(self):
        import asyncio

        ctx = FakePartitionContext()
        event = FakeEvent({"job_id": "jid", "entity_id": "e1", "job_type": "export", "payload": {}})

        task = build_truth_consumer_task(
            namespace="ns.servicebus.windows.net",
            topic=EXPORT_JOBS_TOPIC,
            consumer_group="svc-export",
            client_factory=lambda: FakeConsumerClient(ctx, event),
        )
        assert isinstance(task, asyncio.Task)
        await task
