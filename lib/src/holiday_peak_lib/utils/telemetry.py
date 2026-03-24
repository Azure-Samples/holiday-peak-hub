"""Structured telemetry helpers: custom metrics and distributed tracing.

Wraps OpenTelemetry APIs with a thin convenience layer that also emits
structured log lines when the OTEL SDK is not available.

Usage::

    from holiday_peak_lib.utils.telemetry import get_meter, get_tracer, record_metric

    meter = get_meter("my-service")
    counter = meter.create_counter("truth.ingestion.rate")
    counter.add(1, {"category": "apparel"})

    tracer = get_tracer("my-service")
    with tracer.start_as_current_span("ingest"):
        ...
"""

from __future__ import annotations

import logging
import os
from collections import Counter, deque
from datetime import datetime, timezone
from threading import Lock
from typing import Any
from weakref import WeakKeyDictionary

from .correlation import get_correlation_id

logger = logging.getLogger(__name__)

_OTEL_AVAILABLE = False  # pylint: disable=invalid-name
try:
    from opentelemetry import metrics, trace  # type: ignore[import]

    _OTEL_AVAILABLE = True
except ImportError:  # pragma: no cover
    pass

_PROJECTS_TELEMETRY_AVAILABLE = False  # pylint: disable=invalid-name
try:
    from azure.ai.projects.telemetry import AIProjectInstrumentor  # type: ignore[import]

    _PROJECTS_TELEMETRY_AVAILABLE = True
except ImportError:  # pragma: no cover
    AIProjectInstrumentor = None  # type: ignore[assignment]

_INFERENCE_TELEMETRY_AVAILABLE = False  # pylint: disable=invalid-name
try:
    from azure.ai.inference.tracing import AIInferenceInstrumentor  # type: ignore[import]

    _INFERENCE_TELEMETRY_AVAILABLE = True
except ImportError:  # pragma: no cover
    AIInferenceInstrumentor = None  # type: ignore[assignment]

_AZURE_MONITOR_AVAILABLE = False  # pylint: disable=invalid-name
try:
    from azure.monitor.opentelemetry import configure_azure_monitor  # type: ignore[import]

    _AZURE_MONITOR_AVAILABLE = True
except ImportError:  # pragma: no cover
    configure_azure_monitor = None  # type: ignore[assignment]

_FOUNDRY_INSTRUMENTATION_LOCK = Lock()
_FOUNDRY_INSTRUMENTATION_STATE: dict[str, bool] = {
    "azure_monitor": False,
    "ai_projects": False,
    "ai_inference": False,
}


def _is_truthy(value: str | None, *, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _coerce_latency_ms(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_latency_ms(metadata: dict[str, Any] | None) -> float | None:
    if not isinstance(metadata, dict):
        return None
    for key in ("latency_ms", "elapsed_ms", "duration_ms"):
        if key in metadata:
            latency = _coerce_latency_ms(metadata.get(key))
            if latency is not None:
                return latency
    return None


def _trace_id_from_otel() -> str | None:
    if not _OTEL_AVAILABLE:
        return None
    try:
        current_span = trace.get_current_span()  # type: ignore[union-attr]
        span_context = current_span.get_span_context() if current_span else None
        if span_context is None:
            return None

        trace_id = getattr(span_context, "trace_id", 0)
        is_valid = getattr(span_context, "is_valid", bool(trace_id))
        if not is_valid or not isinstance(trace_id, int) or trace_id <= 0:
            return None
        return f"{trace_id:032x}"
    except (AttributeError, TypeError, ValueError):
        return None


def _resolve_trace_id(metadata: dict[str, Any] | None) -> str | None:
    if isinstance(metadata, dict):
        for key in ("trace_id", "traceId", "operation_id"):
            value = metadata.get(key)
            if value is not None:
                resolved = str(value).strip()
                if resolved:
                    return resolved
    return _trace_id_from_otel()


def _resolve_correlation_id(metadata: dict[str, Any] | None) -> str | None:
    if isinstance(metadata, dict):
        value = metadata.get("correlation_id")
        if value is not None:
            resolved = str(value).strip()
            if resolved:
                return resolved
    return get_correlation_id()


def _build_envelope_fields(
    *,
    operation: str,
    status: str,
    metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "operation": operation,
        "trace_id": _resolve_trace_id(metadata),
        "correlation_id": _resolve_correlation_id(metadata),
        "status": status,
        "latency_ms": _extract_latency_ms(metadata),
    }


class FoundryTracer:
    """Facade for Foundry tracing with env-gated no-op behavior.

    Implements a minimal in-memory activity store for trace events, aggregate
    counters, and latest evaluation payload.
    """

    def __init__(
        self,
        service_name: str,
        *,
        enabled: bool | None = None,
        connection_string: str | None = None,
        max_events: int | None = None,
    ) -> None:
        self.service_name = service_name
        self.enabled = (
            _is_truthy(os.getenv("FOUNDRY_TRACING_ENABLED"), default=True)
            if enabled is None
            else enabled
        )
        self.connection_string = (
            connection_string
            or os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
            or os.getenv("APPINSIGHTS_CONNECTION_STRING")
        )
        configured_max = int(os.getenv("FOUNDRY_TRACING_MAX_EVENTS", "500"))
        self.max_events = max_events if max_events is not None else configured_max
        self._events: deque[dict[str, Any]] = deque(maxlen=self.max_events)
        self._counts: Counter[str] = Counter()
        self._latest_evaluation: dict[str, Any] | None = None
        self._lock = Lock()
        self._instrumentation_status = {
            "azure_monitor": False,
            "ai_projects": False,
            "ai_inference": False,
        }
        self._initialize_foundry_instrumentation()

    def _initialize_foundry_instrumentation(self) -> None:
        if not self.enabled:
            return

        os.environ.setdefault("AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING", "true")
        os.environ.setdefault("AZURE_SDK_TRACING_IMPLEMENTATION", "opentelemetry")

        with _FOUNDRY_INSTRUMENTATION_LOCK:
            if (
                self.connection_string
                and _AZURE_MONITOR_AVAILABLE
                and not _FOUNDRY_INSTRUMENTATION_STATE["azure_monitor"]
            ):
                try:
                    configure_azure_monitor(connection_string=self.connection_string)
                    _FOUNDRY_INSTRUMENTATION_STATE["azure_monitor"] = True
                except (TypeError, RuntimeError, ValueError):
                    logger.debug(
                        "Failed to configure Azure Monitor for service=%s",
                        self.service_name,
                        exc_info=True,
                    )

            if _PROJECTS_TELEMETRY_AVAILABLE and not _FOUNDRY_INSTRUMENTATION_STATE["ai_projects"]:
                try:
                    AIProjectInstrumentor().instrument()
                    _FOUNDRY_INSTRUMENTATION_STATE["ai_projects"] = True
                except (TypeError, RuntimeError, ValueError, AttributeError):
                    logger.debug(
                        "Failed to instrument azure.ai.projects telemetry for service=%s",
                        self.service_name,
                        exc_info=True,
                    )

            if (
                _INFERENCE_TELEMETRY_AVAILABLE
                and not _FOUNDRY_INSTRUMENTATION_STATE["ai_inference"]
            ):
                try:
                    AIInferenceInstrumentor().instrument()
                    _FOUNDRY_INSTRUMENTATION_STATE["ai_inference"] = True
                except (TypeError, RuntimeError, ValueError, AttributeError):
                    logger.debug(
                        "Failed to instrument azure.ai.inference telemetry for service=%s",
                        self.service_name,
                        exc_info=True,
                    )

            self._instrumentation_status = dict(_FOUNDRY_INSTRUMENTATION_STATE)

    def _record(self, event_type: str, name: str, outcome: str, metadata: dict[str, Any]) -> None:
        if not self.enabled:
            return
        event_metadata = dict(metadata)
        event = {
            "timestamp": _now_iso(),
            "service": self.service_name,
            **_build_envelope_fields(
                operation=name,
                status=outcome,
                metadata=event_metadata,
            ),
            "type": event_type,
            "name": name,
            "outcome": outcome,
            "metadata": event_metadata,
        }
        with self._lock:
            self._events.append(event)
            self._counts[event_type] += 1
            self._counts[f"{event_type}:{outcome}"] += 1

    def trace_model_invocation(
        self,
        *,
        model: str,
        target: str,
        outcome: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._record(
            "model_invocation",
            target,
            outcome,
            {
                "model": model,
                **(metadata or {}),
            },
        )

    def trace_tool_call(
        self,
        *,
        tool_name: str,
        outcome: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._record("tool_call", tool_name, outcome, metadata or {})

    def trace_decision(
        self,
        *,
        decision: str,
        outcome: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._record("decision", decision, outcome, metadata or {})

    def record_evaluation(self, payload: dict[str, Any]) -> None:
        if not self.enabled:
            return
        payload_data = dict(payload)
        operation = str(payload_data.get("operation", "evaluation"))
        status = str(payload_data.get("status", "recorded"))
        enriched_payload = {
            **payload_data,
            "timestamp": _now_iso(),
            "service": self.service_name,
            **_build_envelope_fields(
                operation=operation,
                status=status,
                metadata=payload_data,
            ),
        }
        with self._lock:
            self._latest_evaluation = enriched_payload
            self._counts["evaluation_updates"] += 1

    def get_traces(self, limit: int = 50) -> list[dict[str, Any]]:
        resolved_limit = max(1, min(limit, self.max_events))
        with self._lock:
            events = list(self._events)
        return events[-resolved_limit:][::-1]

    def get_metrics(self) -> dict[str, Any]:
        with self._lock:
            counts = dict(self._counts)
            traces_buffered = len(self._events)
        return {
            "service": self.service_name,
            "enabled": self.enabled,
            "app_insights_configured": bool(self.connection_string),
            "traces_buffered": traces_buffered,
            "instrumentation": dict(self._instrumentation_status),
            "counts": counts,
        }

    def get_latest_evaluation(self) -> dict[str, Any] | None:
        with self._lock:
            if self._latest_evaluation is None:
                return None
            return dict(self._latest_evaluation)

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
            self._counts.clear()
            self._latest_evaluation = None


_TRACERS: dict[str, FoundryTracer] = {}
_TRACERS_LOCK = Lock()
_METER_INSTRUMENT_CACHE: WeakKeyDictionary[Any, dict[str, Any]] = WeakKeyDictionary()
_METER_INSTRUMENT_CACHE_BY_ID: dict[int, dict[str, Any]] = {}


def get_foundry_tracer(service_name: str) -> FoundryTracer:
    """Return a service-scoped :class:`FoundryTracer` singleton."""
    with _TRACERS_LOCK:
        tracer = _TRACERS.get(service_name)
        if tracer is None:
            tracer = FoundryTracer(service_name)
            _TRACERS[service_name] = tracer
        return tracer


def get_tracer(name: str) -> Any:
    """Return an OpenTelemetry :class:`Tracer` or a no-op stub.

    Args:
        name: Instrumentation scope / service name.

    Returns:
        A real :class:`opentelemetry.trace.Tracer` when the SDK is installed,
        otherwise a :class:`_NoopTracer` stub that emits log lines instead.
    """
    if _OTEL_AVAILABLE:
        return trace.get_tracer(name)  # type: ignore[union-attr]
    return _NoopTracer(name)


def get_meter(name: str) -> Any:
    """Return an OpenTelemetry :class:`Meter` or a no-op stub.

    Args:
        name: Instrumentation scope / service name.

    Returns:
        A real :class:`opentelemetry.metrics.Meter` when the SDK is installed,
        otherwise a :class:`_NoopMeter` stub that emits log lines instead.
    """
    if _OTEL_AVAILABLE:
        return metrics.get_meter(name)  # type: ignore[union-attr]
    return _NoopMeter(name)


def record_metric(
    meter: Any,
    instrument_name: str,
    value: float,
    attributes: dict[str, Any] | None = None,
    *,
    kind: str = "counter",
) -> None:
    """Record a single measurement on *meter*.

    Creates (or reuses) an instrument of the requested *kind* and records
    *value*.  When the real OTEL SDK is absent the measurement is written to
    the Python :mod:`logging` system instead.

    Args:
        meter: A meter obtained from :func:`get_meter`.
        instrument_name: Metric name (e.g. ``"truth.completeness.score"``).
        value: The measurement to record.
        attributes: Optional key/value labels attached to the measurement.
        kind: One of ``"counter"``, ``"histogram"``, or ``"gauge"``.
    """
    attrs = attributes or {}
    if isinstance(meter, _NoopMeter):
        logger.info(
            "metric instrument=%s kind=%s value=%s attributes=%s",
            instrument_name,
            kind,
            value,
            attrs,
        )
        return

    instrument_cache = _METER_INSTRUMENT_CACHE.get(meter)
    if instrument_cache is None:
        try:
            _METER_INSTRUMENT_CACHE[meter] = {}
            instrument_cache = _METER_INSTRUMENT_CACHE[meter]
        except TypeError:
            instrument_cache = _METER_INSTRUMENT_CACHE_BY_ID.setdefault(id(meter), {})

    if instrument_name not in instrument_cache:
        if kind == "histogram":
            instrument_cache[instrument_name] = meter.create_histogram(instrument_name)
        elif kind == "gauge":
            instrument_cache[instrument_name] = meter.create_gauge(instrument_name)
        else:
            instrument_cache[instrument_name] = meter.create_counter(instrument_name)

    instrument = instrument_cache[instrument_name]
    if kind == "histogram":
        instrument.record(value, attrs)
    else:
        instrument.add(value, attrs)


# ---------------------------------------------------------------------------
# No-op stubs used when opentelemetry-sdk is not installed
# ---------------------------------------------------------------------------


class _NoopSpan:
    """Minimal span stub that supports the context-manager protocol."""

    def __init__(self, name: str) -> None:
        self._name = name

    def set_attribute(self, key: str, value: Any) -> None:  # noqa: D401
        pass

    def set_status(self, *_args: Any, **_kwargs: Any) -> None:
        pass

    def record_exception(self, exc: Exception) -> None:
        logger.debug("span=%s exception=%s", self._name, exc)

    def __enter__(self) -> "_NoopSpan":
        logger.debug("span.start name=%s", self._name)
        return self

    def __exit__(self, *_: Any) -> None:
        logger.debug("span.end name=%s", self._name)


class _NoopTracer:
    def __init__(self, name: str) -> None:
        self._name = name

    def start_as_current_span(self, name: str, **_kwargs: Any) -> _NoopSpan:
        return _NoopSpan(name)

    def start_span(self, name: str, **_kwargs: Any) -> _NoopSpan:
        return _NoopSpan(name)


class _NoopCounter:
    def __init__(self, name: str) -> None:
        self._name = name

    def add(self, value: float, attributes: dict | None = None) -> None:
        logger.debug("metric counter=%s value=%s attributes=%s", self._name, value, attributes)


class _NoopHistogram:
    def __init__(self, name: str) -> None:
        self._name = name

    def record(self, value: float, attributes: dict | None = None) -> None:
        logger.debug("metric histogram=%s value=%s attributes=%s", self._name, value, attributes)


class _NoopGauge:
    def __init__(self, name: str) -> None:
        self._name = name

    def add(self, value: float, attributes: dict | None = None) -> None:
        logger.debug("metric gauge=%s value=%s attributes=%s", self._name, value, attributes)


class _NoopMeter:
    def __init__(self, name: str) -> None:
        self._name = name

    def create_counter(self, name: str, **_kwargs: Any) -> _NoopCounter:
        return _NoopCounter(name)

    def create_histogram(self, name: str, **_kwargs: Any) -> _NoopHistogram:
        return _NoopHistogram(name)

    def create_gauge(self, name: str, **_kwargs: Any) -> _NoopGauge:
        return _NoopGauge(name)
