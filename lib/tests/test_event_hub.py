"""Tests for Event Hub subscription helpers."""

import asyncio
from typing import cast
from unittest.mock import AsyncMock

import holiday_peak_lib.utils.event_hub as event_hub_module
import pytest
from azure.eventhub.aio import EventHubConsumerClient
from holiday_peak_lib.self_healing import SelfHealingKernel, SurfaceType, default_surface_manifest
from holiday_peak_lib.utils.compensation import CompensationResult
from holiday_peak_lib.utils.event_hub import (
    DeadLetterPolicy,
    DeadLetterStrategy,
    EventHubSubscriber,
    EventHubSubscriberConfig,
    EventHubSubscription,
    EventPublishError,
    PublishReliabilityProfile,
    create_eventhub_lifespan,
    publish_with_reliability,
)


class FakePartitionContext:
    """Simple partition context stub."""

    def __init__(self) -> None:
        self.checkpoints = 0

    async def update_checkpoint(self, _event) -> None:  # noqa: ANN001
        self.checkpoints += 1


class FakeEvent:
    """Simple event stub."""

    def __init__(self, payload: str) -> None:
        self.payload = payload


def _build_consumer_client(
    partition_context: FakePartitionContext,
    event: FakeEvent,
) -> EventHubConsumerClient:
    return cast(EventHubConsumerClient, FakeConsumerClient(partition_context, event))


def _build_error_consumer_client(
    partition_context: FakePartitionContext,
    event: FakeEvent,
) -> EventHubConsumerClient:
    return cast(EventHubConsumerClient, FakeErrorConsumerClient(partition_context, event))


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
        _ = on_error
        _ = starting_position
        self.received = True
        await on_event(self._partition_context, self._event)


class FakeErrorConsumerClient(FakeConsumerClient):
    """Fake Event Hub client that triggers the on_error callback."""

    async def receive(self, *, on_event, on_error, starting_position):  # noqa: ANN001
        self.received = True
        if on_error is not None:
            await on_error(self._partition_context, RuntimeError("subscriber_failure"))


@pytest.mark.asyncio
async def test_event_hub_subscriber_invokes_handler():
    """Ensure EventHubSubscriber calls handler and checkpoints."""
    context = FakePartitionContext()
    event = FakeEvent("test")
    handler_calls = {"count": 0}

    async def on_event(_partition_context, event):  # noqa: ANN001
        assert event.payload == "test"
        handler_calls["count"] += 1

    config = EventHubSubscriberConfig(
        connection_string="Endpoint=sb://test/;SharedAccessKeyName=key;SharedAccessKey=val",
        eventhub_name="test-hub",
    )

    subscriber = EventHubSubscriber(
        config,
        on_event=on_event,
        client_factory=lambda: _build_consumer_client(context, event),
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

    async def on_event(_partition_context, _event):  # noqa: ANN001
        checkpoint_calls["count"] += 1

    config = EventHubSubscriberConfig(
        connection_string="Endpoint=sb://test/;SharedAccessKeyName=key;SharedAccessKey=val",
        eventhub_name="test-hub",
        checkpoint=False,
    )

    subscriber = EventHubSubscriber(
        config,
        on_event=on_event,
        client_factory=lambda: _build_consumer_client(context, event),
    )

    await subscriber.start()
    assert checkpoint_calls["count"] == 1
    assert context.checkpoints == 0


@pytest.mark.asyncio
async def test_create_eventhub_lifespan_uses_per_subscription_binding_envs(monkeypatch):
    """Ensure each subscription resolves its own binding contract."""
    monkeypatch.setenv(
        "EVENT_HUB_NAMESPACE",
        "retail-namespace.servicebus.windows.net",
    )
    monkeypatch.delenv("EVENT_HUB_CONNECTION_STRING", raising=False)
    monkeypatch.setenv(
        "PLATFORM_JOBS_EVENT_HUB_CONNECTION_STRING",
        "Endpoint=sb://platform/;SharedAccessKeyName=key;SharedAccessKey=val",
    )

    created = {"configs": [], "factories": []}

    def fake_init(_self, config, *, on_event, on_error=None, client_factory=None):  # noqa: ANN001
        _ = on_event
        _ = on_error
        created["configs"].append(config)
        created["factories"].append(client_factory)

    async def fake_start(_self):  # noqa: ANN001
        return None

    monkeypatch.setattr(event_hub_module.EventHubSubscriber, "__init__", fake_init)
    monkeypatch.setattr(event_hub_module.EventHubSubscriber, "start", fake_start)

    async def handler(_partition_context, _event):  # noqa: ANN001
        return None

    lifespan = create_eventhub_lifespan(
        service_name="test-service",
        subscriptions=[
            EventHubSubscription("product-events", "catalog-group"),
            EventHubSubscription(
                "export-jobs",
                "export-engine",
                namespace_env="PLATFORM_JOBS_EVENT_HUB_NAMESPACE",
                connection_string_env="PLATFORM_JOBS_EVENT_HUB_CONNECTION_STRING",
            ),
        ],
        handlers={"product-events": handler, "export-jobs": handler},
    )

    async with lifespan(None):
        await asyncio.sleep(0)

    assert len(created["configs"]) == 2
    assert created["configs"][0].eventhub_name == "product-events"
    assert created["configs"][0].connection_string == ""
    assert created["factories"][0] is not None
    assert created["configs"][1].eventhub_name == "export-jobs"
    assert created["configs"][1].connection_string.startswith("Endpoint=sb://platform/")
    assert created["factories"][1] is None


@pytest.mark.asyncio
async def test_create_eventhub_lifespan_uses_namespace_when_connection_string_missing(monkeypatch):
    """Ensure lifespan falls back to namespace + managed identity mode."""
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

    def fake_init(_self, config, *, on_event, on_error=None, client_factory=None):  # noqa: ANN001
        _ = on_event
        _ = on_error
        created["configs"].append(config)
        created["factories"].append(client_factory)

    async def fake_start(_self):  # noqa: ANN001
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


@pytest.mark.asyncio
async def test_create_eventhub_lifespan_rejects_legacy_namespace_alias(monkeypatch):
    """Ensure the legacy namespace alias is not used on the shared consumer path."""
    monkeypatch.delenv("EVENT_HUB_CONNECTION_STRING", raising=False)
    monkeypatch.delenv("EVENT_HUB_NAMESPACE", raising=False)
    monkeypatch.setenv("EVENTHUB_NAMESPACE", "legacy-namespace")

    async def handler(_partition_context, _event):  # noqa: ANN001
        return None

    lifespan = create_eventhub_lifespan(
        service_name="test-service",
        subscriptions=[EventHubSubscription("hitl-jobs", "hitl-service")],
        handlers={"hitl-jobs": handler},
    )

    with pytest.raises(RuntimeError, match="EVENT_HUB_CONNECTION_STRING or EVENT_HUB_NAMESPACE"):
        async with lifespan(None):
            await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_create_eventhub_lifespan_fails_closed_when_platform_binding_is_missing(monkeypatch):
    """Ensure platform subscriptions do not fall back to the retail Event Hubs envs."""
    monkeypatch.setenv("EVENT_HUB_NAMESPACE", "retail-namespace")
    monkeypatch.delenv("PLATFORM_JOBS_EVENT_HUB_NAMESPACE", raising=False)
    monkeypatch.delenv("PLATFORM_JOBS_EVENT_HUB_CONNECTION_STRING", raising=False)

    async def handler(_partition_context, _event):  # noqa: ANN001
        return None

    lifespan = create_eventhub_lifespan(
        service_name="test-service",
        subscriptions=[
            EventHubSubscription(
                "export-jobs",
                "export-engine",
                namespace_env="PLATFORM_JOBS_EVENT_HUB_NAMESPACE",
                connection_string_env="PLATFORM_JOBS_EVENT_HUB_CONNECTION_STRING",
            )
        ],
        handlers={"export-jobs": handler},
    )

    with pytest.raises(
        RuntimeError,
        match="PLATFORM_JOBS_EVENT_HUB_CONNECTION_STRING or PLATFORM_JOBS_EVENT_HUB_NAMESPACE",
    ):
        async with lifespan(None):
            await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_event_hub_on_error_emits_failure_signal():
    context = FakePartitionContext()
    event = FakeEvent("test")
    captured = []

    async def on_event(_partition_context, _event):  # noqa: ANN001
        return None

    async def emit(signal):  # noqa: ANN001
        captured.append(signal)

    config = EventHubSubscriberConfig(
        connection_string="Endpoint=sb://test/;SharedAccessKeyName=key;SharedAccessKey=val",
        eventhub_name="test-hub",
    )

    subscriber = EventHubSubscriber(
        config,
        on_event=on_event,
        client_factory=lambda: _build_error_consumer_client(context, event),
        failure_signal_emitter=emit,
    )

    await subscriber.start()

    assert captured
    assert captured[0].surface == SurfaceType.MESSAGING
    assert captured[0].component == "test-hub"


@pytest.mark.asyncio
async def test_event_hub_on_error_can_trigger_reconcile():
    context = FakePartitionContext()
    event = FakeEvent("test")
    kernel = SelfHealingKernel(
        service_name="svc",
        manifest=default_surface_manifest("svc"),
        enabled=True,
    )
    kernel.reconcile = AsyncMock(return_value={"reconciled_incidents": 0})  # type: ignore[method-assign]

    async def on_event(_partition_context, _event):  # noqa: ANN001
        return None

    config = EventHubSubscriberConfig(
        connection_string="Endpoint=sb://test/;SharedAccessKeyName=key;SharedAccessKey=val",
        eventhub_name="test-hub",
    )

    subscriber = EventHubSubscriber(
        config,
        on_event=on_event,
        client_factory=lambda: _build_error_consumer_client(context, event),
        self_healing_kernel=kernel,
        reconcile_on_error=True,
    )

    await subscriber.start()

    kernel.reconcile.assert_awaited_once()


@pytest.mark.asyncio
async def test_publish_with_reliability_emits_compensation_metadata():
    kernel = SelfHealingKernel(
        service_name="crud-service",
        manifest=default_surface_manifest("crud-service"),
        enabled=True,
        reconcile_on_messaging_error=True,
    )
    compensation = CompensationResult(completed=["reservation_lock_rollback"])

    async def failing_send() -> None:
        raise TimeoutError("event hub unavailable")

    with pytest.raises(EventPublishError) as exc_info:
        await publish_with_reliability(
            send=failing_send,
            service_name="crud-service",
            topic="order-events",
            event_type="OrderCreated",
            self_healing_kernel=kernel,
            metadata={"domain": "orders", "entity_id": "order-1"},
            remediation_context={
                "preferred_action": "reset_messaging_publisher_bindings",
                "workflow": "checkout_finalize",
            },
            compensation_result=compensation,
        )

    incident = kernel.list_incidents(limit=1)[0]
    assert exc_info.value.envelope.category.value == "transient"
    assert incident.metadata["failure_stage"] == "publish"
    assert incident.metadata["compensation"]["completed_actions"] == ["reservation_lock_rollback"]
    assert incident.actions == ["reset_messaging_publisher_bindings"]


@pytest.mark.asyncio
async def test_publish_with_reliability_retries_transient_failures_with_backoff():
    attempts = {"count": 0}
    retry_delays: list[float] = []

    async def flaky_send() -> None:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise TimeoutError("event hub unavailable")

    async def fake_sleep(delay: float) -> None:
        retry_delays.append(delay)

    await publish_with_reliability(
        send=flaky_send,
        service_name="crud-service",
        topic="order-events",
        event_type="OrderCreated",
        profile=PublishReliabilityProfile(
            name="retrying",
            retry_max_attempts=3,
            retry_backoff_base_seconds=0.1,
            retry_backoff_max_seconds=1.0,
        ),
        sleep=fake_sleep,
    )

    assert attempts["count"] == 3
    assert retry_delays == [0.1, 0.2]


@pytest.mark.asyncio
async def test_publish_with_reliability_uses_profile_dead_letter_callback():
    dead_letter_topics: list[str] = []

    async def failing_send() -> None:
        raise TimeoutError("event hub unavailable")

    async def record_dead_letter(envelope) -> dict[str, object]:  # noqa: ANN001
        dead_letter_topics.append(envelope.topic)
        return {"stored": True, "topic": envelope.topic}

    with pytest.raises(EventPublishError) as exc_info:
        await publish_with_reliability(
            send=failing_send,
            service_name="crud-service",
            topic="order-events",
            event_type="OrderCreated",
            profile=PublishReliabilityProfile(
                name="critical_with_callback_dlq",
                retry_max_attempts=1,
                dead_letter_policy=DeadLetterPolicy(
                    strategy=DeadLetterStrategy.CALLBACK,
                    reason="persist_publish_failure",
                    metadata={"sink": "compensation-audit"},
                ),
            ),
            dead_letter_callback=record_dead_letter,
        )

    dead_letter_metadata = exc_info.value.envelope.metadata["dead_letter"]
    assert dead_letter_topics == ["order-events"]
    assert dead_letter_metadata == {
        "strategy": "callback",
        "reason": "persist_publish_failure",
        "callback_configured": True,
        "callback_invoked": True,
        "policy_metadata": {"sink": "compensation-audit"},
        "callback_result": {"stored": True, "topic": "order-events"},
    }
