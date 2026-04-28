# Truth Ingestion

> Full pipeline documentation: [`docs/implementation/truth-layer-agents-guide.md`](../../docs/implementation/truth-layer-agents-guide.md)

## Purpose

Ingests raw product data from PIM (Product Information Management) and DAM (Digital Asset Management) sources into the canonical truth store. Acts as the **first stage** of the Product Truth Layer pipeline.

## Why This Agent Exists

Retail platforms integrate with dozens of PIM/DAM vendors, each with proprietary schemas. This agent creates a single normalized data format (`ProductStyle`/`ProductVariant`) that all downstream agents rely on without coupling to vendor-specific APIs.

## How It Works

1. Receives a product payload via REST endpoint or PIM webhook
2. Applies field mapping (source → canonical schema) using deterministic rules; AI resolves ambiguous mappings
3. Validates against the canonical schema
4. Persists `ProductStyle` / `ProductVariant` to Cosmos DB (partition key: `entity_id`)
5. Publishes `ingestion.completed` event to `ingest-jobs` Event Hub topic
6. Downstream agents (truth-enrichment) subscribe and begin gap analysis

## Key Endpoints

| Method | Path | Purpose |
|--------|------|---------|---|
| POST | `/ingest/product` | Ingest single product |
| POST | `/ingest/bulk` | Batch ingest (1-50 concurrent) |
| POST | `/ingest/sync` | Full PIM paginated sync (background) |
| GET | `/ingest/status/{job_id}` | Job status check |
| POST | `/ingest/webhook` | PIM webhook receiver |
| POST | `/invoke` | Agent entry (actions: `ingest_single`, `ingest_bulk`, `get_status`) |

**MCP Tools** (agent-to-agent): `/ingest/product`, `/ingest/status`, `/ingest/sources`

## Required Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `PROJECT_ENDPOINT` / `FOUNDRY_ENDPOINT` | Yes | Azure AI Foundry endpoint |
| `FOUNDRY_AGENT_ID_FAST` | Yes | SLM agent ID |
| `MODEL_DEPLOYMENT_NAME_FAST` | Yes | SLM deployment name |
| `FOUNDRY_AGENT_ID_RICH` | Yes | LLM agent ID |
| `MODEL_DEPLOYMENT_NAME_RICH` | Yes | LLM deployment name |
| `COSMOS_ACCOUNT_URI` | Yes | Cosmos DB endpoint |
| `COSMOS_DATABASE` | Yes | Database (default: `truth-store`) |
| `COSMOS_CONTAINER` | Yes | Product container (default: `products`) |
| `PLATFORM_JOBS_EVENT_HUB_NAMESPACE_ENV` | Yes | Event Hub namespace FQDN |
| `PIM_BASE_URL` | Yes | Source PIM REST endpoint |
| `PIM_AUTH_TYPE` | Yes | `bearer`, `basic`, or `custom` |
| `PIM_AUTH_TOKEN` | Conditional | Token when auth type is bearer |
| `REDIS_URL` | Optional | Hot cache (degrades gracefully) |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Optional | Telemetry |

## Data Requirements

**Input** — Raw product from PIM:
```json
{
  "product": { "id": "sku-123", "name": "Explorer Jacket", "category": "outerwear" },
  "field_mapping": { "category": "product_type", "name": "title" }
}
```

**Output** — Canonical product in Cosmos DB + event on `ingest-jobs`:
```json
{ "event_type": "ingestion.completed", "entity_id": "sku-123", "status": "success" }
```

## Run/Test commands
```bash
cd apps/truth-ingestion/src
uv sync
uv run uvicorn truth_ingestion.main:app --reload
python -m pytest ../tests
```

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
SERVICE_NAME="truth-ingestion"
APP_PATH="apps/truth-ingestion/src"
DOCKERFILE_PATH="${APP_PATH}/Dockerfile"
AZD_ENV_NAME="dev"
K8S_NAMESPACE="holiday-peak-agents"
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
| PLATFORM_JOBS_EVENT_HUB_NAMESPACE | Yes | Platform-jobs Event Hubs namespace FQDN for `ingest-jobs`; no fallback to retail `EVENT_HUB_NAMESPACE` |
| PLATFORM_JOBS_EVENT_HUB_CONNECTION_STRING | Optional | Needed only when workload identity is not used; no fallback to retail `EVENT_HUB_CONNECTION_STRING` |
| APP_NAME | Recommended | Set to truth-ingestion |
| CRUD_SERVICE_URL | Service-dependent | Required when this service calls CRUD APIs |
| REDIS_URL / COSMOS_* / BLOB_* | Optional | Three-tier memory; service degrades gracefully when absent |
| APPLICATIONINSIGHTS_CONNECTION_STRING | Optional | App telemetry |

Example azd env commands:

```bash
azd env select "${AZD_ENV_NAME}"
azd env set APP_NAME "truth-ingestion"
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
SERVICE_NAME="${SERVICE_NAME}" IMAGE_PREFIX="${ACR_LOGIN_SERVER}" IMAGE_TAG="${IMAGE_TAG}" K8S_NAMESPACE="${K8S_NAMESPACE}" KEDA_ENABLED="false" PUBLICATION_MODE="none" .infra/azd/hooks/render-helm.sh truth-ingestion
helm upgrade --install truth-ingestion .kubernetes/chart --namespace "${K8S_NAMESPACE}" --create-namespace --set serviceName=truth-ingestion --set "image.repository=${IMAGE_REPO}" --set "image.tag=${IMAGE_TAG}" --wait --timeout 5m
```

If you deploy manually, provide env values through a local values file and do not commit secrets.

### 5. Validate deployment

```bash
kubectl rollout status deployment/truth-ingestion -n "${K8S_NAMESPACE}" --timeout=5m
kubectl get pods -n "${K8S_NAMESPACE}" -l app=truth-ingestion
kubectl logs -n "${K8S_NAMESPACE}" -l app=truth-ingestion --tail=100
kubectl port-forward -n "${K8S_NAMESPACE}" deployment/truth-ingestion 8080:8000
curl -s http://localhost:8080/health
curl -s http://localhost:8080/ready
```

### 6. Teardown

Standalone service cleanup:

```bash
helm uninstall truth-ingestion -n "${K8S_NAMESPACE}" || true
kubectl delete configmap truth-ingestion-config -n "${K8S_NAMESPACE}" --ignore-not-found
kubectl delete secret truth-ingestion-secrets -n "${K8S_NAMESPACE}" --ignore-not-found
```

Full environment cleanup (destructive, use only when intended):

```bash
azd down -e "${AZD_ENV_NAME}" --purge --force
```
