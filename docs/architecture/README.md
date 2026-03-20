# Architecture Documentation

This folder contains the canonical architecture, ADRs, component references, operational playbooks, and diagrams for Holiday Peak Hub.

## Canonical Documents

- [Architecture Overview](architecture.md) — Primary technical architecture narrative (context, interactions, deployment)
- [Architecture Decision Records](ADRs.md) — Full ADR index and status
- [Components](components.md) — Library, app, and frontend component references
- [Architecture Compliance Review](architecture-compliance-review.md) — Branch-level ADR and policy conformance assessment
- [Event Hub Topology Matrix](eventhub-topology-matrix.md) — Topic-level publisher/subscriber coverage contract and gap tracking
- [Operational Playbooks](playbooks/README.md) — Incident runbooks aligned to governance policies
- [Diagrams](diagrams/README.md) — Draw.io C4 diagrams and sequence flow documents
- [Business Summary](business-summary.md) — Executive architecture summary

## Governance Alignment

- [Governance Overview](../governance/README.md)
- [Frontend Governance](../governance/frontend-governance.md)
- [Backend Governance](../governance/backend-governance.md)
- [Infrastructure Governance](../governance/infrastructure-governance.md)

## Source of Truth Rules

- Use this folder as architecture source of truth for repo-level design.
- Use `components/apps/*.md` for service-level implementation details.
- Use ADRs for all non-trivial architecture decisions and updates.
- Keep deployment policy references aligned with `deploy-azd-dev.yml`, `deploy-azd-prod.yml`, and reusable `deploy-azd.yml`.
- Prefer diagrams in `diagrams/*.drawio` for C4 views and `diagrams/sequence-*.md` for runtime flows.
