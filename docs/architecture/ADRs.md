# Architecture Decision Records (ADRs)

This document indexes all architectural decisions for the Holiday Peak Hub accelerator.

## ADR Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-001](adrs/adr-001-python-3.13.md) | Python 3.13 as Primary Language | Accepted | 2024-12 |
| [ADR-002](adrs/adr-002-azure-services.md) | Azure Service Stack Selection | Accepted | 2024-12 |
| [ADR-003](adrs/adr-003-adapter-pattern.md) | Adapter Pattern for Retail Integrations | Accepted | 2024-12 |
| [ADR-004](adrs/adr-004-builder-pattern-memory.md) | Builder Pattern for Agent Memory Configuration | Accepted | 2024-12 |
| [ADR-005](adrs/adr-005-fastapi-mcp.md) | FastAPI + MCP for API Exposition | Accepted | 2024-12 |
| [ADR-006](adrs/adr-006-agent-framework.md) | Microsoft Agent Framework + Foundry | Accepted | 2024-12 |
| [ADR-007](adrs/adr-007-saga-choreography.md) | SAGA Choreography with Event Hubs | Accepted | 2024-12 |
| [ADR-008](adrs/adr-008-memory-tiers.md) | Three-Tier Memory Architecture | Accepted | 2024-12 |
| [ADR-009](adrs/adr-009-aks-deployment.md) | AKS with Helm, KEDA, and Canary Deployments | Accepted | 2024-12 |
| [ADR-010](adrs/adr-010-rest-and-mcp-exposition.md) | Dual Exposition: REST + MCP Servers | Accepted | 2024-12 |

## How to Use ADRs

Each ADR follows a standard template:
- **Status**: Proposed, Accepted, Deprecated, Superseded
- **Context**: Business/technical drivers
- **Decision**: What was chosen and why
- **Consequences**: Trade-offs, benefits, and risks
- **Alternatives Considered**: Other options evaluated

## ADR Process

1. **Propose**: Create new ADR markdown file in `adrs/` folder
2. **Review**: Discuss with architecture team and stakeholders
3. **Decide**: Mark status as Accepted or Rejected
4. **Document**: Update this index and link from relevant component docs
5. **Revisit**: Mark as Superseded if decision changes; create new ADR for replacement

## Key Decision Themes

### Language & Tooling
- Python 3.13 for async/performance improvements ([ADR-001](adrs/adr-001-python-3.13.md))
- FastAPI for high-throughput APIs ([ADR-005](adrs/adr-005-fastapi-mcp.md))
- Bicep for declarative infrastructure ([ADR-002](adrs/adr-002-azure-services.md))

### Architecture Patterns
- Adapter pattern for pluggable retail system integrations ([ADR-003](adrs/adr-003-adapter-pattern.md))
- Builder pattern for flexible memory tier configuration ([ADR-004](adrs/adr-004-builder-pattern-memory.md))
- SAGA choreography for decoupled service coordination ([ADR-007](adrs/adr-007-saga-choreography.md))

### Agent & AI
- Microsoft Agent Framework for standardization ([ADR-006](adrs/adr-006-agent-framework.md))
- MCP servers for tool exposure ([ADR-010](adrs/adr-010-rest-and-mcp-exposition.md))

### Infrastructure
- Azure-native services for enterprise readiness ([ADR-002](adrs/adr-002-azure-services.md))
- Three-tier memory for latency/cost optimization ([ADR-008](adrs/adr-008-memory-tiers.md))
- AKS with KEDA for elastic scaling ([ADR-009](adrs/adr-009-aks-deployment.md))

## References

- [Architecture Overview](architecture.md)
- [Components Documentation](components.md)
- [Business Summary](business-summary.md)
