# ADR-011: ACP Alignment for Ecommerce Catalog Search

**Status**: Accepted  
**Date**: 2026-01  
**Deciders**: Architecture Team

## Context

The ecommerce catalog search service needs a standard, agent-friendly product schema that can be used consistently across:

- Search results returned to agents
- Downstream enrichment and recommendation tools
- MCP tool responses for partner integrations

A proprietary schema would increase integration effort and reduce interoperability with agent ecosystems.

## Decision

Adopt **Agentic Commerce Protocol (ACP)** field mapping for catalog search responses and MCP tools.

### Scope
- Catalog search responses return ACP-compatible product payloads.
- Product detail lookups expose ACP fields for consistency.
- ACP mapping is applied in adapters to keep agent logic consistent.

### MCP Tool Surface
- `catalog.search` for ACP result sets
- `catalog.product` for ACP single product retrieval

## Consequences

### Positive
- **Interoperability**: Standard field names across agent workflows
- **Consistency**: Search, detail, and enrichment align on one schema
- **Partner readiness**: Easier integration with external tooling

### Negative
- **Mapping overhead**: Requires adapter mapping and validation
- **Schema constraints**: ACP-required fields must be maintained

## Alternatives Considered

### Proprietary Product Schema
- **Pros**: Maximum flexibility
- **Cons**: Higher integration cost and fragmented contracts

### OpenAPI-Only Contracts
- **Pros**: Strong typing
- **Cons**: Less semantic alignment for agent ecosystems

## Related ADRs
- [ADR-010: REST + MCP Exposition](adr-010-rest-and-mcp-exposition.md)
- [ADR-003: Adapter Pattern](adr-003-adapter-pattern.md)
