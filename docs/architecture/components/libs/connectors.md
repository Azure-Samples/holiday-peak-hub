# Connectors Component

Enterprise connector framework for integrating external retail systems with tenant-aware routing, versioning, and resilience controls.

## Path

- `lib/src/holiday_peak_lib/connectors/`

## Core Responsibilities

- Connector contract registry and lookup
- Tenant-aware connector resolution and isolation
- Version compatibility utilities for connector contracts
- Shared protocols for connector implementations

## Key Modules

- `registry.py` — Connector registration and resolution
- `tenant_resolver.py` — Tenant-to-connector mapping
- `tenant_config.py` — Tenant connector configuration schema
- `common/protocols.py` — Shared connector protocol contracts
- `common/versioning.py` — Connector compatibility/version helpers

## Related Components

- [Integrations](integrations.md)
- [Adapters](adapters.md)
- [Schemas](schemas.md)

## Related ADRs

- [ADR-003: Adapter Pattern, Boundaries, and Connector Registry](../../adrs/adr-003-adapter-pattern.md)
