# Infrastructure Governance and Compliance Guidelines

**Version**: 2.3
**Last Updated**: 2026-04-07
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
- `.github/workflows/protected-dev-live-agent-readiness.yml` (protected dev live validation)

### Core policy

- **azd-first deployment is mandatory** (ADR-021).
- Reusable workflow `deploy-azd.yml` is not the primary operator entrypoint; use env-specific entrypoint workflows.
- OIDC Azure login is required in CI/CD; no static cloud credentials committed to repository.
- Provisioning must fail fast when `projectName` is not `holidaypeakhub405` or when `resourceGroupName`/`AZURE_RESOURCE_GROUP` are not `holidaypeakhub405-<environment>-rg`; this is enforced through azd `preprovision` hooks.

## Environment Policy Matrix

| Policy Area | dev | prod | staging |
| --- | --- | --- | --- |
| Entrypoint workflow | `deploy-azd-dev.yml` | `deploy-azd-prod.yml` | Not currently provisioned as dedicated workflow |
| Trigger model | Successful `test` `workflow_run` for a push to `main` + `workflow_dispatch` | Stable tag push `v*.*.*` | Manual via reusable workflow only if explicitly configured |
| Protected live validation | `protected-dev-live-agent-readiness.yml` via the `dev` environment boundary on trusted `workflow_run`, `workflow_dispatch`, and `schedule`; the `dev` environment must remain restricted to the selected branch `main` | N/A | N/A |
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

### Protected live validation boundary

- The GitHub Environment `dev` is the approved boundary for privileged live validation against the deployed dev environment.
- `protected-dev-live-agent-readiness.yml` is the approved workflow for this boundary and validates one representative agent service end to end: Foundry ensure, direct `/ready`, and live APIM `/agents/<service>/invoke`.
- Allowed triggers are `workflow_run` after successful `deploy-azd-dev (entrypoint)` runs on `main`, `workflow_dispatch`, and `schedule`.
- Forbidden triggers are `pull_request`, `pull_request_target`, and other untrusted contributor contexts.
- Authentication must use OIDC-backed `azure/login`; do not introduce Azure client secrets, API keys, connection strings, or repository-committed credentials.
- Store `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, and `AZURE_SUBSCRIPTION_ID` in the `dev` environment so privileged live checks remain isolated from standard PR automation.
- Repository code establishes the privileged workflow and environment-scoped secret boundary, while GitHub Environment protection rules remain external to repository code. The `dev` environment must remain configured with selected-branch deployment protection on `main`.
- This workflow is operational evidence and must not be added to required PR status checks.

## Security and Access Controls

- Use Managed Identity and Entra-based federation for deployment identities.
- Keep Key Vault as secret authority; no direct secret literals in IaC templates or workflows.
- Enforce RBAC-scoped assignments for deployment principal operations.
- Use private networking posture for backend services where configured.
- Protected live validation must use GitHub-hosted runners plus OIDC-backed Azure auth; do not rely on self-hosted managed-identity runners for this public repository path.

## Runtime Deployment Controls

- Canonical AKS edge posture is **APIM -> AGC -> AKS** as defined by ADR-027; AGC is the only supported ingress target state for APIM-published AKS workloads.
- APIM is the only supported public API facade for AKS-hosted services.
- APIM backends for AKS workloads must target approved AGC hostnames or listeners only.
- APIM backends must not target pod IPs, node IPs, `ClusterIP` addresses, or `*.svc.cluster.local` names.
- AKS services published through APIM must remain `ClusterIP` unless a newer accepted ADR documents an exception.
- CRUD-first sequencing before dependent agent rollouts.
- AKS service deployment must build or resolve immutable per-SHA images first, then render/apply manifests pinned by digest (`repo@sha256:...`); deploy jobs must not rebuild service images during manifest rollout.
- Changed-service detection to reduce blast radius and deployment duration.
- Reusable deploy workflows must accept an explicit tested source SHA/ref and use that checkout consistently across detection, build, render, sync, and validation jobs.
- Push-event changed-service detection must diff `${{ github.event.before }}...${{ github.sha }}` to avoid empty comparisons against `origin/main` after merge.
- APIM sync/smoke checks for API path health after relevant changes.
- Deployment workflows must validate AGC GatewayClass readiness and direct CRUD `/health` reachability on the approved AGC frontend hostname before APIM sync.
- APIM sync determinism is required: ingress sync must resolve against an explicit AGC target in workflow execution.
- APIM smoke coverage must include direct AGC CRUD health, APIM CRUD health, CRUD CORS preflight behavior, and at least one negative CRUD path that proves failures are not masked as upstream 5xx responses.
- Transitional workflow or manifest logic may still detect legacy ingress classes during migration, but AGC is the canonical target state and must take precedence in governance and cutover planning.
- APIM sync filtering must always include `crud-service` when CRUD sync is enabled, even under changed-services filtering.
- For AGC-backed CRUD routing, ingress must expose app-native paths (`/health`, `/api`) and APIM CRUD backend must target the AGC listener root with no workload-specific suffix.
- Path translation must not be split across AGC and APIM for CRUD. APIM keeps health rewrite (`/api/health -> /health`), while `/api/*` routes are forwarded as-is.
- Agent-service deployments must enforce the Foundry runtime contract end to end: workflow intent currently requires `FOUNDRY_STRICT_ENFORCEMENT=true` and `FOUNDRY_AUTO_ENSURE_ON_STARTUP=true`, render hooks must emit both keys into Helm output, and the post-deploy gate must compare workflow intent, rendered manifests, live Deployment env values, `POST /foundry/agents/ensure`, and live `/ready` behavior for each changed agent service.
- A changed agent service is a hard deployment failure when any Foundry contract seam drifts: missing rendered keys, rendered-versus-live env mismatch, ensure responses without resolved `fast` and `rich` agent ids, or `/ready` responses that remain healthy while the strict Foundry contract is not actually enforced.
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
- UI proxy observability must classify proxy failures by `failureKind` (`config`, `policy`, `network`, `upstream`) and capture `upstreamPath`, `sourceKey`, `status`, and `fallbackUsed` dimensions for incident triage.
- Sustained `502` alerting is mandatory for critical UI proxy endpoints (`/api/*` set defined by endpoint-contract governance):
  - Warn threshold: `502` rate >= 3% over 10 minutes with request count >= 30.
  - Critical threshold: `502` rate >= 8% over 5 minutes with request count >= 50.
- Fallback-enabled routes must publish fallback usage telemetry separately from `502` failure alerts so graceful degradation does not mask upstream reliability regressions.
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
7. Privileged live validation remains bound to the `dev` environment, excluded from PR contexts, and constrained by selected-branch deployment protection on `main`.
8. Changed agent services passed the Foundry runtime contract gate across workflow intent, rendered manifests, live Deployment env values, ensure responses, and `/ready` validation.

## ADR References

- ADR-002 Azure service stack
- ADR-009 AKS deployment pattern
- ADR-021 azd-first deployment
- ADR-022 branch naming convention
- ADR-023 enterprise resilience patterns
- ADR-026 historical AGIC traffic-management record
- ADR-027 canonical APIM -> AGC -> AKS edge
