# ADR-022: DAM Image Analysis as an Enrichment Pipeline within Truth Boundaries

## Status
Accepted

## Date
2026-03-19

## Context

Issue #336 identifies DAM image analysis as a foundational dependency for the enrichment pipeline. Downstream services are blocked until image-derived signals (for example tags, visual attributes, quality indicators, and moderation hints) are produced in a stable and governable way.

The architecture must preserve bounded-context integrity:

1. DAM image analysis must operate as an enrichment capability that feeds the Truth Layer lifecycle.
2. Ownership of search-domain concerns (query indexing, ranking policy, search relevance tuning) must remain outside this decision.
3. Existing integration standards must be reused to avoid introducing a parallel ingestion model.

Constraints and drivers:

- Throughput and latency must support enrichment workflows without blocking core transactional paths.
- Cost must remain controllable as image-analysis volume scales.
- Failures in DAM or model dependencies must degrade gracefully rather than halting the full enrichment pipeline.
- The decision must align with existing ADRs for adapters, choreography, exposition, model routing, connector governance, and Truth ownership.

## Decision

Adopt an Adapter + Pipeline architecture for DAM image analysis, with graceful degradation and explicit resilience controls.

### 1) DAM Adapter as the Integration Boundary

Implement DAM access behind an adapter contract, consistent with the platform adapter pattern.

- Adapter responsibility: fetch/normalize asset metadata, image URIs, and provider-specific diagnostics.
- Adapter non-responsibility: search indexing strategy, search relevance logic, and search-domain ownership.
- Adapter outputs are canonical enrichment inputs for Truth workflows.

### 2) Event-Driven Pipeline for Analysis Execution

Execute image analysis as an asynchronous pipeline stage coordinated by choreography.

- Triggered from enrichment flow events.
- Produces image analysis artifacts and confidence metadata for Truth records.
- Exposes operational status via REST for service consumers and MCP for agent-to-agent usage where appropriate.

### 3) Graceful Degradation and Circuit Breaker Policy

Apply resilience controls at external dependency boundaries (DAM APIs and image-analysis inference dependencies):

- Circuit breaker protects upstream systems and prevents retry storms.
- Timeouts and bounded retries are mandatory.
- On failure/open-circuit, pipeline degrades to partial enrichment:
  - Preserve existing source/product truth data.
  - Mark image-analysis fields as unavailable or stale.
  - Emit structured degradation events/metrics for recovery processing.

Degradation is an accepted runtime mode; full-pipeline failure is not.

### 4) Truth Layer Ownership Rules

Image-analysis results are enrichment artifacts under Truth Layer governance.

- Truth remains the authoritative boundary for reviewed/approved product data.
- DAM analysis contributes candidate enrichment data, not independent published truth.
- Any human review or publication workflow continues to follow Truth Layer controls.

## Latency and Cost Trade-offs

| Option | Latency | Cost | Reliability Impact | Decision |
|---|---|---|---|---|
| Synchronous image analysis in request path | Lowest freshness delay for caller, but increases end-user response time and tail latency | Highest compute burst cost and potential overprovisioning | Tight coupling; external failures directly impact user path | Rejected |
| Asynchronous pipeline analysis (selected) | Eventual consistency; enrichment available after pipeline completion | Better cost control via batching/scaling policies and model routing strategy | Fault isolation with retries, circuit breaker, and degradation | Accepted |
| Offline batch-only analysis | Lowest immediate load on runtime path | Potentially lowest unit cost at scale | Stale enrichment for fast-changing catalogs | Rejected as primary mode |

Rationale: asynchronous pipeline best satisfies modifiability, resilience, and cost control while keeping transactional/user paths protected.

## Acceptance Implications

To be considered implemented against this ADR:

- DAM image analysis is integrated via adapter boundary only (no direct provider coupling in domain services).
- Pipeline stage is asynchronous and event-driven, with observable success/failure/degradation states.
- Circuit breaker + timeout + retry + fallback/degradation behavior is implemented and validated.
- Truth Layer remains data-ownership boundary for approved product outcomes.
- No search-domain ownership is introduced by DAM analysis components.
- Documentation and service contracts explicitly describe partial-enrichment behavior.

## Consequences

### Positive

1. Unblocks downstream enrichment work with a clear architecture contract.
2. Preserves bounded contexts and avoids search-domain leakage.
3. Improves resilience through fault isolation and graceful degradation.
4. Controls scaling cost by avoiding synchronous coupling and enabling routing policies.

### Negative

1. Introduces eventual-consistency behavior for image-derived attributes.
2. Requires operational maturity in event monitoring, retry/dead-letter handling, and degraded-state observability.
3. Adds complexity to consumer expectations because enrichment completeness can vary during incidents.

## Related ADRs

- [ADR-003](adr-003-adapter-pattern.md) — Adapter Pattern for Retail Integrations
- [ADR-006](adr-006-saga-choreography.md) — SAGA Choreography with Event Hubs
- [ADR-004](adr-004-fastapi-mcp.md) — FastAPI with Dual REST + MCP Exposition
- [ADR-009](adr-009-acp-catalog-search.md) — ACP Alignment for Ecommerce Catalog Search
- [ADR-010](adr-010-model-routing.md) — SLM-First Model Routing Strategy
- [ADR-020](adr-020-product-truth-layer.md) — Product Truth Layer Architecture

## References

- [Architecture Overview](../architecture.md)
- [ADRs Index](../ADRs.md)