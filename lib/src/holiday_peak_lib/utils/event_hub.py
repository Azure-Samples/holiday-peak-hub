"""Event Hub subscription helpers for agent services."""
from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator, Awaitable, Callable, Iterable

from azure.eventhub.aio import EventHubConsumerClient

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
) -> Callable[[Any], AsyncIterator[None]]:
    """Create a FastAPI lifespan that starts Event Hub subscribers."""

    @asynccontextmanager
    async def lifespan(app) -> AsyncIterator[None]:  # noqa: ANN001
        logger = configure_logging(app_name=f"{service_name}-events")
        connection_string = os.getenv(connection_string_env)
        if not connection_string:
            logger.warning("eventhub_connection_string_missing")
            yield
            return

        tasks: list[asyncio.Task] = []

        def make_handler(eventhub_name: str):
            async def _handler(partition_context, event):  # noqa: ANN001
                payload = json.loads(event.body_as_str())
                logger.info(
                    "event_received",
                    event_type=payload.get("event_type"),
                    eventhub=eventhub_name,
                )

            return _handler

        for subscription in subscriptions:
            subscriber = EventHubSubscriber(
                EventHubSubscriberConfig(
                    connection_string=connection_string,
                    eventhub_name=subscription.eventhub_name,
                    consumer_group=subscription.consumer_group,
                ),
                on_event=make_handler(subscription.eventhub_name),
            )
            tasks.append(asyncio.create_task(subscriber.start()))

        try:
            yield
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    return lifespan
