# Truth Enrichment

> Last Updated: 2026-04-30

> Full pipeline documentation: [`docs/implementation/truth-layer-agents-guide.md`](../../docs/implementation/truth-layer-agents-guide.md)

## Purpose

Detects missing product attributes by comparing ingested products against category-specific schemas, then proposes AI-generated values using text reasoning and vision analysis. Acts as the **second stage** of the Product Truth Layer pipeline.

## Domain Bounded Context
- **Owner**: Truth Layer team
- **Bounded Context**: Truth Layer

## Why This Agent Exists

Products arrive from PIM with incomplete data — missing colors, materials, dimensions, care instructions. Manual data entry is expensive and slow. This agent automates attribute gap-fill using AI while maintaining a human review checkpoint for quality assurance.

## How It Works

1. Loads product from **Blob Storage** (`{entity_id}.json` in the `products` container)
2. Loads category schema from **Blob Storage** (`_schemas/{category}.json`)
3. **Gap detection** — Compares product attributes against `required_fields` in the schema
4. **Enrichment** (two strategies):
   - **Agentic** (default): LLM orchestrates tool calls to decide enrichment approach
   - **Sequential fallback**: SLM enriches each field independently
5. For each gap: builds prompt → calls AI model → scores confidence → persists proposal
6. Publishes `attribute.proposed` to `hitl-jobs` Event Hub (resilient — failure is logged, not fatal)
7. Publishes `enrichment.completed` to `search-enrichment-jobs`

## Key Endpoints

| Method | Path | Purpose |
|--------|------|---------|---|
| POST | `/invoke` | Full product enrichment (detect gaps + enrich all) |
| POST | `/enrich/product/{entity_id}` | Enrich all gaps for a product |
| POST | `/enrich/field` | Enrich a single specific field |
| GET | `/enrich/status/{job_id}` | Job status check |

**MCP Tools**: `/enrich/product`

## Required Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `PROJECT_ENDPOINT` / `FOUNDRY_ENDPOINT` | Yes | Azure AI Foundry endpoint |
| `FOUNDRY_AGENT_ID_FAST` | Yes | SLM agent ID (per-field enrichment) |
| `MODEL_DEPLOYMENT_NAME_FAST` | Yes | SLM deployment (e.g., `gpt-4-1-nano`) |
| `FOUNDRY_AGENT_ID_RICH` | Yes | LLM agent ID (agentic orchestration) |
| `MODEL_DEPLOYMENT_NAME_RICH` | Yes | LLM deployment (e.g., `gpt-4-1`) |
| `BLOB_ACCOUNT_URL` | Yes | Blob Storage URL for products |
| `TRUTH_PRODUCT_BLOB_CONTAINER` | Yes | Container name (e.g., `products`) |
| `PLATFORM_JOBS_EVENT_HUB_NAMESPACE_ENV` | Yes | Event Hub namespace |
| `COSMOS_ACCOUNT_URI`, `COSMOS_DATABASE` | Yes | Cosmos DB for proposed attributes |
| `DAM_MAX_IMAGES` | Optional | Max images for vision analysis (default: 4) |
| `REDIS_URL` | Optional | Hot cache |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Optional | Telemetry |

## Data Requirements

**Product in Blob** (`{entity_id}.json`):
```json
{
  "entity_id": "TEST-LIVE-001",
  "name": "Explorer Waterproof Jacket",
  "category": "outerwear",
  "attributes": { "color": null, "material": null }
}
```

**Schema in Blob** (`_schemas/outerwear.json`):
```json
{
  "category": "outerwear",
  "required_fields": ["color", "material", "weight_kg"],
  "field_definitions": {
    "color": { "type": "string", "description": "Primary visible color" }
  }
}
```

## Event Production

- `hitl-jobs`: `{ "event_type": "attribute.proposed", "entity_id": "...", "field_name": "color", "proposed_value": "Navy Blue" }`
- `search-enrichment-jobs`: `{ "event_type": "enrichment.completed", "entity_id": "...", "proposed_count": 2 }`

## Run/Test commands
```bash
cd apps/truth-enrichment/src
uv sync
uv run uvicorn truth_enrichment.main:app --reload
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
SERVICE_NAME="truth-enrichment"
APP_PATH="apps/truth-enrichment/src"
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
| PLATFORM_JOBS_EVENT_HUB_NAMESPACE | Yes | Platform-jobs Event Hubs namespace FQDN for `enrichment-jobs`; no fallback to retail `EVENT_HUB_NAMESPACE` |
| PLATFORM_JOBS_EVENT_HUB_CONNECTION_STRING | Optional | Needed only when workload identity is not used; no fallback to retail `EVENT_HUB_CONNECTION_STRING` |
| APP_NAME | Recommended | Set to truth-enrichment |
| CRUD_SERVICE_URL | Service-dependent | Required when this service calls CRUD APIs |
| REDIS_URL / COSMOS_* / BLOB_* | Optional | Three-tier memory; service degrades gracefully when absent |
| APPLICATIONINSIGHTS_CONNECTION_STRING | Optional | App telemetry |

Example azd env commands:

```bash
azd env select "${AZD_ENV_NAME}"
azd env set APP_NAME "truth-enrichment"
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
SERVICE_NAME="${SERVICE_NAME}" IMAGE_PREFIX="${ACR_LOGIN_SERVER}" IMAGE_TAG="${IMAGE_TAG}" K8S_NAMESPACE="${K8S_NAMESPACE}" KEDA_ENABLED="false" PUBLICATION_MODE="none" .infra/azd/hooks/render-helm.sh truth-enrichment
helm upgrade --install truth-enrichment .kubernetes/chart --namespace "${K8S_NAMESPACE}" --create-namespace --set serviceName=truth-enrichment --set "image.repository=${IMAGE_REPO}" --set "image.tag=${IMAGE_TAG}" --wait --timeout 5m
```

If you deploy manually, provide env values through a local values file and do not commit secrets.

### 5. Validate deployment

```bash
kubectl rollout status deployment/truth-enrichment -n "${K8S_NAMESPACE}" --timeout=5m
kubectl get pods -n "${K8S_NAMESPACE}" -l app=truth-enrichment
kubectl logs -n "${K8S_NAMESPACE}" -l app=truth-enrichment --tail=100
kubectl port-forward -n "${K8S_NAMESPACE}" deployment/truth-enrichment 8080:8000
curl -s http://localhost:8080/health
curl -s http://localhost:8080/ready
```

### 6. Teardown

Standalone service cleanup:

```bash
helm uninstall truth-enrichment -n "${K8S_NAMESPACE}" || true
kubectl delete configmap truth-enrichment-config -n "${K8S_NAMESPACE}" --ignore-not-found
kubectl delete secret truth-enrichment-secrets -n "${K8S_NAMESPACE}" --ignore-not-found
```

Full environment cleanup (destructive, use only when intended):

```bash
azd down -e "${AZD_ENV_NAME}" --purge --force
```
