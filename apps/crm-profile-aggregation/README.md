# CRM Profile Aggregation

> Last Updated: 2026-04-30

## Purpose

Builds unified customer profiles by aggregating identity, contact, and engagement context from distributed CRM and interaction sources. Resolves profile-level signals for downstream decisioning agents.

## Domain Bounded Context
- **Owner**: CRM team
- **Bounded Context**: CRM

## Endpoints

### REST
| Method | Path | Description |
|--------|------|-------------|
| POST | `/invoke` | Synchronous agent invocation |
| GET | `/health` | Liveness probe |
| GET | `/ready` | Readiness probe |

### MCP Tools
| Tool | Description |
|------|-------------|
| `/profile/contact-context` | Retrieve full contact context with interactions |
| `/profile/summary` | AI-generated profile summary |
| `/profile/account-summary` | Account-level aggregation |

### Event Subscriptions
| Topic | Consumer Group | Action |
|-------|---------------|--------|
| `user-events` | `profile-agg-group` | Update profile on user changes |
| `order-events` | `profile-agg-group` | Incorporate purchase history |

## Model Routing
- **SLM (fast)**: GPT-5-nano via `FOUNDRY_AGENT_ID_FAST`
- **LLM (rich)**: GPT-4o via `FOUNDRY_AGENT_ID_RICH`

## Memory Usage
| Tier | Purpose |
|------|---------||
| Hot (Redis) | Cached profile lookups (TTL 300s) |
| Warm (Cosmos DB) | Aggregated profile state |
| Cold (Blob) | Historical profile snapshots |

## Environment Variables
| Variable | Required | Description |
|----------|----------|-------------|
| `PROJECT_ENDPOINT` | Yes | Azure AI Foundry project endpoint |
| `FOUNDRY_AGENT_ID_FAST` | Yes | SLM agent ID |
| `MODEL_DEPLOYMENT_NAME_FAST` | Yes | SLM deployment name |
| `FOUNDRY_AGENT_ID_RICH` | Yes | LLM agent ID |
| `MODEL_DEPLOYMENT_NAME_RICH` | Yes | LLM deployment name |
| `REDIS_URL` | No | Redis connection URL |
| `COSMOS_ACCOUNT_URI` | No | Cosmos DB endpoint |
| `EVENTHUB_NAMESPACE` | Yes | Event Hub namespace |

## Local Development
```bash
cd apps/crm-profile-aggregation/src
uv sync
uv run uvicorn crm_profile_aggregation.main:app --reload --port 8002
```

## Test Coverage
```bash
python -m pytest apps/crm-profile-aggregation/tests
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
SERVICE_NAME="crm-profile-aggregation"
APP_PATH="apps/crm-profile-aggregation/src"
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
| EVENT_HUB_NAMESPACE or EVENTHUB_NAMESPACE | Yes | Event Hub namespace FQDN |
| EVENT_HUB_CONNECTION_STRING or EVENTHUB_CONNECTION_STRING | Usually | Needed when workload identity is not used |
| APP_NAME | Recommended | Set to crm-profile-aggregation |
| CRUD_SERVICE_URL | Service-dependent | Required when this service calls CRUD APIs |
| REDIS_URL / COSMOS_* / BLOB_* | Optional | Three-tier memory; service degrades gracefully when absent |
| APPLICATIONINSIGHTS_CONNECTION_STRING | Optional | App telemetry |

Example azd env commands:

```bash
azd env select "${AZD_ENV_NAME}"
azd env set APP_NAME "crm-profile-aggregation"
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
SERVICE_NAME="${SERVICE_NAME}" IMAGE_PREFIX="${ACR_LOGIN_SERVER}" IMAGE_TAG="${IMAGE_TAG}" K8S_NAMESPACE="${K8S_NAMESPACE}" KEDA_ENABLED="false" PUBLICATION_MODE="none" .infra/azd/hooks/render-helm.sh crm-profile-aggregation
helm upgrade --install crm-profile-aggregation .kubernetes/chart --namespace "${K8S_NAMESPACE}" --create-namespace --set serviceName=crm-profile-aggregation --set "image.repository=${IMAGE_REPO}" --set "image.tag=${IMAGE_TAG}" --wait --timeout 5m
```

If you deploy manually, provide env values through a local values file and do not commit secrets.

### 5. Validate deployment

```bash
kubectl rollout status deployment/crm-profile-aggregation -n "${K8S_NAMESPACE}" --timeout=5m
kubectl get pods -n "${K8S_NAMESPACE}" -l app=crm-profile-aggregation
kubectl logs -n "${K8S_NAMESPACE}" -l app=crm-profile-aggregation --tail=100
kubectl port-forward -n "${K8S_NAMESPACE}" deployment/crm-profile-aggregation 8080:8000
curl -s http://localhost:8080/health
curl -s http://localhost:8080/ready
```

### 6. Teardown

Standalone service cleanup:

```bash
helm uninstall crm-profile-aggregation -n "${K8S_NAMESPACE}" || true
kubectl delete configmap crm-profile-aggregation-config -n "${K8S_NAMESPACE}" --ignore-not-found
kubectl delete secret crm-profile-aggregation-secrets -n "${K8S_NAMESPACE}" --ignore-not-found
```

Full environment cleanup (destructive, use only when intended):

```bash
azd down -e "${AZD_ENV_NAME}" --purge --force
```
