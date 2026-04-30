"""Event Hub subscription helpers for agent services."""

from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import StrEnum
from inspect import isawaitable, signature
from typing import Any, AsyncContextManager, AsyncIterator, Awaitable, Callable, Iterable

from azure.eventhub.aio import EventHubConsumerClient
from azure.identity.aio import DefaultAzureCredential
from holiday_peak_lib.self_healing import FailureSignal, SelfHealingKernel, SurfaceType
from holiday_peak_lib.utils.compensation import CompensationResult
from holiday_peak_lib.utils.logging import configure_logging

EventHandler = Callable[[Any, Any], Awaitable[None]]
ErrorHandler = Callable[..., Awaitable[None] | None]
FailureSignalEmitter = Callable[[FailureSignal], Awaitable[Any] | Any]
PublishOperation = Callable[[], Awaitable[None]]
DeadLetterCallback = Callable[["PublishFailureEnvelope"], Awaitable[Any] | Any]
TerminalFailureHandler = Callable[
    [Exception],
    Awaitable[CompensationResult | None] | CompensationResult | None,
]

_RECOVERABLE_PUBLISH_5XX = frozenset({500, 502, 503, 504})


class MessagingFailureCategory(StrEnum):
    """Shared taxonomy for producer-side messaging failures."""

    CONFIGURATION = "configuration"
    PAYLOAD_VALIDATION = "payload_validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    THROTTLED = "throttled"
    TRANSIENT = "transient"
    UNKNOWN = "unknown"


class DeadLetterStrategy(StrEnum):
    """Application-managed dead-letter handling modes for Event Hubs publishers."""

    NONE = "none"
    METADATA_ONLY = "metadata_only"
    CALLBACK = "callback"


@dataclass(frozen=True, slots=True)
class DeadLetterPolicy:
    """Strategy object describing how terminal publish failures are recorded."""

    strategy: DeadLetterStrategy = DeadLetterStrategy.METADATA_ONLY
    reason: str = "event_hubs_requires_application_managed_dead_letter"
    metadata: dict[str, Any] = field(default_factory=dict)


_DEFAULT_RETRYABLE_CATEGORIES = frozenset(
    {
        MessagingFailureCategory.THROTTLED,
        MessagingFailureCategory.TRANSIENT,
    }
)
EVENT_HUB_METADATA_DEAD_LETTER_POLICY = DeadLetterPolicy()
DEFAULT_EVENT_HUB_NAMESPACE_ENV = "EVENT_HUB_NAMESPACE"
DEFAULT_EVENT_HUB_CONNECTION_STRING_ENV = "EVENT_HUB_CONNECTION_STRING"
PLATFORM_JOBS_EVENT_HUB_NAMESPACE_ENV = "PLATFORM_JOBS_EVENT_HUB_NAMESPACE"
PLATFORM_JOBS_EVENT_HUB_CONNECTION_STRING_ENV = "PLATFORM_JOBS_EVENT_HUB_CONNECTION_STRING"


@dataclass(frozen=True, slots=True)
class PublishReliabilityProfile:
    """Strategy object describing how a topic should react to publish failure."""

    name: str
    raise_on_failure: bool = True
    status_code: int = 503
    remediation_action: str = "reset_messaging_publisher_bindings"
    retry_max_attempts: int = 3
    retry_backoff_base_seconds: float = 0.25
    retry_backoff_max_seconds: float = 2.0
    retryable_categories: frozenset[MessagingFailureCategory] = _DEFAULT_RETRYABLE_CATEGORIES
    dead_letter_policy: DeadLetterPolicy = EVENT_HUB_METADATA_DEAD_LETTER_POLICY


CRITICAL_SAGA_PUBLISH_PROFILE = PublishReliabilityProfile(name="critical_saga")
BEST_EFFORT_PUBLISH_PROFILE = PublishReliabilityProfile(
    name="best_effort",
    raise_on_failure=False,
    retry_max_attempts=2,
)


class PublishFailureEnvelope:
    """Structured failure envelope for producer-side messaging incidents."""

    __slots__ = (
        "service_name",
        "topic",
        "operation",
        "error_type",
        "error_message",
        "category",
        "status_code",
        "profile",
        "event_type",
        "metadata",
    )

    def __init__(
        self,
        *,
        service_name: str,
        topic: str,
        operation: str,
        error_type: str,
        error_message: str,
        category: MessagingFailureCategory,
        status_code: int,
        profile: PublishReliabilityProfile,
        event_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.service_name = service_name
        self.topic = topic
        self.operation = operation
        self.error_type = error_type
        self.error_message = error_message
        self.category = category
        self.status_code = status_code
        self.profile = profile
        self.event_type = event_type
        self.metadata = dict(metadata or {})

    def to_failure_signal(self) -> FailureSignal:
        """Convert the envelope into the self-healing kernel input model."""

        signal_metadata = {
            "topic": self.topic,
            "event_type": self.event_type,
            "operation": self.operation,
            "failure_stage": "publish",
            "failure_category": self.category.value,
            "profile": self.profile.name,
            "remediation_action": self.profile.remediation_action,
        }
        signal_metadata.update(self.metadata)
        return FailureSignal(
            service_name=self.service_name,
            surface=SurfaceType.MESSAGING,
            component=self.topic,
            status_code=self.status_code,
            error_type=self.error_type,
            error_message=self.error_message,
            metadata={key: value for key, value in signal_metadata.items() if value is not None},
        )


class EventPublishError(RuntimeError):
    """Raised when a publish profile requires hard failure instead of silent loss."""

    def __init__(
        self,
        envelope: PublishFailureEnvelope,
        *,
        incident_id: str | None = None,
    ) -> None:
        self.envelope = envelope
        self.incident_id = incident_id
        event_type = envelope.event_type or "unknown"
        super().__init__(
            "Event publish failed "
            f"service={envelope.service_name} topic={envelope.topic} event_type={event_type} "
            f"category={envelope.category.value} profile={envelope.profile.name}"
        )


def _safe_log(logger: Any, level: str, message: str, **metadata: Any) -> None:
    log_method = getattr(logger, level, None)
    if not callable(log_method):
        return
    try:
        log_method(message, **metadata)
    except TypeError:
        try:
            log_method(message, extra=metadata)
        except TypeError:
            log_method(message)


def resolve_publish_reliability_profile(
    topic: str,
    *,
    topic_profiles: dict[str, PublishReliabilityProfile] | None = None,
    default_profile: PublishReliabilityProfile = CRITICAL_SAGA_PUBLISH_PROFILE,
) -> PublishReliabilityProfile:
    """Resolve the reliability profile for a topic using a small strategy map."""

    if topic_profiles is None:
        return default_profile
    return topic_profiles.get(topic, default_profile)


def serialize_compensation_result(
    compensation_result: CompensationResult | None,
) -> dict[str, Any] | None:
    """Normalize compensation output for incident metadata and audit trails."""

    if compensation_result is None:
        return None
    return {
        "succeeded": compensation_result.succeeded,
        "completed_actions": list(compensation_result.completed),
        "failed_action": compensation_result.failed_action,
        "failed_error_type": (
            type(compensation_result.failed_error).__name__
            if compensation_result.failed_error is not None
            else None
        ),
        "failed_error": (
            str(compensation_result.failed_error)
            if compensation_result.failed_error is not None
            else None
        ),
    }


def classify_publish_failure(
    error: Exception,
) -> tuple[MessagingFailureCategory, int]:
    """Map producer-side exceptions into the shared failure taxonomy."""

    status_code = getattr(error, "status_code", None)
    error_type = type(error).__name__.lower()
    error_message = str(error).lower()

    if isinstance(error, LookupError):
        return MessagingFailureCategory.CONFIGURATION, int(status_code or 500)
    if isinstance(error, (ValueError, TypeError)) or "validation" in error_type:
        return MessagingFailureCategory.PAYLOAD_VALIDATION, int(status_code or 422)
    if status_code == 401 or "credential" in error_message or "authentication" in error_message:
        return MessagingFailureCategory.AUTHENTICATION, int(status_code or 401)
    if (
        status_code == 403
        or isinstance(error, PermissionError)
        or "permission" in error_message
        or "authorization" in error_message
    ):
        return MessagingFailureCategory.AUTHORIZATION, int(status_code or 403)
    if status_code == 429 or "throttle" in error_message or "too many requests" in error_message:
        return MessagingFailureCategory.THROTTLED, int(status_code or 429)
    if (
        status_code in _RECOVERABLE_PUBLISH_5XX
        or isinstance(error, (ConnectionError, TimeoutError, OSError))
        or "timeout" in error_message
        or "temporarily unavailable" in error_message
        or "connection" in error_message
    ):
        return MessagingFailureCategory.TRANSIENT, int(status_code or 503)
    return MessagingFailureCategory.UNKNOWN, int(status_code or 500)


def _coerce_retry_after_seconds(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return max(float(value), 0.0)
    except (TypeError, ValueError):
        return None


def _extract_retry_after_seconds(error: Exception) -> float | None:
    for attribute_name in (
        "retry_after",
        "retry_after_in_seconds",
        "retry_after_seconds",
    ):
        delay = _coerce_retry_after_seconds(getattr(error, attribute_name, None))
        if delay is not None:
            return delay

    for candidate in (
        getattr(error, "headers", None),
        getattr(getattr(error, "response", None), "headers", None),
    ):
        if candidate is None or not hasattr(candidate, "get"):
            continue
        delay = _coerce_retry_after_seconds(candidate.get("retry-after"))
        if delay is not None:
            return delay
    return None


def resolve_retry_delay_seconds(
    error: Exception,
    *,
    attempt: int,
    profile: PublishReliabilityProfile,
) -> float:
    """Resolve retry delay using retry-after metadata before exponential backoff."""

    retry_after = _extract_retry_after_seconds(error)
    if retry_after is not None:
        return retry_after

    backoff_seconds = profile.retry_backoff_base_seconds * (2 ** max(attempt - 1, 0))
    return max(0.0, min(backoff_seconds, profile.retry_backoff_max_seconds))


async def _resolve_terminal_compensation_result(
    *,
    error: Exception,
    compensation_result: CompensationResult | None,
    on_terminal_failure: TerminalFailureHandler | None,
    logger: Any | None,
    service_name: str,
    topic: str,
) -> CompensationResult | None:
    resolved_compensation = compensation_result
    if on_terminal_failure is None:
        return resolved_compensation

    try:
        callback_result = on_terminal_failure(error)
        if isawaitable(callback_result):
            callback_result = await callback_result
        return callback_result if callback_result is not None else resolved_compensation
    except Exception as exc:  # pylint: disable=broad-exception-caught
        _safe_log(
            logger,
            "warning",
            "eventhub_terminal_failure_handler_failed",
            service=service_name,
            topic=topic,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return CompensationResult(
            failed_action="terminal_failure_compensation",
            failed_error=exc,
        )


async def apply_dead_letter_policy(
    envelope: PublishFailureEnvelope,
    *,
    dead_letter_callback: DeadLetterCallback | None = None,
    logger: Any | None = None,
) -> None:
    """Record terminal publish failure handling without assuming broker-native DLQ support."""

    policy = envelope.profile.dead_letter_policy
    dead_letter_metadata: dict[str, Any] = {
        "strategy": policy.strategy.value,
        "reason": policy.reason,
        "callback_configured": dead_letter_callback is not None,
        "callback_invoked": False,
    }
    if policy.metadata:
        dead_letter_metadata["policy_metadata"] = dict(policy.metadata)

    if policy.strategy == DeadLetterStrategy.CALLBACK and dead_letter_callback is not None:
        try:
            callback_result = dead_letter_callback(envelope)
            if isawaitable(callback_result):
                callback_result = await callback_result
            dead_letter_metadata["callback_invoked"] = True
            if callback_result is not None:
                dead_letter_metadata["callback_result"] = callback_result
        except Exception as exc:  # pylint: disable=broad-exception-caught
            dead_letter_metadata["callback_invoked"] = True
            dead_letter_metadata["callback_error_type"] = type(exc).__name__
            dead_letter_metadata["callback_error"] = str(exc)
            _safe_log(
                logger,
                "warning",
                "eventhub_dead_letter_callback_failed",
                service=envelope.service_name,
                topic=envelope.topic,
                error_type=type(exc).__name__,
                error=str(exc),
            )

    envelope.metadata["dead_letter"] = dead_letter_metadata


def build_publish_failure_envelope(
    *,
    error: Exception,
    service_name: str,
    topic: str,
    event_type: str | None,
    profile: PublishReliabilityProfile,
    metadata: dict[str, Any] | None = None,
    remediation_context: dict[str, Any] | None = None,
    compensation_result: CompensationResult | None = None,
    operation: str = "publish",
    category: MessagingFailureCategory | None = None,
    status_code: int | None = None,
) -> PublishFailureEnvelope:
    """Create a normalized publish failure envelope before emission/escalation."""

    resolved_category, resolved_status_code = classify_publish_failure(error)
    envelope_metadata = dict(metadata or {})
    if remediation_context:
        envelope_metadata["remediation_context"] = dict(remediation_context)
    compensation_metadata = serialize_compensation_result(compensation_result)
    if compensation_metadata is not None:
        envelope_metadata["compensation"] = compensation_metadata
    return PublishFailureEnvelope(
        service_name=service_name,
        topic=topic,
        event_type=event_type,
        operation=operation,
        error_type=type(error).__name__,
        error_message=str(error),
        category=category or resolved_category,
        status_code=status_code or resolved_status_code or profile.status_code,
        profile=profile,
        metadata=envelope_metadata,
    )


async def emit_publish_failure(
    envelope: PublishFailureEnvelope,
    *,
    self_healing_kernel: SelfHealingKernel | None = None,
    logger: Any | None = None,
) -> EventPublishError:
    """Emit a producer failure into self-healing and return the structured exception."""

    _safe_log(
        logger,
        "error",
        "eventhub_publish_failed",
        service=envelope.service_name,
        topic=envelope.topic,
        event_type=envelope.event_type,
        category=envelope.category.value,
        profile=envelope.profile.name,
        error_type=envelope.error_type,
    )

    incident_id: str | None = None
    if self_healing_kernel is not None:
        try:
            incident = await self_healing_kernel.handle_failure_signal(envelope.to_failure_signal())
            incident_id = incident.id if incident is not None else None
        except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
            _safe_log(
                logger,
                "warning",
                "eventhub_publish_failure_signal_failed",
                service=envelope.service_name,
                topic=envelope.topic,
                error=str(exc),
            )

    return EventPublishError(envelope, incident_id=incident_id)


async def publish_with_reliability(
    *,
    send: PublishOperation,
    service_name: str,
    topic: str,
    event_type: str | None,
    profile: PublishReliabilityProfile = CRITICAL_SAGA_PUBLISH_PROFILE,
    self_healing_kernel: SelfHealingKernel | None = None,
    logger: Any | None = None,
    metadata: dict[str, Any] | None = None,
    remediation_context: dict[str, Any] | None = None,
    compensation_result: CompensationResult | None = None,
    on_terminal_failure: TerminalFailureHandler | None = None,
    dead_letter_callback: DeadLetterCallback | None = None,
    operation: str = "publish",
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> PublishFailureEnvelope | None:
    """Template method for producer sends with shared failure handling."""

    max_attempts = max(profile.retry_max_attempts, 1)
    attempt = 1

    while True:
        try:
            await send()
            return None
        except Exception as exc:  # pylint: disable=broad-exception-caught
            category, _ = classify_publish_failure(exc)
            if attempt < max_attempts and category in profile.retryable_categories:
                delay_seconds = resolve_retry_delay_seconds(
                    exc,
                    attempt=attempt,
                    profile=profile,
                )
                _safe_log(
                    logger,
                    "warning",
                    "eventhub_publish_retry_scheduled",
                    service=service_name,
                    topic=topic,
                    event_type=event_type,
                    category=category.value,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    retry_in_seconds=delay_seconds,
                )
                attempt += 1
                await sleep(delay_seconds)
                continue

            resolved_compensation = await _resolve_terminal_compensation_result(
                error=exc,
                compensation_result=compensation_result,
                on_terminal_failure=on_terminal_failure,
                logger=logger,
                service_name=service_name,
                topic=topic,
            )
            envelope = build_publish_failure_envelope(
                error=exc,
                service_name=service_name,
                topic=topic,
                event_type=event_type,
                profile=profile,
                metadata={
                    **(metadata or {}),
                    "attempt_count": attempt,
                    "retry_max_attempts": max_attempts,
                },
                remediation_context=remediation_context,
                compensation_result=resolved_compensation,
                operation=operation,
            )
            await apply_dead_letter_policy(
                envelope,
                dead_letter_callback=dead_letter_callback,
                logger=logger,
            )
            publish_error = await emit_publish_failure(
                envelope,
                self_healing_kernel=self_healing_kernel,
                logger=logger,
            )
            if profile.raise_on_failure:
                raise publish_error from exc
            return envelope


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
            expects_partition_context = len(signature(self._on_error).parameters) >= 2
        except (TypeError, ValueError):
            expects_partition_context = True

        if expects_partition_context:
            result = self._on_error(partition_context, error)
        else:
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
    """Parameter object describing a service's Event Hubs binding."""

    eventhub_name: str
    consumer_group: str
    namespace_env: str | None = None
    connection_string_env: str | None = None


@dataclass(frozen=True, slots=True)
class EventHubBinding:
    """Resolved environment-backed binding for a single subscription."""

    namespace: str
    connection_string: str
    namespace_env: str
    connection_string_env: str

    @property
    def fully_qualified_namespace(self) -> str:
        if self.namespace.endswith(".servicebus.windows.net"):
            return self.namespace
        return f"{self.namespace}.servicebus.windows.net"

    @property
    def uses_connection_string(self) -> bool:
        return bool(self.connection_string)


def resolve_eventhub_binding(
    subscription: EventHubSubscription,
    *,
    default_namespace_env: str = DEFAULT_EVENT_HUB_NAMESPACE_ENV,
    default_connection_string_env: str = DEFAULT_EVENT_HUB_CONNECTION_STRING_ENV,
) -> EventHubBinding:
    """Resolve the configured namespace or connection string for a subscription."""

    namespace_env = subscription.namespace_env or default_namespace_env
    connection_string_env = subscription.connection_string_env or default_connection_string_env
    namespace = (os.getenv(namespace_env) or "").strip()
    connection_string = (os.getenv(connection_string_env) or "").strip()

    if connection_string or namespace:
        return EventHubBinding(
            namespace=namespace,
            connection_string=connection_string,
            namespace_env=namespace_env,
            connection_string_env=connection_string_env,
        )

    raise RuntimeError(
        "Event Hub binding missing for "
        f"eventhub={subscription.eventhub_name} consumer_group={subscription.consumer_group}. "
        f"Set {connection_string_env} or {namespace_env}."
    )


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
    connection_string_env: str = DEFAULT_EVENT_HUB_CONNECTION_STRING_ENV,
    namespace_env: str = DEFAULT_EVENT_HUB_NAMESPACE_ENV,
    handlers: dict[str, EventHandler] | None = None,
    self_healing_kernel: SelfHealingKernel | None = None,
    reconcile_on_error: bool = False,
) -> Callable[[Any], AsyncContextManager[None]]:
    """Create a FastAPI lifespan that starts Event Hub subscribers."""

    @asynccontextmanager
    async def lifespan(_app) -> AsyncIterator[None]:  # noqa: ANN001
        logger = configure_logging(app_name=f"{service_name}-events")
        credential: DefaultAzureCredential | None = None
        client_id = os.getenv("AZURE_CLIENT_ID")

        resolved_subscriptions = [
            (
                subscription,
                resolve_eventhub_binding(
                    subscription,
                    default_namespace_env=namespace_env,
                    default_connection_string_env=connection_string_env,
                ),
            )
            for subscription in subscriptions
        ]

        tasks: list[asyncio.Task] = []

        def get_credential() -> DefaultAzureCredential:
            nonlocal credential
            if credential is None:
                credential = DefaultAzureCredential(managed_identity_client_id=client_id)
            return credential

        def make_handler(eventhub_name: str):
            handler = handlers.get(eventhub_name) if handlers else None

            async def _handler(partition_context, event):  # noqa: ANN001
                if handler is not None:
                    try:
                        await handler(partition_context, event)
                    except Exception as exc:
                        logger.error(
                            "eventhub_handler_failed eventhub=%s service=%s error=%s",
                            eventhub_name,
                            service_name,
                            exc,
                            exc_info=True,
                        )
                        raise
                    return
                payload = json.loads(event.body_as_str())
                _safe_log(
                    logger,
                    "info",
                    "event_received",
                    event_type=payload.get("event_type"),
                    eventhub=eventhub_name,
                )

            return _handler

        for subscription, binding in resolved_subscriptions:

            def make_client_factory(
                target_subscription: EventHubSubscription,
                target_binding: EventHubBinding,
            ):
                if target_binding.uses_connection_string:
                    return None
                active_credential = get_credential()

                def _factory() -> EventHubConsumerClient:
                    return EventHubConsumerClient(
                        fully_qualified_namespace=target_binding.fully_qualified_namespace,
                        consumer_group=target_subscription.consumer_group,
                        eventhub_name=target_subscription.eventhub_name,
                        credential=active_credential,
                    )

                return _factory

            subscriber = EventHubSubscriber(
                EventHubSubscriberConfig(
                    connection_string=binding.connection_string,
                    eventhub_name=subscription.eventhub_name,
                    consumer_group=subscription.consumer_group,
                ),
                on_event=make_handler(subscription.eventhub_name),
                on_error=build_basic_error_handler(
                    logger=logger,
                    eventhub_name=subscription.eventhub_name,
                ),
                client_factory=make_client_factory(subscription, binding),
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
            _safe_log(
                logger,
                "info",
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
            _safe_log(
                logger,
                "info",
                "event_processed",
                event_type=(payload.get("event_type") if isinstance(payload, dict) else None),
                eventhub=eventhub_name,
                entity_id=identifier,
            )

        return _handler

    return {name: make_handler(name, keys) for name, keys in eventhub_keys.items()}
