# ADR-024: Agent Communication Policy, Isolation, and Async Contracts

## Status

Accepted (Revised 2026-04-29 — added Part 4: Agent Mode Classification and Differentiated SLA Policy)  
**Supersedes**: prior separate decisions on Agent Isolation Policy and Async Communication Contract (now absorbed into this ADR)

## Date

2026-03-18

## Context

The platform uses dual exposition (REST + MCP) as defined in [ADR-004](adr-004-fastapi-mcp.md). As agent services scaled, internal service-to-service communication paths diverged, creating architecture drift risk and inconsistent rollout controls.

Issue #329 requests an explicit internal communication policy that service teams can execute consistently and that provides rollout guardrails for #330.

This addendum defines mandatory MCP communication boundaries, prohibited coupling patterns, observability and compliance requirements, and release governance checks.

Architecture principles applied:

- **Domain-Driven Design (Bounded Contexts)**: internal calls must respect domain ownership and explicit interfaces.
- **TOGAF (Architecture Governance and Building Blocks)**: communication contracts are governed architecture building blocks with compliance checkpoints.
- **microservices.io (Loose Coupling, Smart Endpoints)**: avoid point-to-point coupling that bypasses policy and observability controls.

## Decision

Adopt a mandatory **MCP-first internal communication policy** for agent-to-agent interaction boundaries, with explicit exceptions.

### Allowed Internal Communication Paths

1. **Agent service -> Agent service via MCP tools**
   - Required for internal capability composition and tool discovery.
2. **Frontend -> CRUD service via REST**
   - Allowed for transactional UX operations.
3. **Frontend -> Agent service via REST**
   - Allowed for user-facing intelligence endpoints exposed as HTTP APIs.
4. **CRUD service -> Agent service via REST**
   - Allowed for fast enrichment/decision assist flows where CRUD remains the transactional system of record.
5. **Async domain events via Event Hubs**
   - Allowed for decoupled choreography and background processing.

### Boundary Rules (Mandatory)

1. **Domain ownership**
   - MCP tools expose domain capabilities only from owning services.
   - Cross-domain direct data reads must go through owning service contracts (MCP tool or approved REST API).
2. **No transport leakage**
   - Callers must not depend on internal storage or adapter details of another service.
3. **Stable contracts**
   - MCP input/output schemas must be versioned and backward compatible for additive changes.
4. **Identity and tenant propagation**
   - Internal calls must propagate tenant, correlation, and caller identity context.
5. **Default deny for new paths**
   - Any new internal communication edge requires architecture review and ADR reference before production enablement.

### Prohibited Direct Coupling Patterns

1. Agent service directly calling another service's database, cache, or blob container.
2. Agent service invoking another service's private, non-governed HTTP endpoint (bypassing MCP/approved API surface).
3. Shared mutable schema ownership across bounded contexts without an owning contract.
4. Hard-coded service internals (pod IPs, internal hostnames, storage keys) in application call paths.
5. Runtime dependency on undocumented tool names or unversioned MCP payload fields.
6. Agent service invoking CRUD REST endpoints directly — all agent-to-CRUD reads must use approved cross-namespace DNS paths (ADR-026); enrichment and decision flows are initiated by CRUD calling agents, not the reverse (§Part 2 Isolation).

```mermaid
%%{init: {'theme':'base', 'themeVariables': {
  'primaryColor':'#FFB3BA',
  'primaryTextColor':'#000',
  'primaryBorderColor':'#FF8B94',
  'lineColor':'#BAE1FF',
  'secondaryColor':'#BAE1FF',
  'tertiaryColor':'#FFFFFF'
}}}%%
flowchart LR
    UI[Frontend] -->|REST| CRUD[CRUD Service]
    UI -->|REST| AGENTA[Agent Service A]
    CRUD -->|REST approved| AGENTA
    AGENTA -->|MCP Tools| AGENTB[Agent Service B]
    AGENTA -->|Events| EH[(Event Hubs)]
    AGENTB -->|Events| EH
    AGENTA -.->|cross-ns DNS<br/>reads only, ADR-026| CRUD

    AGENTA -. prohibited .-> DBB[(Service B DB)]
    AGENTA -. prohibited .-> PRIVB[Service B Private Endpoint]
    AGENTA -. "prohibited: direct\nCRUD REST calls\n(ADR-024)" .-> CRUD_REST[CRUD REST API]
```

### Observability and Compliance Expectations

Every internal MCP interaction must emit the following minimum telemetry fields:

- `correlation_id`
- `tenant_id`
- `caller_service`
- `target_service`
- `tool_name`
- `tool_version`
- `latency_ms`
- `status` (`success|error|timeout|rejected`)

Compliance requirements:

1. Retain structured audit logs for internal MCP calls per environment retention policy.
2. Alert on policy violations (prohibited direct-coupling path detected, missing tenant context, missing correlation).
3. Include MCP dependency edges in architecture inventory for review cadence.

## Governance Checks for #330 Rollout

The following gates are required for service-team rollout approval.

### Gate 1: Contract and Boundary Readiness

- MCP tools are documented with owner, purpose, request/response schema, and version.
- Internal communication edges are classified as allowed paths in this ADR.
- No prohibited direct coupling patterns are present.

### Gate 2: Runtime Safety and Telemetry

- Correlation and tenant context propagation verified in integration tests.
- Telemetry fields required by this ADR are present in logs and traces.
- Error handling and timeout behavior are defined for upstream callers.

### Gate 3: Compliance and Operations

- Policy violation alert rules are enabled.
- Runbook entries exist for MCP tool failures and dependency degradation.
- Rollback plan includes feature flags or route controls to disable new internal edges safely.

## Practical Implementation Checklist (Service Teams)

- [ ] Internal service dependencies are represented as MCP tools or approved REST contracts only.
- [ ] No direct reads/writes to another service's persistence layer.
- [ ] MCP contracts are versioned and additive-change compatible.
- [ ] Tenant and correlation context are propagated end-to-end.
- [ ] Required MCP telemetry fields are emitted and queryable.
- [ ] Policy violation alerts are configured and tested.
- [ ] Integration tests validate allowed-path behavior and denied-path safeguards.
- [ ] Rollout plan maps to Gate 1–3 and identifies rollback controls.

## Alternatives Considered

1. **REST-only internal communication**
   - Rejected: loses MCP tool discoverability and weakens agent-native composition patterns.
2. **Unrestricted protocol choice by team**
   - Rejected: increases drift risk and weakens governance consistency.
3. **Event-only internal communication**
   - Rejected: unsuitable for synchronous capability invocation and request-response workflows.

## Consequences

### Positive

1. Reduces architecture drift with explicit communication boundaries.
2. Improves auditability and incident triage for internal agent interactions.
3. Provides consistent rollout gates for #330 across service teams.

### Negative

1. Adds governance overhead for introducing new internal communication edges.
2. Requires teams to maintain MCP contract metadata and telemetry discipline.

## References

- [ADR-004](adr-004-fastapi-mcp.md)
- [ADR-019](adr-019-enterprise-resilience-patterns.md)
- [ADR-026](adr-026-namespace-isolation-strategy.md)
- [Architecture Overview](../architecture.md)

---

## Part 2: Agent Isolation Policy

### Context

The platform deploys 26 agent services alongside 1 CRUD service. Agents are forbidden from importing or calling CRUD service adapters and REST endpoints directly — this prevents blast radius expansion, coupling, and security surface issues.

### Approved Communication Paths

| Path | Direction | Mechanism | Governed By |
|------|-----------|-----------|-------------|
| Cross-namespace K8s DNS | Agent → CRUD | Transactional reads only | ADR-026 Option A |
| APIM MCP tools | Agent → Agent | MCP tool invocation through APIM | §Allowed Paths above |
| Event Hubs | Agent ↔ CRUD | Asynchronous domain events (SAGA) | ADR-006 |
| APIM REST | CRUD → Agent | Enrichment/decision-assist calls | §Allowed Paths above |
| APIM REST | Frontend → CRUD | Transactional UI operations | ADR-021 |
| APIM REST | Frontend → Agent | Intelligence endpoints for UI | ADR-021 |

### Prohibited Patterns (Isolation)

1. **Agent importing `BaseCRUDAdapter`** or any CRUD-specific adapter from `holiday_peak_lib`.
2. **Agent calling `register_crud_tools()`** or registering CRUD endpoints as MCP tools within agent processes.
3. **Agent making direct HTTP calls** to CRUD REST endpoints outside the approved cross-namespace DNS path for transactional reads.
4. **Agent holding CRUD database connection strings** or accessing CRUD's PostgreSQL, Redis, or Cosmos DB instances directly.
5. **Shared mutable state** between agent and CRUD services via any mechanism other than Event Hubs.

### Communication Path Topology

```mermaid
%%{init: {'theme':'base', 'themeVariables': {
  'primaryColor':'#FFB3BA',
  'primaryTextColor':'#000',
  'primaryBorderColor':'#FF8B94',
  'lineColor':'#BAE1FF',
  'secondaryColor':'#BAE1FF',
  'tertiaryColor':'#FFFFFF'
}}}%%
flowchart LR
    subgraph Approved["Approved Communication Paths"]
        direction TB
        UI[Frontend] -->|REST via APIM| CRUD[CRUD Service]
        UI -->|REST via APIM| AGENT_A[Agent Service A]
        CRUD -->|REST via APIM| AGENT_A
        AGENT_A -->|MCP via APIM| AGENT_B[Agent Service B]
        AGENT_A -->|cross-ns DNS<br/>reads only| CRUD
        AGENT_A -->|Events| EH[(Event Hubs)]
        CRUD -->|Events| EH
        EH -->|Events| AGENT_B
    end

    subgraph Prohibited["Prohibited Patterns"]
        direction TB
        BAD_AGENT[Agent Service] -. BaseCRUDAdapter .-> BAD_CRUD[CRUD Internals]
        BAD_AGENT -. direct REST calls .-> BAD_REST[CRUD REST API]
        BAD_AGENT -. shared DB access .-> BAD_DB[(CRUD Database)]
    end

    style Approved fill:#e8f5e9,stroke:#4caf50,color:#000
    style Prohibited fill:#ffebee,stroke:#f44336,color:#000
```

### Isolation Enforcement

- **CI/CD checks**: Import scanning for `BaseCRUDAdapter` and `register_crud_tools` in agent code
- **Architecture review**: New agent→CRUD paths require ADR reference and team approval
- **Runtime monitoring**: APIM and Istio telemetry detect unauthorized direct REST calls

### Implementation Evidence

| Change | PR | Scope |
|--------|----|-------|
| Removed `BaseCRUDAdapter` from `holiday_peak_lib` | #881 | Eliminates compile-time CRUD coupling |
| Removed `register_crud_tools()` from `registration_helpers.py` | #881 | Prevents CRUD tool registration in agents |
| Swept 22 agent services to drop CRUD imports/calls | #882 | Removes all direct CRUD invocations |
| Stripped `CRUD_SERVICE_URL` from 25 rendered manifests | #882 | Removes runtime CRUD config from agents |

---

## Part 3: Async Communication Contracts

### Observer Pattern Primitives

#### `TopicSubject`

A named topic wrapper implementing the Observer pattern:

```python
from holiday_peak_lib.messaging import TopicSubject

# Producer side
product_events = TopicSubject(topic="product-updates", schema=ProductUpdateEvent)
await product_events.publish(ProductUpdateEvent(product_id="123", action="enriched"))

# Consumer side
product_events = TopicSubject(topic="product-updates", schema=ProductUpdateEvent)
product_events.register_observer(handle_product_update)
await product_events.start_consuming()
```

#### `AgentAsyncContract`

A Pydantic model self-describing an agent's async capabilities:

```python
from holiday_peak_lib.messaging import AgentAsyncContract, TopicDescriptor

contract = AgentAsyncContract(
    agent_name="ecommerce-catalog-search",
    publishes=[
        TopicDescriptor(topic="search-index-updated", schema_ref="SearchIndexEvent",
                        description="Emitted when catalog search index is refreshed"),
    ],
    consumes=[
        TopicDescriptor(topic="product-updates", schema_ref="ProductUpdateEvent",
                        description="Triggers re-indexing when product data changes"),
    ],
)
```

#### `/async/contract` Endpoint

Auto-registered by `create_standard_app()` to expose async contracts as machine-readable JSON.

### Async Contract Topology

```mermaid
%%{init: {'theme':'base', 'themeVariables': {
  'primaryColor':'#FFB3BA',
  'primaryTextColor':'#000',
  'primaryBorderColor':'#FF8B94',
  'lineColor':'#BAE1FF',
  'secondaryColor':'#BAE1FF',
  'tertiaryColor':'#FFFFFF'
}}}%%
flowchart LR
    subgraph CRUD_NS["holiday-peak-crud"]
        CRUD[CRUD Service]
    end
    subgraph EH["Azure Event Hubs"]
        T1([product-updates])
        T2([order-events])
        T3([inventory-alerts])
    end
    subgraph AGENTS_NS["holiday-peak-agents"]
        A1[catalog-search<br/>/async/contract]
        A2[cart-intelligence<br/>/async/contract]
        A3[inventory-alerts<br/>/async/contract]
    end
    CRUD -->|publish| T1
    CRUD -->|publish| T2
    T1 -->|consume| A1
    T2 -->|consume| A2
    T3 -->|consume| A3
    A3 -->|publish| T3
```

### Risk Mitigation for Async Contracts

| Risk | Mitigation |
|------|------------|
| Contract drift (declared vs. actual) | CI check comparing declared topics against `TopicSubject` instantiations |
| Over-abstraction | `TopicSubject` wraps existing primitives; agents can fall back to raw `EventPublisher` |
| Adoption lag | Incremental rollout by domain (truth-layer first, then ecommerce, CRM, etc.) |

---

## Part 4: Agent Mode Classification and Differentiated SLA Policy

### Context

Parts 1–3 define synchronous (REST/MCP) and asynchronous (Event Hub) communication paths. However, the platform applied a uniform latency SLA (8s invoke response) to all 26 agents regardless of their primary interaction pattern. This produced false-positive alerts for event-driven agents and masked real violations for user-facing agents (see [issue #927](https://github.com/Azure-Samples/holiday-peak-hub/issues/927) — confirmed SLA violation for `ecommerce-cart-intelligence`).

This section formalizes a **dual-class SLA model** based on each agent's primary interaction mode.

### Classification Criteria

| Criterion | Primary Synchronous | Primary Asynchronous |
|-----------|--------------------|--------------------|
| **User blocking** | A human or frontend component is waiting for the response | No user is waiting; processing happens in the background |
| **Trigger pattern** | REST `POST /invoke` or `/invoke/stream` from UI/CRUD | Event Hub consumer group processing domain events |
| **Value metric** | Response latency and streaming first-token time | Throughput, completeness, and processing lag |
| **Failure impact** | Immediate UX degradation (empty page, timeout spinner) | Delayed data freshness; users unaware until downstream read |

### Agent Registry

#### Primary Synchronous (11 agents)

| Agent | Domain | Rationale |
|-------|--------|-----------|
| ecommerce-catalog-search | eCommerce | Search results rendered to shopper in real time |
| ecommerce-cart-intelligence | eCommerce | Cart scoring and recommendations at checkout |
| ecommerce-checkout-support | eCommerce | Checkout validation blocking purchase flow |
| ecommerce-order-status | eCommerce | Order status query — user waiting for answer |
| ecommerce-product-detail-enrichment | eCommerce | Real-time PDP enrichment on page load |
| crm-profile-aggregation | CRM | Profile lookup for personalization decisions |
| crm-support-assistance | CRM | Live support guidance for human agents |
| inventory-reservation-validation | Inventory | Stock validation at checkout — user blocking |
| logistics-eta-computation | Logistics | ETA displayed to customer in shipping UI |
| logistics-carrier-selection | Logistics | Carrier options rendered at checkout |
| logistics-returns-support | Logistics | Returns flow guidance — user waiting |

#### Primary Asynchronous (15 agents)

| Agent | Domain | Trigger Pattern |
|-------|--------|-----------------|
| crm-campaign-intelligence | CRM | Funnel behavior events |
| crm-segmentation-personalization | CRM | Behavior/profile change events |
| inventory-alerts-triggers | Inventory | Stock-level threshold events |
| inventory-health-check | Inventory | Periodic/event-triggered health assessment |
| inventory-jit-replenishment | Inventory | Stock depletion events |
| logistics-route-issue-detection | Logistics | Route telemetry events |
| product-management-acp-transformation | Product Mgmt | Product data change events |
| product-management-assortment-optimization | Product Mgmt | Catalog/assortment optimization events |
| product-management-consistency-validation | Product Mgmt | Product update validation events |
| product-management-normalization-classification | Product Mgmt | Product ingestion events |
| search-enrichment-agent | Search | Truth-approved product events |
| truth-ingestion | Truth Layer | Source data upload events |
| truth-enrichment | Truth Layer | Ingestion-complete events |
| truth-hitl | Truth Layer | Low-confidence enrichment events |
| truth-export | Truth Layer | HITL-approved export events |

### SLA Targets by Class

#### Synchronous Agent SLA

| Metric | Target | Measurement |
|--------|--------|-------------|
| Invoke response P95 | < 8 s (end-to-end including APIM/AGC) | `POST /agents/{service}/invoke` |
| Agent processing P95 | < 5 s (excluding network overhead) | Application telemetry span |
| SLM routing path P95 | < 2 s | Model-tier trace annotation |
| LLM routing path P95 | < 6 s | Model-tier trace annotation |
| Health response P95 | < 2 s | `GET /agents/{service}/health` |
| Streaming first token P95 | < 3 s | `POST /agents/{service}/invoke/stream` |

#### Asynchronous Agent SLA

| Metric | Target | Measurement |
|--------|--------|-------------|
| Event processing latency P95 | < 10 min (event received → processing complete) | Event Hub consumer lag + app telemetry |
| Sustained throughput | ≥ 100 events/min per partition | Load test and production metrics |
| Event loss rate | 0 % | Event Hub abandoned/dead-letter metrics |
| Health response P95 | < 2 s | `GET /agents/{service}/health` |
| Invoke response (when called sync) | Best-effort, no SLA violation | Informational metric only |

### Classification Topology

```mermaid
%%{init: {'theme':'base', 'themeVariables': {
  'primaryColor':'#FFB3BA',
  'primaryTextColor':'#000',
  'primaryBorderColor':'#FF8B94',
  'lineColor':'#BAE1FF',
  'secondaryColor':'#BAE1FF',
  'tertiaryColor':'#FFFFFF'
}}}%%
flowchart TB
    subgraph SYNC["Primary Synchronous (11)"]
        direction LR
        S1[catalog-search]
        S2[cart-intelligence]
        S3[checkout-support]
        S4[order-status]
        S5[product-detail-enrichment]
        S6[profile-aggregation]
        S7[support-assistance]
        S8[reservation-validation]
        S9[eta-computation]
        S10[carrier-selection]
        S11[returns-support]
    end
    subgraph ASYNC["Primary Asynchronous (15)"]
        direction LR
        A1[campaign-intelligence]
        A2[segmentation-personalization]
        A3[alerts-triggers]
        A4[health-check]
        A5[jit-replenishment]
        A6[route-issue-detection]
        A7[acp-transformation]
        A8[assortment-optimization]
        A9[consistency-validation]
        A10[normalization-classification]
        A11[search-enrichment]
        A12[truth-ingestion]
        A13[truth-enrichment]
        A14[truth-hitl]
        A15[truth-export]
    end

    UI[Frontend / CRUD] -->|REST invoke| SYNC
    EH[(Event Hubs)] -->|domain events| ASYNC

    style SYNC fill:#e8f5e9,stroke:#4caf50,color:#000
    style ASYNC fill:#e3f2fd,stroke:#1976d2,color:#000
```

### Monitoring and Alerting Differentiation

| Alert Type | Sync Agents | Async Agents |
|------------|-------------|--------------|
| **P95 invoke latency > 8 s** | ⚠️ Critical alert (P1) | ℹ️ Informational only — not an SLA violation |
| **Streaming first-token > 3 s** | ⚠️ Warning alert (P2) | N/A — async agents do not stream |
| **Consumer lag > 10 min** | N/A — sync agents do not consume Event Hubs primarily | ⚠️ Critical alert (P1) |
| **Throughput < 100 events/min** | N/A | ⚠️ Warning alert (P2) |
| **Event loss / dead-letter > 0** | N/A | 🚨 Critical alert (P1) — data loss |
| **Health endpoint > 2 s** | ⚠️ Warning (both classes) | ⚠️ Warning (both classes) |

### Consequences

#### Positive

1. **Eliminates false-positive alerts** for async agents called synchronously during testing.
2. **Surfaces real SLA violations** for user-facing agents (e.g., [issue #927](https://github.com/Azure-Samples/holiday-peak-hub/issues/927)).
3. **Enables differentiated dashboards** in the UI agent-activity page using `primaryMode` metadata.
4. **Aligns monitoring Bicep module** alert rules with actual user impact.

#### Negative

1. Classification adds a governance overhead — new agents must declare their primary mode.
2. Agents with mixed usage (sync invoke + async event processing) require explicit documentation of which SLA class applies to which path.

#### Impact on Existing Artifacts

| Artifact | Change |
|----------|--------|
| E2E validation skill (`.github/skills/agent-e2e-validation/SKILL.md`) | Must check `primaryMode` before applying invoke latency SLA; async agents validate throughput instead |
| UI agent profiles (`apps/ui/lib/agents/profiles.ts`) | Add `primaryMode: 'sync' \| 'async'` field per agent profile |
| Monitoring Bicep (`.infra/modules/monitoring/monitoring.bicep`) | Split alert rules by class; suppress latency alerts for async agents |
| ADR-019 resilience patterns | Circuit breakers apply different timeout budgets per class (see [ADR-019](adr-019-enterprise-resilience-patterns.md)) |
| ADR-006 saga choreography | Async agents are the primary participants in saga flows (see [ADR-006](adr-006-saga-choreography.md)) |

### Cross-References

- [ADR-006: Saga Choreography](adr-006-saga-choreography.md) — async agents as primary saga participants
- [ADR-019: Enterprise Resilience Patterns](adr-019-enterprise-resilience-patterns.md) — timeout and circuit-breaker budgets per class
- [Issue #927](https://github.com/Azure-Samples/holiday-peak-hub/issues/927) — confirmed sync SLA violation for `ecommerce-cart-intelligence`
- [Issue #936](https://github.com/Azure-Samples/holiday-peak-hub/issues/936) — this classification proposal

---

## Migration Notes

This ADR consolidates three formerly separate decisions:
- MCP Internal Communication Policy (original)
- Agent Isolation Policy — prohibited coupling, enforcement evidence, approved paths
- Async Communication Contract — Observer pattern, `TopicSubject`, `AgentAsyncContract`
- Agent Mode Classification and Differentiated SLA Policy (Part 4, added 2026-04-29)

The isolation and async-contract decisions are now superseded and absorbed into this ADR.
