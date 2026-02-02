"""Tests for Event Hub subscription helpers."""
import pytest

from holiday_peak_lib.utils.event_hub import EventHubSubscriber, EventHubSubscriberConfig


class FakePartitionContext:
    """Simple partition context stub."""

    def __init__(self) -> None:
        self.checkpoints = 0

    async def update_checkpoint(self, event) -> None:  # noqa: ANN001
        self.checkpoints += 1


class FakeEvent:
    """Simple event stub."""

    def __init__(self, payload: str) -> None:
        self.payload = payload


class FakeConsumerClient:
    """Fake EventHubConsumerClient for tests."""

    def __init__(self, partition_context: FakePartitionContext, event: FakeEvent) -> None:
        self.received = False
        self._partition_context = partition_context
        self._event = event

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):  # noqa: ANN001
        return False

    async def receive(self, *, on_event, on_error, starting_position):  # noqa: ANN001
        self.received = True
        await on_event(self._partition_context, self._event)


@pytest.mark.asyncio
async def test_event_hub_subscriber_invokes_handler():
    """Ensure EventHubSubscriber calls handler and checkpoints."""
    context = FakePartitionContext()
    event = FakeEvent("test")
    handler_calls = {"count": 0}

    async def on_event(partition_context, event):  # noqa: ANN001
        assert event.payload == "test"
        handler_calls["count"] += 1

    config = EventHubSubscriberConfig(
        connection_string="Endpoint=sb://test/;SharedAccessKeyName=key;SharedAccessKey=val",
        eventhub_name="test-hub",
    )

    subscriber = EventHubSubscriber(
        config,
        on_event=on_event,
        client_factory=lambda: FakeConsumerClient(context, event),
    )

    await subscriber.start()
    assert handler_calls["count"] == 1
    assert context.checkpoints == 1


@pytest.mark.asyncio
async def test_event_hub_subscriber_disables_checkpoint():
    """Ensure checkpointing can be disabled."""
    checkpoint_calls = {"count": 0}
    context = FakePartitionContext()
    event = FakeEvent("test")

    async def on_event(partition_context, event):  # noqa: ANN001
        checkpoint_calls["count"] += 1

    config = EventHubSubscriberConfig(
        connection_string="Endpoint=sb://test/;SharedAccessKeyName=key;SharedAccessKey=val",
        eventhub_name="test-hub",
        checkpoint=False,
    )

    subscriber = EventHubSubscriber(
        config,
        on_event=on_event,
        client_factory=lambda: FakeConsumerClient(context, event),
    )

    await subscriber.start()
    assert checkpoint_calls["count"] == 1
    assert context.checkpoints == 0
