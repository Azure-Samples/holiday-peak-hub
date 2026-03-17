# 001: CRUD Service Not Registered in APIM

**Severity**: Critical  
**Category**: Infrastructure  
**Discovered**: February 2026

## Summary

The CRUD service is explicitly excluded from the `sync-apim-agents` script. As a result, all frontend API calls that route through APIM to the CRUD service fail. The CRUD service endpoints are unreachable via the API gateway.

## Current Behavior

- The `sync-apim-agents` script iterates over agent services but skips `crud-service`
- APIM has no API definition or route for the CRUD service
- Frontend calls to `NEXT_PUBLIC_API_URL` (pointed at APIM) return 404 for all CRUD endpoints
- Only direct pod-to-pod calls within AKS can reach the CRUD service

## Expected Behavior

- CRUD service should be registered in APIM with its own API definition
- All 31 CRUD endpoints should be routable through APIM
- JWT validation policies should be applied at the APIM layer
- Frontend should reach CRUD endpoints through `https://<apim>.azure-api.net/crud/*`

## Root Cause

The `sync-apim-agents` deployment job was designed for agent services only. The CRUD service has a different URL structure and was excluded during script development. No separate APIM registration step was added for the CRUD service.

## Suggested Fix

1. Add a dedicated APIM API definition for the CRUD service (separate from agent APIs)
2. Either extend `sync-apim-agents` to include CRUD or create a dedicated `sync-apim-crud` step in the deploy pipeline
3. Apply JWT validation, rate limiting, and CORS policies at the APIM level
4. Update `deploy-azd.yml` to run CRUD APIM sync after `deploy-crud` job

## Implementation Notes (Feb 2026)

- `sync-apim-agents.ps1` and `sync-apim-agents.sh` now register `crud-service` in APIM.
- CRUD sync now creates a dedicated API (`api-id: crud-service`, path: `api`) with route operations for:
  - `/health`
  - `/api` and `/api/{*path}`
  - `/acp/{*path}`
- This enables frontend calls proxied as `/api/*` to resolve through APIM to the CRUD backend.
- `.github/workflows/deploy-azd.yml` is the official APIM reconciliation source of truth and runs ingress/App Gateway-first sync.
- `azure.yaml` postdeploy now mirrors that same ingress/App Gateway-first APIM sync model for `azd up`, while still forcing CRUD inclusion.
- `.infra/azd/main.bicep` now exports `APIM_NAME` and `AKS_CLUSTER_NAME` to strengthen hook resolution in fresh environments.

## Validation Snapshot (2026-02-28, env: `dev` / `405`)

- `GET https://holidaypeakhub405-dev-apim.azure-api.net/api/health` returns `200`.
- `GET https://holidaypeakhub405-dev-apim.azure-api.net/api/products?limit=1` reaches CRUD auth flow (returns `401` when unauthenticated), confirming APIM route-to-backend correctness.
- CRUD remains included in strict postdeploy APIM sync (`-UseIngress -IncludeCrudService:$true`) and stays healthy in full 22-service sweep.

## Recurrence Hardening (Mar 2026)

- APIM sync ingress endpoint discovery now supports both AGIC/App Gateway and AKS Web App Routing or ingress-nginx (`nginx` in `app-routing-system`, `ingress-nginx-controller` in `ingress-nginx`, and `app.kubernetes.io/name=nginx` service labels).
- When ingress endpoint resolution fails, APIM sync now fails fast instead of falling back to cluster-local service addresses (`*.svc.cluster.local` or `ClusterIP`) that APIM cannot reach.
- CRUD APIM policy now includes:
  - Guarded rewrite conditions for `/api`, `/api/*`, and `/api/health`
  - Explicit backend forward timeout (`60` seconds)
  - Structured error responses for invalid path (`400`) and upstream APIM routing failures (`502`)

These controls reduce the chance that frontend `/api/products` or `/api/categories` requests surface opaque APIM 500 responses caused by unreachable backend URLs or policy expression edge cases.

## Incident-Closure Safeguards (Mar 2026)

- `deploy-azd.yml` now exposes `workflow_dispatch` input `forceApimSync` (default `false`).
- `sync-apim` and `smoke-apim` jobs now run when either:
  - changed service detection reports CRUD/agent changes, or
  - `forceApimSync` is set to `true` for manual incident closure verification.
- In ingress mode, APIM sync hooks now require deterministic backend ingress host selection:
  - Prefer explicit `ingress host` or explicit `app gateway name/ip` when provided.
  - Auto-resolution is allowed only when a single unambiguous candidate exists.
  - Ambiguous routing candidates now fail fast.
- Before any APIM update in ingress mode, hooks probe `http://<resolved-ingress-host>/health` and abort on unhealthy/invalid resolution.
- APIM sync hooks now include a CRUD backend stability guard that fails if resolved CRUD `serviceUrl` host matches a current `crud-service` endpoint IP.
- Reusable deploy workflow now validates APIM CRUD `serviceUrl` (`crud-service` fallback `crud`) against live `crud-service` endpoint IPs via `az aks command invoke`, and fails before smoke tests on unstable target detection.
- Demo recovery now explicitly re-runs ingress/App Gateway-first APIM reconciliation before validating APIM CRUD endpoints or reseeding demo data.

## Closure Status Update (2026-03-06, PR #198)

- Routing hardening for this incident is now implemented and merged on the hotfix branch.
- Deployment control gates now enforce fail-fast behavior before user traffic is exposed:
  - ACR preflight check before CRUD deploy.
  - CRUD readiness gate (`/ready`) after CRUD rollout.
  - Deterministic SWA resolution and APIM drift validation in UI deploy.
  - Mandatory APIM smoke checks for health/products/categories around UI release.
- Follow-up runtime fix removed a readiness false-negative mode by allowing `/ready` to recover from stale startup DB init errors once live pool health succeeds.

### Residual Roadmap Items

- Add periodic non-deploy drift scans (scheduled) for APIM backend URL and smoke endpoint health.
- Add alerting hooks on repeated readiness degradation and APIM smoke failures.
- Continue environment policy convergence for PostgreSQL auth mode with explicit per-environment contract.

### When to use `forceApimSync`

- Use `forceApimSync=true` for incident closure or drift verification after infra/runtime remediation when no app files changed in the current diff.
- Keep `forceApimSync=false` for normal incremental deploys driven by changed-service detection.

## Files to Modify

- `.github/workflows/deploy-azd.yml` — Add CRUD APIM sync job
- `.infra/azd/hooks/sync-apim-agents.*` — Extend or create CRUD variant
- `apps/crud-service/` — Add OpenAPI spec export for APIM import

## References

- [ADR-021](../architecture/adrs/adr-021-azd-first-deployment.md) — azd-first deployment
- [CRUD Service Docs](../architecture/crud-service-implementation.md)
