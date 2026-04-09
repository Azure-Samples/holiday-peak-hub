"""Utility helpers."""

from .bulkhead import Bulkhead, BulkheadFullError
from .circuit_breaker import CircuitBreaker, CircuitBreakerOpenError, CircuitState
from .compensation import CompensationAction, CompensationResult, execute_compensation
from .correlation import (
    CORRELATION_HEADER,
    clear_correlation_id,
    get_correlation_id,
    set_correlation_id,
)
from .event_hub import (
    DEFAULT_EVENT_HUB_CONNECTION_STRING_ENV,
    DEFAULT_EVENT_HUB_NAMESPACE_ENV,
    EventHubSubscriber,
    EventHubSubscriberConfig,
    EventHubSubscription,
    PLATFORM_JOBS_EVENT_HUB_CONNECTION_STRING_ENV,
    PLATFORM_JOBS_EVENT_HUB_NAMESPACE_ENV,
    create_eventhub_lifespan,
)
from .logging import configure_logging
from .rate_limiter import RateLimiter, RateLimitExceededError
from .retry import async_retry
from .telemetry import FoundryTracer, get_foundry_tracer, get_meter, get_tracer, record_metric

__all__ = [
    "Bulkhead",
    "BulkheadFullError",
    "CircuitBreaker",
    "CircuitBreakerOpenError",
    "CircuitState",
    "CompensationAction",
    "CompensationResult",
    "CORRELATION_HEADER",
    "clear_correlation_id",
    "DEFAULT_EVENT_HUB_CONNECTION_STRING_ENV",
    "DEFAULT_EVENT_HUB_NAMESPACE_ENV",
    "EventHubSubscriber",
    "EventHubSubscriberConfig",
    "EventHubSubscription",
    "PLATFORM_JOBS_EVENT_HUB_CONNECTION_STRING_ENV",
    "PLATFORM_JOBS_EVENT_HUB_NAMESPACE_ENV",
    "create_eventhub_lifespan",
    "configure_logging",
    "get_correlation_id",
    "RateLimiter",
    "RateLimitExceededError",
    "set_correlation_id",
    "execute_compensation",
    "async_retry",
    "FoundryTracer",
    "get_foundry_tracer",
    "get_meter",
    "get_tracer",
    "record_metric",
]
