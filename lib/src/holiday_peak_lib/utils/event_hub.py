"""Event Hub subscription helpers for agent services."""

from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from inspect import isawaitable
from typing import Any, AsyncContextManager, AsyncIterator, Awaitable, Callable, Iterable

from azure.eventhub.aio import EventHubConsumerClient
from azure.identity.aio import DefaultAzureCredential
from holiday_peak_lib.self_healing import FailureSignal, SelfHealingKernel, SurfaceType
from holiday_peak_lib.utils.logging import configure_logging

EventHandler = Callable[[Any, Any], Awaitable[None]]
ErrorHandler = Callable[..., Awaitable[None] | None]
FailureSignalEmitter = Callable[[FailureSignal], Awaitable[Any] | Any]


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
        failure_signal_emitter: FailureSignalEmitter | None = None,
        self_healing_kernel: SelfHealingKernel | None = None,
        reconcile_on_error: bool = False,
    ) -> None:
        self._config = config
        self._on_event = on_event
        self._on_error = on_error
        self._client_factory = client_factory
        self._failure_signal_emitter = failure_signal_emitter
        self._self_healing_kernel = self_healing_kernel
        self._reconcile_on_error = reconcile_on_error
        self._client: EventHubConsumerClient | None = None
        self._logger = configure_logging(app_name="eventhub-subscriber")

    def _log_warning(self, message: str, **metadata: Any) -> None:
        log_method = getattr(self._logger, "warning", None)
        if callable(log_method):
            try:
                log_method(message, **metadata)
            except TypeError:
                log_method(message)

    async def start(self) -> None:
        """Start receiving events using the configured handler."""
        client = self._client_factory() if self._client_factory else self._default_client()
        self._client = client

        async def _on_event(partition_context: Any, event: Any) -> None:
            await self._on_event(partition_context, event)
            if self._config.checkpoint:
                await partition_context.update_checkpoint(event)

        async def _on_error(partition_context: Any, error: Any) -> None:
            await self._run_error_handler(partition_context, error)
            await self._emit_failure_signal(partition_context, error)

        async with client:
            await client.receive(
                on_event=_on_event,
                on_error=_on_error,
                starting_position=self._config.starting_position,
            )

    def _default_client(self) -> EventHubConsumerClient:
        return EventHubConsumerClient.from_connection_string(
            conn_str=self._config.connection_string,
            consumer_group=self._config.consumer_group,
            eventhub_name=self._config.eventhub_name,
        )

    async def _run_error_handler(self, partition_context: Any, error: Any) -> None:
        if self._on_error is None:
            return

        try:
            result = self._on_error(partition_context, error)
        except TypeError:
            result = self._on_error(error)

        if isawaitable(result):
            await result

    async def _emit_failure_signal(self, partition_context: Any, error: Any) -> None:
        emitter = self._failure_signal_emitter
        if emitter is None and self._self_healing_kernel is not None:
            emitter = self._self_healing_kernel.handle_failure_signal

        signal = FailureSignal(
            service_name=(
                self._self_healing_kernel.service_name
                if self._self_healing_kernel is not None
                else "eventhub-subscriber"
            ),
            surface=SurfaceType.MESSAGING,
            component=self._config.eventhub_name,
            status_code=getattr(error, "status_code", 500),
            error_type=type(error).__name__,
            error_message=str(error),
            metadata={
                "consumer_group": self._config.consumer_group,
                "partition": getattr(partition_context, "partition_id", None),
            },
        )

        if emitter is not None:
            try:
                emitted = emitter(signal)
                if isawaitable(emitted):
                    await emitted
            except TypeError as exc:
                self._log_warning(
                    "eventhub_failure_signal_emitter_signature_mismatch",
                    eventhub=self._config.eventhub_name,
                    error=str(exc),
                )

        if (
            self._reconcile_on_error
            and self._self_healing_kernel is not None
            and self._self_healing_kernel.enabled
        ):
            await self._self_healing_kernel.reconcile()


@dataclass(frozen=True)
class EventHubSubscription:
    """Event Hub subscription details for a service."""

    eventhub_name: str
    consumer_group: str


def build_basic_error_handler(*, logger: Any, eventhub_name: str) -> ErrorHandler:
    """Return a lightweight error logger used by default subscribers."""

    async def _on_error(_partition_context: Any, error: Any) -> None:
        logger.warning(
            "eventhub_receive_error",
            eventhub=eventhub_name,
            error=str(error),
        )

    return _on_error


def create_eventhub_lifespan(
    *,
    service_name: str,
    subscriptions: Iterable[EventHubSubscription],
    connection_string_env: str = "EVENTHUB_CONNECTION_STRING",
    handlers: dict[str, EventHandler] | None = None,
    self_healing_kernel: SelfHealingKernel | None = None,
    reconcile_on_error: bool = False,
) -> Callable[[Any], AsyncContextManager[None]]:
    """Create a FastAPI lifespan that starts Event Hub subscribers."""

    @asynccontextmanager
    async def lifespan(_app) -> AsyncIterator[None]:  # noqa: ANN001
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
                if handler is not None:
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
                on_error=build_basic_error_handler(
                    logger=logger,
                    eventhub_name=subscription.eventhub_name,
                ),
                client_factory=make_client_factory(subscription),
                **(
                    {
                        "self_healing_kernel": self_healing_kernel,
                        "reconcile_on_error": reconcile_on_error,
                    }
                    if self_healing_kernel is not None or reconcile_on_error
                    else {}
                ),
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
        async def _handler(_partition_context, event):  # noqa: ANN001
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

        async def _handler(_partition_context, event):  # noqa: ANN001
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
