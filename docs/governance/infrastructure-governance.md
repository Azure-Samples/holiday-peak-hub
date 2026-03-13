# Infrastructure Governance and Compliance Guidelines

**Version**: 2.1  
**Last Updated**: 2026-03-12  
**Owner**: Infrastructure Team

## Scope

Infrastructure provisioning, deployment orchestration, identity, security controls, and runtime operations for Holiday Peak Hub.

## IaC and Deployment Baseline

### Source of truth

- `azure.yaml` (service topology and deployment hooks)
- `.infra/azd/` (azd project and Bicep orchestration)
- `.kubernetes/` (Helm chart templates and rendered manifests)
- `.github/workflows/deploy-azd-dev.yml` (dev entrypoint)
- `.github/workflows/deploy-azd-prod.yml` (prod entrypoint)
- `.github/workflows/deploy-azd.yml` (reusable deployment engine)

### Core policy

- **azd-first deployment is mandatory** (ADR-021).
- Reusable workflow `deploy-azd.yml` is not the primary operator entrypoint; use env-specific entrypoint workflows.
- OIDC Azure login is required in CI/CD; no static cloud credentials committed to repository.

## Environment Policy Matrix

| Policy Area | dev | prod | staging |
| --- | --- | --- | --- |
| Entrypoint workflow | `deploy-azd-dev.yml` | `deploy-azd-prod.yml` | Not currently provisioned as dedicated workflow |
| Trigger model | `push` to `main` + `workflow_dispatch` | Stable tag push `v*.*.*` | Manual via reusable workflow only if explicitly configured |
| Release gate | Not required | Required: published, non-draft, non-prerelease GitHub Release | N/A |
| Main lineage gate | Not required | Required: tagged commit must be reachable from `main` | N/A |
| Demo data seeding mode | Local/manual only (not part of CI deploy) | Local/manual only | Local/manual only |
| Changed-only deployment | Enabled | Enabled | N/A |
| Force APIM sync default | `true` | `true` | N/A |
| Auto allow ACR runner IP | `true` default | `false` default | N/A |
| Non-prod drift remediation | Enabled | Disabled | Would be treated as non-prod if introduced |

### Workflow deduplication policy

- Entrypoint workflows should avoid duplicated job blocks for push/manual variants when the same reusable workflow call can be parameterized with event-aware expressions.
- `deploy-azd-dev.yml` is maintained as a single reusable-workflow invocation path to reduce drift between trigger types.

## Security and Access Controls

- Use Managed Identity and Entra-based federation for deployment identities.
- Keep Key Vault as secret authority; no direct secret literals in IaC templates or workflows.
- Enforce RBAC-scoped assignments for deployment principal operations.
- Use private networking posture for backend services where configured.

## Runtime Deployment Controls

- CRUD-first sequencing before dependent agent rollouts.
- Changed-service detection to reduce blast radius and deployment duration.
- Push-event changed-service detection must diff `${{ github.event.before }}...${{ github.sha }}` to avoid empty comparisons against `origin/main` after merge.
- APIM sync/smoke checks for API path health after relevant changes.
- APIM sync determinism is required: ingress sync must resolve against an explicit Application Gateway target in workflow execution.
- Reusable deploy workflow ingress-class detection must prioritize `azure-application-gateway` before other classes in AGIC-first environments.
- APIM sync filtering must always include `crud-service` when CRUD sync is enabled, even under changed-services filtering.
- For App Gateway-backed CRUD routing, ingress must expose app-native paths (`/health`, `/api`) and APIM CRUD backend must target App Gateway root (no `/crud-service` suffix).
- Path translation must not be split across AGIC and APIM for CRUD. APIM keeps health rewrite (`/api/health -> /health`), while `/api/*` routes are forwarded as-is.
- AKS IaC defaults to AGIC/App Gateway-first ingress by setting Web App Routing addon disabled unless explicitly enabled (`aksWebApplicationRoutingEnabled`).
- Optional UI-only deployment path constrained by SWA token flow and health checks.
- ACR network-rule temporary exceptions may be applied/removed automatically when enabled.

## Data Connectivity Guardrails

- For CRUD PostgreSQL Entra mode, `POSTGRES_USER` must be a workload identity principal (for example AKS agentpool principal), not admin login `crud_admin`.
- CRUD env-generation hooks must normalize invalid/missing Entra users to the environment-derived AKS principal name before manifest rendering.

## Observability and Operational Policy

- Health checks and smoke checks are required post-deploy for critical API paths.
- Required test/smoke gates in CI must not use permissive `|| true` patterns on transport calls; failures must be deterministic for both transport errors and non-200 responses.
- Transport-layer failures in required checks must be normalized to explicit non-success outcomes and treated as hard failures.
- Advisory diagnostics/telemetry checks must be modeled separately from required gates and may remain non-blocking only when explicitly marked non-gating.
- Cleanup and diagnostic commands may remain permissive only when explicitly non-gating.
- Deployment failures in production gates are hard-stop conditions.
- Non-production can tolerate selected warnings where explicitly guarded by workflow conditions.

## Compliance Checklist

1. Deployment executed through approved workflow entrypoint.
2. Environment-specific policy gates satisfied.
3. OIDC auth path used successfully.
4. Smoke checks passed for CRUD/API/UI scope deployed.
5. Any temporary firewall exceptions removed after deployment.
6. Architecture/governance docs updated when policy changes.

## ADR References

- ADR-002 Azure service stack
- ADR-009 AKS deployment pattern
- ADR-021 azd-first deployment
- ADR-022 branch naming convention
- ADR-023 enterprise resilience patterns
