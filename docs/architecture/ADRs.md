# Architecture Decision Records (ADRs)

This document indexes all architectural decisions for the Holiday Peak Hub accelerator.

## ADR Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-001](adrs/adr-001-python-3.13.md) | Python 3.13 as Primary Language | Accepted | 2024-12 |
| [ADR-002](adrs/adr-002-azure-services.md) | Azure Service Stack Selection | Accepted | 2024-12 |
| [ADR-003](adrs/adr-003-adapter-pattern.md) | Adapter Pattern, Boundaries, and Connector Registry | Accepted (Revised) | 2024-12 |
| [ADR-004](adrs/adr-004-fastapi-mcp.md) | FastAPI with Dual REST + MCP Exposition | Accepted (Revised) | 2024-12 |
| [ADR-005](adrs/adr-005-agent-framework.md) | Microsoft Agent Framework + Foundry | Accepted | 2024-12 |
| [ADR-006](adrs/adr-006-saga-choreography.md) | SAGA Choreography with Event Hubs | Accepted | 2024-12 |
| [ADR-007](adrs/adr-007-memory-tiers.md) | Memory Architecture and Isolation Strategy | Accepted (Revised) | 2024-12 |
| [ADR-008](adrs/adr-008-aks-deployment.md) | AKS with Helm, KEDA, and Canary Deployments | Accepted | 2024-12 |
| [ADR-009](adrs/adr-009-acp-catalog-search.md) | ACP Alignment for Ecommerce Catalog Search | Accepted | 2026-01 |
| [ADR-010](adrs/adr-010-model-routing.md) | SLM-First Model Routing Strategy | Accepted | 2026-01 |
| [ADR-011](adrs/adr-011-nextjs-app-router.md) | Next.js 15 with App Router for Frontend | Accepted | 2026-01 |
| [ADR-012](adrs/adr-012-atomic-design-system.md) | Atomic Design System for Component Library | Accepted | 2026-01 |
| [ADR-013](adrs/adr-013-ag-ui-protocol.md) | AG-UI Protocol Integration | Accepted | 2026-01 |
| [ADR-014](adrs/adr-014-acp-frontend.md) | Agentic Commerce Protocol (ACP) Frontend Integration | Accepted | 2026-01 |
| [ADR-015](adrs/adr-015-authentication-rbac.md) | Authentication and Role-Based Access Control | Accepted | 2026-01 |
| [ADR-016](adrs/adr-016-api-client-architecture.md) | API Client Architecture | Accepted | 2026-01 |
| [ADR-017](adrs/adr-017-deployment-strategy.md) | Deployment Strategy — azd Provisioning + Flux CD GitOps | Accepted (Revised) | 2026-02 |
| [ADR-018](adrs/adr-018-branch-naming-convention.md) | Git Branch Naming Convention | Accepted | 2026-03 |
| [ADR-019](adrs/adr-019-enterprise-resilience-patterns.md) | Enterprise Resilience Patterns | Accepted | 2026-03 |
| [ADR-020](adrs/adr-020-product-truth-layer.md) | Product Truth Layer Architecture | Accepted | 2026-03 |
| [ADR-021](adrs/adr-021-apim-agc-edge.md) | APIM + Application Gateway for Containers as Canonical AKS Edge | Accepted | 2026-03 |
| [ADR-022](adrs/adr-022-dam-image-analysis-enrichment-pipeline-boundary.md) | DAM Image Analysis as an Enrichment Pipeline within Truth Boundaries | Accepted | 2026-03 |
| [ADR-023](adrs/adr-023-search-enrichment-bounded-context.md) | Search Enrichment as an Isolated Bounded Context | Accepted | 2026-03 |
| [ADR-024](adrs/adr-024-agent-communication-policy.md) | Agent Communication Policy, Isolation, and Async Contracts | Accepted (Revised) | 2026-03 |
| [ADR-025](adrs/adr-025-self-healing-boundaries.md) | Self-Healing Boundaries, Risk Tiers, and Prohibited Actions | Accepted | 2026-04 |
| [ADR-026](adrs/adr-026-namespace-isolation-strategy.md) | Namespace Isolation Strategy (CRUD vs Agent Namespaces) | Accepted | 2026-04 |
| [ADR-027](adrs/adr-027-api-center-apim-mcp-strategy.md) | API Center + APIM MCP Strategy | Accepted | 2026-04 |

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
- FastAPI for high-throughput APIs ([ADR-004](adrs/adr-004-fastapi-mcp.md))
- Bicep for declarative infrastructure ([ADR-002](adrs/adr-002-azure-services.md))
- Next.js 15 with App Router for frontend ([ADR-011](adrs/adr-011-nextjs-app-router.md))
- TanStack Query for data fetching ([ADR-016](adrs/adr-016-api-client-architecture.md))

### Frontend
- Next.js 15 with App Router ([ADR-011](adrs/adr-011-nextjs-app-router.md))
- Atomic Design System for components ([ADR-012](adrs/adr-012-atomic-design-system.md))
- AG-UI Protocol for agent interoperability ([ADR-013](adrs/adr-013-ag-ui-protocol.md))
- ACP frontend compliance for product data ([ADR-014](adrs/adr-014-acp-frontend.md))
- JWT-based authentication with RBAC ([ADR-015](adrs/adr-015-authentication-rbac.md))
- Layered API client architecture ([ADR-016](adrs/adr-016-api-client-architecture.md))

### Architecture Patterns
- Adapter pattern with boundary rules and connector registry ([ADR-003](adrs/adr-003-adapter-pattern.md))
- SAGA choreography for decoupled service coordination ([ADR-006](adrs/adr-006-saga-choreography.md))

### Agent & AI
- Microsoft Agent Framework with Azure AI Foundry ([ADR-005](adrs/adr-005-agent-framework.md))
- SLM-first routing for cost optimization ([ADR-010](adrs/adr-010-model-routing.md))

### Memory & State
- Memory architecture: three-tier, builder, partitioning, and namespace isolation ([ADR-007](adrs/adr-007-memory-tiers.md))
- Microsoft Agent Framework for standardization ([ADR-005](adrs/adr-005-agent-framework.md))
- FastAPI with dual REST + MCP exposition ([ADR-004](adrs/adr-004-fastapi-mcp.md))

### Infrastructure & Deployment
- Azure-native services for enterprise readiness ([ADR-002](adrs/adr-002-azure-services.md))
- Three-tier memory for latency/cost optimization ([ADR-007](adrs/adr-007-memory-tiers.md))
- AKS with KEDA for elastic scaling, 3 node pools ([ADR-008](adrs/adr-008-aks-deployment.md))
- Deployment strategy: azd provisioning + Flux CD GitOps ([ADR-017](adrs/adr-017-deployment-strategy.md))
- APIM + AGC as the canonical AKS edge ([ADR-021](adrs/adr-021-apim-agc-edge.md))
- Namespace isolation for CRUD and agent workloads ([ADR-026](adrs/adr-026-namespace-isolation-strategy.md))

### Governance
- Git branch naming convention ([ADR-018](adrs/adr-018-branch-naming-convention.md))
- Agent communication policy, isolation, and async contracts ([ADR-024](adrs/adr-024-agent-communication-policy.md))
- Self-healing boundaries, risk tiers, and prohibited actions ([ADR-025](adrs/adr-025-self-healing-boundaries.md))
- API Center + APIM MCP strategy for API governance ([ADR-027](adrs/adr-027-api-center-apim-mcp-strategy.md))

### Enterprise Integration
- Enterprise resilience patterns (Circuit Breaker, Bulkhead, Rate Limiter) ([ADR-019](adrs/adr-019-enterprise-resilience-patterns.md))
- Connector registry integrated into adapter pattern ([ADR-003](adrs/adr-003-adapter-pattern.md))

### Product Data Governance
- Product Truth Layer for AI-enriched data validation ([ADR-020](adrs/adr-020-product-truth-layer.md))
- Human-in-the-loop review workflow ([ADR-020](adrs/adr-020-product-truth-layer.md))
- PIM writeback for approved changes ([ADR-020](adrs/adr-020-product-truth-layer.md))

## References

- [Architecture Overview](architecture.md)
- [Components Documentation](components.md)
- [Business Summary](business-summary.md)
