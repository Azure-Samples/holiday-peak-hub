# Truth HITL

> Last Updated: 2026-04-30

> Full pipeline documentation: [`docs/implementation/truth-layer-agents-guide.md`](../../docs/implementation/truth-layer-agents-guide.md)

## Purpose

Manages the human-in-the-loop review queue for AI-proposed product attributes. Acts as the **quality gate** between AI-generated proposals and canonical approved truth.

## Domain Bounded Context
- **Owner**: Truth Layer team
- **Bounded Context**: Truth Layer

## Why This Agent Exists

AI-generated product attributes cannot be trusted blindly — incorrect values damage catalog quality and customer trust. This agent ensures **human validation** before any AI-proposed value becomes truth, providing full audit trails and decision governance.

## How It Works

1. Subscribes to `hitl-jobs` Event Hub (consumer group: `hitl-service`)
2. Receives enrichment proposals from truth-enrichment
3. Queues proposals in the **ReviewManager** (pending review)
4. Exposes review queue via REST endpoints for human reviewers
5. On approval: publishes to `export-jobs` (PIM writeback) and `search-enrichment-jobs` (search re-indexing)
6. On rejection: logs decision and removes from queue

## Key Endpoints

| Method | Path | Purpose |
|--------|------|---------|---|
| GET | `/review/queue` | List pending items (paginated, filterable) |
| GET | `/review/stats` | Queue statistics (pending/approved/rejected) |
| GET | `/review/{entity_id}` | Proposals for one product |
| POST | `/review/{entity_id}/approve` | Approve proposal(s) |
| POST | `/review/{entity_id}/reject` | Reject with reason |
| POST | `/review/{entity_id}/edit` | Edit value and approve |
| POST | `/review/approve/batch` | Batch approve |
| POST | `/review/reject/batch` | Batch reject |
| POST | `/invoke` | Agent entry (actions: `stats`, `queue`, `detail`, `audit`) |

**MCP Tools**: `/hitl/queue`, `/hitl/stats`, `/hitl/audit`, `/review/get_proposal`

## Required Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `PROJECT_ENDPOINT` / `FOUNDRY_ENDPOINT` | Yes | Azure AI Foundry endpoint |
| `FOUNDRY_AGENT_ID_FAST` | Yes | SLM for confidence re-evaluation |
| `MODEL_DEPLOYMENT_NAME_FAST` | Yes | SLM deployment |
| `FOUNDRY_AGENT_ID_RICH` | Yes | LLM for disputed proposal reasoning |
| `MODEL_DEPLOYMENT_NAME_RICH` | Yes | LLM deployment |
| `PLATFORM_JOBS_EVENT_HUB_NAMESPACE_ENV` | Yes | Event Hub namespace |
| `COSMOS_ACCOUNT_URI`, `COSMOS_DATABASE` | Optional | Warm memory tier |
| `REDIS_URL` | Optional | Hot cache |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Optional | Telemetry |

## Data Requirements

**Inbound** (from `hitl-jobs` Event Hub):
```json
{
  "event_type": "attribute.proposed",
  "entity_id": "TEST-LIVE-001",
  "field_name": "color",
  "proposed_value": "Navy Blue",
  "confidence": 0.92
}
```

**Review Decision** (POST body):
```json
{
  "attr_ids": ["attr-uuid"],
  "reason": "Correct per product photography",
  "reviewed_by": "reviewer@company.com"
}
```

## Event Production

- `export-jobs`: `{ "event_type": "hitl.approved", "entity_id": "...", "approved_fields": ["color"] }`
- `search-enrichment-jobs`: `{ "event_type": "hitl.approved.search", "entity_id": "...", "approved_fields": ["color"] }`

## Run/Test commands
```bash
cd apps/truth-hitl/src
uv sync
uv run uvicorn truth_hitl.main:app --reload
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
SERVICE_NAME="truth-hitl"
APP_PATH="apps/truth-hitl/src"
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
| PLATFORM_JOBS_EVENT_HUB_NAMESPACE | Yes | Platform-jobs Event Hubs namespace FQDN for `hitl-jobs`; no fallback to retail `EVENT_HUB_NAMESPACE` |
| PLATFORM_JOBS_EVENT_HUB_CONNECTION_STRING | Optional | Needed only when workload identity is not used; no fallback to retail `EVENT_HUB_CONNECTION_STRING` |
| APP_NAME | Recommended | Set to truth-hitl |
| CRUD_SERVICE_URL | Service-dependent | Required when this service calls CRUD APIs |
| REDIS_URL / COSMOS_* / BLOB_* | Optional | Three-tier memory; service degrades gracefully when absent |
| APPLICATIONINSIGHTS_CONNECTION_STRING | Optional | App telemetry |

Example azd env commands:

```bash
azd env select "${AZD_ENV_NAME}"
azd env set APP_NAME "truth-hitl"
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
SERVICE_NAME="${SERVICE_NAME}" IMAGE_PREFIX="${ACR_LOGIN_SERVER}" IMAGE_TAG="${IMAGE_TAG}" K8S_NAMESPACE="${K8S_NAMESPACE}" KEDA_ENABLED="false" PUBLICATION_MODE="none" .infra/azd/hooks/render-helm.sh truth-hitl
helm upgrade --install truth-hitl .kubernetes/chart --namespace "${K8S_NAMESPACE}" --create-namespace --set serviceName=truth-hitl --set "image.repository=${IMAGE_REPO}" --set "image.tag=${IMAGE_TAG}" --wait --timeout 5m
```

If you deploy manually, provide env values through a local values file and do not commit secrets.

### 5. Validate deployment

```bash
kubectl rollout status deployment/truth-hitl -n "${K8S_NAMESPACE}" --timeout=5m
kubectl get pods -n "${K8S_NAMESPACE}" -l app=truth-hitl
kubectl logs -n "${K8S_NAMESPACE}" -l app=truth-hitl --tail=100
kubectl port-forward -n "${K8S_NAMESPACE}" deployment/truth-hitl 8080:8000
curl -s http://localhost:8080/health
curl -s http://localhost:8080/ready
```

### 6. Teardown

Standalone service cleanup:

```bash
helm uninstall truth-hitl -n "${K8S_NAMESPACE}" || true
kubectl delete configmap truth-hitl-config -n "${K8S_NAMESPACE}" --ignore-not-found
kubectl delete secret truth-hitl-secrets -n "${K8S_NAMESPACE}" --ignore-not-found
```

Full environment cleanup (destructive, use only when intended):

```bash
azd down -e "${AZD_ENV_NAME}" --purge --force
```
