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
- `azure.yaml` postdeploy now enforces CRUD inclusion explicitly in APIM sync for `azd up`.
- `.infra/azd/main.bicep` now exports `APIM_NAME` and `AKS_CLUSTER_NAME` to strengthen hook resolution in fresh environments.

## Validation Snapshot (2026-02-28, env: `dev` / `405`)

- `GET https://holidaypeakhub405-dev-apim.azure-api.net/api/health` returns `200`.
- `GET https://holidaypeakhub405-dev-apim.azure-api.net/api/products?limit=1` reaches CRUD auth flow (returns `401` when unauthenticated), confirming APIM route-to-backend correctness.
- CRUD remains included in strict postdeploy APIM sync (`-IncludeCrudService:$true -RequireLoadBalancer:$true`) and stays healthy in full 22-service sweep.

## Files to Modify

- `.github/workflows/deploy-azd.yml` — Add CRUD APIM sync job
- `.infra/azd/hooks/sync-apim-agents.*` — Extend or create CRUD variant
- `apps/crud-service/` — Add OpenAPI spec export for APIM import

## References

- [ADR-021](../architecture/adrs/adr-021-azd-first-deployment.md) — azd-first deployment
- [CRUD Service Docs](../architecture/crud-service-implementation.md)
