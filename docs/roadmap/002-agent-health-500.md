# 002: Agent Health Endpoints Return 500 Through APIM

**Severity**: Critical  
**Category**: Agents  
**Discovered**: February 2026

## Summary

All 21 agent services return HTTP 500 errors when their `/health` endpoint is accessed through APIM. Direct pod access within AKS may work, but the APIM route consistently fails.

## Current Behavior

- `GET https://<apim>.azure-api.net/<agent-service>/health` → HTTP 500
- All 21 agents exhibit the same behavior
- APIM shows backend connection errors in diagnostics
- Agent pods are running in AKS (kubectl reports Ready state)

## Expected Behavior

- All agent health endpoints should return HTTP 200 with service status
- APIM should proxy health checks to the backend AKS pods cleanly
- Kubernetes liveness/readiness probes should succeed through the same paths

## Possible Root Causes

1. **Missing environment variables**: Agents may fail to start properly without `REDIS_URL`, `COSMOS_ACCOUNT_URI`, or Foundry configuration. The `FOUNDRY_STRICT_ENFORCEMENT` flag may block the health endpoint.
2. **Startup crash loop**: Agents may be crashing on startup due to missing memory/model config and restarting continuously.
3. **APIM backend pool misconfiguration**: Backend URLs in APIM may not resolve to actual agent ClusterIP services in AKS.
4. **Network policy**: NSGs or Kubernetes NetworkPolicies may block APIM → AKS traffic.

## Suggested Fix

1. Check agent pod logs: `kubectl logs -l app=<agent-name> -n holiday-peak --tail=100`
2. Verify environment variables in AKS ConfigMaps/Secrets
3. Ensure graceful startup: agents should respond to `/health` even when memory/model is unconfigured (already partially addressed in `8ce9b25`)
4. Verify APIM backend pool URLs match AKS service DNS
5. Test direct pod access: `kubectl port-forward svc/<agent-service> 8000:8000`

## Files to Modify

- `lib/src/holiday_peak_lib/app_factory.py` — Ensure health endpoint never depends on external services
- `.kubernetes/chart/values.yaml` — Verify agent service DNS and port mappings
- `.infra/azd/hooks/sync-apim-agents.*` — Verify backend URL construction

## References

- Commit `8ce9b25` — Graceful startup without memory/model env vars
- Commit `a80f6fb` — Make MemorySettings optional
