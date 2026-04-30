# Standalone Deployment Guide

**Version**: 1.2
**Last Updated**: 2026-04-30

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
azd env set MODEL_DEPLOYMENT_NAME_FAST "gpt-4-1-nano" -e $AZD_ENV
azd env set MODEL_DEPLOYMENT_NAME_RICH "gpt-4-1" -e $AZD_ENV
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
# NOTE: Build context MUST be repo root (.) so the prompts/ COPY can resolve.
#       The Dockerfile is at apps/<svc>/src/Dockerfile, not apps/<svc>/Dockerfile.
docker build \
  --target prod \
  --tag ${ACR_LOGIN_SERVER}/${SERVICE_NAME}:${IMAGE_TAG} \
  --tag ${ACR_LOGIN_SERVER}/${SERVICE_NAME}:latest \
  -f ${APP_PATH}/src/Dockerfile \
  .

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
| `MODEL_DEPLOYMENT_NAME_FAST` | SLM model deployment | `gpt-4-1-nano` |
| `MODEL_DEPLOYMENT_NAME_RICH` | LLM model deployment | `gpt-4-1` |
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

## Namespace Strategy (ADR-026)

All agent services deploy to a single shared namespace per [ADR-026](../architecture/adrs/adr-026-namespace-isolation-strategy.md):

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
# 1. Build and push image (build context must be repo root for prompts COPY)
docker build -t <acr>.azurecr.io/ecommerce-catalog-search:latest \
  --target prod \
  -f apps/ecommerce-catalog-search/src/Dockerfile .
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

All agent services share the same multi-stage Dockerfile pattern with **five stages**:

```dockerfile
# Stage 1 (lib-builder): Install the shared holiday-peak-lib wheel
FROM python:3.13-slim AS lib-builder
WORKDIR /build
COPY lib/ lib/
RUN pip install --no-cache-dir uv && cd lib && uv pip install --system .

# Stage 2 (base): Common runtime base image
FROM python:3.13-slim AS base
# ... system dependencies, user setup ...

# Stage 3 (dev): Development image with dev dependencies
FROM base AS dev
# ... dev extras ...

# Stage 4 (prod-builder): Install production deps from the app's pyproject.toml
FROM base AS prod-builder
COPY apps/<service-name>/src/ /app/src/
RUN cd /app/src && uv pip install --system .

# Stage 5 (prod): Production runtime
FROM python:3.13-slim AS prod
COPY --from=prod-builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=prod-builder --chown=appuser:appgroup /app/src /app/src
COPY --chown=appuser:appgroup apps/<service-name>/prompts/ /app/apps/<service-name>/prompts/
CMD ["uvicorn", "<service_module>.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Prompt Packaging (Critical)

The `COPY ... prompts/` line in stage 5 is **mandatory** for all agent services. Without it:

1. The `prompt_loader` cannot find `prompts/instructions.md` inside the container
2. It falls back to generic placeholder instructions
3. Foundry refuses to create agents with fallback text (`fallback_instructions_refused`)
4. The pod's `/ready` probe returns 503 indefinitely
5. The pod never becomes Ready and `/invoke` returns errors

**CI enforcement**: Run `python scripts/ci/verify_dockerfile_prompts.py` to verify all agent Dockerfiles include the prompts COPY. This script is a fast static gate that catches the issue before any image is built.

The prompts directory at `apps/<service>/prompts/instructions.md` is the authoritative source for each agent's Foundry instructions. The `prompt_loader` resolution order is:
1. `importlib.resources` (package data inside installed wheel)
2. Repo layout relative to `module_file` (`../../prompts/instructions.md`)
3. Service scan from repo roots (`/apps/<service>/prompts/instructions.md`)
4. Fallback text (blocked by Foundry in strict and auto-ensure modes)

---

## Troubleshooting

| Symptom | Check | Fix |
|---------|-------|-----|
| Pod in `CrashLoopBackoff` | `kubectl logs -l app=<svc> --previous` | Usually missing env var (`PROJECT_ENDPOINT`, `EVENT_HUB_NAMESPACE`) |
| `/health` returns 503 | Foundry agent not provisioned | Run `ensure-foundry-agents.ps1` hook |
| `/ready` returns 503, logs show `fallback_instructions_refused` | `prompts/instructions.md` not in Docker image | Add `COPY ... prompts/` to Dockerfile prod stage. Run `python scripts/ci/verify_dockerfile_prompts.py` to check all |
| Event Hub consumer not receiving | Consumer group mismatch | Verify `EVENT_HUB_CONNECTION_STRING` and consumer group name |
| Memory timeouts | Redis/Cosmos unreachable | Check network policies allow egress from agent namespace |
| Image pull error | ACR auth expired | `az acr login --name <acr>` then re-deploy |
| Tool calls silently dropped | Old `FoundryInvoker` in use | Ensure `holiday-peak-lib` uses `FoundryAgentInvoker` (PR #802+) |
| APIM returns 502 | Backend health probe failing | Check `/health` endpoint directly via pod port-forward |
| `could not determine AKS cluster` | `AZURE_AKS_CLUSTER_NAME` not set in azd env | `azd env set AZURE_AKS_CLUSTER_NAME <cluster-name>` |
| `could not determine container registry endpoint` | `AZURE_CONTAINER_REGISTRY_ENDPOINT` not set | `azd env set AZURE_CONTAINER_REGISTRY_ENDPOINT <acr>.azurecr.io` |
| `namespaces is forbidden` | User missing AKS RBAC role | Assign `Azure Kubernetes Service RBAC Cluster Admin` to your principal on the AKS resource |
| `kubectl: Unauthorized` | Kubeconfig not converted for Azure AD | Run `kubelogin convert-kubeconfig -l azurecli` after `az aks get-credentials` |
| Model deployment warns "not available" | Model name/version not in region | Check `az cognitiveservices account list-models` — use `gpt-4.1-nano`/`gpt-4.1` instead of `gpt-5-*` |
| PostgreSQL `LocationIsOfferRestricted` | Region doesn't support PostgreSQL Flexible Server | Set `POSTGRES_LOCATION` to a supported region (e.g., `centralus`) |
| PostgreSQL `InvalidResourceLocation` after failed deploy | Phantom ARM records from failed deployments block new attempts | Delete all failed sub-deployments via `az deployment group delete` then retry |
| ACR 403 `client IP not allowed` | ACR has `publicNetworkAccess=Disabled` with private endpoint only | Enable export policy via ARM REST API, then `az acr update --public-network-enabled true` and add IP rule |
| ACR `exports disabled` blocks public-network-enabled | ACR export policy set to `disabled` (Premium SKU default with PE) | PATCH the registry via ARM API: `properties.policies.exportPolicy.status = "enabled"`, then retry |
| ACR 401 `token validation failed` / `admin user not enabled` | User doesn't have `AcrPush` role on ACR | `az role assignment create --assignee <principal> --role AcrPush --scope <acr-resource-id>` |

---

## PoC Deployment Walkthrough

This section documents the complete step-by-step process used to deploy an isolated PoC environment for customer testing, including all errors encountered and their resolutions.

### Step 1: Create azd Environment

```powershell
azd env new <env-name>
azd env set projectName <short-project-name> -e <env-name>
azd env set AZURE_LOCATION eastus2 -e <env-name>
azd env set deployStatic false -e <env-name>
```

### Step 2: Provision Infrastructure

```powershell
azd provision -e <env-name> --no-prompt
```

**Error encountered**: PostgreSQL `LocationIsOfferRestricted` in eastus2.

**Resolution**: Set a dedicated PostgreSQL region:
```powershell
azd env set POSTGRES_LOCATION centralus -e <env-name>
azd env set POSTGRES_AUTH_MODE password -e <env-name>
```

**Error encountered**: After failed deployments, retries hit `InvalidResourceLocation` due to phantom ARM resource records.

**Resolution**: Delete all failed sub-deployments (both at subscription level and resource-group level):
```powershell
# List failed sub-deployments
az deployment group list --resource-group <rg> --query "[?properties.provisioningState=='Failed'].name" -o tsv

# Delete each one
az deployment group delete --resource-group <rg> --name <deployment-name>

# Also check subscription-level deployments
az deployment sub list --query "[?starts_with(name,'<env-name>')].name" -o tsv
```

Then retry provision — PostgreSQL created successfully in Central US.

### Step 3: Set Missing azd Environment Variables

After infrastructure provision completes, `azd` outputs Bicep values to the `.env` file. However, postprovision hooks require additional variables not output by Bicep:

```powershell
# Required for postprovision hooks and deployment
azd env set AZURE_AKS_CLUSTER_NAME <cluster-name> -e <env-name>
azd env set AZURE_CONTAINER_REGISTRY_ENDPOINT <acr-name>.azurecr.io -e <env-name>
azd env set AZURE_RESOURCE_GROUP <resource-group> -e <env-name>

# Model deployment names (after deploying models)
azd env set MODEL_DEPLOYMENT_NAME_FAST gpt-4-1-nano -e <env-name>
azd env set MODEL_DEPLOYMENT_NAME_RICH gpt-4-1 -e <env-name>
```

**How to discover actual values**:
```powershell
# Find AKS cluster name
az aks list --resource-group <rg> --query "[].name" -o tsv

# Find ACR name
az acr list --resource-group <rg> --query "[].loginServer" -o tsv

# Find actual resource group (may differ from azd project name)
az group list --query "[?contains(name,'<project>')].name" -o tsv
```

### Step 4: Grant AKS RBAC Access

The AKS cluster uses Azure AD RBAC. Your user principal needs cluster admin:

```powershell
# Get your principal ID
$principalId = az ad signed-in-user show --query id -o tsv

# Get AKS resource ID
$aksId = az aks show --name <cluster-name> --resource-group <rg> --query id -o tsv

# Assign AKS RBAC Cluster Admin
az role assignment create `
  --assignee $principalId `
  --role "Azure Kubernetes Service RBAC Cluster Admin" `
  --scope $aksId
```

Then fetch kubeconfig with Azure AD auth:
```powershell
az aks get-credentials --name <cluster-name> --resource-group <rg> --overwrite-existing --format azure
kubelogin convert-kubeconfig -l azurecli
```

**Validation**:
```powershell
kubectl get ns holiday-peak-agents
# Expected: NAME                  STATUS   AGE
#           holiday-peak-agents   Active   <age>
```

### Step 5: Deploy AI Models

The `deploy-foundry-models.ps1` hook attempts to deploy `gpt-5-nano` and `gpt-5`, but these models may not be available in your region yet. Deploy available models manually:

```powershell
# Check available models
az cognitiveservices account list-models `
  --name <ai-services-account> `
  --resource-group <rg> -o json | Select-String '"name": "gpt-4'

# Deploy SLM (gpt-4.1-nano — 5K TPM)
az cognitiveservices account deployment create `
  --name <ai-services-account> `
  --resource-group <rg> `
  --deployment-name gpt-4-1-nano `
  --model-name gpt-4.1-nano `
  --model-version "2025-04-14" `
  --model-format OpenAI `
  --sku-name GlobalStandard `
  --sku-capacity 5000

# Deploy LLM (gpt-4.1 — 1K TPM)
az cognitiveservices account deployment create `
  --name <ai-services-account> `
  --resource-group <rg> `
  --deployment-name gpt-4-1 `
  --model-name gpt-4.1 `
  --model-version "2025-04-14" `
  --model-format OpenAI `
  --sku-name GlobalStandard `
  --sku-capacity 1000
```

**Validation**:
```powershell
az cognitiveservices account deployment list `
  --name <ai-services-account> `
  --resource-group <rg> `
  --query "[].{name:name, model:properties.model.name, state:properties.provisioningState}" -o table
```

### Step 6: Upload Product Data (truth-enrichment)

The `truth-enrichment` agent reads product JSON files from Blob Storage. If the storage account has `publicNetworkAccess=Disabled`:

```powershell
# Temporarily enable public access
az storage account update --name <storage-account> --resource-group <rg> `
  --public-network-access Enabled

# Add your IP to network rules
$myIp = (Invoke-RestMethod https://api.ipify.org)
az storage account network-rule add --account-name <storage-account> `
  --resource-group <rg> --ip-address $myIp

# Ensure you have Storage Blob Data Contributor role
az role assignment create --assignee $principalId `
  --role "Storage Blob Data Contributor" `
  --scope (az storage account show --name <storage-account> --resource-group <rg> --query id -o tsv)

# Create container and upload
az storage container create --name products --account-name <storage-account> --auth-mode login

# Upload product JSONs (799 files)
az storage blob upload-batch --destination products --source ./data/products `
  --account-name <storage-account> --auth-mode login --overwrite

# Upload category schemas
az storage blob upload-batch --destination products --source ./data/schemas `
  --destination-path _schemas --account-name <storage-account> --auth-mode login --overwrite

# Re-lock storage
az storage account update --name <storage-account> --resource-group <rg> `
  --public-network-access Disabled
```

### Step 6b: Enable ACR Access (Private Endpoint Environments)

If the ACR has `publicNetworkAccess=Disabled` (default with private endpoints), you must temporarily enable public access to push images from your workstation:

```powershell
# 1. Enable export policy via ARM REST API (CLI doesn't expose this)
$acrId = az acr show --name <acr-name> --resource-group <rg> --query id -o tsv
$token = az account get-access-token --query accessToken -o tsv
$body = @{ properties = @{ policies = @{ exportPolicy = @{ status = "enabled" } } } } | ConvertTo-Json -Depth 5
Invoke-RestMethod -Uri "https://management.azure.com${acrId}?api-version=2023-07-01" `
  -Method Patch -Headers @{Authorization="Bearer $token"; "Content-Type"="application/json"} -Body $body

# 2. Enable public network access
az acr update --name <acr-name> --resource-group <rg> --public-network-enabled true

# 3. Add your IP to ACR firewall
$myIp = (Invoke-RestMethod https://api.ipify.org)
az acr network-rule add --name <acr-name> --resource-group <rg> --ip-address $myIp

# 4. Login to ACR (required — azd token exchange may fail without this)
az acr login --name <acr-name>
```

After deploying all agents, re-lock:
```powershell
az acr update --name <acr-name> --resource-group <rg> --public-network-enabled false
```

> **Note**: You also need `AcrPush` role on the ACR to push images:
> ```powershell
> az role assignment create --assignee $(az ad signed-in-user show --query id -o tsv) `
>   --role AcrPush --scope $(az acr show --name <acr-name> --resource-group <rg> --query id -o tsv)
> ```

### Step 7: Deploy Agent Services

```powershell
# Deploy each agent service
azd deploy truth-enrichment -e <env-name> --no-prompt
azd deploy ecommerce-catalog-search -e <env-name> --no-prompt
azd deploy search-enrichment-agent -e <env-name> --no-prompt
```

**Validation**:
```powershell
kubectl get pods -n holiday-peak-agents
kubectl logs -l app=truth-enrichment -n holiday-peak-agents --tail=20
```

### Step 8: Validate End-to-End

```powershell
# Port-forward to test directly
kubectl port-forward svc/truth-enrichment 8080:8000 -n holiday-peak-agents &
curl http://localhost:8080/health

# Or test via APIM (if configured)
$APIM_BASE = "https://<apim-name>.azure-api.net"
Invoke-RestMethod "$APIM_BASE/agents/truth-enrichment/health"
```

### Errors Summary

| # | Error | Root Cause | Resolution |
|---|-------|-----------|------------|
| 1 | `LocationIsOfferRestricted` for PostgreSQL | eastus2 doesn't support PostgreSQL Flexible Server | Set `POSTGRES_LOCATION=centralus` |
| 2 | `InvalidResourceLocation` on retry | Phantom ARM records from failed deployments | Delete failed sub-deployments, then retry |
| 3 | `ResourceNotFound` for role assignment | Cross-region ARM propagation race (PostgreSQL in centralus, ref in eastus2) | Simple retry — ARM needs ~30s to propagate |
| 4 | `could not determine AKS cluster` | `AZURE_AKS_CLUSTER_NAME` not in azd env | `azd env set AZURE_AKS_CLUSTER_NAME <name>` |
| 5 | `namespaces is forbidden` | User lacks AKS RBAC | Assign `Azure Kubernetes Service RBAC Cluster Admin` |
| 6 | `kubectl: Unauthorized` | Kubeconfig not converted for Azure AD auth | `kubelogin convert-kubeconfig -l azurecli` |
| 7 | `could not determine container registry endpoint` | `AZURE_CONTAINER_REGISTRY_ENDPOINT` not in azd env | `azd env set AZURE_CONTAINER_REGISTRY_ENDPOINT <acr>.azurecr.io` |
| 8 | Model "not available in this account/region" | `gpt-5-nano`/`gpt-5` not yet in eastus2 | Deploy `gpt-4.1-nano`/`gpt-4.1` manually instead |
| 9 | ACR 403 — IP not allowed access | ACR `publicNetworkAccess=Disabled` behind private endpoint | Enable export policy via ARM REST API, enable public access, add IP rule |
| 10 | ACR `exports disabled` blocks `--public-network-enabled` | Premium ACR export policy is `disabled` by default when PE attached | PATCH via `https://management.azure.com/{acrId}?api-version=2023-07-01` with `properties.policies.exportPolicy.status = "enabled"` |
| 11 | ACR 401 `token validation failed` | User doesn't have `AcrPush` role on ACR | `az role assignment create --assignee <principal> --role AcrPush --scope <acr-id>` |

---

## Related

- [Infrastructure README](../../.infra/README.md) — Full provisioning guide
- [Deployment Guide](../../.infra/DEPLOYMENT.md) — Multi-service deployment
- [ADR-017: Helm Deployment Strategy](adrs/adr-017-deployment-strategy.md)
- [ADR-026: Namespace Isolation Strategy](adrs/adr-026-namespace-isolation-strategy.md)
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

## Namespace Strategy (ADR-026)

In production, services are deployed to two namespaces per [ADR-026](../architecture/adrs/adr-026-namespace-isolation-strategy.md):

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
| `/ready` returns 503, logs show `fallback_instructions_refused` | `prompts/instructions.md` not in Docker image | Add `COPY ... prompts/` to Dockerfile prod stage. See § Prompt Packaging |
| Event Hub consumer not receiving | Consumer group mismatch | Check `EVENT_HUB_CONNECTION_STRING` and consumer group name |
| Memory timeouts | Redis/Cosmos unreachable | Verify network policies allow egress from agent namespace |
| Image pull error | ACR auth expired | `az acr login --name <acr>` |

---

## Related

- [Infrastructure README](../../.infra/README.md) — Full infrastructure provisioning
- [Deployment Guide](../../.infra/DEPLOYMENT.md) — Multi-service deployment
- [Solution Architecture](solution-architecture-overview.md) — System diagrams
- [ADR-017: Helm Deployment Strategy](adrs/adr-017-deployment-strategy.md)
- [ADR-026: Namespace Isolation](adrs/adr-026-namespace-isolation-strategy.md)
