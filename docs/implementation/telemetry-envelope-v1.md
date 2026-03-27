# Telemetry envelope v1

This document defines the telemetry event envelope for shared `lib` emission paths via `FoundryTracer`.

**Source of truth**: `lib/src/holiday_peak_lib/utils/telemetry.py`

---

## 1. Required envelope dimensions

Every event emitted by `FoundryTracer._record()` includes these fields:

| Field | Type | Required | Description |
|---|---|---|---|
| `timestamp` | `string` | Yes | UTC ISO-8601 timestamp of emission. |
| `service` | `string` | Yes | Service name emitting the event (e.g. `"ecommerce-catalog-search"`). |
| `operation` | `string` | Yes | Logical operation/target for the event (maps to `name`). |
| `trace_id` | `string \| null` | Yes | Distributed trace identifier from metadata or active span context. |
| `correlation_id` | `string \| null` | Yes | Request correlation identifier from metadata or request context. |
| `status` | `string` | Yes | Normalized status enum for aggregations: `success \| error \| degraded \| skipped \| pending`. |
| `latency_ms` | `number \| null` | Yes | Latency in milliseconds (reads `latency_ms`, `elapsed_ms`, or `duration_ms` from metadata). |
| `type` | `string` | Yes | Event type: `model_invocation`, `tool_call`, `decision`. |
| `name` | `string` | Yes | Event-specific name (model target, tool name, or decision type). |
| `outcome` | `string` | Yes | Semantic outcome string (service-specific, e.g. `"slm"`, `"skip_no_gaps"`). |
| `outcome_status` | `string` | Yes | **Normalized** status enum: `success \| error \| degraded \| skipped \| pending`. |
| `metadata` | `object` | Yes | Event-specific key-value payload. |

## 2. Normalized `outcome_status` enum

The `outcome_status` field normalizes the free-form `outcome` string into a machine-parsable enum. This enables UI aggregators to classify events without per-service special-casing.

| Value | Meaning | Example outcomes mapped |
|---|---|---|
| `success` | Operation completed normally | `success`, `ok`, `completed`, `enrich`, `slm`, `llm`, `keyword`, `intelligent`, `provider_controlled`, `llm_by_complexity` |
| `error` | Operation failed | `error`, `failed`, `failure`, `timeout`, `exception`, or any outcome containing `"error"` or `"fail"` |
| `degraded` | Operation completed with reduced quality | `degraded`, `fallback`, `partial` |
| `skipped` | Operation intentionally not performed | `skip`, `skip_no_gaps`, `skipped`, `no_upgrade`, `noop`, `missing_entity_id`, `product_not_found` |
| `pending` | Operation started, not yet resolved | `pending`, `start`, `queued`, `in_progress` |

**Default**: Unrecognized outcomes map to `success` (model selection results like `"llm_by_slm_upgrade"` are successful routing decisions).

## 3. Event type catalog

### 3.1 `model_invocation`

Emitted when a model target is invoked. One event per model call.

| Metadata key | Type | Required | Description |
|---|---|---|---|
| `model` | `string` | Yes | Model deployment name (e.g. `"gpt-5"`, `"phi-4-mini"`). |
| `model_tier` | `string` | Yes | Routing tier: `slm \| llm \| unknown`. Derived from agent config. |
| `elapsed_ms` | `number` | Yes | Invocation wall-clock time in milliseconds. |
| `stream` | `boolean` | No | Whether streaming was enabled. |
| `temperature` | `number` | No | Temperature parameter used. |
| `top_p` | `number` | No | Top-p parameter used. |
| `error` | `string \| null` | No | Error text if outcome is `error`. |

**Example**:
```json
{
  "timestamp": "2026-03-24T14:30:00.000Z",
  "service": "ecommerce-catalog-search",
  "operation": "rich",
  "trace_id": "abc123",
  "correlation_id": "req-456",
  "status": "success",
  "latency_ms": 120.5,
  "type": "model_invocation",
  "name": "rich",
  "outcome": "success",
  "outcome_status": "success",
  "metadata": {
    "model": "gpt-5",
    "model_tier": "llm",
    "elapsed_ms": 120.5,
    "stream": false,
    "temperature": 0.2,
    "top_p": 0.9,
    "error": null
  }
}
```

### 3.2 `tool_call`

Emitted for each tool declared in a model invocation payload. Records tool participation in the call.

| Metadata key | Type | Required | Description |
|---|---|---|---|
| (inherits from parent model call) | — | — | Metadata from the parent `model_invocation` unless overridden. |

**Example**:
```json
{
  "timestamp": "2026-03-24T14:30:00.100Z",
  "service": "ecommerce-catalog-search",
  "operation": "search_catalog",
  "trace_id": "abc123",
  "correlation_id": "req-456",
  "status": "success",
  "latency_ms": 120.5,
  "type": "tool_call",
  "name": "search_catalog",
  "outcome": "success",
  "outcome_status": "success",
  "metadata": {
    "elapsed_ms": 120.5,
    "stream": false,
    "temperature": 0.2,
    "top_p": 0.9,
    "error": null
  }
}
```

### 3.3 `decision`

Emitted for agent routing and workflow decisions. Domain-specific decisions are encouraged — the `outcome_status` normalizer handles classification.

| Metadata key | Type | Required | Description |
|---|---|---|---|
| (service-specific) | varies | No | Decision-specific context keys (e.g. `entity_id`, `reason`, `has_slm`). |

**Common decision names from `base_agent.py`**:

| `name` (decision) | Typical `outcome` values | Normalized `outcome_status` |
|---|---|---|
| `invoke_model` | `start` | `pending` |
| `routing_strategy` | `provider_controlled` | `success` |
| `model_upgrade` | `llm_by_complexity`, `llm_by_slm_upgrade` | `success` |
| `model_selection` | `slm`, `<target_name>` | `success` |

**Common service-specific decisions**:

| Service | Decision name | Typical outcomes | Normalized |
|---|---|---|---|
| `truth-enrichment` | `enrichment_request_validation` | `missing_entity_id` | `skipped` |
| `truth-enrichment` | `enrichment_lookup` | `product_not_found` | `skipped` |
| `truth-enrichment` | `enrichment_decision` | `skip_no_gaps`, `enrich` | `skipped`, `success` |
| `ecommerce-catalog-search` | `search_mode_selection` | `keyword`, `intelligent` | `success` |
| `search-enrichment-agent` | `search_enrichment_validation` | `missing_entity_id` | `skipped` |
| `search-enrichment-agent` | `search_enrichment_strategy` | strategy name | `success` |

**Example**:
```json
{
  "timestamp": "2026-03-24T14:30:00.050Z",
  "service": "truth-enrichment",
  "operation": "enrichment_decision",
  "trace_id": "abc123",
  "correlation_id": "req-456",
  "status": "skipped",
  "latency_ms": null,
  "type": "decision",
  "name": "enrichment_decision",
  "outcome": "skip_no_gaps",
  "outcome_status": "skipped",
  "metadata": {
    "entity_id": "sku-12345",
    "schema_category": "apparel"
  }
}
```

### 3.4 `evaluation` (via `record_evaluation`)

Recorded separately from the trace stream. Represents agent evaluation payloads for quality tracking.

| Metadata key | Type | Required | Description |
|---|---|---|---|
| `operation` | `string` | No | Defaults to `"evaluation"`. |
| `status` | `string` | No | Defaults to `"recorded"`. |
| (domain-specific) | varies | No | Evaluation metrics, scores, details. |

## 4. Endpoint contracts

Events are exposed via auto-registered FastAPI endpoints in `app_factory_components/endpoints.py`:

| Endpoint | Response shape | Notes |
|---|---|---|
| `GET /agent/traces?limit=N` | `{ "service": str, "traces": [event, ...] }` | Most recent `N` events (default 50, max `FOUNDRY_TRACING_MAX_EVENTS`). Reverse chronological. |
| `GET /agent/metrics` | `{ "service": str, "enabled": bool, "app_insights_configured": bool, "traces_buffered": int, "instrumentation": {...}, "counts": {...} }` | Aggregate counters keyed by `{event_type}`, `{event_type}:{outcome_status}`, and compatibility keys `{event_type}:{outcome}`. |
| `GET /agent/evaluation/latest` | `{ "service": str, "latest": event \| null }` | Most recent evaluation payload or `null`. |

## 5. Resolution precedence

| Field | Priority 1 (highest) | Priority 2 | Fallback |
|---|---|---|---|
| `trace_id` | `metadata["trace_id"]` | `metadata["traceId"]` or `metadata["operation_id"]` | Active OpenTelemetry span context |
| `correlation_id` | `metadata["correlation_id"]` | Request-scoped context var | `null` |
| `latency_ms` | `metadata["latency_ms"]` | `metadata["elapsed_ms"]` | `metadata["duration_ms"]` |

## 6. Service onboarding checklist

To emit compliant telemetry events from a new agent service:

- [ ] **Extend `BaseRetailAgent`** — model invocation, tool, and decision tracing are automatic via `invoke_model()`.
- [ ] **Use `_trace_decision()`** for domain-specific decisions with descriptive `decision` and `outcome` strings.
- [ ] **Use `_trace_tools()`** only if you need to trace tools outside the standard `invoke_model` flow.
- [ ] **Pass `model_tier`** when calling `trace_model_invocation()` directly (automatic when using `BaseRetailAgent.__invoke_target`).
- [ ] **Include `entity_id`** in decision metadata when the operation targets a specific entity.
- [ ] **Verify endpoint availability** — `GET /agent/traces`, `/agent/metrics`, `/agent/evaluation/latest` are auto-registered by `build_service_app()`.
- [ ] **Test**: Run `pytest` and verify events include all required envelope fields.

## 7. Compatibility notes

- Existing fields (`type`, `name`, `outcome`, `metadata`) are preserved alongside the normalized fields.
- `outcome_status` is computed from `outcome` at emission time — never set by callers.
- `status` and `outcome_status` are both normalized enum values; use `outcome` when raw service-specific detail is needed.
- `model_tier` defaults to `"unknown"` when not provided.
- `trace_id` and `correlation_id` may be `null` when no context is available.
