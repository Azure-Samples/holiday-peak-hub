# Backend Development Governance and Compliance Guidelines

**Version**: 2.1  
**Last Updated**: 2026-04-30  
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

### Package manager policy (canonical)

- CI and repository documentation must use `uv` commands for dependency installation.
- In GitHub-hosted runners, use `uv pip --system` to avoid extra venv activation complexity.
- `pip` usage is compatibility-only (for example, installing `uv` on fresh developer machines) and must not be introduced as the primary workflow path.

## Mandatory Standards

### Code and architecture

- Follow PEP 8 and project lint rules (`line-length=100`).
- Keep agents lightweight; domain/business logic belongs in adapters.
- Enforce adapter boundaries (ADR-003).
- Keep dual exposition clear: REST for app/front-end and MCP for agent-to-agent (ADR-004).
- Use SLM-first routing with optional LLM upgrade for complex requests (ADR-010).
- Canonical retail and connector event envelopes must carry top-level `schema_version` in `major.minor` format.
- Missing canonical envelope versions must be interpreted as implicit `1.0` during migration windows.
- Same-major schema evolution must remain additive-only with unknown fields tolerated; breaking changes require a major bump and contract-gate updates.

### Data and memory

- Use three-tier memory strategy where applicable (Redis hot, Cosmos warm, Blob cold) (ADR-007).
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
- ADR-004 FastAPI + MCP
- ADR-006 SAGA Choreography
- ADR-007 Three-Tier Memory
- ADR-004 REST + MCP Exposition
- ADR-003 Adapter Boundaries
- ADR-010 SLM-First Routing
- ADR-007 Memory Partitioning
- ADR-017 azd-first deployment
- ADR-019 enterprise resilience patterns
- ADR-025 self-healing boundaries
- ADR-026 namespace isolation
