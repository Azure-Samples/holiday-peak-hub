"""Tests for Event Hub subscription helpers."""

import asyncio

import holiday_peak_lib.utils.event_hub as event_hub_module
import pytest
from holiday_peak_lib.utils.event_hub import (
    EventHubSubscriber,
    EventHubSubscriberConfig,
    EventHubSubscription,
    create_eventhub_lifespan,
)


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


@pytest.mark.asyncio
async def test_create_eventhub_lifespan_supports_event_hub_connection_string_alias(monkeypatch):
    """Ensure lifespan accepts EVENT_HUB_CONNECTION_STRING alias."""
    monkeypatch.delenv("EVENTHUB_CONNECTION_STRING", raising=False)
    monkeypatch.setenv(
        "EVENT_HUB_CONNECTION_STRING",
        "Endpoint=sb://test/;SharedAccessKeyName=key;SharedAccessKey=val",
    )

    created = {"configs": [], "factories": []}

    def fake_init(self, config, *, on_event, on_error=None, client_factory=None):  # noqa: ANN001
        created["configs"].append(config)
        created["factories"].append(client_factory)

    async def fake_start(self):  # noqa: ANN001
        return None

    monkeypatch.setattr(event_hub_module.EventHubSubscriber, "__init__", fake_init)
    monkeypatch.setattr(event_hub_module.EventHubSubscriber, "start", fake_start)

    async def handler(_partition_context, _event):  # noqa: ANN001
        return None

    lifespan = create_eventhub_lifespan(
        service_name="test-service",
        subscriptions=[EventHubSubscription("hitl-jobs", "hitl-service")],
        handlers={"hitl-jobs": handler},
    )

    async with lifespan(None):
        await asyncio.sleep(0)

    assert len(created["configs"]) == 1
    assert created["configs"][0].connection_string.startswith("Endpoint=sb://test/")
    assert created["factories"][0] is None


@pytest.mark.asyncio
async def test_create_eventhub_lifespan_uses_namespace_when_connection_string_missing(monkeypatch):
    """Ensure lifespan falls back to namespace + managed identity mode."""
    monkeypatch.delenv("EVENTHUB_CONNECTION_STRING", raising=False)
    monkeypatch.delenv("EVENT_HUB_CONNECTION_STRING", raising=False)
    monkeypatch.setenv("EVENT_HUB_NAMESPACE", "test-namespace")
    monkeypatch.setenv("AZURE_CLIENT_ID", "00000000-0000-0000-0000-000000000000")

    class FakeCredential:
        def __init__(self, managed_identity_client_id=None):  # noqa: ANN001
            self.client_id = managed_identity_client_id
            self.closed = False

        async def close(self):
            self.closed = True

    created = {"configs": [], "factories": []}

    def fake_init(self, config, *, on_event, on_error=None, client_factory=None):  # noqa: ANN001
        created["configs"].append(config)
        created["factories"].append(client_factory)

    async def fake_start(self):  # noqa: ANN001
        return None

    monkeypatch.setattr(event_hub_module, "DefaultAzureCredential", FakeCredential)
    monkeypatch.setattr(event_hub_module.EventHubSubscriber, "__init__", fake_init)
    monkeypatch.setattr(event_hub_module.EventHubSubscriber, "start", fake_start)

    async def handler(_partition_context, _event):  # noqa: ANN001
        return None

    lifespan = create_eventhub_lifespan(
        service_name="test-service",
        subscriptions=[EventHubSubscription("hitl-jobs", "hitl-service")],
        handlers={"hitl-jobs": handler},
    )

    async with lifespan(None):
        await asyncio.sleep(0)

    assert len(created["configs"]) == 1
    assert created["configs"][0].connection_string == ""
    assert created["factories"][0] is not None
