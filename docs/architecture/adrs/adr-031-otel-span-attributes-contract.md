# ADR-031: OTEL Span Attributes Contract for Retail Agents

**Status**: Accepted
**Date**: 2026-05-08
**Deciders**: Architecture Team, Ricardo Cataldi
**Tags**: observability, opentelemetry, telemetry, governance
**References**: [ADR-007](adr-007-memory-tiers.md), [ADR-010](adr-010-model-routing.md), ADR-028 (Continuous Agent Evaluation — in flight on PR #974; link will be added when merged), [ADR-029](adr-029-agc-weighted-canary-policy.md), [ADR-030](adr-030-mcp-only-a2a.md)

## Context

Every agent service emits OpenTelemetry spans into Application Insights. Without a pinned schema, dashboards drift, queries break, and per-agent comparisons (eval, latency, canary impact) become unreliable. Each new ADR (canary policy, MCP A2A, eval engine) implicitly relies on specific span attributes; today those reliances are documented per-ADR rather than centrally enforced.

This ADR pins the **mandatory** and **conditional** span attributes for all retail agents and the CRUD service, and ships a framework helper that refuses to start a span lacking the mandatory parts.

## Decision

### 1. Mandatory Attributes (every span emitted by an agent or the CRUD service)

| Key | Type | Source |
|---|---|---|
| `service.name` | string | Pod env (Helm chart) — e.g., `ecommerce-cart-intelligence` |
| `service.version` | string | Pod env (image tag) |
| `pod.name` | string | Kubernetes Downward API |
| `model.id` | string | Model deployment id used for this span (`gpt-4o-mini`, `gpt-4o`, etc.); `none` for non-model spans |
| `prompt.sha` | string | SHA-256 of the prompt **template file** as loaded from `apps/<service>/prompts/` (the on-disk content, before any variable substitution); `none` if no prompt was used. Hashes of the rendered prompt are forbidden — those are input-dependent and would leak query shape. |
| `tenant.id` | string | Resolved from request context on agent-invocation spans only (matches §Risks cardinality budget); `unknown` for unauthenticated requests; absent (not set) on infrastructure / background / scheduled spans. **Privacy**: when `tenant.id` represents an end-user identity (B2C deployments), the helper hashes it (`sha256` truncated to 16 hex chars) before the value reaches the exporter. B2B tenant IDs may pass through unhashed. |
| `bounded_context` | string | One of `crm`, `ecommerce`, `inventory`, `logistics`, `product-management`, `search`, `truth`, `crud`. Pinned per service in Helm values. |

### 2. Conditional Attributes

| Key | Required when | Type |
|-----|--------------|------|
| `mcp.hop` | The span is an MCP request span | int |
| `mcp.tool` | The span is an MCP tool invocation | string |
| `mcp.tool_version` | The span is an MCP tool invocation (covers ADR-024 audit-field `tool_version`) | string |
| `mcp.peer_service` | An MCP outbound call is made (covers ADR-024 audit-field `target_service`) | string |
| `mcp.hop_overflow` | The MCP hop counter exceeded the cap (per ADR-030) | bool |
| `agc.weight` | The pod is serving traffic from a canary route | int (0..100) |
| `agc.canary.from_weight` | An AGC canary transition occurs (per ADR-029) | int |
| `agc.canary.to_weight` | An AGC canary transition occurs | int |
| `agc.canary.step_outcome` | An AGC canary step exits | enum `advanced` \| `held` \| `rolled_back` |
| `agc.canary.rollback_reason` | An AGC canary rollback occurs | string |
| `eval.score` | A continuous eval evaluation completes inside the span (per ADR-028; key subject to ADR-028 final schema in PR #974) | float |
| `eval.baseline_id` | A continuous eval evaluation completes (key subject to ADR-028 final schema in PR #974) | string |
| `cosmos.ru` | A Cosmos query / upsert occurs | float |
| `cosmos.diagnostic_string` | Cosmos call exceeded P99 latency budget OR returned non-2xx | string |
| `redis.op` | A Redis call occurs | enum `get` \| `set` \| `del` \| `expire` |
| `blob.path` | A Blob read / write occurs | string |
| `agent.routing_target` | The SLM-first router selected a model target (per ADR-010) | enum `slm` \| `llm` |
| `agent.routing_reason` | The router upgraded SLM → LLM | string |

**ADR-024 cross-walk**: span attribute `mcp.peer_service` corresponds to ADR-024 audit field `target_service`; span attribute `mcp.tool_version` corresponds to ADR-024 audit field `tool_version`. Both are populated from the same source value; the rename is intentional to namespace span attributes under `mcp.*`.

### 3. Forbidden in Span Attributes (privacy)

- Raw user PII (email, phone, full name).
- Customer order line item details.
- Auth tokens or any secret.

PII flows through the Warm tier (per ADR-007) for permitted purposes (eval, audit) — never through trace attributes.

### 4. Framework Helper

`lib/holiday_peak_lib/telemetry/retail_span.py` exposes a context manager that:

- Reads `service.name`, `service.version`, `pod.name`, `bounded_context`, `tenant.id` from the runtime context (env + request scope).
- Refuses to start a span lacking any mandatory attribute (raises at runtime in dev/test; logs and continues in prod with a `telemetry.contract_violation` event).
- Strips / hashes known PII patterns (email, phone, credit card regexes) at the boundary before values reach the exporter.
- Validates conditional attributes against the table above when their preconditions are met.

Usage:

```python
from holiday_peak_lib.telemetry import retail_span

async with retail_span("agent.invoke", model_id=cfg.model_id, prompt_sha=prompt.sha) as span:
    span.set_attribute("agent.routing_target", "slm")
    ...
```

### 5. Lint Enforcement

A pre-commit / CI check rejects direct `opentelemetry.trace.start_as_current_span` imports from `apps/**` and replaces them with `retail_span()`. The lib itself is allowed to use the bare OTEL API; nothing else is.

### 6. App Insights Workbooks

Workbook templates saved under `docs/ops/workbooks/` pivot on the pinned attributes. The first workbook (`agent-traces.json`) is referenced from the AGC canary runbook (ADR-029) and answers cross-cutting queries such as "P95 latency by `bounded_context` and `model.id` over the last 24 h."

## Consequences

### Positive

- Dashboards and queries become stable across services and across releases.
- New observability features (eval, canary, MCP) reuse the same attribute keys consistently.
- PII leaks via tracing become a contract violation, not a silent regression.
- Lint catches drift at PR time, not at workbook-broken time.

### Negative

- Engineers cannot reach for the bare OTEL API in app code; one helper is the single seam.
- Backward-incompatible attribute renames require coordinated workbook migrations in the same PR.

### Risks

| Risk | Mitigation |
|------|------------|
| Cardinality explosion (e.g., `tenant.id` with millions of distinct values) inflates App Insights cost. | Document expected cardinality per attribute. `tenant.id` only on agent-invocation spans, not infrastructure spans. Cardinality budget reviewed quarterly. |
| Forbidden PII slips through. | Lib helper strips/hashes known PII patterns at the boundary; workbook `pii-anomaly-scan.json` flags anomalies; periodic audit. |
| Adoption friction — engineers reach for raw OTEL. | Lint rule fails the PR; ADR explains the rationale; framework helper provides idiomatic ergonomics. |
| Schema evolution breaks existing dashboards. | Backward-compatible additions only. Removals or renames require workbook migration in the same PR. |
| Helper raise-in-dev / log-in-prod policy creates uneven enforcement. | Both modes log a `telemetry.contract_violation` event so audits see the full picture; production must not page on dev-only contract failures. |

## Alternatives Considered

### Alternative A — Documentation-only contract

Rejected. Documentation-only contracts have drifted before in this repo; lint enforcement is the only durable mechanism.

### Alternative B — Centralize in a side-car / collector

Considered. Sidecar-based attribute injection works for some attributes (`pod.name`, `service.version`) but cannot synthesize semantic attributes (`prompt.sha`, `eval.score`, `agent.routing_*`). The framework-helper approach covers both classes uniformly.

### Alternative C — Adopt OTel Semantic Conventions verbatim

Considered. Where overlapping (`service.name`, `service.version`), this ADR aligns with OTel SemConv. Retail-specific attributes (`prompt.sha`, `agc.canary.*`, `mcp.hop`) have no SemConv counterpart; this ADR pins the local extension.

## Implementation

> **Conditional acceptance**: this ADR is Accepted on the contract (§1–§5 above), but the helper module, lint script, and workbooks (`docs/ops/workbooks/agent-traces.json`, `docs/ops/workbooks/pii-anomaly-scan.json`) are net-new artifacts that MUST land in the same merge train as the schema. Until they exist, the schema is advisory; lint enforcement and PII filtering activate only when the helper ships.

| Component | File / Location | Change |
|-----------|----------------|--------|
| ADR | `docs/architecture/adrs/adr-031-otel-span-attributes-contract.md` | This file |
| Helper | `lib/src/holiday_peak_lib/telemetry/retail_span.py` | New — context manager + PII filter + contract enforcement |
| Helper tests | `lib/tests/test_retail_span.py` | New — covers missing mandatory, conditional gating, PII stripping (template-only `prompt.sha`, B2C tenant hashing) |
| Lint | `scripts/ci/lint_no_bare_otel.py` | New — rejects both direct `opentelemetry.trace.start_as_current_span` imports and `<anything>.start_as_current_span(...)` call sites outside `lib/` |
| Migration | All 26 agent services + `crud-service` | Adopt `retail_span()`; tracked under R1 epic per service |
| Workbook | `docs/ops/workbooks/agent-traces.json` | New — pivots on pinned attributes |
| Workbook | `docs/ops/workbooks/pii-anomaly-scan.json` | New — flags candidate PII leaks |

## Verification

- **Unit**: `retail_span()` rejects calls missing `model.id` when invoking an agent that has a model target.
- **Unit**: PII filter rejects values matching `[\w.-]+@[\w.-]+`, common phone formats, credit-card check digits before they reach the exporter.
- **Integration**: end-to-end Frontend → Agent → MCP peer → CRUD trace emits the full attribute set; one App Insights query reconstructs the chain.
- **Cross-cutting query**: "P95 latency by `bounded_context` and `model.id` over the last 24 h" returns rows for every active context.

## Pattern References

- **Distributed Tracing** — Azure Well-Architected Framework, Operational Excellence pillar.
- **Observability** — microservices.io.
- **OpenTelemetry Semantic Conventions** — https://opentelemetry.io/docs/specs/semconv/

## References

- [OpenTelemetry Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/)
- [ADR-007 — Memory Architecture and Isolation Strategy](adr-007-memory-tiers.md)
- [ADR-010 — SLM-First Model Routing Strategy](adr-010-model-routing.md)
- ADR-028 — Continuous Agent Evaluation (in flight on PR #974; link will be added once that PR merges and the ADR file lands at `adrs/adr-028-continuous-agent-evaluation.md`)
- [ADR-029 — AGC Weighted Canary Policy](adr-029-agc-weighted-canary-policy.md)
- [ADR-030 — MCP-Only Agent-to-Agent Communication](adr-030-mcp-only-a2a.md)
