# Truth Enrichment

## Purpose
Generates proposed truth-layer attribute enrichments for products.

## Responsibilities
- Detect enrichable product attribute gaps.
- Generate candidate attribute values.
- Persist and expose enrichment job status.

## Key endpoints or interfaces
- `POST /invoke` for synchronous agent requests.
- `POST /enrich/product/{entity_id}` to enrich a product.
- `POST /enrich/field` to enrich a specific field.
- `GET /enrich/status/{job_id}` to read enrichment status.
- MCP interfaces under `/mcp/*` for agent-to-agent usage.
- Event Hub subscription: `enrichment-jobs` / consumer group `enrichment-engine`.

## Run/Test commands
```bash
cd apps/truth-enrichment/src
uv sync
uv run uvicorn truth_enrichment.main:app --reload
python -m pytest ../tests
```

## Configuration notes
- Uses Foundry model settings (`PROJECT_ENDPOINT` or `FOUNDRY_ENDPOINT`, fast/rich model identifiers).
- Supports Redis/Cosmos/Blob memory configuration via shared memory settings.
- Requires Event Hub namespace and consumer configuration for background jobs.

---

## Deployment Guide — ACR → AKS

This guide covers a **manual, step-by-step deployment** of this agent from source to a running pod in AKS.  
No KeyVault agent is required; environment variables are injected directly into the cluster.

### Prerequisites

| Tool | Purpose |
|------|---------|
| `az` CLI ≥ 2.60 | Azure CLI for ACR and AKS operations |
| `docker` or `az acr build` | Build and push the container image |
| `helm` ≥ 3.14 | Render and install the Helm chart |
| `kubectl` | Apply rendered manifests to AKS |

```bash
# Verify versions
az version
docker version
helm version --short
kubectl version --client --short
```

---

### Step 1 — Set shell variables

Replace the placeholder values to match your environment before running any subsequent step.

```bash
# ── Project identifiers ──────────────────────────────────────────────────────
SUBSCRIPTION_ID="<your-subscription-id>"
RESOURCE_GROUP="rg-holidaypeakhub405-dev"
ENVIRONMENT="dev"
# dev | staging | prod
PROJECT_NAME="holidaypeakhub405"

# ── ACR ──────────────────────────────────────────────────────────────────────
ACR_NAME="${PROJECT_NAME}${ENVIRONMENT}acr"
# e.g. holidaypeakhub405devacr
ACR_LOGIN_SERVER="${ACR_NAME}.azurecr.io"

# ── Service ──────────────────────────────────────────────────────────────────
SERVICE_NAME="truth-enrichment"
IMAGE_TAG="$(git rev-parse --short HEAD)"
# or any explicit tag, e.g. "1.0.0"
IMAGE_REPO="${ACR_LOGIN_SERVER}/${SERVICE_NAME}"

# ── AKS ──────────────────────────────────────────────────────────────────────
AKS_CLUSTER="aks-holidaypeakhub405-${ENVIRONMENT}"
K8S_NAMESPACE="holiday-peak"
```

---

### Step 2 — Authenticate

```bash
# Log in to Azure
az login
az account set --subscription "$SUBSCRIPTION_ID"

# Attach ACR credentials to the local Docker daemon (one-time per session)
az acr login --name "$ACR_NAME"

# Merge AKS credentials into the local kubeconfig
az aks get-credentials \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --overwrite-existing

# Verify cluster access
kubectl get nodes
```

---

### Step 3 — Build and push the image to ACR

Build from the service `src` directory, which acts as the Docker build context.

```bash
# From the repository root
docker build \
  --target dev \
  --tag "${IMAGE_REPO}:${IMAGE_TAG}" \
  --tag "${IMAGE_REPO}:latest" \
  -f apps/truth-enrichment/src/Dockerfile \
  apps/truth-enrichment/src

# Push both tags
docker push "${IMAGE_REPO}:${IMAGE_TAG}"
docker push "${IMAGE_REPO}:latest"
```

> **Alternative — build directly inside ACR** (removes the need for a local Docker daemon):
> ```bash
> az acr build \
>   --registry "$ACR_NAME" \
>   --image "${SERVICE_NAME}:${IMAGE_TAG}" \
>   --file apps/truth-enrichment/src/Dockerfile \
>   apps/truth-enrichment/src
> ```

Verify the image is available in the registry:

```bash
az acr repository show-tags \
  --name "$ACR_NAME" \
  --repository "$SERVICE_NAME" \
  --orderby time_desc \
  --output table
```

---

### Step 4 — Create the Kubernetes namespace

```bash
kubectl get namespace "$K8S_NAMESPACE" &>/dev/null \
  || kubectl create namespace "$K8S_NAMESPACE"
```

---

### Step 5 — Inject environment variables into the cluster

Environment variables are split into two manifests: a **ConfigMap** for non-sensitive settings and a **Secret** for credentials.  
Neither manifest should be committed to source control.

#### 5a — ConfigMap (non-sensitive)

```bash
kubectl create configmap truth-enrichment-config \
  --namespace "$K8S_NAMESPACE" \
  --from-literal=APP_NAME="truth-enrichment" \
  --from-literal=PROJECT_ENDPOINT="https://<foundry-project>.api.azureml.ms" \
  --from-literal=FOUNDRY_ENDPOINT="https://<foundry-project>.api.azureml.ms" \
  --from-literal=FOUNDRY_AGENT_ID_FAST="<fast-agent-id>" \
  --from-literal=MODEL_DEPLOYMENT_NAME_FAST="gpt-4o-mini" \
  --from-literal=FOUNDRY_AGENT_ID_RICH="<rich-agent-id>" \
  --from-literal=MODEL_DEPLOYMENT_NAME_RICH="gpt-4o" \
  --from-literal=FOUNDRY_STREAM="false" \
  --from-literal=CRUD_SERVICE_URL="http://crud-service.holiday-peak.svc.cluster.local" \
  --from-literal=EVENT_HUB_NAMESPACE="<eventhub-namespace>.servicebus.windows.net" \
  --from-literal=DAM_ENDPOINT="https://<dam-service-url>" \
  --from-literal=DAM_MAX_IMAGES="4" \
  --from-literal=COSMOS_ACCOUNT_URI="https://<cosmos-account>.documents.azure.com:443/" \
  --from-literal=COSMOS_DATABASE="holiday-peak" \
  --from-literal=COSMOS_CONTAINER="memory" \
  --from-literal=BLOB_ACCOUNT_URL="https://<storage-account>.blob.core.windows.net" \
  --from-literal=BLOB_CONTAINER="agent-memory" \
  --dry-run=client -o yaml | kubectl apply -f -
```

> Re-running `--dry-run=client -o yaml | kubectl apply -f -` is idempotent and safe to repeat on updates.

#### 5b — Secret (sensitive credentials)

```bash
kubectl create secret generic truth-enrichment-secrets \
  --namespace "$K8S_NAMESPACE" \
  --from-literal=EVENT_HUB_CONNECTION_STRING="Endpoint=sb://<ns>.servicebus.windows.net/;SharedAccessKeyName=...;SharedAccessKey=..." \
  --from-literal=REDIS_URL="rediss://:<password>@<redis-host>:6380/0" \
  --from-literal=DAM_API_KEY="<dam-service-api-key>" \
  --from-literal=APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=...;IngestionEndpoint=..." \
  --dry-run=client -o yaml | kubectl apply -f -
```

> **Prefer managed identity over static keys when available.** Set `AZURE_CLIENT_ID` to the workload identity client ID and omit static connection strings for services that support Azure AD authentication (Event Hubs, Cosmos DB, Blob Storage).

#### 5c — Verify

```bash
kubectl describe configmap truth-enrichment-config -n "$K8S_NAMESPACE"
kubectl describe secret truth-enrichment-secrets -n "$K8S_NAMESPACE"
```

---

### Step 6 — Render the Helm chart

The render hook produces a `kubectl`-ready manifest under `.kubernetes/rendered/`.

```bash
# From the repository root
SERVICE_NAME="truth-enrichment" \
IMAGE_PREFIX="${ACR_LOGIN_SERVER}" \
IMAGE_TAG="${IMAGE_TAG}" \
K8S_NAMESPACE="${K8S_NAMESPACE}" \
KEDA_ENABLED="false" \
PUBLICATION_MODE="none" \
  .infra/azd/hooks/render-helm.sh truth-enrichment
```

Inspect the rendered output before applying:

```bash
cat .kubernetes/rendered/truth-enrichment/*.yaml
```

---

### Step 7 — Inject env vars into the rendered manifest

The Helm chart exposes environment variables via `--set env.<KEY>=<VALUE>`. To pass all values without exposing credentials in shell history, create a local `values-env.yaml` file (**do not commit this file**).

```yaml
# values-env.yaml  — LOCAL FILE, add to .gitignore
env:
  # ConfigMap values
  APP_NAME: "truth-enrichment"
  PROJECT_ENDPOINT: "https://<foundry-project>.api.azureml.ms"
  FOUNDRY_AGENT_ID_FAST: "<fast-agent-id>"
  MODEL_DEPLOYMENT_NAME_FAST: "gpt-4o-mini"
  FOUNDRY_AGENT_ID_RICH: "<rich-agent-id>"
  MODEL_DEPLOYMENT_NAME_RICH: "gpt-4o"
  FOUNDRY_STREAM: "false"
  CRUD_SERVICE_URL: "http://crud-service.holiday-peak.svc.cluster.local"
  EVENT_HUB_NAMESPACE: "<eventhub-namespace>.servicebus.windows.net"
  DAM_ENDPOINT: "https://<dam-service-url>"
  DAM_MAX_IMAGES: "4"
  COSMOS_ACCOUNT_URI: "https://<cosmos-account>.documents.azure.com:443/"
  COSMOS_DATABASE: "holiday-peak"
  COSMOS_CONTAINER: "memory"
  BLOB_ACCOUNT_URL: "https://<storage-account>.blob.core.windows.net"
  BLOB_CONTAINER: "agent-memory"
  # Sensitive values — keep this file out of version control
  EVENT_HUB_CONNECTION_STRING: "Endpoint=sb://..."
  REDIS_URL: "rediss://:<password>@<host>:6380/0"
  DAM_API_KEY: "<dam-service-api-key>"
  APPLICATIONINSIGHTS_CONNECTION_STRING: "InstrumentationKey=..."
```

Then install or upgrade:

```bash
helm upgrade --install truth-enrichment \
  .kubernetes/chart \
  --namespace "$K8S_NAMESPACE" \
  --create-namespace \
  --set serviceName=truth-enrichment \
  --set "image.repository=${IMAGE_REPO}" \
  --set "image.tag=${IMAGE_TAG}" \
  --set nodeSelector.agentpool=agents \
  --set tolerations[0].key=workload \
  --set tolerations[0].operator=Equal \
  --set tolerations[0].value=agents \
  --set tolerations[0].effect=NoSchedule \
  --values values-env.yaml \
  --wait \
  --timeout 5m
```

---

### Step 8 — Validate the deployment

```bash
# Watch rollout progress
kubectl rollout status deployment/truth-enrichment \
  --namespace "$K8S_NAMESPACE" \
  --timeout=5m

# Inspect the running pods
kubectl get pods -n "$K8S_NAMESPACE" -l app=truth-enrichment

# Stream logs from the first pod
kubectl logs -n "$K8S_NAMESPACE" \
  -l app=truth-enrichment \
  --follow --tail=100

# Smoke-test via port-forward
kubectl port-forward \
  -n "$K8S_NAMESPACE" \
  deployment/truth-enrichment 8080:8000 &

curl -s http://localhost:8080/health | python3 -m json.tool
curl -s http://localhost:8080/ready  | python3 -m json.tool

# Test the enrichment endpoint
curl -s -X POST http://localhost:8080/enrich/product/SKU-001 \
  -H "Content-Type: application/json" | python3 -m json.tool
```

---

### Environment Variable Reference

#### Azure AI Foundry (required)

| Variable | Description | Example |
|----------|-------------|---------|
| `PROJECT_ENDPOINT` / `FOUNDRY_ENDPOINT` | Azure AI Foundry project endpoint | `https://<project>.api.azureml.ms` |
| `FOUNDRY_AGENT_ID_FAST` | SLM agent ID for low-complexity requests | `asst_abc123` |
| `MODEL_DEPLOYMENT_NAME_FAST` | SLM deployment name | `gpt-4o-mini` |
| `FOUNDRY_AGENT_ID_RICH` | LLM agent ID for complex enrichment requests | `asst_xyz456` |
| `MODEL_DEPLOYMENT_NAME_RICH` | LLM deployment name | `gpt-4o` |
| `FOUNDRY_STREAM` | Enable streaming responses | `false` |

#### CRUD Service (required)

| Variable | Description | Example |
|----------|-------------|---------|
| `CRUD_SERVICE_URL` | Internal URL of the CRUD service for product lookups | `http://crud-service.holiday-peak.svc.cluster.local` |

#### Azure Event Hub (required)

| Variable | Description | Example |
|----------|-------------|---------|
| `EVENT_HUB_CONNECTION_STRING` / `EVENTHUB_CONNECTION_STRING` | Connection string with *Listen* rights on `enrichment-jobs` | `Endpoint=sb://...` |
| `EVENT_HUB_NAMESPACE` / `EVENTHUB_NAMESPACE` | Namespace FQDN (used when workload identity replaces connection strings) | `<ns>.servicebus.windows.net` |
| `AZURE_CLIENT_ID` | Managed identity client ID for Event Hub auth via workload identity | `<uuid>` |

#### DAM Image Analysis (optional — vision enrichment path)

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `DAM_ENDPOINT` / `DAM_BASE_URL` | Digital Asset Management service base URL | — | `https://<dam-service>` |
| `DAM_API_KEY` | API key for the DAM service | — | `<secret>` |
| `DAM_MAX_IMAGES` | Maximum number of images analyzed per enrichment request | `4` | `4` |

#### Three-tier Memory (optional — degrades gracefully when absent)

| Variable | Description | Example |
|----------|-------------|---------|
| `REDIS_URL` | Hot memory — Redis connection string | `rediss://:<password>@<host>:6380/0` |
| `COSMOS_ACCOUNT_URI` | Warm memory — Cosmos DB account endpoint | `https://<account>.documents.azure.com:443/` |
| `COSMOS_DATABASE` | Cosmos DB database name | `holiday-peak` |
| `COSMOS_CONTAINER` | Cosmos DB container name | `memory` |
| `BLOB_ACCOUNT_URL` | Cold memory — Blob Storage account URL | `https://<account>.blob.core.windows.net` |
| `BLOB_CONTAINER` | Blob container name | `agent-memory` |

#### Observability (optional)

| Variable | Description | Example |
|----------|-------------|---------|
| `APPLICATIONINSIGHTS_CONNECTION_STRING` / `APPINSIGHTS_CONNECTION_STRING` | Application Insights telemetry connection string | `InstrumentationKey=...;IngestionEndpoint=...` |
| `FOUNDRY_TRACING_ENABLED` | Enable Foundry trace capture | `true` |
| `FOUNDRY_TRACING_MAX_EVENTS` | Max events buffered per trace | `500` |

---

### Updating the deployment

To deploy a new image version without replacing env vars:

```bash
IMAGE_TAG="<new-tag>"

kubectl set image deployment/truth-enrichment \
  truth-enrichment="${IMAGE_REPO}:${IMAGE_TAG}" \
  --namespace "$K8S_NAMESPACE"

kubectl rollout status deployment/truth-enrichment \
  --namespace "$K8S_NAMESPACE" --timeout=5m
```

To update a single environment variable without a full redeploy:

```bash
# Edit the ConfigMap directly
kubectl edit configmap truth-enrichment-config -n "$K8S_NAMESPACE"

# Then trigger a rolling restart to pick up the changes
kubectl rollout restart deployment/truth-enrichment -n "$K8S_NAMESPACE"
```

---

### Teardown

```bash
helm uninstall truth-enrichment --namespace "$K8S_NAMESPACE"
kubectl delete configmap truth-enrichment-config -n "$K8S_NAMESPACE"
kubectl delete secret truth-enrichment-secrets -n "$K8S_NAMESPACE"
```
