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

## Implementation Notes (Feb 2026)

- APIM backend URL construction in `sync-apim-agents.ps1` and `sync-apim-agents.sh` now resolves the **actual Kubernetes service name and port** using `kubectl` label lookup (`app=<service>`).
- Service exposure now uses internal Azure Load Balancers (Helm `Service` type `LoadBalancer` with `service.beta.kubernetes.io/azure-load-balancer-internal: "true"`), providing APIM-reachable private backends in the shared VNet.
- Sync hooks now bootstrap AKS credentials automatically (`az aks get-credentials`) and wait for backend load-balancer addresses before APIM API updates.
- Hooks fail fast by default when no load-balancer backend is available, so `azd up` surfaces connectivity problems immediately instead of leaving APIM with broken backend URLs.
- Agent services now consume `holiday-peak-lib` from the stable GitHub release tag (`v1.0.0`) instead of the removed `feat/api-layer` branch ref, unblocking image builds during `azd deploy` and `azd up`.

## Validation Snapshot (2026-02-28, env: `dev` / `405`)

- `sync-apim-agents.ps1 -IncludeCrudService:$true -RequireLoadBalancer:$true` now completes for all 22 AKS services.
- APIM health sweep result: **22/22 services return HTTP 200**.
- During staged redeploy of the four `product-management-*` services, `azd deploy` reported failures caused by `postdeploy` hook `ensure-foundry-agents.ps1`, not by AKS deployment itself.
- After those four services received internal LB addresses (`10.0.0.109` to `10.0.0.112`) and APIM sync was re-run, all product-management health routes returned `200`.

### Service Matrix (APIM health)

| Service | Status |
| --- | --- |
| crud-service (`/api/health`) | 200 |
| crm-campaign-intelligence | 200 |
| crm-profile-aggregation | 200 |
| crm-segmentation-personalization | 200 |
| crm-support-assistance | 200 |
| ecommerce-cart-intelligence | 200 |
| ecommerce-catalog-search | 200 |
| ecommerce-checkout-support | 200 |
| ecommerce-order-status | 200 |
| ecommerce-product-detail-enrichment | 200 |
| inventory-alerts-triggers | 200 |
| inventory-health-check | 200 |
| inventory-jit-replenishment | 200 |
| inventory-reservation-validation | 200 |
| logistics-carrier-selection | 200 |
| logistics-eta-computation | 200 |
| logistics-returns-support | 200 |
| logistics-route-issue-detection | 200 |
| product-management-acp-transformation | 200 |
| product-management-assortment-optimization | 200 |
| product-management-consistency-validation | 200 |
| product-management-normalization-classification | 200 |

## Postdeploy Hook Error Evaluation (2026-02-28)

- **Hook**: `ensure-foundry-agents`  
	**Observed Error**: connection refused during `kubectl port-forward` (`localhost:<port>`)  
	**Root Cause**: hook used azure service keys as Kubernetes service names and assumed service port `8000`; deployed Services are chart-generated names and expose Service port `80`.  
	**Criticality**: **Medium** (agent bootstrap issue; deployment infra is healthy)  
	**Resolution**: corrected in both `ensure-foundry-agents.ps1` and `ensure-foundry-agents.sh` by resolving service name via `app=<service>` label and using actual Service port. Hook now succeeds for all 21 services in `dev/405`.

- **Hook**: `seed-crud-demo-data`  
	**Observed Error**: PostgreSQL connect timeout from CRUD pod and seed Job (`POSTGRES_HOST ...:5432`).  
	**Root Cause**: runtime DB network path is unreachable from AKS workload in current environment (not a hook parser/command defect).  
	**Criticality**: **High** for CRUD data persistence and mock-data seeding; **Low** for APIM gateway routing validation.  
	**Resolution**: implemented seed hooks (`seed-crud-demo-data.ps1` / `.sh`) with preflight connectivity checks and explicit non-blocking behavior in postdeploy. Deployments no longer fail due seeding when DB is unreachable, while emitting clear warning diagnostics.

## Files to Modify

- `lib/src/holiday_peak_lib/app_factory.py` — Ensure health endpoint never depends on external services
- `.kubernetes/chart/values.yaml` — Verify agent service DNS and port mappings
- `.infra/azd/hooks/sync-apim-agents.*` — Verify backend URL construction

## References

- Commit `8ce9b25` — Graceful startup without memory/model env vars
- Commit `a80f6fb` — Make MemorySettings optional
