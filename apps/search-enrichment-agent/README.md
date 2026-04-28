# Search Enrichment Agent

> Full pipeline documentation: [`docs/implementation/truth-layer-agents-guide.md`](../../docs/implementation/truth-layer-agents-guide.md)

## Purpose

Generates search-optimized content (keywords, facets, marketing copy, sustainability signals) for products and pushes them to Azure AI Search. Acts as the **discovery amplification stage** of the Product Truth Layer pipeline.

## Why This Agent Exists

Raw product attributes are insufficient for high-quality search. Customers search using natural language, synonyms, and intent-based queries. This agent transforms structured product data into discovery-optimized content that powers semantic and keyword search.

## How It Works

1. Subscribes to `search-enrichment-jobs` Event Hub (consumer group: `search-enrichment-agent`)
2. Receives triggers from truth-enrichment (`enrichment.completed`) or truth-hitl (`hitl.approved.search`)
3. Loads approved product truth data
4. Selects enrichment strategy:
   - **Simple**: SLM for products with complete attributes
   - **Complex**: LLM for multi-attribute reasoning
   - **Agentic**: LLM with function calling for orchestrated enrichment
5. Generates: keywords, use cases, marketing bullets, facet tags, SEO title, audience, seasonality
6. Persists `SearchEnrichedProduct` to Cosmos DB
7. Pushes to Azure AI Search (direct push or indexer trigger)

## Key Endpoints

| Method | Path | Purpose |
|--------|------|---------|---|
| POST | `/invoke` | Synchronous enrichment request |
| GET | `/health`, `/ready` | Health probes |

## Required Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `PROJECT_ENDPOINT` / `FOUNDRY_ENDPOINT` | Yes | Azure AI Foundry endpoint |
| `FOUNDRY_AGENT_ID_FAST` | Yes | SLM agent ID (simple strategy) |
| `MODEL_DEPLOYMENT_NAME_FAST` | Yes | SLM deployment |
| `FOUNDRY_AGENT_ID_RICH` | Yes | LLM agent ID (complex/agentic) |
| `MODEL_DEPLOYMENT_NAME_RICH` | Yes | LLM deployment |
| `AI_SEARCH_ENDPOINT` | Yes | Azure AI Search endpoint |
| `AI_SEARCH_ADMIN_KEY` / `AI_SEARCH_CREDENTIAL` | Yes | Search credentials |
| `AI_SEARCH_INDEX_NAME` | Yes | Target index name |
| `AI_SEARCH_INDEXER_NAME` | Optional | Indexer for pull-mode sync |
| `AI_SEARCH_PUSH_IMMEDIATE` | Optional | Direct push (`true`) vs indexer (default) |
| `PLATFORM_JOBS_EVENT_HUB_NAMESPACE_ENV` | Yes | Event Hub namespace |
| `COSMOS_ACCOUNT_URI`, `COSMOS_DATABASE`, `COSMOS_CONTAINER` | Yes | Enriched product storage |
| `BLOB_ACCOUNT_URL`, `TRUTH_PRODUCT_BLOB_CONTAINER` | Optional | Approved truth source |
| `REDIS_URL` | Optional | Hot cache |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Optional | Telemetry |

## Data Requirements

**Inbound** (from `search-enrichment-jobs` Event Hub):
```json
{ "event_type": "enrichment.completed", "data": { "entity_id": "TEST-LIVE-001" } }
```

**Output** — `SearchEnrichedProduct` in Cosmos DB + AI Search:
```json
{
  "id": "TEST-LIVE-001",
  "enrichedData": {
    "search_keywords": ["waterproof jacket", "gore-tex", "navy"],
    "use_cases": ["Winter hiking", "Urban commute"],
    "facet_tags": ["color:navy", "material:gore-tex"],
    "marketing_bullets": ["100% waterproof", "Breathable"],
    "completeness_pct": 0.95
  }
}
```

## Run/Test commands
```bash
cd apps/search-enrichment-agent/src
uv sync
uv run uvicorn search_enrichment_agent.main:app --reload
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
SERVICE_NAME="search-enrichment-agent"
APP_PATH="apps/search-enrichment-agent/src"
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
| PLATFORM_JOBS_EVENT_HUB_NAMESPACE | Yes | Platform-jobs Event Hubs namespace FQDN for `search-enrichment-jobs`; no fallback to retail `EVENT_HUB_NAMESPACE` |
| PLATFORM_JOBS_EVENT_HUB_CONNECTION_STRING | Optional | Needed only when workload identity is not used; no fallback to retail `EVENT_HUB_CONNECTION_STRING` |
| APP_NAME | Recommended | Set to search-enrichment-agent |
| CRUD_SERVICE_URL | Service-dependent | Required when this service calls CRUD APIs |
| REDIS_URL / COSMOS_* / BLOB_* | Optional | Three-tier memory; service degrades gracefully when absent |
| APPLICATIONINSIGHTS_CONNECTION_STRING | Optional | App telemetry |

Example azd env commands:

```bash
azd env select "${AZD_ENV_NAME}"
azd env set APP_NAME "search-enrichment-agent"
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
SERVICE_NAME="${SERVICE_NAME}" IMAGE_PREFIX="${ACR_LOGIN_SERVER}" IMAGE_TAG="${IMAGE_TAG}" K8S_NAMESPACE="${K8S_NAMESPACE}" KEDA_ENABLED="false" PUBLICATION_MODE="none" .infra/azd/hooks/render-helm.sh search-enrichment-agent
helm upgrade --install search-enrichment-agent .kubernetes/chart --namespace "${K8S_NAMESPACE}" --create-namespace --set serviceName=search-enrichment-agent --set "image.repository=${IMAGE_REPO}" --set "image.tag=${IMAGE_TAG}" --wait --timeout 5m
```

If you deploy manually, provide env values through a local values file and do not commit secrets.

### 5. Validate deployment

```bash
kubectl rollout status deployment/search-enrichment-agent -n "${K8S_NAMESPACE}" --timeout=5m
kubectl get pods -n "${K8S_NAMESPACE}" -l app=search-enrichment-agent
kubectl logs -n "${K8S_NAMESPACE}" -l app=search-enrichment-agent --tail=100
kubectl port-forward -n "${K8S_NAMESPACE}" deployment/search-enrichment-agent 8080:8000
curl -s http://localhost:8080/health
curl -s http://localhost:8080/ready
```

### 6. Teardown

Standalone service cleanup:

```bash
helm uninstall search-enrichment-agent -n "${K8S_NAMESPACE}" || true
kubectl delete configmap search-enrichment-agent-config -n "${K8S_NAMESPACE}" --ignore-not-found
kubectl delete secret search-enrichment-agent-secrets -n "${K8S_NAMESPACE}" --ignore-not-found
```

Full environment cleanup (destructive, use only when intended):

```bash
azd down -e "${AZD_ENV_NAME}" --purge --force
```
