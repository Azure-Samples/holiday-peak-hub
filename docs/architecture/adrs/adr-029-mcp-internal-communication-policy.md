# ADR-029: MCP Internal Communication Policy Addendum

## Status

Accepted

## Date

2026-03-18

## Context

The platform uses dual exposition (REST + MCP) as defined in [ADR-010](adr-010-rest-and-mcp-exposition.md). As agent services scaled, internal service-to-service communication paths diverged, creating architecture drift risk and inconsistent rollout controls.

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
    CRUD -->|REST (approved)| AGENTA
    AGENTA -->|MCP Tools| AGENTB[Agent Service B]
    AGENTA -->|Events| EH[(Event Hubs)]
    AGENTB -->|Events| EH

    AGENTA -. prohibited .-> DBB[(Service B DB)]
    AGENTA -. prohibited .-> PRIVB[Service B Private Endpoint]
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

- [ADR-005](adr-005-fastapi-mcp.md)
- [ADR-010](adr-010-rest-and-mcp-exposition.md)
- [ADR-012](adr-012-adapter-boundaries.md)
- [ADR-023](adr-023-enterprise-resilience-patterns.md)
- [Architecture Overview](../architecture.md)
