# Architecture

<!-- Last Updated: 2026-04-30 -->

Welcome to the Holiday Peak Hub architecture documentation. This section covers system design, decision records, component specifications, operational playbooks, and test plans.

## Sections

| Section | Description |
|---------|-------------|
| [Architecture Overview](architecture.md) | Primary technical architecture narrative |
| [Solution Architecture Overview](solution-architecture-overview.md) | C4 diagrams, domain agent map, deployment topology |
| [Solution Architecture Diagrams](solution-architecture-diagrams.md) | Per-domain Mermaid diagrams |
| [ADRs](ADRs.md) | Architecture Decision Records index |
| [Components](components.md) | Library, app, and frontend components |
| [Diagrams](diagrams/README.md) | C4 diagrams and sequence flows |
| [Playbooks](playbooks/README.md) | Incident response and operational runbooks |
| [Test Plans](test-plans/README.md) | Load and resilience test plans |

## Key Decisions

The platform is built on 27 Architecture Decision Records spanning:

- **Infrastructure**: AKS deployment, namespace isolation, Flux CD GitOps, APIM + AGC edge (ADR-008, ADR-017, ADR-021, ADR-026)
- **Application**: Adapter pattern, agent framework, memory tiers, model routing (ADR-003, ADR-005, ADR-007, ADR-010)
- **Frontend**: Next.js App Router, atomic design, AG-UI protocol (ADR-011, ADR-012, ADR-013)
- **Security**: Authentication RBAC, self-healing boundaries, MCP communication policy (ADR-015, ADR-024, ADR-025)
- **Data**: Memory partitioning, Cosmos DB, product truth layer, search enrichment (ADR-007, ADR-020, ADR-023)
- **Governance**: API Center + APIM MCP strategy, branch naming (ADR-018, ADR-027)

See the full [ADR index](ADRs.md) for details.
