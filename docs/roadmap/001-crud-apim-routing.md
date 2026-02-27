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

## Files to Modify

- `.github/workflows/deploy-azd.yml` — Add CRUD APIM sync job
- `.infra/azd/hooks/sync-apim-agents.*` — Extend or create CRUD variant
- `apps/crud-service/` — Add OpenAPI spec export for APIM import

## References

- [ADR-021](../architecture/adrs/adr-021-azd-first-deployment.md) — azd-first deployment
- [CRUD Service Docs](../architecture/crud-service-implementation.md)
