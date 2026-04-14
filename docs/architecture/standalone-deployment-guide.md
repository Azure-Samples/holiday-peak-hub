# Standalone Deployment Guide

**Version**: 1.0
**Last Updated**: 2026-04-12

How to deploy a single agent service independently on AKS. This guide covers both the quick `azd deploy` path and the manual Helm-based path.

---

## Prerequisites

| Requirement | Version | Check |
|------------|---------|-------|
| Azure CLI | ≥ 2.67 | `az version` |
| Azure CLI `alb` extension | latest | `az extension add --name alb` (required for AGC management) |
| azd | ≥ 1.10 | `azd version` |
| Docker | ≥ 24 | `docker version` |
| Helm | ≥ 3.12 | `helm version` |
| kubectl | ≥ 1.28 | `kubectl version` |
| Python | ≥ 3.13 | `python --version` |
| uv | latest | `uv --version` |

### Azure Resources Required

For standalone (demo) deployment, each service provisions its **own isolated** resources via `.infra/templates/app.bicep.tpl`:

| Resource | SKU | Estimated Cost |
|----------|-----|----------------|
| Azure Cosmos DB | Serverless | ~$25/month (low traffic) |
| Azure Cache for Redis | Standard C0 | ~$40/month |
| Azure Storage Account | StorageV2 | ~$5/month |
| Azure AI Search | Basic | ~$75/month |
| Azure OpenAI (3 deployments) | Standard | ~$100-500/month (usage) |
| AKS (shared or standalone) | Standard_D4ds_v5 | ~$140/month |

**Total per standalone service**: ~$400-800/month

For **shared infrastructure** (production), all 28 services share one set of resources at ~85% cost reduction. See [.infra/README.md](../../.infra/README.md).

---

## Quick Path: `azd deploy`

```bash
# 1. Set your environment
export SERVICE_NAME="ecommerce-catalog-search"  # any of the 28 services
export AZD_ENV="dev"

# 2. Configure required env vars
azd env set PROJECT_ENDPOINT "https://<your-foundry>.api.azureml.ms" -e $AZD_ENV
azd env set FOUNDRY_AGENT_ID_FAST "<fast-agent-id>" -e $AZD_ENV
azd env set FOUNDRY_AGENT_ID_RICH "<rich-agent-id>" -e $AZD_ENV
azd env set MODEL_DEPLOYMENT_NAME_FAST "gpt-5-nano" -e $AZD_ENV
azd env set MODEL_DEPLOYMENT_NAME_RICH "gpt-5" -e $AZD_ENV
azd env set EVENT_HUB_NAMESPACE "<namespace>.servicebus.windows.net" -e $AZD_ENV
azd env set REDIS_URL "rediss://<host>:6380" -e $AZD_ENV
azd env set COSMOS_ACCOUNT_URI "https://<account>.documents.azure.com" -e $AZD_ENV
azd env set BLOB_ACCOUNT_URL "https://<account>.blob.core.windows.net" -e $AZD_ENV
azd env set KEY_VAULT_URI "https://<vault>.vault.azure.net" -e $AZD_ENV

# 3. Deploy (builds, pushes, renders Helm, applies to AKS)
azd deploy --service $SERVICE_NAME -e $AZD_ENV
```

This wraps steps 3–6 of the manual path below.

---

## Manual Path: Docker + Helm

### Step 1: Build the Container Image

```bash
SERVICE_NAME="ecommerce-catalog-search"
APP_PATH="apps/${SERVICE_NAME}"
ACR_LOGIN_SERVER="<your-acr>.azurecr.io"
IMAGE_TAG=$(git rev-parse --short HEAD)

# Build production image
docker build \
  --target prod \
  --tag ${ACR_LOGIN_SERVER}/${SERVICE_NAME}:${IMAGE_TAG} \
  --tag ${ACR_LOGIN_SERVER}/${SERVICE_NAME}:latest \
  -f ${APP_PATH}/Dockerfile \
  ${APP_PATH}

# Push to ACR
az acr login --name <your-acr>
docker push ${ACR_LOGIN_SERVER}/${SERVICE_NAME}:${IMAGE_TAG}
docker push ${ACR_LOGIN_SERVER}/${SERVICE_NAME}:latest
```

### Step 2: Render Helm Manifests

```bash
# Set required Helm render variables
export SERVICE=$SERVICE_NAME
export K8S_NAMESPACE="holiday-peak-agents"  # or per-domain namespace
export CHART_PATH=".kubernetes/chart"
export RENDERED_PATH=".kubernetes/rendered/${SERVICE_NAME}"

# Render using the shared chart
helm template $SERVICE_NAME $CHART_PATH \
  --namespace $K8S_NAMESPACE \
  --set image.repository=${ACR_LOGIN_SERVER}/${SERVICE_NAME} \
  --set image.tag=${IMAGE_TAG} \
  --set service.name=${SERVICE_NAME} \
  --set nodeSelector.agentpool=agents \
  --output-dir $RENDERED_PATH
```

Or use the render hook script:
```bash
bash .infra/azd/hooks/render-helm.sh
```

### Step 3: Deploy to AKS

```bash
# Ensure kubectl context points to your cluster
az aks get-credentials -g <resource-group> -n <cluster-name>

# Create namespace if it doesn't exist
kubectl create namespace $K8S_NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Deploy via Helm
helm upgrade --install $SERVICE_NAME $CHART_PATH \
  --namespace $K8S_NAMESPACE \
  --set image.repository=${ACR_LOGIN_SERVER}/${SERVICE_NAME} \
  --set image.tag=${IMAGE_TAG} \
  --wait --timeout 5m
```

### Step 4: Validate

```bash
# Check rollout status
kubectl rollout status deployment/${SERVICE_NAME} -n $K8S_NAMESPACE

# Check pod logs
kubectl logs -l app=${SERVICE_NAME} -n $K8S_NAMESPACE --tail=50

# Test health endpoint
kubectl port-forward svc/${SERVICE_NAME} 8080:8000 -n $K8S_NAMESPACE
curl http://localhost:8080/health
curl http://localhost:8080/ready
```

---

## Environment Variables Reference

### Required for All Agent Services

| Variable | Description | Example |
|----------|-------------|---------|
| `PROJECT_ENDPOINT` | Azure AI Foundry project endpoint | `https://proj.api.azureml.ms` |
| `FOUNDRY_AGENT_ID_FAST` | SLM agent ID (created via Foundry) | `asst_abc123` |
| `FOUNDRY_AGENT_ID_RICH` | LLM agent ID (created via Foundry) | `asst_def456` |
| `MODEL_DEPLOYMENT_NAME_FAST` | SLM model deployment | `gpt-5-nano` |
| `MODEL_DEPLOYMENT_NAME_RICH` | LLM model deployment | `gpt-5` |
| `EVENT_HUB_NAMESPACE` | Event Hubs namespace FQDN | `ns.servicebus.windows.net` |
| `REDIS_URL` | Redis connection URL | `rediss://host:6380` |
| `COSMOS_ACCOUNT_URI` | Cosmos DB account URI | `https://acct.documents.azure.com` |
| `COSMOS_DATABASE` | Cosmos DB database name | `agent-memory` |
| `COSMOS_CONTAINER` | Cosmos DB container name | `warm-memory` |
| `BLOB_ACCOUNT_URL` | Blob Storage account URL | `https://acct.blob.core.windows.net` |
| `BLOB_CONTAINER` | Blob container name | `cold-memory` |
| `KEY_VAULT_URI` | Key Vault URI | `https://kv.vault.azure.net` |
| `CRUD_SERVICE_URL` | CRUD service base URL | `http://crud-service:8000` |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `FOUNDRY_STREAM` | Enable streaming responses | `false` |
| `FOUNDRY_STRICT_ENFORCEMENT` | Enforce Foundry prompt governance | `true` |
| `SELF_HEALING_ENABLED` | Enable self-healing runtime | `false` |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | App Insights connection | (disabled) |

### Service-Specific

| Service | Extra Variables |
|---------|----------------|
| `ecommerce-catalog-search` | `AI_SEARCH_ENDPOINT`, `AI_SEARCH_INDEX`, `AI_SEARCH_VECTOR_INDEX`, `CATALOG_SEARCH_REQUIRE_AI_SEARCH` |
| `truth-*` services | `PLATFORM_JOBS_EVENT_HUB_NAMESPACE` (separate from retail Event Hubs) |

---

## Helm Chart Configuration

The shared Helm chart at `.kubernetes/chart/` supports these key values:

```yaml
# .kubernetes/chart/values.yaml (key overrides for standalone)
replicaCount: 1                    # Single replica for standalone
service:
  type: ClusterIP
  port: 80
  targetPort: 8000

image:
  repository: <acr-name>.azurecr.io/<service-name>
  tag: latest

resources:
  requests:
    cpu: 250m
    memory: 256Mi
  limits:
    cpu: 500m
    memory: 512Mi

nodeSelector:
  workload: agents                 # Target the agents node pool

tolerations:
  - key: workload
    value: agents
    effect: NoSchedule

probes:
  startup:
    path: /health
    initialDelaySeconds: 10
  liveness:
    path: /health
    periodSeconds: 30
  readiness:
    path: /ready
    periodSeconds: 10

autoscaling:
  enabled: false                   # Disable KEDA for standalone demo
```

### Per-Service Overrides

Create a values override file for each service:

```bash
# Example: apps/ecommerce-catalog-search/values-standalone.yaml
helm install catalog-search .kubernetes/chart/ \
  -f .kubernetes/chart/values.yaml \
  -f apps/ecommerce-catalog-search/values-standalone.yaml \
  -n holiday-peak-agents \
  --set image.tag=$(git rev-parse --short HEAD)
```

---

## Namespace Strategy (ADR-034)

All agent services deploy to a single shared namespace per [ADR-034](../architecture/adrs/adr-034-namespace-isolation-strategy.md):

| Namespace | Services | Node Pool | Network Policy |
|-----------|----------|-----------|----------------|
| `holiday-peak-crud` | crud-service (1 service) | `crud` | Allow: UI ingress, agent egress |
| `holiday-peak-agents` | All 26 agent services (eCommerce, CRM, Inventory, Logistics, Product Mgmt, Search, Truth Layer) | `agents` | Allow: CRUD, Event Hubs, AI Search, Cosmos DB |

Create the namespace before deploying:

```bash
kubectl create namespace holiday-peak-agents
kubectl label namespace holiday-peak-agents holiday-peak/ingress-allowed=true --overwrite
```

---

## Step-by-Step: Deploy a Single Agent

### Path A: azd deploy (Recommended)

```bash
# 1. Set environment
azd env set deployShared true -e dev
azd env set environment dev -e dev

# 2. Deploy single service
azd deploy --service ecommerce-catalog-search -e dev

# 3. Verify
kubectl get pods -n holiday-peak-agents -l app=ecommerce-catalog-search
kubectl logs -l app=ecommerce-catalog-search -n holiday-peak-agents --tail=20
```

### Path B: Manual Helm

```bash
# 1. Build and push image
docker build -t <acr>.azurecr.io/ecommerce-catalog-search:latest \
  -f apps/ecommerce-catalog-search/Dockerfile .
docker push <acr>.azurecr.io/ecommerce-catalog-search:latest

# 2. Ensure Foundry agents are provisioned
pwsh .infra/azd/hooks/ensure-foundry-agents.ps1

# 3. Install via Helm
helm upgrade --install ecommerce-catalog-search .kubernetes/chart/ \
  --namespace holiday-peak-agents \
  --set image.repository=<acr>.azurecr.io/ecommerce-catalog-search \
  --set image.tag=latest \
  --set env.PROJECT_ENDPOINT=<foundry-endpoint> \
  --set env.FOUNDRY_AGENT_ID_FAST=<fast-agent-id> \
  --set env.FOUNDRY_AGENT_ID_RICH=<rich-agent-id> \
  --set env.REDIS_URL=<redis-url> \
  --set env.COSMOS_ACCOUNT_URI=<cosmos-uri>

# 4. Verify health
kubectl wait --for=condition=ready pod \
  -l app=ecommerce-catalog-search \
  -n holiday-peak-agents \
  --timeout=120s

curl -s http://localhost:8001/health | jq
```

### Path C: Standalone Bicep (Demo Isolation)

```bash
# 1. Generate standalone Bicep from template
python .infra/cli.py generate --service ecommerce-catalog-search

# 2. Deploy isolated resources
az deployment group create \
  --resource-group rg-catalog-search-demo \
  --template-file .infra/modules/ecommerce-catalog-search/app.bicep \
  --parameters appName=ecommerce-catalog-search

# 3. Deploy service to newly created AKS
# (see generated README in .infra/modules/ecommerce-catalog-search/)
```

---

## Dockerfile Structure

All services share the same multi-stage Dockerfile pattern:

```dockerfile
# Stage 1: Build
FROM python:3.13-slim AS builder
WORKDIR /build
COPY lib/ lib/
COPY apps/<service-name>/ app/
RUN pip install --no-cache-dir uv && \
    cd app && uv pip install --system -e ".[dev]"

# Stage 2: Runtime
FROM python:3.13-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.13 /usr/local/lib/python3.13
COPY --from=builder /build/app/src ./src
EXPOSE 8000
CMD ["uvicorn", "src.<service_module>.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Troubleshooting

| Symptom | Check | Fix |
|---------|-------|-----|
| Pod in `CrashLoopBackoff` | `kubectl logs -l app=<svc> --previous` | Usually missing env var (`PROJECT_ENDPOINT`, `EVENT_HUB_NAMESPACE`) |
| `/health` returns 503 | Foundry agent not provisioned | Run `ensure-foundry-agents.ps1` hook |
| Event Hub consumer not receiving | Consumer group mismatch | Verify `EVENT_HUB_CONNECTION_STRING` and consumer group name |
| Memory timeouts | Redis/Cosmos unreachable | Check network policies allow egress from agent namespace |
| Image pull error | ACR auth expired | `az acr login --name <acr>` then re-deploy |
| Tool calls silently dropped | Old `FoundryInvoker` in use | Ensure `holiday-peak-lib` uses `FoundryAgentInvoker` (PR #802+) |
| APIM returns 502 | Backend health probe failing | Check `/health` endpoint directly via pod port-forward |

---

## Related

- [Infrastructure README](../../.infra/README.md) — Full provisioning guide
- [Deployment Guide](../../.infra/DEPLOYMENT.md) — Multi-service deployment
- [ADR-033: Helm Deployment Strategy](adrs/adr-033-helm-deployment-strategy.md)
- [ADR-034: Namespace Isolation Strategy](adrs/adr-034-namespace-isolation-strategy.md)
- [Flux GitOps Deployment Flow](diagrams/sequence-flux-gitops-deployment.md)
- [Agentic Microservices Reference](../agentic-microservices-reference.md)
| Value | Default | Description |
|-------|---------|-------------|
| `image.repository` | — | ACR image path |
| `image.tag` | `latest` | Image tag |
| `replicaCount` | `1` | Pod replicas |
| `resources.requests.cpu` | `250m` | CPU request |
| `resources.requests.memory` | `256Mi` | Memory request |
| `resources.limits.cpu` | `500m` | CPU limit |
| `resources.limits.memory` | `512Mi` | Memory limit |
| `nodeSelector.agentpool` | `agents` | AKS node pool |
| `probes.startup.path` | `/health` | Startup probe |
| `probes.readiness.path` | `/ready` | Readiness probe |
| `autoscaling.enabled` | `true` | KEDA autoscaling |
| `autoscaling.minReplicas` | `1` | Minimum |
| `autoscaling.maxReplicas` | `5` | Maximum |
| `publication.mode` | `legacy` | `legacy` (Ingress), `agc` (App Gateway), `dual`, `none` |

---

## Namespace Strategy (ADR-034)

In production, services are deployed to two namespaces per [ADR-034](../architecture/adrs/adr-034-namespace-isolation-strategy.md):

| Namespace | Services | Node Pool |
|-----------|----------|-----------|
| `holiday-peak-crud` | crud-service (1 service) | `crud` |
| `holiday-peak-agents` | All 26 agent services (eCommerce, CRM, Inventory, Logistics, Product Mgmt, Search, Truth Layer) | `agents` |

Override the namespace with `--namespace <name>` in Helm commands.

---

## Troubleshooting

| Symptom | Check | Fix |
|---------|-------|-----|
| Pod in `CrashLoopBackoff` | `kubectl logs -l app=<svc> --previous` | Usually missing env var (Foundry, Event Hub) |
| `/health` returns 503 | Foundry agent not provisioned | Run `ensure-foundry-agents.ps1` hook |
| Event Hub consumer not receiving | Consumer group mismatch | Check `EVENT_HUB_CONNECTION_STRING` and consumer group name |
| Memory timeouts | Redis/Cosmos unreachable | Verify network policies allow egress from agent namespace |
| Image pull error | ACR auth expired | `az acr login --name <acr>` |

---

## Related

- [Infrastructure README](../../.infra/README.md) — Full infrastructure provisioning
- [Deployment Guide](../../.infra/DEPLOYMENT.md) — Multi-service deployment
- [Solution Architecture](solution-architecture-overview.md) — System diagrams
- [ADR-033: Helm Deployment Strategy](adrs/adr-033-helm-deployment-strategy.md)
- [ADR-034: Namespace Isolation](adrs/adr-034-namespace-isolation-strategy.md)
