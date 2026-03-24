# Telemetry envelope v1

This document defines the minimum telemetry event envelope for shared `lib` emission paths.

## Required dimensions

| Field | Type | Description |
|---|---|---|
| `service` | `string` | Service name emitting the event. |
| `operation` | `string` | Logical operation/target for the event. |
| `trace_id` | `string \| null` | Distributed trace identifier from metadata or active span context. |
| `correlation_id` | `string \| null` | Request correlation identifier from metadata or request context. |
| `status` | `string` | Outcome/status value for the event. |
| `latency_ms` | `number \| null` | Latency in milliseconds (`latency_ms`, `elapsed_ms`, or `duration_ms`). |
| `timestamp` | `string` | UTC ISO-8601 timestamp of emission. |

## Compatibility notes

- Existing fields are preserved where present (for example `type`, `name`, `outcome`, and `metadata`).
- `trace_id` and `correlation_id` may be `null` when no context is available.
- Correlation precedence: event metadata value first, then request context.
- Trace precedence: event metadata value first, then active OpenTelemetry span context.
