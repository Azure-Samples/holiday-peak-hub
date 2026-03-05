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
from typing import Any, Optional

logger = logging.getLogger(__name__)

_OTEL_AVAILABLE = False  # pylint: disable=invalid-name
try:
    from opentelemetry import metrics, trace  # type: ignore[import]

    _OTEL_AVAILABLE = True
except ImportError:  # pragma: no cover
    pass


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
    attributes: Optional[dict[str, Any]] = None,
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

    instrument_cache: dict[str, Any] = getattr(meter, "_hph_cache", {})
    if not hasattr(meter, "_hph_cache"):
        meter._hph_cache = instrument_cache  # type: ignore[attr-defined]

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

    def add(self, value: float, attributes: Optional[dict] = None) -> None:
        logger.debug("metric counter=%s value=%s attributes=%s", self._name, value, attributes)


class _NoopHistogram:
    def __init__(self, name: str) -> None:
        self._name = name

    def record(self, value: float, attributes: Optional[dict] = None) -> None:
        logger.debug("metric histogram=%s value=%s attributes=%s", self._name, value, attributes)


class _NoopGauge:
    def __init__(self, name: str) -> None:
        self._name = name

    def add(self, value: float, attributes: Optional[dict] = None) -> None:
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
