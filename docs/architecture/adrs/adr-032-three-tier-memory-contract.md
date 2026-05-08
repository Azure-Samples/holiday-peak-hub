# ADR-032: Three-Tier Memory Contract Pinning (Hot / Warm / Cold)

**Status**: Accepted (Refines ADR-007)
**Date**: 2026-05-08
**Deciders**: Architecture Team, Ricardo Cataldi
**Tags**: memory, redis, cosmos-db, blob-storage, contract
**References**: [ADR-007](adr-007-memory-tiers.md), [ADR-026](adr-026-namespace-isolation-strategy.md), [ADR-031](adr-031-otel-span-attributes-contract.md)

## Context

ADR-007 established the three-tier memory architecture: Hot (Redis), Warm (Cosmos DB), Cold (Azure Blob). The implementation in `lib/holiday_peak_lib/memory/` is largely in place and used by every agent service via `MemorySettings`. What is still missing is a **pinned contract** — a single, enforceable specification that fixes:

- Public API surface (class names, method signatures).
- Per-tier latency budgets, durability, indexability.
- Tier-promotion / demotion policy.
- Health-probe contract (read-only, no PII).

Without this, agent authors and integrators drift on what each tier means, when each is read or written, and what survives eviction. R1 (the MAF cutover) re-binds the agent runtime to memory; pinning the contract ahead of R1 means every migrated service inherits the same expectations.

## Decision

### 1. Tier Semantics

| Tier | Backend | Latency budget (P99) | Durability | Indexability | Use cases |
|------|---------|---------------------|------------|--------------|-----------|
| **Hot** | Redis (Azure Managed Redis) | ≤ 5 ms read, ≤ 10 ms write | Best-effort, ephemeral | Key-based; optional secondary indexes via RediSearch | Per-conversation context, session state, in-flight agent prompt cache, rate-limit counters |
| **Warm** | Cosmos DB (NoSQL API) | ≤ 50 ms read, ≤ 100 ms write | Multi-region durable | Partition key + composite indexes; vector search via container indexing policy | Per-user profile context, agent decision history, eval traces, RAG document chunks |
| **Cold** | Azure Blob Storage | ≤ 500 ms (single-blob read) | Geo-redundant | Path-based, no query | Raw event payloads, batch eval datasets, archived prompts, source-of-truth for replay |

### 2. Tier-Promotion Policy

- **Cold → Warm**: triggered when a read access pattern exceeds N reads per H hours (configurable per service). Promotes a copy of the artifact into a Cosmos container with a TTL.
- **Warm → Hot**: triggered by a read access pattern within an active session (existing TTL on the Hot tier).
- **Hot → discard**: TTL-based. No automatic demotion to Warm; if state must survive eviction, the writer also writes to Warm.
- **Warm → Cold**: TTL-based. Records older than N days are written to Blob (compressed), then evicted from Cosmos.

### 3. Public API (pinned by contract test)

```python
class MemorySettings(BaseSettings):
    redis_url: str | None
    cosmos_account_uri: str | None
    cosmos_database: str | None
    cosmos_container: str | None
    blob_account_url: str | None
    blob_container: str | None

class HotStore:  # Redis
    async def get(self, key: str) -> bytes | None: ...
    async def set(self, key: str, value: bytes, ttl: timedelta | None = None) -> None: ...
    async def delete(self, key: str) -> None: ...
    async def health(self) -> bool: ...

class WarmStore:  # Cosmos
    async def read(self, partition_key: str, item_id: str) -> dict | None: ...
    async def upsert(self, item: dict) -> None: ...
    async def query(self, sql: str, parameters: list[dict] | None = None) -> AsyncIterator[dict]: ...
    async def health(self) -> bool: ...

class ColdStore:  # Blob
    async def get(self, path: str) -> bytes | None: ...
    async def put(self, path: str, payload: bytes, content_type: str = "application/octet-stream") -> None: ...
    async def list(self, prefix: str) -> AsyncIterator[str]: ...
    async def health(self) -> bool: ...

class MemoryFacade:
    hot: HotStore
    warm: WarmStore
    cold: ColdStore
    async def health(self) -> dict[str, bool]: ...   # {"hot": True, "warm": True, "cold": True}
```

A contract test in `lib/tests/test_memory_contract.py` imports each public symbol and asserts signature compatibility. Any breaking change to the surface fails the test.

### 4. Health-Probe Contract

- Each agent pod exposes `/healthz/memory` returning JSON `{"hot": true, "warm": true, "cold": true}`.
- Kubernetes readiness probe queries `/healthz/memory`. Pod is unready if any tier is unreachable for 30 s.
- The probe attaches **no PII** and does **not** write any value to any tier (read-only ping).
- The contract test asserts `health()` calls no `set` / `upsert` / `put`.

### 5. Cosmos DB Best-Practice Alignment

Per the workspace's Cosmos DB instructions (loaded into every prompt):

- Containers use **Hierarchical Partition Keys** (HPK) where applicable to avoid the 20 GB single-partition limit.
- Partition key cardinality is high (e.g., `tenantId/userId`).
- Warm tier reuses a singleton `CosmosClient` per pod.
- Diagnostic strings are logged via the OTEL `cosmos.diagnostic_string` attribute (per ADR-031) when latency exceeds the P99 budget or status code is unexpected.

### 6. Cold-Tier Path Convention

Blob layout pinned: `<tenant>/<bounded-context>/<date>/<artifact-id>`. Lifecycle policy archives blobs older than 30 days to cool / archive tier.

### 7. Privacy Boundary

- Tracing spans NEVER carry PII (per ADR-031).
- Warm tier MAY carry PII for permitted purposes (eval, audit), with documented retention.
- Cold tier MAY carry PII when the source of truth requires replay; encrypted at rest by Blob defaults; access audited.

## Consequences

### Positive

- Public API stable; agent authors and integrators can rely on the surface across releases.
- Health-probe contract makes pod readiness deterministic.
- Tier-promotion policy makes hot-key behavior predictable.
- HPK alignment prevents Cosmos partition saturation as tenant count grows.

### Negative

- Pinning the API forces a deprecation cycle for any future surface change.
- Promotion thresholds are per-service and must be tuned; defaults are conservative.

### Risks

| Risk | Mitigation |
|------|------------|
| Health probe writes to a tier and fills it with junk over time. | Contract: `health()` is read-only. Contract test asserts no `set` / `upsert` / `put` is called inside `health()`. |
| Cosmos RU consumption spikes when promotion thresholds are too aggressive. | Per-service config; conservative defaults; alerting via App Insights. |
| Hot-tier eviction loses an in-flight agent prompt. | Writers pair Hot writes with a Warm `upsert` for any state that must survive eviction. |
| Cold-tier blob layout becomes unmanageable. | Path convention pinned in this ADR; lifecycle policy archives blobs > 30 days. |
| API drift breaks dependent services silently. | Contract test on `lib/` PRs blocks signature changes; deprecation warnings precede any change. |

## Alternatives Considered

### Alternative A — Single-tier (Cosmos only)

Rejected. Hot-path latency targets (≤ 5 ms reads) are not achievable on Cosmos at the scale and access pattern of in-flight agent state.

### Alternative B — Two-tier (drop Cold)

Rejected. Source-of-truth replay (raw event payloads, batch eval datasets) needs a cheap, durable, geo-redundant store; Blob is the right fit and removing it would push that cost into Cosmos with no benefit.

### Alternative C — Replace Redis with in-memory pod cache

Rejected. Pod-local cache loses state on every restart and cannot share across pods of the same service. The Hot tier needs to be cluster-shared.

## Implementation

| Component | File / Location | Change |
|-----------|----------------|--------|
| ADR | `docs/architecture/adrs/adr-032-three-tier-memory-contract.md` | This file |
| Public API | `lib/holiday_peak_lib/memory/` | Pin classes / signatures; refactor only if signatures already match |
| Contract test | `lib/tests/test_memory_contract.py` | New — asserts public surface + read-only `health()` |
| Health endpoint | `apps/<service>/src/.../routes.py` | `/healthz/memory` per service |
| Helm readiness | `infra/charts/<service>/values.yaml` | `readinessProbe.httpGet.path: /healthz/memory` |
| Performance test | `tests/e2e/perf/test_memory_tiers.py` | New — P99 budgets per tier |
| Documentation | `lib/README.md` | Document the contract + minimal usage example |

## Verification

- **Contract test** imports each public symbol and asserts signature compatibility.
- **Unit** test injects fake Hot / Warm / Cold backends and exercises Cold → Warm → Hot promotion for a single key.
- **Live** test in dev cluster pings `/healthz/memory` on each pod and asserts a 200 with `{"hot": true, "warm": true, "cold": true}`.
- **Cosmos diagnostic** logging verified by intentionally setting a low RU budget and observing the `cosmos.diagnostic_string` span attribute.
- **Performance** test asserts P99 latency budgets per tier.

## Pattern References

- **Cache-Aside** — microservices.io
- **Materialized View** — microservices.io (Warm tier as a queryable projection of Cold)
- **Event-Carried State Transfer** — microservices.io / EIP. Cold-blob events trigger Warm rebuild on demand.

## References

- [ADR-007 — Memory Architecture and Isolation Strategy](adr-007-memory-tiers.md) — base decision; this ADR refines the contract.
- [ADR-026 — Namespace Isolation Strategy](adr-026-namespace-isolation-strategy.md)
- [ADR-031 — OTEL Span Attributes Contract for Retail Agents](adr-031-otel-span-attributes-contract.md)
- Workspace Cosmos DB best practices (loaded via `azurecosmosdb.instructions.md`).
