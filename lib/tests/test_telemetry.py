"""Unit tests for telemetry helpers."""

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
    def test_returns_real_tracer_with_otel(self):
        tracer = get_tracer("svc")
        # OTel is a hard dependency, so we always get a real tracer
        assert not isinstance(tracer, _NoopTracer)

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
    def test_returns_real_meter_with_otel(self):
        meter = get_meter("svc")
        # OTel is a hard dependency, so we always get a real meter
        assert not isinstance(meter, _NoopMeter)

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
        assert metrics["counts"]["decision:success"] == 1
        assert metrics["counts"]["tool_call:success"] == 1
        assert metrics["counts"]["model_invocation:success"] == 1
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

    def test_get_foundry_tracer_updates_enabled_state(self, monkeypatch):
        monkeypatch.setenv("FOUNDRY_TRACING_ENABLED", "true")

        tracer = get_foundry_tracer("svc-toggle", enabled=False)
        assert tracer.enabled is False

        same_tracer = get_foundry_tracer("svc-toggle", enabled=True)
        assert same_tracer is tracer
        assert same_tracer.enabled is True


class TestNormalizeOutcomeStatus:
    """Tests for _normalize_outcome_status()."""

    def test_success_outcomes(self):
        from holiday_peak_lib.utils.telemetry import _normalize_outcome_status

        for outcome in (
            "success",
            "ok",
            "completed",
            "enrich",
            "slm",
            "llm",
            "keyword",
            "intelligent",
            "provider_controlled",
        ):
            assert _normalize_outcome_status(outcome) == "success", f"Failed for {outcome}"

    def test_error_outcomes(self):
        from holiday_peak_lib.utils.telemetry import _normalize_outcome_status

        for outcome in ("error", "failed", "failure", "timeout", "exception"):
            assert _normalize_outcome_status(outcome) == "error", f"Failed for {outcome}"

    def test_skipped_outcomes(self):
        from holiday_peak_lib.utils.telemetry import _normalize_outcome_status

        for outcome in (
            "skip",
            "skip_no_gaps",
            "skipped",
            "no_upgrade",
            "noop",
            "missing_entity_id",
            "product_not_found",
        ):
            assert _normalize_outcome_status(outcome) == "skipped", f"Failed for {outcome}"

    def test_degraded_outcomes(self):
        from holiday_peak_lib.utils.telemetry import _normalize_outcome_status

        for outcome in ("degraded", "fallback", "partial"):
            assert _normalize_outcome_status(outcome) == "degraded", f"Failed for {outcome}"

    def test_pending_outcomes(self):
        from holiday_peak_lib.utils.telemetry import _normalize_outcome_status

        for outcome in ("pending", "start", "queued", "in_progress"):
            assert _normalize_outcome_status(outcome) == "pending", f"Failed for {outcome}"

    def test_heuristic_error_detection(self):
        from holiday_peak_lib.utils.telemetry import _normalize_outcome_status

        assert _normalize_outcome_status("connection_error") == "error"
        assert _normalize_outcome_status("auth_failure") == "error"

    def test_unknown_defaults_to_success(self):
        from holiday_peak_lib.utils.telemetry import _normalize_outcome_status

        assert _normalize_outcome_status("llm_by_complexity") == "success"
        assert _normalize_outcome_status("llm_by_slm_upgrade") == "success"
        assert _normalize_outcome_status("some_custom_value") == "success"

    def test_case_insensitive(self):
        from holiday_peak_lib.utils.telemetry import _normalize_outcome_status

        assert _normalize_outcome_status("SUCCESS") == "success"
        assert _normalize_outcome_status("Error") == "error"
        assert _normalize_outcome_status(" PENDING ") == "pending"


class TestOutcomeStatusInEvents:
    """Tests that outcome_status appears in all traced events."""

    def test_model_invocation_has_outcome_status(self, monkeypatch):
        monkeypatch.setenv("FOUNDRY_TRACING_ENABLED", "true")
        tracer = FoundryTracer("svc", max_events=5)
        tracer.trace_model_invocation(
            model="gpt-5",
            target="rich",
            outcome="success",
            model_tier="llm",
            metadata={"elapsed_ms": 10.0},
        )
        event = tracer.get_traces(limit=1)[0]
        assert event["outcome_status"] == "success"
        assert event["metadata"]["model_tier"] == "llm"

    def test_model_invocation_error_outcome_status(self, monkeypatch):
        monkeypatch.setenv("FOUNDRY_TRACING_ENABLED", "true")
        tracer = FoundryTracer("svc", max_events=5)
        tracer.trace_model_invocation(
            model="gpt-5",
            target="rich",
            outcome="error",
            metadata={"elapsed_ms": 5.0, "error": "timeout"},
        )
        event = tracer.get_traces(limit=1)[0]
        assert event["outcome_status"] == "error"

    def test_tool_call_has_outcome_status(self, monkeypatch):
        monkeypatch.setenv("FOUNDRY_TRACING_ENABLED", "true")
        tracer = FoundryTracer("svc", max_events=5)
        tracer.trace_tool_call(tool_name="search", outcome="success", metadata={})
        event = tracer.get_traces(limit=1)[0]
        assert event["status"] == "success"
        assert event["outcome_status"] == "success"

    def test_decision_has_outcome_status(self, monkeypatch):
        monkeypatch.setenv("FOUNDRY_TRACING_ENABLED", "true")
        tracer = FoundryTracer("svc", max_events=5)
        tracer.trace_decision(
            decision="model_selection",
            outcome="slm",
            metadata={"reason": "no_upgrade"},
        )
        event = tracer.get_traces(limit=1)[0]
        assert event["status"] == "success"
        assert event["outcome_status"] == "success"

    def test_decision_skipped_outcome_status(self, monkeypatch):
        monkeypatch.setenv("FOUNDRY_TRACING_ENABLED", "true")
        tracer = FoundryTracer("svc", max_events=5)
        tracer.trace_decision(
            decision="enrichment_decision",
            outcome="skip_no_gaps",
            metadata={"entity_id": "sku-1"},
        )
        event = tracer.get_traces(limit=1)[0]
        assert event["status"] == "skipped"
        assert event["outcome_status"] == "skipped"

    def test_decision_pending_outcome_status(self, monkeypatch):
        monkeypatch.setenv("FOUNDRY_TRACING_ENABLED", "true")
        tracer = FoundryTracer("svc", max_events=5)
        tracer.trace_decision(
            decision="invoke_model",
            outcome="start",
            metadata={"has_slm": True, "has_llm": True},
        )
        event = tracer.get_traces(limit=1)[0]
        assert event["status"] == "pending"
        assert event["outcome_status"] == "pending"

    def test_model_tier_defaults_to_unknown(self, monkeypatch):
        monkeypatch.setenv("FOUNDRY_TRACING_ENABLED", "true")
        tracer = FoundryTracer("svc", max_events=5)
        tracer.trace_model_invocation(
            model="gpt-5",
            target="rich",
            outcome="success",
            metadata={"elapsed_ms": 10.0},
        )
        event = tracer.get_traces(limit=1)[0]
        assert event["metadata"]["model_tier"] == "unknown"
