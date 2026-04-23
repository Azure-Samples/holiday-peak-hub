# Runbook: ecommerce-catalog-search /ready 503

## Symptom

The `ecommerce-catalog-search` pod fails readiness probes with HTTP 503 on `/ready`. Kubernetes marks the pod as not ready, which causes:

- Pod restart loops (when `restartPolicy` applies after repeated probe failures)
- Service endpoint removal (no traffic routed to the pod)
- Downstream 503s from ingress or gateway

The `/ready` response body includes a JSON object with a `catalog_ai_search` key describing the specific failure condition.

## Affected Service

| Field | Value |
|-------|-------|
| Service | `ecommerce-catalog-search` |
| Namespace | `holiday-peak-agents` (default) |
| Endpoint | `GET /ready` |
| Probe type | Kubernetes readiness probe |

## Root Cause Decision Tree

Work through these steps in order. Stop at the first match.

| Step | Check | Command | If failing |
|------|-------|---------|------------|
| 1 | Are AI Search env vars set? | `kubectl exec -n <ns> <pod> -- env \| grep -E "AI_SEARCH_ENDPOINT\|AI_SEARCH_INDEX\|AI_SEARCH_VECTOR_INDEX"` | Missing env vars → go to [Resolution A](#a-missing-ai-search-environment-variables) |
| 2 | Is the AI Search endpoint reachable from the pod? | `kubectl exec -n <ns> <pod> -- curl -sf "https://<endpoint>/indexes?api-version=2024-07-01" -H "api-key: <key>"` or check managed identity auth | Unreachable → go to [Resolution B](#b-ai-search-endpoint-unreachable) |
| 3 | Does the AI Search index have documents? | `kubectl exec -n <ns> <pod> -- curl -sf "https://<endpoint>/indexes/<index>/docs/\$count?api-version=2024-07-01" -H "api-key: <key>"` | Count is 0 → go to [Resolution C](#c-ai-search-index-empty) |
| 4 | Is strict mode explicitly overridden? | `kubectl exec -n <ns> <pod> -- env \| grep CATALOG_SEARCH_REQUIRE_AI_SEARCH` | If set to `true` or unset (defaults to strict in K8s) → go to [Resolution D](#d-disable-strict-mode-temporary-workaround) |
| 5 | Are Foundry agents configured? (secondary) | `kubectl exec -n <ns> <pod> -- env \| grep -E "FOUNDRY_AGENT_ID_FAST\|FOUNDRY_AGENT_ID_RICH"` | Missing → go to [Resolution E](#e-foundry-agent-configuration). Note: this does **not** cause 503 for this service |

## Diagnostic Commands

### Pod status and events

```bash
kubectl get pods -n <namespace> -l app=ecommerce-catalog-search
kubectl describe pod -n <namespace> <pod-name>
```

### Readiness probe response

```bash
kubectl port-forward -n <namespace> <pod-name> 8080:8000
curl -sv http://localhost:8080/ready
```

### Environment variable audit

```bash
kubectl exec -n <namespace> <pod-name> -- env | grep -E "AI_SEARCH_|CATALOG_SEARCH_|CRUD_SERVICE_URL|APP_NAME"
```

### Application logs filtered to readiness

```bash
kubectl logs -n <namespace> <pod-name> | grep -E "catalog_ai_search|readiness|strict"
```

### AI Search connectivity test from pod

```bash
kubectl exec -n <namespace> <pod-name> -- curl -sf --max-time 5 "https://<ai-search-endpoint>/indexes?api-version=2024-07-01" -o /dev/null -w "%{http_code}"
```

### AI Search document count

```bash
kubectl exec -n <namespace> <pod-name> -- curl -sf "https://<ai-search-endpoint>/indexes/<index-name>/docs/\$count?api-version=2024-07-01" -H "api-key: <key>"
```

## Resolution Steps

### A. Missing AI Search environment variables

**Root cause**: One or more of `AI_SEARCH_ENDPOINT`, `AI_SEARCH_INDEX`, `AI_SEARCH_VECTOR_INDEX`, or `AI_SEARCH_AUTH_MODE` are not set in the pod spec.

**Fix**:

1. Check ConfigMap and Secret resources for the service:
   ```bash
   kubectl get configmap -n <namespace> | grep catalog-search
   kubectl get secret -n <namespace> | grep catalog-search
   ```
2. Add missing values to the azd environment or Helm values:
   ```bash
   azd env set AI_SEARCH_ENDPOINT "https://<name>.search.windows.net"
   azd env set AI_SEARCH_INDEX "<index-name>"
   azd env set AI_SEARCH_VECTOR_INDEX "<vector-index-name>"
   azd env set AI_SEARCH_AUTH_MODE "managed_identity"
   ```
3. Redeploy the service:
   ```bash
   azd deploy --service ecommerce-catalog-search --no-prompt
   ```

### B. AI Search endpoint unreachable

**Root cause**: The pod cannot reach the AI Search service. Common causes:

- DNS resolution failure (Private DNS zone not linked to AKS VNet)
- Private Endpoint not provisioned or not linked
- NSG or firewall rules blocking outbound traffic on port 443

**Fix**:

1. Test DNS resolution from the pod:
   ```bash
   kubectl exec -n <namespace> <pod-name> -- nslookup <ai-search-name>.search.windows.net
   ```
2. If DNS fails, verify the Private DNS zone `privatelink.search.windows.net` is linked to the AKS VNet:
   ```bash
   az network private-dns zone show -g <rg> -n privatelink.search.windows.net
   az network private-dns link vnet list -g <rg> -z privatelink.search.windows.net -o table
   ```
3. Verify the Private Endpoint exists and is in a `Succeeded` state:
   ```bash
   az network private-endpoint list -g <rg> -o table | grep search
   ```
4. Check NSG rules on the AKS subnet allow outbound HTTPS (443).

### C. AI Search index empty

**Root cause**: The AI Search index exists but contains 0 documents. The service attempts bounded CRUD-based seeding at startup, but seeding may fail if the CRUD service is unavailable or the product catalog is empty.

**Fix**:

1. Confirm the `search-enrichment-agent` has run successfully:
   ```bash
   kubectl logs -n <namespace> -l app=search-enrichment-agent --tail=200 | grep -E "index|enrich|complete"
   ```
2. Check the indexer status in Azure:
   ```bash
   az search indexer status --service-name <search-service> --name <indexer-name> -g <rg>
   ```
3. Verify the CRUD service is accessible and has products:
   ```bash
   kubectl exec -n <namespace> <pod-name> -- curl -sf "http://crud-service:8000/api/products?limit=1"
   ```
4. If needed, trigger a manual enrichment run or re-index via the `search-enrichment-agent`.

### D. Disable strict mode (temporary workaround)

> **Warning**: This workaround allows the pod to pass readiness without AI Search. Search queries will fall back to CRUD adapter/text matching, which may return degraded results.

```bash
kubectl set env deployment/ecommerce-catalog-search -n <namespace> CATALOG_SEARCH_REQUIRE_AI_SEARCH=false
```

Revert after the underlying issue is fixed:

```bash
kubectl set env deployment/ecommerce-catalog-search -n <namespace> CATALOG_SEARCH_REQUIRE_AI_SEARCH=true
```

### E. Foundry agent configuration

**Note**: Missing Foundry agent IDs produce `foundry_runtime_targets_disabled` warnings but do **not** cause 503 on `/ready` for this service.

If agent-powered intelligent search is required:

1. Verify Foundry env vars:
   ```bash
   kubectl exec -n <namespace> <pod-name> -- env | grep -E "FOUNDRY_AGENT_ID|FOUNDRY_ENDPOINT|PROJECT_ENDPOINT|MODEL_DEPLOYMENT"
   ```
2. Set missing values via azd or ConfigMap and redeploy.

## Escalation

| Severity | Condition | Action |
|----------|-----------|--------|
| **P1** | All pods in CrashLoopBackOff, no traffic served | Apply workaround (Resolution D), then investigate root cause |
| **P2** | Pods ready but AI Search returning empty results | Check index population (Resolution C), engage search-enrichment-agent owner |
| **P3** | Foundry warnings in logs, intelligent mode degraded | Schedule Foundry config fix, no immediate pod impact |

**Escalation contacts**:

- Platform/infra issues (networking, DNS, Private Endpoints): Platform Engineering team
- AI Search index/indexer failures: Search Enrichment team (`search-enrichment-agent` owners)
- Foundry agent resolution: AI Platform team
