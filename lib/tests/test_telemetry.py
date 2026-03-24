"""Unit tests for telemetry helpers."""

import sys

from holiday_peak_lib.utils.correlation import clear_correlation_id, set_correlation_id
from holiday_peak_lib.utils.telemetry import (
    FoundryTracer,
    _NoopMeter,
    _NoopTracer,
    get_foundry_tracer,
    get_meter,
    get_tracer,
    record_metric,
)


class TestGetTracer:
    def test_returns_noop_tracer_without_otel(self, monkeypatch):
        telemetry_mod = sys.modules[get_tracer.__module__]

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
        telemetry_mod = sys.modules[get_meter.__module__]

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


class TestFoundryTracer:
    def test_disabled_via_env(self, monkeypatch):
        monkeypatch.setenv("FOUNDRY_TRACING_ENABLED", "false")
        tracer = FoundryTracer("svc")
        tracer.trace_decision(decision="route", outcome="slm", metadata={"x": 1})
        assert tracer.get_traces(limit=10) == []
        metrics = tracer.get_metrics()
        assert metrics["enabled"] is False
        assert "instrumentation" in metrics
        assert set(metrics["instrumentation"].keys()) == {
            "azure_monitor",
            "ai_projects",
            "ai_inference",
        }

    def test_records_traces_and_metrics(self, monkeypatch):
        monkeypatch.setenv("FOUNDRY_TRACING_ENABLED", "true")
        tracer = FoundryTracer("svc", max_events=5)
        set_correlation_id("corr-test-123")
        try:
            tracer.trace_decision(decision="route", outcome="slm", metadata={"x": 1})
            tracer.trace_tool_call(tool_name="inventory_lookup", outcome="success", metadata={})
            tracer.trace_model_invocation(
                model="gpt-5",
                target="rich",
                outcome="success",
                metadata={"elapsed_ms": 12.3},
            )
            tracer.record_evaluation({"score": 0.9})
        finally:
            clear_correlation_id()

        traces = tracer.get_traces(limit=10)
        assert len(traces) == 3
        assert traces[0]["type"] == "model_invocation"
        assert traces[1]["type"] == "tool_call"
        assert traces[2]["type"] == "decision"

        for trace_event in traces:
            assert "service" in trace_event
            assert "operation" in trace_event
            assert "trace_id" in trace_event
            assert "correlation_id" in trace_event
            assert "status" in trace_event
            assert "latency_ms" in trace_event
            assert "timestamp" in trace_event

        assert traces[0]["operation"] == "rich"
        assert traces[0]["status"] == "success"
        assert traces[0]["latency_ms"] == 12.3
        assert traces[0]["correlation_id"] == "corr-test-123"

        metrics = tracer.get_metrics()
        assert metrics["counts"]["decision"] == 1
        assert metrics["counts"]["tool_call"] == 1
        assert metrics["counts"]["model_invocation"] == 1
        assert metrics["counts"]["evaluation_updates"] == 1
        assert "instrumentation" in metrics
        latest = tracer.get_latest_evaluation()
        assert latest is not None
        assert latest["score"] == 0.9
        assert latest["service"] == "svc"
        assert latest["operation"] == "evaluation"
        assert latest["status"] == "recorded"
        assert "trace_id" in latest
        assert latest["correlation_id"] == "corr-test-123"
        assert "latency_ms" in latest
        assert "timestamp" in latest

    def test_metadata_correlation_id_overrides_context(self, monkeypatch):
        monkeypatch.setenv("FOUNDRY_TRACING_ENABLED", "true")
        tracer = FoundryTracer("svc", max_events=5)
        set_correlation_id("corr-context")
        try:
            tracer.trace_tool_call(
                tool_name="inventory_lookup",
                outcome="success",
                metadata={"correlation_id": "corr-metadata"},
            )
        finally:
            clear_correlation_id()

        event = tracer.get_traces(limit=1)[0]
        assert event["correlation_id"] == "corr-metadata"

    def test_get_foundry_tracer_returns_singleton(self):
        tracer_a = get_foundry_tracer("svc-singleton")
        tracer_b = get_foundry_tracer("svc-singleton")
        assert tracer_a is tracer_b
