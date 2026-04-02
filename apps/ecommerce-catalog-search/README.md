# Ecommerce Catalog Search

## Purpose
Provides product discovery and ACP-aligned catalog search responses.

## Responsibilities
- Resolve search queries into relevant product sets.
- Return inventory-aware and commerce-ready product context.
- Support intelligent search enrichment for downstream flows.

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

---

## Standalone Deployment - azd-first (ACR -> AKS)

This service supports standalone deployment to an existing Holiday Peak Hub Azure environment.
Use azd as the primary deployment path. Use the manual ACR -> AKS path only when you need isolated rollout or troubleshooting outside the standard workflow.

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

| Variable | Required | Notes |
|----------|----------|-------|
| PROJECT_ENDPOINT or FOUNDRY_ENDPOINT | Yes | Azure AI Foundry project endpoint |
| FOUNDRY_AGENT_ID_FAST | Yes | Fast-path model agent id |
| MODEL_DEPLOYMENT_NAME_FAST | Yes | Fast-path deployment name |
| FOUNDRY_AGENT_ID_RICH | Yes | Rich-path model agent id |
| MODEL_DEPLOYMENT_NAME_RICH | Yes | Rich-path deployment name |
| EVENT_HUB_NAMESPACE or EVENTHUB_NAMESPACE | Yes | Event Hub namespace FQDN |
| EVENT_HUB_CONNECTION_STRING or EVENTHUB_CONNECTION_STRING | Usually | Needed when workload identity is not used |
| APP_NAME | Recommended | Set to ecommerce-catalog-search |
| CRUD_SERVICE_URL | Service-dependent | Required when this service calls CRUD APIs |
| REDIS_URL / COSMOS_* / BLOB_* | Optional | Three-tier memory; service degrades gracefully when absent |
| APPLICATIONINSIGHTS_CONNECTION_STRING | Optional | App telemetry |

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
