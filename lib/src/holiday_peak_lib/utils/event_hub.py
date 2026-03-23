"""Event Hub subscription helpers for agent services."""

from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator, Awaitable, Callable, Iterable

from azure.eventhub.aio import EventHubConsumerClient
from azure.identity.aio import DefaultAzureCredential
from holiday_peak_lib.utils.logging import configure_logging

EventHandler = Callable[[Any, Any], Awaitable[None]]
ErrorHandler = Callable[[Any], Awaitable[None]]


@dataclass(frozen=True)
class EventHubSubscriberConfig:
    """Configuration for Event Hub subscriptions."""

    connection_string: str
    eventhub_name: str
    consumer_group: str = "$Default"
    starting_position: str = "-1"
    checkpoint: bool = True


class EventHubSubscriber:
    """Abstract Event Hub subscriber with pluggable event handler."""

    def __init__(
        self,
        config: EventHubSubscriberConfig,
        *,
        on_event: EventHandler,
        on_error: ErrorHandler | None = None,
        client_factory: Callable[[], EventHubConsumerClient] | None = None,
    ) -> None:
        self._config = config
        self._on_event = on_event
        self._on_error = on_error
        self._client_factory = client_factory
        self._client: EventHubConsumerClient | None = None

    async def start(self) -> None:
        """Start receiving events using the configured handler."""
        client = self._client_factory() if self._client_factory else self._default_client()
        self._client = client

        async def _on_event(partition_context: Any, event: Any) -> None:
            await self._on_event(partition_context, event)
            if self._config.checkpoint:
                await partition_context.update_checkpoint(event)

        async with client:
            await client.receive(
                on_event=_on_event,
                on_error=self._on_error,
                starting_position=self._config.starting_position,
            )

    def _default_client(self) -> EventHubConsumerClient:
        return EventHubConsumerClient.from_connection_string(
            conn_str=self._config.connection_string,
            consumer_group=self._config.consumer_group,
            eventhub_name=self._config.eventhub_name,
        )


@dataclass(frozen=True)
class EventHubSubscription:
    """Event Hub subscription details for a service."""

    eventhub_name: str
    consumer_group: str


def create_eventhub_lifespan(
    *,
    service_name: str,
    subscriptions: Iterable[EventHubSubscription],
    connection_string_env: str = "EVENTHUB_CONNECTION_STRING",
    handlers: dict[str, EventHandler] | None = None,
) -> Callable[[Any], AsyncIterator[None]]:
    """Create a FastAPI lifespan that starts Event Hub subscribers."""

    @asynccontextmanager
    async def lifespan(app) -> AsyncIterator[None]:  # noqa: ANN001
        logger = configure_logging(app_name=f"{service_name}-events")
        connection_string = os.getenv(connection_string_env) or os.getenv(
            "EVENT_HUB_CONNECTION_STRING"
        )
        namespace = os.getenv("EVENT_HUB_NAMESPACE") or os.getenv("EVENTHUB_NAMESPACE")
        use_connection_string = bool(connection_string)

        credential: DefaultAzureCredential | None = None

        if not use_connection_string and not namespace:
            logger.warning("eventhub_configuration_missing")
            yield
            return

        if not use_connection_string and namespace:
            client_id = os.getenv("AZURE_CLIENT_ID")
            credential = DefaultAzureCredential(managed_identity_client_id=client_id)

        tasks: list[asyncio.Task] = []

        def make_handler(eventhub_name: str):
            handler = handlers.get(eventhub_name) if handlers else None

            async def _handler(partition_context, event):  # noqa: ANN001
                if handler:
                    await handler(partition_context, event)
                    return
                payload = json.loads(event.body_as_str())
                logger.info(
                    "event_received",
                    event_type=payload.get("event_type"),
                    eventhub=eventhub_name,
                )

            return _handler

        for subscription in subscriptions:

            def make_client_factory(target_subscription: EventHubSubscription):
                if use_connection_string and connection_string:
                    return None

                qualified_namespace = (
                    namespace
                    if namespace and namespace.endswith(".servicebus.windows.net")
                    else f"{namespace}.servicebus.windows.net"
                )

                def _factory() -> EventHubConsumerClient:
                    return EventHubConsumerClient(
                        fully_qualified_namespace=qualified_namespace,
                        consumer_group=target_subscription.consumer_group,
                        eventhub_name=target_subscription.eventhub_name,
                        credential=credential,
                    )

                return _factory

            subscriber = EventHubSubscriber(
                EventHubSubscriberConfig(
                    connection_string=connection_string or "",
                    eventhub_name=subscription.eventhub_name,
                    consumer_group=subscription.consumer_group,
                ),
                on_event=make_handler(subscription.eventhub_name),
                client_factory=make_client_factory(subscription),
            )
            tasks.append(asyncio.create_task(subscriber.start()))

        try:
            yield
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            if credential is not None:
                await credential.close()

    return lifespan


def build_basic_event_handlers(
    *,
    service_name: str,
    eventhub_names: Iterable[str],
) -> dict[str, EventHandler]:
    """Build lightweight event handlers that log event type per hub."""
    logger = configure_logging(app_name=f"{service_name}-events")

    def make_handler(eventhub_name: str) -> EventHandler:
        async def _handler(partition_context, event):  # noqa: ANN001
            payload = json.loads(event.body_as_str())
            logger.info(
                "event_processed",
                event_type=payload.get("event_type"),
                eventhub=eventhub_name,
            )

        return _handler

    return {name: make_handler(name) for name in eventhub_names}


def build_event_handlers_with_keys(
    *,
    service_name: str,
    eventhub_keys: dict[str, Iterable[str]],
) -> dict[str, EventHandler]:
    """Build event handlers that log a key identifier per hub.

    Args:
        service_name: Service name used for logger context.
        eventhub_keys: Mapping of event hub name to preferred identifier keys.
    """
    logger = configure_logging(app_name=f"{service_name}-events")

    def make_handler(eventhub_name: str, keys: Iterable[str]) -> EventHandler:
        key_list = list(keys)

        async def _handler(partition_context, event):  # noqa: ANN001
            payload = json.loads(event.body_as_str())
            data = payload.get("data", {}) if isinstance(payload, dict) else {}
            identifier = None
            for key in key_list:
                identifier = data.get(key) or payload.get(key)
                if identifier:
                    break
            logger.info(
                "event_processed",
                event_type=(payload.get("event_type") if isinstance(payload, dict) else None),
                eventhub=eventhub_name,
                entity_id=identifier,
            )

        return _handler

    return {name: make_handler(name, keys) for name, keys in eventhub_keys.items()}
