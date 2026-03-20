# Infrastructure Governance and Compliance Guidelines

**Version**: 2.2  
**Last Updated**: 2026-03-17  
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

- Canonical AKS edge posture is **APIM -> AGC -> AKS** as defined by ADR-027; AGC is the only supported ingress target state for APIM-published AKS workloads.
- APIM is the only supported public API facade for AKS-hosted services.
- APIM backends for AKS workloads must target approved AGC hostnames or listeners only.
- APIM backends must not target pod IPs, node IPs, `ClusterIP` addresses, or `*.svc.cluster.local` names.
- AKS services published through APIM must remain `ClusterIP` unless a newer accepted ADR documents an exception.
- CRUD-first sequencing before dependent agent rollouts.
- Changed-service detection to reduce blast radius and deployment duration.
- Push-event changed-service detection must diff `${{ github.event.before }}...${{ github.sha }}` to avoid empty comparisons against `origin/main` after merge.
- APIM sync/smoke checks for API path health after relevant changes.
- Deployment workflows must validate AGC GatewayClass readiness and direct CRUD `/health` reachability on the approved AGC frontend hostname before APIM sync.
- APIM sync determinism is required: ingress sync must resolve against an explicit AGC target in workflow execution.
- APIM smoke coverage must include direct AGC CRUD health, APIM CRUD health, CRUD CORS preflight behavior, and at least one negative CRUD path that proves failures are not masked as upstream 5xx responses.
- Transitional workflow or manifest logic may still detect legacy ingress classes during migration, but AGC is the canonical target state and must take precedence in governance and cutover planning.
- APIM sync filtering must always include `crud-service` when CRUD sync is enabled, even under changed-services filtering.
- For AGC-backed CRUD routing, ingress must expose app-native paths (`/health`, `/api`) and APIM CRUD backend must target the AGC listener root with no workload-specific suffix.
- Path translation must not be split across AGC and APIM for CRUD. APIM keeps health rewrite (`/api/health -> /health`), while `/api/*` routes are forwarded as-is.
- During migration, legacy AGIC or Web App Routing configuration may exist only as transitional state and must not be described as the target architecture.
- Optional UI-only deployment path constrained by SWA token flow and health checks.
- ACR network-rule temporary exceptions may be applied/removed automatically when enabled.

## Data Connectivity Guardrails

- For CRUD PostgreSQL Entra mode, `POSTGRES_USER` must be a workload identity principal (for example AKS agentpool principal), not admin login `crud_admin`.
- CRUD env-generation hooks must normalize invalid/missing Entra users to the environment-derived AKS principal name before manifest rendering.

## Observability and Operational Policy

- Health checks and smoke checks are required post-deploy for critical API paths.
- Shared infrastructure must deploy baseline metric alerts for Cosmos DB, Redis, PostgreSQL, Event Hubs, AKS, and APIM via `.infra/modules/monitoring/monitoring.bicep`.
- Action group notification targets for observability alerts are configured through azd/Bicep parameters `alertNotificationEmail` and `alertTeamsWebhookUrl`.
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
- ADR-026 historical AGIC traffic-management record
- ADR-027 canonical APIM -> AGC -> AKS edge
