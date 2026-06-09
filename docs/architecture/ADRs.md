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
| [ADR-011](adrs/adr-011-nextjs-app-router.md) | Next.js 15 with App Router for Frontend | Accepted (Revised by ADR-033) | 2026-01 |
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
| [ADR-028](adrs/adr-028-continuous-agent-evaluation.md) | Continuous Agent Evaluation Engine | Accepted | 2026-05 |
| [ADR-029](adrs/adr-029-agc-weighted-canary-policy.md) | AGC Weighted Canary Policy with Automatic Rollback | Accepted | 2026-05 |
| [ADR-030](adrs/adr-030-mcp-only-a2a.md) | MCP-Only Agent-to-Agent Communication with Hop Counter | Accepted | 2026-05 |
| [ADR-031](adrs/adr-031-otel-span-attributes-contract.md) | OTEL Span Attributes Contract for Retail Agents | Accepted | 2026-05 |
| [ADR-032](adrs/adr-032-three-tier-memory-contract.md) | Three-Tier Memory Contract Pinning (Hot / Warm / Cold) | Accepted (Refines ADR-007) | 2026-05 |
| [ADR-033](adrs/adr-033-ui-modular-monolith-on-swa.md) | UI as a Modular Monolith on Static Web Apps (Path 2) | Accepted | 2026-05 |
| [ADR-034](adrs/adr-034-audience-segmented-ia.md) | Audience-Segmented Information Architecture for the UI | Accepted (Extends ADR-033) | 2026-05 |
| [ADR-035](adrs/adr-035-ui-design-system.md) | UI Design System Contract: Tokens, Components, CSS, Quality Gates | Accepted (Extends ADR-033 + ADR-034) | 2026-05 |
| [ADR-036](adrs/adr-036-foundry-agent-surface-taxonomy.md) | Foundry Agent Surface Taxonomy | Accepted | 2026-05 |

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
- Continuous agent evaluation with Foundry SDK and local fallback ([ADR-028](adrs/adr-028-continuous-agent-evaluation.md))
- Foundry Hosted/Custom Agent exposure taxonomy ([ADR-036](adrs/adr-036-foundry-agent-surface-taxonomy.md))

#### Evaluation Engine Cross-References (Amended: 2026-04)

ADR-028 is the source of truth for the continuous evaluation engine. Its accepted contract amends and depends on these current ADRs:

| Concern | Current ADR | Evaluation relationship |
|---------|-------------|-------------------------|
| Framework runtime and Foundry/MAF integration | [ADR-005](adrs/adr-005-agent-framework.md) | Evaluation lifecycle uses the direct-model MAF runtime and Foundry/local evaluator strategies without restoring portal-agent runtime |
| SLM/LLM routing quality governance | [ADR-010](adrs/adr-010-model-routing.md) | Datasets validate `expected_model_tier` and evaluate SLM and LLM paths independently |
| CI/CD and deployment evidence | [ADR-017](adrs/adr-017-deployment-strategy.md) | `.github/workflows/eval-advisory.yml` (`agent-eval-advisory`) publishes advisory evaluation artifacts for PR review |
| Async evaluation evidence channel | [ADR-024](adrs/adr-024-agent-communication-policy.md) | `agent-evaluation-results` uses `EvaluationResultEvent` without changing MCP-only A2A rules |
| Quality-drift escalation | [ADR-025](adrs/adr-025-self-healing-boundaries.md) | `SurfaceType.EVALUATION` and `QUALITY_DRIFT` incidents are T3 manual-only |
| Saga/event compatibility | [ADR-006](adrs/adr-006-saga-choreography.md) | Event Hub topic evolution rules apply to evaluation result events |

Stale issue references to non-existent ADR-037 or ADR-038 are reconciled to the current accepted ADRs above; this index must not cite ADR-038 as an existing decision.

### Memory & State
- Memory architecture: three-tier, builder, partitioning, and namespace isolation ([ADR-007](adrs/adr-007-memory-tiers.md))
- Microsoft Agent Framework for standardization ([ADR-005](adrs/adr-005-agent-framework.md))
- FastAPI with dual REST + MCP exposition ([ADR-004](adrs/adr-004-fastapi-mcp.md))

### Infrastructure & Deployment
- Azure-native services for enterprise readiness ([ADR-002](adrs/adr-002-azure-services.md))
- Three-tier memory for latency/cost optimization ([ADR-007](adrs/adr-007-memory-tiers.md))
- Three-tier memory contract pinning ([ADR-032](adrs/adr-032-three-tier-memory-contract.md))
- AKS with KEDA for elastic scaling, 3 node pools ([ADR-008](adrs/adr-008-aks-deployment.md))
- Deployment strategy: azd provisioning + Flux CD GitOps ([ADR-017](adrs/adr-017-deployment-strategy.md))
- APIM + AGC as the canonical AKS edge ([ADR-021](adrs/adr-021-apim-agc-edge.md))
- Namespace isolation for CRUD and agent workloads ([ADR-026](adrs/adr-026-namespace-isolation-strategy.md))
- AGC weighted canary policy with automatic rollback ([ADR-029](adrs/adr-029-agc-weighted-canary-policy.md))
- UI as a modular monolith on Static Web Apps ([ADR-033](adrs/adr-033-ui-modular-monolith-on-swa.md))

### Governance
- Git branch naming convention ([ADR-018](adrs/adr-018-branch-naming-convention.md))
- Agent communication policy, isolation, and async contracts ([ADR-024](adrs/adr-024-agent-communication-policy.md))
- MCP-only agent-to-agent communication with hop counter ([ADR-030](adrs/adr-030-mcp-only-a2a.md))
- Self-healing boundaries, risk tiers, and prohibited actions ([ADR-025](adrs/adr-025-self-healing-boundaries.md))
- API Center + APIM MCP strategy for API governance ([ADR-027](adrs/adr-027-api-center-apim-mcp-strategy.md))
- OTEL span attributes contract for retail agents ([ADR-031](adrs/adr-031-otel-span-attributes-contract.md))

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
