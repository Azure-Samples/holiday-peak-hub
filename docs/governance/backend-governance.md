# Backend Development Governance and Compliance Guidelines

**Version**: 2.0  
**Last Updated**: 2026-03-11  
**Owner**: Backend Team

## Scope

Applies to all Python services and shared framework packages under:

- `lib/src/`
- `apps/*/src/` (including `apps/crud-service/src/` and all agent services)

## Runtime and Tooling Baseline

- **Python**: `>=3.13`
- **Framework**: FastAPI + FastAPI MCP
- **Data contracts**: Pydantic v2
- **Agent runtime**: Microsoft Agent Framework + Azure AI Foundry
- **Async stack**: `asyncio`, `httpx` async, async SDK clients
- **Package management**: `pyproject.toml` + `uv`

## Mandatory Standards

### Code and architecture

- Follow PEP 8 and project lint rules (`line-length=100`).
- Keep agents lightweight; domain/business logic belongs in adapters.
- Enforce adapter boundaries (ADR-003, ADR-012).
- Keep dual exposition clear: REST for app/front-end and MCP for agent-to-agent (ADR-010).
- Use SLM-first routing with optional LLM upgrade for complex requests (ADR-013).

### Data and memory

- Use three-tier memory strategy where applicable (Redis hot, Cosmos warm, Blob cold) (ADR-008, ADR-014).
- Keep Cosmos queries partition-aware and resilient to throttling (`429` backoff).
- Do not bypass configured identity and secret patterns.

### Security

- Use Managed Identity and Key Vault for secrets.
- No hard-coded credentials, tokens, or connection strings in source.
- Validate JWT and RBAC at service boundaries for protected endpoints.

## Testing and Quality Gates

- **Repo baseline**: minimum 75% coverage on shared CI/test expectations.
- **Service/package local policy**: stricter thresholds permitted (some pyproject configs enforce 80%).
- Unit tests for core logic and adapters.
- Integration tests for API contracts, persistence, and messaging edges.
- Use pytest/pytest-asyncio; keep tests deterministic and isolated.

## Observability Requirements

- Structured logging for service operations and error paths.
- Emit telemetry for latency, error rate, and dependency calls.
- Capture diagnostics around external dependency failures and retries.

## CI/CD and Environment Alignment

Backend deployment policy follows infrastructure entrypoint workflows:

- `deploy-azd-dev.yml` for dev deployments
- `deploy-azd-prod.yml` for production-tag deployments
- reusable execution engine: `deploy-azd.yml`

For environment-specific deployment rules, see [Infrastructure Governance](infrastructure-governance.md#environment-policy-matrix).

## ADR References

- ADR-003 Adapter Pattern
- ADR-005 FastAPI + MCP
- ADR-007 SAGA Choreography
- ADR-008 Three-Tier Memory
- ADR-010 REST + MCP Exposition
- ADR-012 Adapter Boundaries
- ADR-013 SLM-First Routing
- ADR-014 Memory Partitioning
- ADR-021 azd-first deployment
- ADR-023 enterprise resilience patterns
