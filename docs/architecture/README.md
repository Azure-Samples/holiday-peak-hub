# Architecture Documentation

This folder contains comprehensive architectural documentation for the Holiday Peak Hub retail accelerator.

## Index

- [Business Summary](business-summary.md) — Business need, value proposition, and scope per lib/app
- [Architecture Overview](architecture.md) — System context, use case diagrams, component interaction, deployment views
- [Architecture Decision Records](ADRs.md) — Index of all ADRs
- [Components](components.md) — Detailed component documentation for libs, apps, and frontend
- [Frontend Implementation Plan](FRONTEND_IMPLEMENTATION_PLAN.md) — Complete frontend implementation with color system and service mappings
- [Operational Playbooks](playbooks/README.md) — Incident response guides and runbooks

### Governance and Compliance

- [Governance Overview](../governance/README.md) — Standards and compliance guidelines
- [Frontend Governance](../governance/frontend-governance.md) — Next.js, React, TypeScript standards
- [Backend Governance](../governance/backend-governance.md) — Python, FastAPI, agent development standards
- [Infrastructure Governance](../governance/infrastructure-governance.md) — Bicep, AKS, Azure services standards

## Quick Links

### Core Concepts
- **Libs**: Reusable micro-framework (adapters, agents, memory, orchestration)
- **Apps**: Domain-specific services built on the framework
- **Memory Tiers**: Redis (hot), Cosmos DB (warm), Blob Storage (cold)
- **Integration**: Event Hubs for async choreography, MCP + REST for sync APIs
- **Deployment**: Bicep for provisioning, Helm/KEDA for Kubernetes orchestration
- **Frontend**: Next.js 15 + React 19 + TypeScript, 52-component atomic design library
- **Protocols**: AG-UI for agent interoperability, ACP for product data standardization

### ADRs
See [ADRs.md](ADRs.md) for the complete list. Key decisions include:

**Backend**:
- Programming language (Python 3.13)
- Cloud services (Azure stack)
- Design patterns (Adapter, Builder)
- Agent framework (Microsoft Agent Framework + Foundry)
- Memory architecture
- API exposition strategy (MCP + REST)
- Deployment model (AKS with canary + KEDA)

**Frontend** (ADR-015 through ADR-020):
- Next.js 15 with App Router
- Atomic Design System (52 components)
- AG-UI Protocol integration
- ACP frontend compliance
- JWT authentication with RBAC
- Layered API client architecture

### Components
See [components.md](components.md) for detailed component documentation organized by:
- **Libs**: [components/libs/](components/libs/)
- **Apps**: [components/apps/](components/apps/)

## Diagrams

All architectural diagrams are embedded as Mermaid in [architecture.md](architecture.md), including:
- System context
- Use case diagrams per retail domain
- Component interaction
- Deployment topology
