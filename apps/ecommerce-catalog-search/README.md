# Ecommerce Catalog Search

## Purpose
Provides product discovery and ACP-aligned catalog search responses.

## Responsibilities
- Resolve search queries into relevant product sets.
- Default to intelligent search mode when no mode is specified, while keeping explicit keyword mode available for demos and compatibility.
- Return inventory-aware and commerce-ready product context.
- Support intelligent search enrichment for downstream flows.
- Emit explicit degraded fallback metadata (`result_type`, `degraded_reason`, `fallback_keywords`) when model synthesis times out or fails.
- Uses generic intent classification with model-first evaluation and deterministic fallback.
- Runs a full retrieval cycle (baseline keyword retrieval, intent-driven query expansion, semantic retrieval, and fallback rerank) to return relevant results.

## Key endpoints or interfaces
- `POST /invoke` for synchronous service requests.
- MCP interfaces under `/mcp/*` for agent-to-agent usage.
- Event Hub subscription: `product-events` / consumer group `catalog-search-group`.

## Run/Test commands
```bash
cd apps/ecommerce-catalog-search/src
uv sync
uv run uvicorn ecommerce_catalog_search.main:app --reload
python -m pytest ../tests
```

## Configuration notes
- Uses Foundry model settings (`PROJECT_ENDPOINT` or `FOUNDRY_ENDPOINT`, fast/rich model identifiers).
- Supports Redis/Cosmos/Blob memory configuration via shared memory settings.
- Requires Event Hub namespace and consumer configuration for background jobs.
- Uses strict AI Search runtime mode by default on AKS unless `CATALOG_SEARCH_REQUIRE_AI_SEARCH` is explicitly overridden.

---

## Standalone Deployment - azd-first (ACR -> AKS)

This service supports standalone deployment to an existing Holiday Peak Hub Azure environment.
Use azd as the primary deployment path. Use the manual ACR -> AKS path only when you need isolated rollout or troubleshooting outside the standard workflow.

### Strict AI Search runtime contract (AKS/image path)

- Strict mode defaults to enabled when running in Kubernetes (`KUBERNETES_SERVICE_HOST` detected). Set `CATALOG_SEARCH_REQUIRE_AI_SEARCH=true` explicitly in deployment env to make intent unambiguous.
- During startup, the service checks AI Search status. When Search is configured but the index is empty, it attempts bounded CRUD-based seeding before serving traffic.
- During readiness checks, strict mode can trigger another bounded seed attempt when the index is still empty. If Search remains not ready, `/ready` returns `503` with `catalog_ai_search` details.
- In strict mode, degraded AI Search conditions block adapter/text fallback for query resolution. This protects runtime behavior from silently serving a non-AI Search path in AKS.

### Prerequisites

| Tool | Why it is needed |
|------|------------------|
| az CLI | Azure authentication and resource operations |
| azd | Environment selection and service deploy |
| docker (or az acr build) | Build and push the container image |
| kubectl + helm | Manual AKS deployment and validation |

### 1. Set service variables

```bash
SERVICE_NAME="ecommerce-catalog-search"
APP_PATH="apps/ecommerce-catalog-search/src"
DOCKERFILE_PATH="${APP_PATH}/Dockerfile"
AZD_ENV_NAME="dev"
K8S_NAMESPACE="holiday-peak"
IMAGE_TAG="$(git rev-parse --short HEAD)"
```

### 2. Configure required environment variables

Set these in the selected azd environment (recommended) or in your manual Helm values file:

| Variable | Required (AKS strict path) | Notes |
|----------|----------------------------|-------|
| CATALOG_SEARCH_REQUIRE_AI_SEARCH | Yes | Set to `true` for strict runtime contract; use `false` only for non-strict local/debug paths |
| AI_SEARCH_ENDPOINT | Yes | Azure AI Search endpoint |
| AI_SEARCH_INDEX | Yes | Keyword/SKU lookup index |
| AI_SEARCH_VECTOR_INDEX | Yes | Vector/hybrid index |
| AI_SEARCH_INDEXER_NAME | Yes | Indexer identifier used by deployment/runtime wiring |
| AI_SEARCH_AUTH_MODE | Yes | `managed_identity` (recommended) or `api_key` |
| EMBEDDING_DEPLOYMENT_NAME | Yes | Embedding deployment name used by vector flows |
| AI_SEARCH_KEY | Conditional | Required only when `AI_SEARCH_AUTH_MODE=api_key` |
| CATALOG_SEARCH_SEED_MAX_ATTEMPTS | Optional | Bounded startup/readiness seed budget (default `2`, min `1`, max `10`) |
| CATALOG_SEARCH_SEED_BATCH_SIZE | Optional | Per-attempt seed batch size (default `50`, min `1`, max `100`) |
| CATALOG_SEARCH_SEED_HTTP_TIMEOUT_SECONDS | Optional | CRUD seed fetch timeout in seconds (default `5`) |
| CRUD_SERVICE_URL | Yes | Source for CRUD bootstrap seeding and adapter lookups |
| PROJECT_ENDPOINT or FOUNDRY_ENDPOINT | Yes | Azure AI Foundry project endpoint |
| PROJECT_NAME or FOUNDRY_PROJECT_NAME | Yes | Foundry project name used by runtime ensure flow |
| FOUNDRY_AGENT_ID_FAST or FOUNDRY_AGENT_NAME_FAST | Yes | Fast-role Foundry agent identity |
| MODEL_DEPLOYMENT_NAME_FAST | Yes | Fast-role deployment name |
| FOUNDRY_AGENT_ID_RICH or FOUNDRY_AGENT_NAME_RICH | Yes | Rich-role Foundry agent identity |
| MODEL_DEPLOYMENT_NAME_RICH | Yes | Rich-role deployment name |
| KEY_VAULT_URI | Yes | Key Vault endpoint for secret-backed runtime configuration |
| EVENT_HUB_NAMESPACE or EVENTHUB_NAMESPACE | Yes | Event Hub namespace FQDN |
| APP_NAME | Recommended | Set to `ecommerce-catalog-search` |
| REDIS_URL / COSMOS_* / BLOB_* | Optional | Three-tier memory configuration |
| APPLICATIONINSIGHTS_CONNECTION_STRING | Optional | App telemetry |

### Authorization and RBAC expectations by dependency

| Dependency | Runtime auth pattern | Authorization expectation |
|------------|----------------------|---------------------------|
| Azure AI Search | Managed identity (`AI_SEARCH_AUTH_MODE=managed_identity`) or API key | Managed identity should have `Search Index Data Contributor` on the AI Search service for query + upsert/delete + seed flows. If using API key mode, `AI_SEARCH_KEY` must grant equivalent index data permissions. |
| CRUD source (`CRUD_SERVICE_URL`) | Internal HTTP call from service container | The service does not inject an auth header for CRUD requests; enforce trust with AKS network boundaries and/or gateway policy. Runtime needs access to `GET /api/products` and related CRUD product endpoints. |
| Azure Key Vault (`KEY_VAULT_URI`) | Managed identity | Workload identity must have `Key Vault Secrets User` on the target vault to resolve secret-backed settings. |
| Azure AI Foundry (`PROJECT_ENDPOINT`, `PROJECT_NAME`) | `DefaultAzureCredential` via managed identity | Identity must have project/model permissions required to resolve or ensure Foundry agents and invoke configured deployments (`MODEL_DEPLOYMENT_NAME_FAST`, `MODEL_DEPLOYMENT_NAME_RICH`). |

Example azd env commands:

```bash
azd env select "${AZD_ENV_NAME}"
azd env set APP_NAME "ecommerce-catalog-search"
# repeat azd env set for the required values above
```

### 3. Build and push image

```bash
ACR_NAME="<existing-acr-name>"
az acr login --name "${ACR_NAME}"
ACR_LOGIN_SERVER="$(az acr show --name "${ACR_NAME}" --query loginServer -o tsv)"
IMAGE_REPO="${ACR_LOGIN_SERVER}/${SERVICE_NAME}"
docker build --target prod --tag "${IMAGE_REPO}:${IMAGE_TAG}" --tag "${IMAGE_REPO}:latest" -f "${DOCKERFILE_PATH}" "${APP_PATH}"
docker push "${IMAGE_REPO}:${IMAGE_TAG}"
docker push "${IMAGE_REPO}:latest"
```

ACR remote build alternative:

```bash
az acr build --registry "${ACR_NAME}" --image "${SERVICE_NAME}:${IMAGE_TAG}" --file "${DOCKERFILE_PATH}" "${APP_PATH}"
```

### 4. Render and deploy

Preferred (azd-first):

```bash
azd deploy --service "${SERVICE_NAME}" -e "${AZD_ENV_NAME}" --no-prompt
```

Manual render/deploy path:

```bash
SERVICE_NAME="${SERVICE_NAME}" IMAGE_PREFIX="${ACR_LOGIN_SERVER}" IMAGE_TAG="${IMAGE_TAG}" K8S_NAMESPACE="${K8S_NAMESPACE}" KEDA_ENABLED="false" PUBLICATION_MODE="none" .infra/azd/hooks/render-helm.sh ecommerce-catalog-search
helm upgrade --install ecommerce-catalog-search .kubernetes/chart --namespace "${K8S_NAMESPACE}" --create-namespace --set serviceName=ecommerce-catalog-search --set "image.repository=${IMAGE_REPO}" --set "image.tag=${IMAGE_TAG}" --wait --timeout 5m
```

If you deploy manually, provide env values through a local values file and do not commit secrets.

### 5. Validate deployment

```bash
kubectl rollout status deployment/ecommerce-catalog-search -n "${K8S_NAMESPACE}" --timeout=5m
kubectl get pods -n "${K8S_NAMESPACE}" -l app=ecommerce-catalog-search
kubectl logs -n "${K8S_NAMESPACE}" -l app=ecommerce-catalog-search --tail=100
kubectl port-forward -n "${K8S_NAMESPACE}" deployment/ecommerce-catalog-search 8080:8000
curl -s http://localhost:8080/health
curl -s http://localhost:8080/ready
```

### 6. Teardown

Standalone service cleanup:

```bash
helm uninstall ecommerce-catalog-search -n "${K8S_NAMESPACE}" || true
kubectl delete configmap ecommerce-catalog-search-config -n "${K8S_NAMESPACE}" --ignore-not-found
kubectl delete secret ecommerce-catalog-search-secrets -n "${K8S_NAMESPACE}" --ignore-not-found
```

Full environment cleanup (destructive, use only when intended):

```bash
azd down -e "${AZD_ENV_NAME}" --purge --force
```
