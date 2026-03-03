"""Unit tests for telemetry helpers."""

import pytest
from holiday_peak_lib.utils.telemetry import (
    _NoopMeter,
    _NoopTracer,
    get_meter,
    get_tracer,
    record_metric,
)


class TestGetTracer:
    def test_returns_noop_tracer_without_otel(self, monkeypatch):
        import holiday_peak_lib.utils.telemetry as telemetry_mod

        monkeypatch.setattr(telemetry_mod, "_OTEL_AVAILABLE", False)
        tracer = get_tracer("svc")
        assert isinstance(tracer, _NoopTracer)

    def test_noop_tracer_context_manager(self):
        tracer = _NoopTracer("svc")
        with tracer.start_as_current_span("op") as span:
            span.set_attribute("key", "val")
            span.set_status("OK")

    def test_noop_tracer_start_span(self):
        tracer = _NoopTracer("svc")
        span = tracer.start_span("op")
        span.__enter__()
        span.__exit__(None, None, None)


class TestGetMeter:
    def test_returns_noop_meter_without_otel(self, monkeypatch):
        import holiday_peak_lib.utils.telemetry as telemetry_mod

        monkeypatch.setattr(telemetry_mod, "_OTEL_AVAILABLE", False)
        meter = get_meter("svc")
        assert isinstance(meter, _NoopMeter)

    def test_noop_meter_creates_instruments(self):
        meter = _NoopMeter("svc")
        counter = meter.create_counter("my.counter")
        histogram = meter.create_histogram("my.histogram")
        gauge = meter.create_gauge("my.gauge")
        counter.add(1, {"k": "v"})
        histogram.record(0.5, {})
        gauge.add(10)


class TestRecordMetric:
    def test_counter_via_noop_meter(self):
        meter = _NoopMeter("svc")
        # Should not raise
        record_metric(meter, "truth.ingestion.rate", 1.0, {"cat": "apparel"})

    def test_histogram_via_noop_meter(self):
        meter = _NoopMeter("svc")
        record_metric(
            meter,
            "truth.enrichment.latency",
            123.4,
            {"stage": "enrich"},
            kind="histogram",
        )

    def test_gauge_via_noop_meter(self):
        meter = _NoopMeter("svc")
        record_metric(
            meter,
            "truth.hitl.queue_depth",
            42.0,
            kind="gauge",
        )

    def test_record_metric_caches_instrument(self):
        meter = _NoopMeter("svc")
        record_metric(meter, "my.counter", 1)
        # Second call should reuse cached instrument — no error
        record_metric(meter, "my.counter", 2)
