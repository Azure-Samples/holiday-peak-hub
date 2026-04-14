# Architecture

Welcome to the Holiday Peak Hub architecture documentation. This section covers system design, decision records, component specifications, operational playbooks, and test plans.

## Sections

| Section | Description |
|---------|-------------|
| [Architecture Overview](architecture.md) | Primary technical architecture narrative |
| [ADRs](ADRs.md) | Architecture Decision Records index |
| [Components](components.md) | Library, app, and frontend components |
| [Diagrams](diagrams/README.md) | C4 diagrams and sequence flows |
| [Playbooks](playbooks/README.md) | Incident response and operational runbooks |
| [Test Plans](test-plans/README.md) | Load and resilience test plans |

## Key Decisions

The platform is built on 35 Architecture Decision Records spanning:

- **Infrastructure**: AKS deployment, namespace isolation, Flux CD, APIM/AGC edge
- **Application**: Adapter pattern, agent framework, memory tiers, model routing
- **Frontend**: Next.js App Router, atomic design, AG-UI protocol
- **Security**: Authentication RBAC, self-healing boundaries, MCP communication policy
- **Data**: Memory partitioning, Cosmos DB, product truth layer

See the full [ADR index](ADRs.md) for details.
