# Incident Infra Hardening Plan (2026-03-06)

## Implementation Closure Update (2026-03-06, PR #198)

### Implemented controls

- Deployment guardrails are now enforced in workflows:
  - ACR data-plane preflight before CRUD deploy.
  - CRUD readiness gate using `/ready` checks through APIM and direct service path.
  - Deterministic Static Web App resolution (`<project>-ui-<env>`) before fallback lookup.
  - APIM URL drift validation and mandatory smoke probes for `/api/health`, `/api/products?limit=1`, and `/api/categories`.
- Workload availability controls are now implemented for AKS-hosted services:
  - CRUD-safe rollout defaults (zero unavailable during rolling updates).
  - Pod disruption budget support and topology spread controls in chart templates/values.
  - PowerShell and shell Helm render hooks now align on node scheduling behavior.
- PostgreSQL auth-mode wiring is now deterministic across IaC/workflow/runtime:
  - Explicit auth mode outputs are propagated into deploy/runtime environment generation.
  - Runtime/env baseline is consistent (`password` default, explicit `entra` opt-in).
- UI and agent proxy failure behavior is now safer:
  - Legacy API URL alias fallback chain is supported.
  - Upstream fetch failures return structured but sanitized `502` responses.
  - Raw upstream exception detail is logged server-side only.
- Follow-up runtime fix is implemented:
  - CRUD `/ready` now recovers from stale startup DB init errors when live pool health is restored.

### Architecture rationale

- Deployment now uses explicit fail-fast control points (ACR/APIM/readiness) to prevent partial rollouts from becoming user-visible incidents.
- Deterministic resource selection reduces routing ambiguity during IaC churn.
- Readiness semantics now reflect current dependency state instead of stale startup state, reducing false-negative health outcomes.

### Operational guardrails (do not bypass)

- Do not deploy UI when APIM smoke checks fail.
- Do not override UI API URL to a value that does not match live APIM gateway URL.
- Treat ACR preflight failures as hard-stop conditions.
- Keep rollout gating on `/ready` and do not downgrade to liveness-only checks.

## Reviewer Checklist

- [ ] Workflow guardrails and stop conditions are documented and verifiable.
- [ ] CRUD `/ready` recovery semantics are documented and test-backed.
- [ ] UI proxy `502` diagnostics are documented as sanitized client payloads.
- [ ] PostgreSQL auth-mode contract is consistent across IaC/workflow/runtime/env generation.
- [ ] Remaining roadmap work is separated from implemented controls.

## Current State

- User-facing SWA API routes are currently healthy:
  - `GET /api/health` -> `200`
  - `GET /api/products?limit=1` -> `200`
  - `GET /api/categories` -> `200`
- Immediate SWA breakage root cause was environment drift:
  - SWA had `NEXT_PUBLIC_API_BASE_URL` only, while runtime proxy expected `NEXT_PUBLIC_API_URL` / `NEXT_PUBLIC_CRUD_API_URL`.
- `deploy-azd` still has an environment blocker unrelated to app code:
  - ACR firewall denied GitHub runner egress IP during `deploy-crud` image push.

## Critical Risks To Eliminate

1. VNet and routing drift across APIM + ingress + SWA can silently break backend resolution on redeploy.
2. AKS availability can degrade under pool/taint pressure, leaving critical CRUD replicas pending.
3. PostgreSQL auth mode and identity mapping can drift (password vs Entra, user mismatch).
4. Workflow logic depends on changed-service detection, missing full reconciliation after infra churn.

## Phase Plan

## Phase 0: Immediate Safety Baseline (1-2 days)

- Enforce SWA API env alias compatibility in app code and deployment:
  - Accept `NEXT_PUBLIC_API_BASE_URL` as fallback in proxy/client resolver.
  - Continue setting `NEXT_PUBLIC_API_URL` + `NEXT_PUBLIC_CRUD_API_URL` during UI deploy.
- Force APIM sync/smoke capability for manual incident closure runs (`forceApimSync=true`).
- Keep APIM smoke gates mandatory before UI deploy.
- Add `deploy-azd` preflight check that fails early when ACR firewall blocks runner IP.

Implementation status (this pass):
- [x] Added early ACR data-plane preflight in `deploy-azd` before CRUD deploy attempts with actionable failure guidance.
- [x] Added CRUD readiness gate after `deploy-crud` that checks `/ready` via APIM and direct service route with retries.
- [x] Made SWA resolution deterministic in workflows using naming convention first (`<projectName>-ui-<environment>`) plus constrained fallback.
- [x] Added IaC outputs for explicit `POSTGRES_AUTH_MODE`, deterministic workload-path `POSTGRES_USER`, and preserved break-glass `POSTGRES_ADMIN_USER`.

Files:
- `apps/ui/app/api/_shared/base-url-resolver.ts`
- `apps/ui/lib/api/client.ts`
- `.github/workflows/deploy-azd.yml`
- `.github/workflows/deploy-ui-swa.yml`

## Phase 1: AKS Always-On Critical Path (2-4 days)

- Make scheduling deterministic for both shell paths:
  - Ensure `render-helm.ps1` mirrors `render-helm.sh` nodeSelector + tolerations.
- Add workload availability controls for CRUD:
  - PodDisruptionBudget (`minAvailable`), topology spread/anti-affinity.
  - Rolling strategy with `maxUnavailable=0` for CRUD.
- Set environment-specific nodepool minima:
  - Shared dev/stage/prod should not allow effective single-node critical path.

Files:
- `.infra/azd/hooks/render-helm.ps1`
- `.infra/azd/hooks/render-helm.sh`
- `.kubernetes/chart/templates/deployment.yaml`
- `.kubernetes/chart/templates/pdb.yaml` (new)
- `.kubernetes/chart/values.yaml`
- `.infra/modules/shared-infrastructure/shared-infrastructure.bicep`

## Phase 2: PostgreSQL Auth Convergence (3-5 days)

- Standardize app runtime to one auth model per environment (recommended: Entra for VNet-secure envs).
- Align workload identity principal used by pods with RBAC principal assigned in IaC.
- Stop using liveness-only endpoint for readiness in CRUD deploy path.
- Add explicit rollout gate: CRUD `/ready` must pass after deploy.

Files:
- `apps/crud-service/src/crud_service/config/settings.py`
- `apps/crud-service/src/crud_service/main.py`
- `apps/crud-service/src/crud_service/routes/health.py`
- `.infra/modules/shared-infrastructure/shared-infrastructure.bicep`
- `.github/workflows/deploy-azd.yml`
- `.infra/azd/hooks/generate-crud-env.sh`
- `.infra/azd/hooks/generate-crud-env.ps1`

## Phase 3: Topology and Drift-Proof IaC (4-7 days)

- Make APIM topology explicit per environment (not mixed implicit behavior):
  - VNet mode + ingress model + backend URL contract.
- Remove ambiguous resource resolution (`[0]` picks) and duplicate resource naming patterns.
- Reduce imperative drift fixes in workflows by moving identity/network contracts into Bicep.

Files:
- `.infra/modules/shared-infrastructure/shared-infrastructure.bicep`
- `.infra/azd/main.bicep`
- `.infra/azd/hooks/sync-apim-agents.sh`
- `.infra/azd/hooks/sync-apim-agents.ps1`
- `.github/workflows/deploy-azd.yml`

## Release Gates (Keep/Extend)

- Keep mandatory smoke checks for:
  - `/api/health`
  - `/api/products?limit=1`
  - `/api/categories`
- Add drift checks:
  - APIM `crud` serviceUrl expected pattern + reachable probe.
  - SWA appsettings required keys present.
  - CRUD pod effective auth mode and `POSTGRES_USER` consistency.

## Execution Order

1. Phase 0 + SWA compatibility + ACR preflight guard.
2. Phase 1 AKS availability controls.
3. Phase 2 Postgres identity/auth convergence.
4. Phase 3 full topology determinism and drift-proofing.

## Success Criteria

- No user-facing `/api/*` 500s during redeploy windows.
- APIM backend mapping remains valid after full `deploy-azd` runs.
- CRUD remains available with at least one ready pod during node disruptions.
- PostgreSQL auth errors (`InvalidAuthorizationSpecificationError`, `pg_hba` rejects) no longer recur in normal deploy flow.
