# 003: SWA API Proxy Returns 404

**Severity**: High  
**Category**: Frontend  
**Discovered**: February 2026

## Summary

The Static Web App (SWA) returns 404 for all `/api/*` routes. The `staticwebapp.config.json` rewrite rules do not correctly proxy API calls to the APIM backend.

## Current Behavior

- `GET https://<swa>.azurestaticapps.net/api/health` → HTTP 404
- `GET https://<swa>.azurestaticapps.net/api/products` → HTTP 404
- All `/api/*` routes return SWA's default 404 page
- The `staticwebapp.config.json` file exists but rewrites are not working as expected

## Expected Behavior

- `/api/*` routes should proxy to `https://<apim>.azure-api.net/*`
- SWA should handle the rewrite transparently
- Frontend API client should work without CORS issues

## Possible Root Causes

1. SWA Free tier does not support managed API backends or reverse proxy rewrites to external URLs
2. The rewrite configuration syntax may be incorrect for the SWA runtime
3. Next.js `next.config.js` API proxy only works in development mode, not in static export
4. SWA App Router mode may handle rewrites differently than expected

## Suggested Fix

1. **Option A**: Configure frontend to call APIM directly (set `NEXT_PUBLIC_API_URL` to the APIM URL and handle CORS at APIM level)
2. **Option B**: Use SWA linked backend (Standard tier required) to connect to the AKS-hosted CRUD service
3. **Option C**: Use Azure Front Door to unify SWA and APIM under a single domain

## Implementation Notes (Feb 2026)

- Removed external `/api/*` rewrite rules from:
  - `apps/ui/staticwebapp.config.json`
  - `apps/ui/public/staticwebapp.config.json`
- Frontend now relies on direct APIM calls via `NEXT_PUBLIC_API_URL` (already required by `apps/ui/lib/api/client.ts`).
- This avoids SWA rewrite/proxy behavior differences and prevents SWA from returning route-level 404 for API calls.

## Files to Modify

- `apps/ui/staticwebapp.config.json` — Fix or remove rewrite rules
- `apps/ui/.env.production` — Set `NEXT_PUBLIC_API_URL` to APIM directly
- `.infra/modules/shared-infrastructure/` — Add CORS policy to APIM for SWA origin

## References

- [SWA configuration docs](https://learn.microsoft.com/azure/static-web-apps/configuration)
- Commit `b54b3d4` — Add staticwebapp.config.json
