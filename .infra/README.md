# Infrastructure Management

This folder contains all infrastructure-as-code (Bicep) and deployment tooling for Holiday Peak Hub.
All infrastructure uses [Azure Verified Modules (AVM)](https://azure.github.io/Azure-Verified-Modules/) for consistency, security, and maintainability.

## 📁 Structure

```
.infra/
├── README.md                    # This file
├── DEPLOYMENT.md                # Step-by-step deployment guide
├── SUMMARY.md                   # Implementation summary and architecture decisions
├── cli.py                       # CLI tool for generating Bicep modules and Dockerfiles
├── config-cli.sh                # CLI environment setup script
├── modules/
│   ├── shared-infrastructure/   # ✅ Shared infrastructure (AKS, Cosmos DB, Event Hubs, etc.)
│   ├── static-web-app/          # ✅ Frontend hosting (Azure Static Web Apps)
│   └── [21 agent modules]/      # Per-service standalone demo resources
└── templates/
    ├── app.bicep.tpl            # Bicep template for standalone agent services
    ├── main.bicep.tpl           # Main Bicep template wrapper (subscription-scoped)
    └── Dockerfile.template      # Multi-stage Dockerfile template
```

## 🚀 Quick Start

### azd Parameters

The azd provisioning flow reads parameter values from `.infra/azd/main.parameters.json`, which pulls
environment values set by the CLI (for example, `keyVaultNameOverride`).

## ✅ Provisioning Strategies

We support two infrastructure provisioning strategies:

### 1) Demo (per-service standalone)

Each of the 21 agent services deploys its **own isolated** resources (Cosmos DB, Redis, Storage, AI Search, OpenAI, AKS) using `app.bicep.tpl`. This is suitable for quick single-service demos and lightweight validation.

- Use the Python CLI (`python cli.py deploy` / `deploy-all`) or `azd deploy --service <name>`.
- Each service is fully independent — no shared infrastructure required.
- **Cost**: High (duplicate resources per service).

### 2) Production (shared infrastructure)

A single shared stack is deployed first, and all 22 services (21 agents + 1 CRUD) run as workloads in the shared AKS cluster.

- Single shared stack: AKS, PostgreSQL (CRUD), Cosmos DB (agent warm memory), Redis, Storage, Event Hubs, AI Foundry, APIM, Key Vault, ACR, VNet, App Insights.
- Services reference shared data stores and memory tiers.
- **Cost**: ~85% reduction vs. per-service deployment.

**azd provisioning**:

```bash
azd env set deployShared true -e <environment>
azd env set deployStatic false -e <environment>
azd env set environment <environment> -e <environment>
azd env set location <location> -e <environment>
azd provision -e <environment>
```

**azd service deployment**:

```bash
azd deploy --service crud-service -e <environment>
azd deploy --all -e <environment>
```

---

## 🏗️ Architecture Overview

### Shared Infrastructure Resources

All resources use AVM (Azure Verified Modules) and deploy to **eastus2** by default.

| Resource | AVM Module | Purpose |
|----------|-----------|---------|
| AKS (3 node pools) | `avm/res/container-service/managed-cluster:0.12.0` | Compute for all services |
| AGC controller identity | Native | Workload identity principal for the ALB controller |
| ACR (Premium) | `avm/res/container-registry/registry:0.9.3` | Container image registry |
| PostgreSQL Flexible Server | `avm/res/db-for-postgre-sql/flexible-server:0.15.0` | CRUD transactional operations |
| Cosmos DB | `avm/res/document-db/database-account:0.18.0` | Agent warm memory |
| Redis Cache (Premium) | `avm/res/cache/redis:0.16.4` | Hot-tier agent memory |
| Storage Account | `avm/res/storage/storage-account:0.31.0` | Cold-tier agent memory |
| Event Hubs (5 topics) | `avm/res/event-hub/namespace:0.14.0` | Async event streaming |
| Key Vault (Premium) | `avm/res/key-vault/vault:0.13.3` | Secrets + certificates |
| API Management | `avm/res/api-management/service:0.14.0` | API gateway |
| AI Foundry Project | `avm/ptn/ai-ml/ai-foundry:0.6.0` | AI/ML model management (pinned to `westus3`, public network enabled) |
| VNet (5-6 subnets) | `avm/res/network/virtual-network:0.7.2` | Network isolation |
| 5-6 NSGs | `avm/res/network/network-security-group:0.5.2` | Subnet-level security |
| 8 Private DNS Zones | `avm/res/network/private-dns-zone:0.8.0` | Private endpoint DNS resolution |
| Log Analytics | `avm/res/operational-insights/workspace:0.15.0` | Centralized logging |
| App Insights | `avm/res/insights/component:0.7.1` | Application monitoring |

### CRUD Database (PostgreSQL)

- Server: `{projectName}-{environment}-postgres`
- Database: `holiday_peak_crud`
- Connectivity: Private Endpoint + private DNS (`privatelink.postgres.database.azure.com`)
- Scope: All CRUD transactional entities (`users`, `orders`, `cart`, `reviews`, `payments`, `shipments`, `tickets`, etc.)

### Cosmos DB (Agent Warm Memory)

- Account: `{projectName}-{environment}-cosmos`
- Database: `holiday-peak-db`
- Containers: `warm-{agent}-chat-memory` (created per agent as needed)

### Event Hubs Topics (5)

`order-events`, `inventory-events`, `shipment-events`, `payment-events`, `user-events`

### VNet Subnets

| Subnet | CIDR | Purpose |
|--------|------|---------|
| `aks-system` | `10.0.0.0/22` | AKS system node pool |
| `aks-agents` | `10.0.4.0/22` | AKS agent node pool |
| `aks-crud` | `10.0.8.0/24` | AKS CRUD node pool |
| `apim` | `10.0.9.0/24` | API Management (prod: Internal VNet) |
| `private-endpoints` | `10.0.10.0/24` | Private endpoint NICs |
| `agc` | `10.0.12.0/24` by default | Delegated subnet for Application Gateway for Containers |

### RBAC Assignments (6)

| Principal | Target | Role |
|-----------|--------|------|
| AKS kubelet identity | ACR | AcrPull |
| AKS system identity | Cosmos DB | Data Contributor |
| AKS system identity | Event Hubs | Data Sender |
| AKS system identity | Event Hubs | Data Receiver |
| AKS Key Vault identity | Key Vault | Secrets User |
| AKS system identity | Storage | Blob Data Contributor |

### Agent-Specific Isolation (within shared infrastructure)

- Cosmos DB containers: `warm-{agent}-chat-memory`
- Redis databases: 0 = CRUD, 1-21 = agents
- Blob containers: `cold-{agent}-chat-memory`
- AI Search indexes (if needed)
- OpenAI deployments (if needed)

---

## 📦 Deployment Steps

### 1. Deploy Shared Infrastructure

```bash
cd modules/shared-infrastructure

az deployment sub create \
  --name shared-infra-<environment> \
  --location <location> \
  --template-file shared-infrastructure-main.bicep \
  --parameters environment=<environment> location=<location>
```

**What this creates**: AKS cluster (3 pools), ACR, PostgreSQL (CRUD), Cosmos DB (agent warm memory), Event Hubs (5 topics), Redis, Storage, Key Vault, APIM, Azure AI Search service, AI Foundry Project, VNet (5 subnets + 5 NSGs), 8 Private DNS Zones with Private Endpoints, App Insights, Log Analytics, 6 RBAC assignments

When `agcSupportEnabled` is on, shared infrastructure also creates the delegated AGC subnet, the ALB controller workload identity, and the RBAC required for later AGC route publication. The `azd` postprovision flow then installs the ALB controller into AKS without cutting over any workloads.

The `catalog-products` Azure AI Search index is ensured during `azd` `postprovision`, after the search service is reachable, to avoid nested ARM child-resource timing conflicts during `azd provision`.

**Duration**: ~25 minutes | **Cost**: see [Cost Estimates](#-cost-estimates)

### 2. Provision Frontend (Static Web App)

```bash
cd modules/static-web-app

az deployment sub create \
  --name static-web-app-<environment> \
  --location <location> \
  --template-file static-web-app-main.bicep \
  --parameters environment=<environment> \
               projectName=holidaypeakhub405 \
               resourceGroupName=holidaypeakhub405-<environment>-rg
```

Publish the UI with `.github/workflows/deploy-ui-swa.yml`. The canonical UI path is workflow-driven and validates the exact Static Web App name before publishing.

**Duration**: ~5 minutes | **Cost**: Free (non-prod), ~$9/month (prod)

### 3. Connect to AKS

```bash
az aks get-credentials \
  --resource-group holidaypeakhub405-<environment>-rg \
  --name holidaypeakhub405-<environment>-aks

kubectl get nodes  # Verify connection
```

### 4. Deploy Services

```bash
# Deploy CRUD service first
azd deploy --service crud-service -e <environment>

# Deploy all agent services
azd deploy --all -e <environment>
```

---

## ✅ Deploy Everything (Demo or Dev)

Use this checklist to deploy the full stack in order.

**1) Shared infrastructure**

```bash
cd modules/shared-infrastructure

az deployment sub create \
  --name shared-infra-<environment> \
  --location <location> \
  --template-file shared-infrastructure-main.bicep \
  --parameters environment=<environment> location=<location>
```

**2) Static Web App**

```bash
cd modules/static-web-app

az deployment sub create \
  --name static-web-app-<environment> \
  --location <location> \
  --template-file static-web-app-main.bicep \
  --parameters environment=<environment> \
               projectName=holidaypeakhub405 \
               resourceGroupName=holidaypeakhub405-<environment>-rg
```

Then publish the UI with `.github/workflows/deploy-ui-swa.yml`.

**3) Services (AKS workloads)**

```bash
az aks get-credentials \
  --resource-group holidaypeakhub405-<environment>-rg \
  --name holidaypeakhub405-<environment>-aks

# Generate CRUD env from azd values (Linux/macOS)
FORCE=true ./.infra/azd/hooks/generate-crud-env.sh <environment>

azd deploy --service crud-service -e <environment>
azd deploy --all -e <environment>
```

On Windows, use:

```powershell
pwsh ./.infra/azd/hooks/generate-crud-env.ps1 -EnvironmentName <environment> -Force
```

**azd Shortcut (provision + deploy)**:

```bash
azd env set deployShared true -e <environment>
azd env set deployStatic true -e <environment>
azd env set location <location> -e <environment>
azd up -e <environment>
```

---

## 🚀 Deploy Services with azd

Before deploying services, configure AKS credentials:

```bash
az aks get-credentials \
  --resource-group holidaypeakhub405-<environment>-rg \
  --name holidaypeakhub405-<environment>-aks
```

Deploy a single service:

```bash
azd deploy --service crud-service -e <environment>
```

Deploy all services:

```bash
azd deploy --all -e <environment>
```

The reusable deployment workflow runs APIM sync, Foundry-agent reconciliation, and API smoke tests as explicit jobs after backend deployment. `azd` no longer owns those global postdeploy side effects, which keeps UI-only publication isolated.

Manual run (if needed):

```bash
./.infra/azd/hooks/sync-apim-agents.sh
# or on Windows
pwsh ./.infra/azd/hooks/sync-apim-agents.ps1
```

Optional env overrides (stored in `.azure/<env>/.env`):

```bash
azd env set K8S_NAMESPACE holiday-peak -e <environment>
azd env set IMAGE_PREFIX ghcr.io/azure-samples -e <environment>
azd env set IMAGE_TAG latest -e <environment>
azd env set KEDA_ENABLED false -e <environment>
```

---

## ☸️ AKS Cluster Operations

Detailed instructions for managing AKS clusters that host CRUD and Agent workloads.
Commands use the **naming convention** `holidaypeakhub-{env}-aks` (resource group `holidaypeakhub-{env}-rg`).
Replace `{env}` with `dev` or `prod` as appropriate.

### Prerequisites

| Tool | Install | Purpose |
|------|---------|---------|
| Azure CLI | `winget install Microsoft.AzureCLI` | Cluster management & RBAC |
| kubectl | `az aks install-cli` | Kubernetes API interaction |
| kubelogin | Included with `az aks install-cli` | AAD/Entra ID authentication for AKS |
| Helm 3 | `winget install Helm.Helm` | Chart-based deployments |

> **PATH note (Windows):** After `az aks install-cli`, add `$HOME\.azure-kubelogin` and `$HOME\.azure-kubectl`
> to your PATH if not already present.

### 1. Authentication & Context

```bash
# Login to Azure
az login
az account set --subscription <SUBSCRIPTION_ID>

# Get AKS credentials (merges into ~/.kube/config)
az aks get-credentials \
  --resource-group holidaypeakhub-{env}-rg \
  --name holidaypeakhub-{env}-aks

# Convert kubeconfig for AAD / Entra ID auth
kubelogin convert-kubeconfig -l azurecli

# Verify connectivity
kubectl cluster-info
kubectl get nodes -o wide
```

**RBAC requirements** — the operating user needs at minimum:

| Scenario | Required Role | Scope |
|----------|--------------|-------|
| Read-only monitoring | `Azure Kubernetes Service Cluster User Role` | AKS resource |
| Full cluster admin | `Azure Kubernetes Service RBAC Cluster Admin` | AKS resource |
| Image pull config | `AcrPull` | ACR resource |

Assign a role:

```bash
AKS_ID=$(az aks show -g holidaypeakhub-{env}-rg -n holidaypeakhub-{env}-aks --query id -o tsv)

az role assignment create \
  --assignee <USER_OR_SP_OBJECT_ID> \
  --role "Azure Kubernetes Service RBAC Cluster Admin" \
  --scope "$AKS_ID"
```

### 2. Cluster Lifecycle

#### Start / Stop (cost saving for dev & demo)

```bash
# Stop cluster (deallocates all nodes, keeps config)
az aks stop \
  --resource-group holidaypeakhub405-<environment>-rg \
  --name holidaypeakhub405-<environment>-aks

# Start cluster
az aks start \
  --resource-group holidaypeakhub405-<environment>-rg \
  --name holidaypeakhub405-<environment>-aks

# Check power state
az aks show -g holidaypeakhub-{env}-rg -n holidaypeakhub-{env}-aks \
  --query "powerState.code" -o tsv
```

> **Production:** Never stop a production cluster. Use node pool scaling instead.

#### Upgrade Kubernetes Version

```bash
# List available versions
az aks get-versions --location eastus2 -o table

# Upgrade control plane + node pools
az aks upgrade \
  --resource-group holidaypeakhub-{env}-rg \
  --name holidaypeakhub-{env}-aks \
  --kubernetes-version <TARGET_VERSION> \
  --yes

# Upgrade a specific node pool only
az aks nodepool upgrade \
  --resource-group holidaypeakhub-{env}-rg \
  --cluster-name holidaypeakhub-{env}-aks \
  --name agents \
  --kubernetes-version <TARGET_VERSION>
```

#### Network Access

```bash
# Check current public network access
az aks show -g holidaypeakhub-{env}-rg -n holidaypeakhub-{env}-aks \
  --query publicNetworkAccess -o tsv

# Enable public access (dev/demo — required for local kubectl)
az resource update \
  --ids $(az aks show -g holidaypeakhub405-<environment>-rg -n holidaypeakhub405-<environment>-aks --query id -o tsv) \
  --set properties.publicNetworkAccess=Enabled \
  --api-version 2024-10-01

# Disable public access (production — use az aks command invoke or VPN)
az resource update \
  --ids $(az aks show -g holidaypeakhub405-prod-rg -n holidaypeakhub405-prod-aks --query id -o tsv) \
  --set properties.publicNetworkAccess=Disabled \
  --api-version 2024-10-01
```

> **Fallback when public access is disabled:** Use `az aks command invoke` to run kubectl
> commands through the Azure control plane without direct network access:
>
> ```bash
> az aks command invoke \
>   --resource-group holidaypeakhub-prod-rg \
>   --name holidaypeakhub-prod-aks \
>   --command "kubectl get pods -n holiday-peak"
> ```

### 3. Node Pool Management

The shared infrastructure provisions **three node pools** with dedicated taints:

| Pool | Purpose | Taint | VM Size | Autoscale (dev) | Autoscale (prod) |
|------|---------|-------|---------|-----------------|------------------|
| `system` | Kubernetes system components | *(none)* | Standard_D8ds_v5 | 1–3 | 1–5 |
| `agents` | 21 agent services | `workload=agents:NoSchedule` | Standard_D8ds_v5 | 2–10 | 2–20 |
| `crud` | CRUD service | `workload=crud:NoSchedule` | Standard_D8ds_v5 | 1–5 | 1–10 |

#### Scale a Node Pool

```bash
# Manual scale (overrides autoscaler temporarily)
az aks nodepool scale \
  --resource-group holidaypeakhub-{env}-rg \
  --cluster-name holidaypeakhub-{env}-aks \
  --name agents \
  --node-count 4

# Update autoscaler bounds
az aks nodepool update \
  --resource-group holidaypeakhub-{env}-rg \
  --cluster-name holidaypeakhub-{env}-aks \
  --name agents \
  --min-count 2 \
  --max-count 15 \
  --enable-cluster-autoscaler
```

#### Add a New Node Pool

```bash
# Example: add a GPU pool for ML inference agents
az aks nodepool add \
  --resource-group holidaypeakhub-{env}-rg \
  --cluster-name holidaypeakhub-{env}-aks \
  --name gpu \
  --node-count 1 \
  --vm-size Standard_NC6s_v3 \
  --node-taints "workload=gpu:NoSchedule" \
  --labels workload=gpu \
  --enable-cluster-autoscaler \
  --min-count 0 \
  --max-count 3
```

#### Delete a Node Pool

```bash
az aks nodepool delete \
  --resource-group holidaypeakhub-{env}-rg \
  --cluster-name holidaypeakhub-{env}-aks \
  --name gpu
```

#### Node Pool Health

```bash
# List all pools with status
az aks nodepool list \
  --resource-group holidaypeakhub-{env}-rg \
  --cluster-name holidaypeakhub-{env}-aks \
  -o table

# Node-level detail
kubectl get nodes -o wide
kubectl describe node <NODE_NAME>
kubectl top nodes
```

### 4. Deploying Workloads — CRUD Service

The CRUD service runs on the `crud` node pool (toleration: `workload=crud`).

#### Deploy via azd (recommended)

```bash
azd deploy --service crud-service -e {env}
```

#### Deploy via Helm (manual)

```bash
# Render the chart
helm template crud-service .kubernetes/chart \
  --set serviceName=crud-service \
  --set image.repository=holidaypeakhubdevacr.azurecr.io/crud-service \
  --set image.tag=latest \
  --set replicaCount=2 \
  --set keda.enabled=false \
  --namespace holiday-peak \
  > .kubernetes/rendered/crud-service/manifest.yaml

# Apply
kubectl apply -f .kubernetes/rendered/crud-service/manifest.yaml -n holiday-peak
```

#### Verify CRUD Deployment

```bash
kubectl get deployments -n holiday-peak -l app=crud-service
kubectl get pods -n holiday-peak -l app=crud-service
kubectl logs -n holiday-peak -l app=crud-service --tail=50 -f
kubectl port-forward -n holiday-peak svc/crud-service 8000:80
# In another terminal: curl http://localhost:8000/health
```

#### Scale CRUD Replicas

```bash
kubectl scale deployment -n holiday-peak -l app=crud-service --replicas=3
```

### 5. Deploying Workloads — Agent Services

All 21 agent services run on the `agents` node pool (toleration: `workload=agents`).

#### Deploy All Agents via azd

```bash
azd deploy --all -e {env}
```

#### Deploy a Single Agent via azd

```bash
azd deploy --service ecommerce-catalog-search -e {env}
```

#### Deploy a Single Agent via Helm (manual)

```bash
SERVICE=ecommerce-catalog-search

helm template "$SERVICE" .kubernetes/chart \
  --set serviceName="$SERVICE" \
  --set image.repository="holidaypeakhubdevacr.azurecr.io/$SERVICE" \
  --set image.tag=latest \
  --set replicaCount=2 \
  --set keda.enabled=true \
  --namespace holiday-peak \
  > ".kubernetes/rendered/$SERVICE/manifest.yaml"

kubectl apply -f ".kubernetes/rendered/$SERVICE/manifest.yaml" -n holiday-peak
```

#### Verify Agent Deployments

```bash
# All agents at once
kubectl get deployments -n holiday-peak -o wide

# Specific agent
kubectl get pods -n holiday-peak -l app=ecommerce-catalog-search
kubectl logs -n holiday-peak -l app=ecommerce-catalog-search --tail=50 -f

# Health endpoint via port-forward
kubectl port-forward -n holiday-peak svc/ecommerce-catalog-search 8001:80
curl http://localhost:8001/health
```

#### Scale an Agent

```bash
# Manual scale
kubectl scale deployment -n holiday-peak -l app=ecommerce-catalog-search --replicas=4

# Or enable/disable KEDA autoscaler via Helm values
helm template ecommerce-catalog-search .kubernetes/chart \
  --set serviceName=ecommerce-catalog-search \
  --set keda.enabled=true \
  --set keda.minReplicaCount=2 \
  --set keda.maxReplicaCount=10 \
  --namespace holiday-peak \
  > .kubernetes/rendered/ecommerce-catalog-search/manifest.yaml

kubectl apply -f .kubernetes/rendered/ecommerce-catalog-search/manifest.yaml -n holiday-peak
```

### 6. Namespace & Resource Management

```bash
# Create the workload namespace (if not exists)
kubectl create namespace holiday-peak --dry-run=client -o yaml | kubectl apply -f -

# Set default namespace for your context
kubectl config set-context --current --namespace=holiday-peak

# List all resources in the namespace
kubectl get all -n holiday-peak

# Resource quotas (production recommended)
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ResourceQuota
metadata:
  name: holiday-peak-quota
  namespace: holiday-peak
spec:
  hard:
    requests.cpu: "40"
    requests.memory: "80Gi"
    limits.cpu: "60"
    limits.memory: "120Gi"
    pods: "200"
EOF

# Limit ranges (enforce per-pod defaults)
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: LimitRange
metadata:
  name: holiday-peak-limits
  namespace: holiday-peak
spec:
  limits:
    - default:
        cpu: "500m"
        memory: "512Mi"
      defaultRequest:
        cpu: "250m"
        memory: "256Mi"
      type: Container
EOF
```

### 7. Image Management with ACR

The shared ACR (`holidaypeakhub{env}acr`) stores all container images.

```bash
ACR_NAME="holidaypeakhub${env}acr"

# Build and push an image from source
az acr build \
  --registry $ACR_NAME \
  --image crud-service:latest \
  --file apps/crud-service/src/Dockerfile \
  apps/crud-service/src

# Build and push an agent image
az acr build \
  --registry $ACR_NAME \
  --image ecommerce-catalog-search:latest \
  --file apps/ecommerce-catalog-search/src/Dockerfile \
  apps/ecommerce-catalog-search/src

# List images in ACR
az acr repository list --name $ACR_NAME -o table

# Show tags for a repository
az acr repository show-tags --name $ACR_NAME --repository crud-service -o table

# Import an external image into ACR
az acr import \
  --name $ACR_NAME \
  --source mcr.microsoft.com/azuredocs/aks-helloworld:v1 \
  --image aks-helloworld:v1

# Verify AKS can pull from ACR
az aks check-acr \
  --resource-group holidaypeakhub-{env}-rg \
  --name holidaypeakhub-{env}-aks \
  --acr "${ACR_NAME}.azurecr.io"
```

> **Private ACR note:** If the ACR has `publicNetworkAccess=Disabled`, cloud builds (`az acr build`)
> require a private build agent or self-hosted runner inside the VNet. For dev/demo, temporarily
> enable public access or use `az acr import` to pull from a public source.

### 8. Cluster Health & Monitoring

#### Quick Health Check

```bash
# Control-plane status
az aks show -g holidaypeakhub-{env}-rg -n holidaypeakhub-{env}-aks \
  --query "{k8sVersion:kubernetesVersion, power:powerState.code, provisioning:provisioningState, fqdn:fqdn}" \
  -o table

# Node readiness
kubectl get nodes -o wide
kubectl top nodes

# System pod health
kubectl get pods -n kube-system -o wide
kubectl get pods -n kube-system | grep -v Running

# Workload health
kubectl get pods -n holiday-peak
kubectl get pods -n holiday-peak | grep -Ev "Running|Completed"

# Events (recent issues)
kubectl get events -n holiday-peak --sort-by='.lastTimestamp' | tail -20
```

#### Diagnostics & Logs

```bash
# Container logs for a specific service
kubectl logs -n holiday-peak -l app=crud-service --tail=100

# Previous container logs (after crash)
kubectl logs -n holiday-peak -l app=crud-service --previous --tail=50

# Describe a pod for event details
kubectl describe pod -n holiday-peak <POD_NAME>

# AKS diagnostics via Azure CLI
az aks kollect \
  --resource-group holidaypeakhub-{env}-rg \
  --name holidaypeakhub-{env}-aks \
  --storage-account holidaypeakhub${env}sa
```

#### Resource Utilization

```bash
# Node-level CPU/memory
kubectl top nodes

# Pod-level CPU/memory
kubectl top pods -n holiday-peak --sort-by=memory

# Per-container resource usage
kubectl top pods -n holiday-peak --containers
```

### 9. Rolling Updates & Rollbacks

```bash
# Trigger a rolling update by changing the image tag
kubectl set image deployment/crud-service \
  crud-service=holidaypeakhubdevacr.azurecr.io/crud-service:v2 \
  -n holiday-peak

# Watch rollout progress
kubectl rollout status deployment/crud-service -n holiday-peak

# Rollback to previous revision
kubectl rollout undo deployment/crud-service -n holiday-peak

# Rollback to a specific revision
kubectl rollout history deployment/crud-service -n holiday-peak
kubectl rollout undo deployment/crud-service -n holiday-peak --to-revision=2

# Restart all pods (without changing spec)
kubectl rollout restart deployment/crud-service -n holiday-peak
```

### 10. Cleanup & Teardown

#### Remove a Single Service

```bash
kubectl delete deployment -n holiday-peak -l app=crud-service
kubectl delete service -n holiday-peak -l app=crud-service
kubectl delete scaledobject -n holiday-peak -l app=crud-service 2>/dev/null
```

#### Remove All Workloads

```bash
kubectl delete all -n holiday-peak --all
```

#### Delete the Namespace

```bash
kubectl delete namespace holiday-peak
```

#### Delete the Entire Cluster (demo only)

```bash
az aks delete \
  --resource-group holidaypeakhub405-<environment>-rg \
  --name holidaypeakhub405-<environment>-aks \
  --yes --no-wait
```

> **Production:** Never delete a production cluster directly. Use Bicep/azd to decommission
> infrastructure so that dependent resources (Private Endpoints, DNS Zones, RBAC) are cleaned up.

### 11. Demo vs Production Quick Reference

| Operation | Demo / Dev | Production |
|-----------|-----------|------------|
| **Cluster access** | Public API enabled; `kubectl` directly | Public API disabled; use `az aks command invoke` or VPN |
| **Cost management** | `az aks stop` / `az aks start` to pause | Node pool autoscaling (never stop) |
| **Image builds** | `az acr build` or local `docker push` | CI/CD pipeline (GitHub Actions) |
| **Deployments** | `azd deploy` or manual `kubectl apply` | `azd deploy` via GitHub Actions workflow |
| **Scaling** | Manual `kubectl scale` | KEDA autoscaler + node pool autoscaling |
| **K8s upgrades** | In-place `az aks upgrade` | Blue-green node pools or staged upgrade |
| **Monitoring** | `kubectl top` + `kubectl logs` | Azure Monitor + Container Insights + alerts |
| **Secrets** | Env vars or `kubectl create secret` | Key Vault CSI driver (auto-synced) |
| **Network policy** | Azure CNI (default allow) | Azure Network Policies + NSGs (deny by default) |
| **Namespace quotas** | Optional | Required (ResourceQuota + LimitRange) |
| **Cluster deletion** | `az aks delete` when done | Decommission via Bicep/azd only |

---

## 📚 Documentation

- **[DEPLOYMENT.md](DEPLOYMENT.md)** — Comprehensive deployment guide with prerequisites, strategies, and troubleshooting
- **[SUMMARY.md](SUMMARY.md)** — Implementation summary with architecture diagrams and deployment relationships
- **[modules/shared-infrastructure/README.md](modules/shared-infrastructure/README.md)** — Shared infrastructure architecture and usage
- **[modules/static-web-app/README.md](modules/static-web-app/README.md)** — Frontend deployment and configuration

---

## 🛠️ CLI Tool Usage

`cli.py` is reserved for scaffolding utilities. Use `azd` for provisioning and deployment.

### Generate Bicep Modules

```bash
python cli.py generate-bicep --service ecommerce-catalog-search   # One agent
python cli.py generate-bicep --apply-all                          # All agents
```

### Generate Dockerfiles

```bash
python cli.py generate-dockerfile --service ecommerce-catalog-search  # One agent
python cli.py generate-dockerfile --apply-all                         # All agents
```

---

## 💰 Cost Estimates

### Dev Environment (Serverless where applicable)

| Component | Cost/Month | Notes |
|-----------|-----------|-------|
| AKS (4 nodes, Standard_D8ds_v5) | ~$1,120 | 1 system + 2 agents + 1 crud |
| PostgreSQL Flexible Server (Burstable) | ~$40-120 | CRUD transactional data |
| Cosmos DB (Serverless) | ~$5-50 | Agent warm memory |
| Redis Cache (Premium P1) | ~$225 | Required for PE support |
| Storage Account | ~$5 | Blob storage for cold memory |
| Event Hubs (Standard) | ~$12 | 5 topics |
| Key Vault (Premium) | ~$5 | Secrets + certificates |
| APIM (Consumption) | ~$4 | Pay-per-call |
| AI Foundry Project | ~$0 | Pay-per-inference |
| Log Analytics + App Insights | ~$10 | Depends on volume |
| Static Web App | Free | Dev tier |
| **Total** | **~$1,400** | |

### Production Environment

| Component | Cost/Month | Notes |
|-----------|-----------|-------|
| AKS (11+ nodes, autoscale) | ~$3,500 | 3 system + 5 agents + 3 crud |
| PostgreSQL Flexible Server (GeneralPurpose) | ~$250-700 | Zone-redundant + HA |
| Cosmos DB (Provisioned) | ~$200-400 | Agent warm memory |
| Redis Cache (Premium P1) | ~$225 | |
| APIM (StandardV2) | ~$175 | Internal VNet |
| Other services | ~$100 | Storage, EH, KV, monitoring |
| Static Web App (Standard) | ~$9 | + bandwidth |
| **Total** | **~$4,400** | |

---

## 🔐 Security Features

- ✅ Private endpoints for all data services (PostgreSQL, Cosmos DB, Redis, Storage, Event Hubs, Key Vault, ACR, AI Services)
- ✅ 8 Private DNS Zones with VNet links for endpoint resolution
- ✅ Managed Identity for Azure APIs + Key Vault-managed DB credentials for PostgreSQL
- ✅ Key Vault Premium for secrets and certificates
- ✅ VNet isolation with 5 dedicated NSGs
- ✅ TLS 1.2 minimum on all services
- ✅ RBAC-based authorization (6 role assignments)
- ✅ Soft delete enabled (Key Vault 90-day + purge protection)
- ✅ Continuous backup (PostgreSQL + Cosmos DB point-in-time restore)
- ✅ Network ACLs: default deny + Azure Services bypass

---

## 📦 Modules

### ✅ Shared Infrastructure

**Path**: `modules/shared-infrastructure/`

**Resources** (all AVM):
- Azure Kubernetes Service (3 node pools: system, agents, crud)
- Azure Container Registry (Premium)
- PostgreSQL Flexible Server (CRUD transactional database)
- Cosmos DB Account (agent warm-memory containers)
- Event Hubs Namespace (5 topics)
- Redis Cache (Premium)
- Storage Account
- Key Vault (Premium)
- API Management (AVM — Consumption/StandardV2)
- AI Foundry Project (pattern module)
- Virtual Network (5 subnets) + 5 Network Security Groups
- 8 Private DNS Zones + Private Endpoints
- Application Insights + Log Analytics Workspace
- 6 RBAC role assignments

**Deploy**: See [modules/shared-infrastructure/README.md](modules/shared-infrastructure/README.md)

---

### ✅ Static Web App

**Path**: `modules/static-web-app/`

**Resources**:
- Azure Static Web Apps (Next.js hosting)
- GitHub Actions CI/CD integration
- Custom domain support (prod only)
- Environment-conditional SKU (Free for dev, Standard for prod)

**Deploy**: See [modules/static-web-app/README.md](modules/static-web-app/README.md)

---

### 🔄 Agent Service Modules (21 services)

**Path**: `modules/{agent-name}/`

Each agent service module is generated from `templates/app.bicep.tpl` and deploys **standalone resources** for isolated demo scenarios. Each module creates its own:

- Cosmos DB account + database + `warm-{agent}-chat-memory` container
- Redis Cache (Standard C0)
- Storage Account + `cold-{agent}-chat-memory` blob container
- Azure AI Search service + retrieval index
- Azure OpenAI account + 3 model deployments (GPT-4.1, GPT-4.1-mini, GPT-4.1-nano)
- AKS cluster (single node, Standard_B4ms)

**Services** (4 domains, 21 total):

| Domain | Services |
|--------|----------|
| CRM | campaign-intelligence, profile-aggregation, segmentation-personalization, support-assistance |
| eCommerce | cart-intelligence, catalog-search, checkout-support, order-status, product-detail-enrichment |
| Inventory | alerts-triggers, health-check, jit-replenishment, reservation-validation |
| Logistics | carrier-selection, eta-computation, returns-support, route-issue-detection |
| Product Mgmt | acp-transformation, assortment-optimization, consistency-validation, normalization-classification |

> **Note**: In production deployments, these services run as AKS workloads in the shared infrastructure. The standalone modules are only used for per-service demo mode.

---

## 🧪 Testing

### Validate Shared Infrastructure

```bash
# Check AKS
kubectl get nodes
kubectl get namespaces

# Test Cosmos DB access token (agent warm memory)
kubectl run test-cosmos --image=mcr.microsoft.com/azure-cli --restart=Never --rm -it \
  --command -- bash -c "curl -H 'Metadata:true' \
    'http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://cosmos.azure.com'"

# Test PostgreSQL endpoint reachability (CRUD database)
kubectl run test-postgres --image=postgres:16 --restart=Never --rm -it \
  --command -- bash -c "pg_isready -h holidaypeakhub405-<environment>-postgres.postgres.database.azure.com -p 5432"

# Test Event Hubs access via Managed Identity
kubectl run test-eventhub --image=mcr.microsoft.com/azure-cli --restart=Never --rm -it \
  --command -- bash -c "curl -H 'Metadata:true' \
    'http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://eventhubs.azure.net'"
```

### Validate Private Endpoints

```bash
# From within AKS, verify DNS resolution to private IPs
kubectl run test-dns --image=busybox --restart=Never --rm -it \
  --command -- nslookup holidaypeakhub405-<environment>-postgres.postgres.database.azure.com

kubectl run test-dns-cosmos --image=busybox --restart=Never --rm -it \
  --command -- nslookup holidaypeakhub405-<environment>-cosmos.documents.azure.com
```

### Validate Static Web App

```bash
az staticwebapp show \
  --name holidaypeakhub405-ui-<environment> \
  --resource-group holidaypeakhub405-<environment>-rg \
  --query defaultHostname -o tsv
```

---

## 🚨 Troubleshooting

### Common Issues

1. **AKS deployment timeout** — AKS takes 15-25 minutes. Be patient.
2. **RBAC permissions not working** — Wait 5-10 minutes for Azure AD propagation.
3. **Private endpoint DNS not resolving** — Verify Private DNS Zone VNet links are active.
4. **PostgreSQL connection/auth failures** — Verify `POSTGRES_HOST`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, private DNS resolution, and Key Vault secret sync.
5. **Cosmos DB quota exceeded (serverless)** — Switch to provisioned throughput for higher RU/s for agent warm-memory workloads.
6. **ACR pull failures** — Verify `AcrPull` role assignment and Private Endpoint connectivity.

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed troubleshooting.

---

## 🤝 Contributing

When adding new infrastructure:

1. Create module in `modules/{name}/`
2. Include `{name}.bicep` and `{name}-main.bicep`
3. Use AVM modules exclusively — no raw resource declarations
4. Write comprehensive `README.md`
5. Update this file and [DEPLOYMENT.md](DEPLOYMENT.md)
6. Test deployment to dev environment

---

## 📞 Support

- **Deployment Guide**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **Architecture Summary**: [SUMMARY.md](SUMMARY.md)
- **Implementation Roadmap**: [../docs/IMPLEMENTATION_ROADMAP.md](../docs/IMPLEMENTATION_ROADMAP.md)
- **ADRs**: [../docs/architecture/ADRs.md](../docs/architecture/ADRs.md)

