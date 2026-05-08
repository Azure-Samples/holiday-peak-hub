# ADR-030: MCP-Only Agent-to-Agent Communication with Hop Counter

**Status**: Accepted
**Date**: 2026-05-08
**Deciders**: Architecture Team, Ricardo Cataldi
**Tags**: mcp, agent-communication, isolation, observability
**References**: [ADR-004](adr-004-fastapi-mcp.md), [ADR-024](adr-024-agent-communication-policy.md), [ADR-026](adr-026-namespace-isolation-strategy.md), [ADR-027](adr-027-api-center-apim-mcp-strategy.md)

## Context

The platform has a clear communication-channel matrix (ADR-024) but the agent-to-agent (A2A) invariant has historically been enforced by convention, not by code. Direct HTTP calls between agent services are technically possible because pods can reach peer services through Kubernetes DNS or APIM. Convention says "agents talk to agents only via MCP," but nothing fails the build or the deploy when convention drifts.

R1 (the Microsoft Agent Framework cutover) is the right moment to **pin the invariant in the framework** and **enforce it in CI**. Two additions are required:

1. **MCP-only A2A** — codify the invariant on the framework seam (`FastAPIMCPServer`) and add a CI lint rejecting any new direct A2A HTTP call.
2. **Hop counter** — add a header that rides on every MCP call, increments on each relay, hard-caps at a configurable bound. This bounds runaway agent chains and detects loops.

## Decision

### 1. Pinned Communication Channel Matrix

| Caller | Callee | Channel |
|---|---|---|
| Frontend | CRUD | HTTPS REST via APIM |
| Frontend | Agent | HTTPS REST via APIM |
| CRUD | Agent | HTTPS REST (with circuit breaker; for fast enrichment) |
| Agent | CRUD | HTTPS REST (transactional reads/writes; cross-namespace per ADR-026) |
| **Agent** | **Agent** | **MCP only (with `x-mcp-hop` header)** |
| Agent | Foundry / AI Search | HTTPS REST (model invocation) |
| Agent | External connector | HTTPS REST or vendor SDK |
| Agent | Event Hubs / Service Bus | AMQP via SDK |

This refines ADR-024 by elevating the A2A row to **enforced**.

### 2. Hop Counter Contract

- **Header name**: `x-mcp-hop` (lowercase). Optional inbound — absent means `0`.
- **Type**: integer in `[0, 5]`. Out-of-range returns `400`. Hard cap at `5`; configurable on `FastAPIMCPServer` constructor (`max_hops` parameter).
- **Propagation**: `FastAPIMCPServer.invoke_tool()` reads inbound, increments by `1` before any outbound MCP call originating from the request's correlation context, restores on exit.
- **Overflow**: an outbound call from a server already at the cap returns `429` with body `{"error": "mcp.hop_overflow", "hop": 5, "cap": 5}` and emits `mcp.hop_overflow=true` as a span attribute.
- **Correlation**: hop counter rides with the existing trace context (W3C `traceparent`). The combination `(trace_id, mcp.hop)` is sufficient to reconstruct any agent chain end-to-end.

### 3. Framework Enforcement (lib seam)

`lib/holiday_peak_lib/mcp/` (the `FastAPIMCPServer` seam) MUST:

- Read the `x-mcp-hop` header on every inbound MCP request; validate; store on the request scope.
- Increment by `1` on every outbound MCP call to a peer agent issued during the same request.
- Refuse outbound MCP calls when the inbound was already at `max_hops`; return `429` with the structured body.
- Emit `mcp.hop` on every MCP request span (mandatory per ADR-031).

Contract tests in `lib/tests/test_mcp_hop_counter.py` MUST cover:

- Inbound `x-mcp-hop=0` → outbound MCP call carries `x-mcp-hop=1`.
- Inbound `x-mcp-hop=5` → any outbound MCP call returns `429 mcp.hop_overflow` and logs the event.
- Inbound malformed header → `400`.

### 4. CI Lint — No A2A HTTP

A new CI script `scripts/ci/lint_no_a2a_http.py` walks `apps/<service>/src/**` and fails the build when:

- An agent service module makes an HTTP call (`httpx`, `aiohttp`, `requests`) whose URL or hostname matches a peer agent service name from `apps/`.
- Allowed targets remain: `crud-service`, AI Foundry endpoints, AI Search, external connector hostnames, Event Hubs / Service Bus.

A per-service allowlist file `apps/<service>/.a2a-allow.txt` exists for legitimate exceptions (today: empty for every service). Reviewer approval required for any allowlist addition.

### 5. Activation Sequence

The lint gate is enabled **per service** as that service completes its R1 MAF cutover (tracked in the R1 epic). This avoids forcing simultaneous remediation across 26 services. By the end of R1, all services pass the lint with empty allowlists.

## Consequences

### Positive

- Convention promoted to contract: the framework refuses to participate in direct A2A HTTP calls.
- Hop counter bounds runaway chains and surfaces them in tracing within milliseconds.
- Existing patterns preserved — REST surfaces remain unchanged for UI / CRUD / external clients.
- Loop detection becomes trivial: `(trace_id, mcp.hop)` reconstructs any chain.

### Negative

- One additional header on every MCP request (sub-microsecond overhead).
- Service mesh-style enforcement is still convention at the network layer; this ADR enforces at the framework + CI layers, not via NetworkPolicy.
- Allowlist creates a gradual-adoption escape hatch — must be policed by review.

### Risks

| Risk | Mitigation |
|---|---|
| Hop cap of 5 too low for a legitimate use case. | `max_hops` configurable; raising it requires an ADR amendment, not 26 service edits. |
| Lint script produces false positives on legitimate non-A2A HTTP calls (Foundry, AI Search, connectors). | Per-service allowlist; reviewer approval gate; default-deny posture. |
| Existing services already make A2A HTTP calls. | Lint enabled per service as R1 cutover lands for that service. Coordinated via R1 epic. |
| Vendor MCP transports drop custom headers. | Standard MCP transports (stdio, HTTP, SSE) preserve arbitrary headers; verified at design time. Span-based fallback (refuse calls without `mcp.hop` span attribute) defends future transports. |
| Performance overhead. | Header read + increment + log on overflow is sub-microsecond; below P99 noise. |

## Alternatives Considered

### Alternative A — Service mesh (Linkerd / Istio) with a deny-by-default A2A policy

Rejected for now. AGC handles ingress and namespace network policies handle east-west posture (ADR-026). Adding a mesh introduces a second control plane and operational surface area without delivering meaningfully tighter enforcement at this stage. Revisit if multi-tenant network isolation becomes a hard requirement.

### Alternative B — REST-based A2A with a contract registry

Rejected. REST A2A would duplicate every MCP tool as a REST endpoint, doubling the API surface and breaking the dual REST + MCP separation pinned in ADR-004.

### Alternative C — gRPC for A2A

Rejected. Adds a third RPC style to the platform with no clear benefit over MCP, which already provides the agent-to-agent semantics.

## Implementation

| Component | File / Location | Change |
|---|---|---|
| ADR | `docs/architecture/adrs/adr-030-mcp-only-a2a.md` | This file |
| Framework seam | `lib/holiday_peak_lib/mcp/server.py` | Read/validate/propagate `x-mcp-hop`; emit `mcp.hop` span attribute |
| Contract test | `lib/tests/test_mcp_hop_counter.py` | New — hop semantics + overflow + malformed |
| CI lint | `scripts/ci/lint_no_a2a_http.py` | New — AST/regex check across `apps/*/src/**` |
| Allowlists | `apps/<service>/.a2a-allow.txt` | New — empty by default |
| Framework docs | `lib/README.md` | Document the contract and example usage |
| Activation | R1 cutover epic | Per-service lint enable as services migrate |

## Verification

- **Contract tests** cover increment, overflow, malformed header.
- **Integration**: a multi-hop scenario in `tests/e2e/` (e.g., `enrichment-agent → product-detail-agent → search-agent`) emits one trace with three correlated spans, each with `mcp.hop=0,1,2`.
- **Lint regression**: a synthetic peer-agent HTTP call in a test fixture causes `lint_no_a2a_http.py` to exit non-zero.
- **Loop detection**: a deliberate cyclical chain in a test fixture surfaces `mcp.hop_overflow=true` within hop 5.

## Pattern References

- **Hop Counter / Pipes and Filters** — Enterprise Integration Patterns (Hohpe & Woolf).
- **Bulkhead** — microservices.io. The hop cap is a bulkhead against runaway agent chains.
- **Circuit Breaker** — microservices.io. The `429` overflow short-circuits the chain.

## References

- [W3C Trace Context](https://www.w3.org/TR/trace-context/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [ADR-004 — FastAPI with Dual REST + MCP Exposition](adr-004-fastapi-mcp.md)
- [ADR-024 — Agent Communication Policy](adr-024-agent-communication-policy.md)
- [ADR-026 — Namespace Isolation Strategy](adr-026-namespace-isolation-strategy.md)
- [ADR-031 — OTEL Span Attributes Contract for Retail Agents](adr-031-otel-span-attributes-contract.md)
