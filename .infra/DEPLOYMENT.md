# Deployment Guide

Comprehensive deployment guide for Holiday Peak Hub infrastructure.

---

## Prerequisites

### Required Tools

| Tool | Version | Purpose |
|------|---------|---------|
| [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) | ≥ 2.60 | Azure resource management |
| [azd](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd) | ≥ 1.10 | Provisioning + deployment |
| [Bicep CLI](https://learn.microsoft.com/azure/azure-resource-manager/bicep/install) | ≥ 0.30 | Infrastructure-as-code (bundled with Azure CLI) |
azd env set deployShared true -e <environment>
azd env set environment <environment> -e <environment>
azd env set location <location> -e <environment>
azd provision -e <environment>
| [Docker](https://docs.docker.com/get-docker/) | ≥ 24 | Container image builds |

### Azure Subscription Requirements

- **Permissions**: Owner or Contributor + User Access Administrator on the subscription
- **Resource Providers**: Ensure the following providers are registered:
  - `Microsoft.ContainerService` (AKS)
  - `Microsoft.DocumentDB` (Cosmos DB)
  --name static-web-app-<environment> \
  --location <location> \
  - `Microsoft.EventHub` (Event Hubs)
  --parameters environment=<environment> \
               projectName=holidaypeakhub405 \
               resourceGroupName=holidaypeakhub405-<environment>-rg
  - `Microsoft.CognitiveServices` (AI Foundry)
  - `Microsoft.ContainerRegistry` (ACR)
  - `Microsoft.Web` (Static Web Apps)

Register missing providers:

```bash
az provider register --namespace Microsoft.ContainerService
  --resource-group holidaypeakhub405-<environment>-rg \
  --name holidaypeakhub405-<environment>-aks
az provider register --namespace Microsoft.EventHub
az provider register --namespace Microsoft.ApiManagement
az provider register --namespace Microsoft.CognitiveServices
azd deploy --service crud-service -e <environment>

### Quota Requirements (Dev)
azd deploy --all -e <environment>
| Resource | Required | SKU |
|----------|----------|-----|
| vCPUs (Ddsv5) | 32 | Standard_D8ds_v5 × 4 nodes |
| Cosmos DB (Serverless) | 1 account | — |
  --name static-web-app-<environment> \
  --location <location> \
| APIM | 1 instance | Consumption |
  --parameters environment=<environment> \
               projectName=holidaypeakhub405 \
               resourceGroupName=holidaypeakhub405-<environment>-rg

```bash
az login
az account set --subscription <SUBSCRIPTION_ID>
```

  --resource-group holidaypeakhub405-<environment>-rg \
  --name holidaypeakhub405-<environment>-aks
## Deployment Strategy 1: Shared Infrastructure (Recommended)

FORCE=true ./.infra/azd/hooks/generate-crud-env.sh <environment>

azd deploy --service crud-service -e <environment>
azd deploy --all -e <environment>
**Deployment order**: Shared Infrastructure → CRUD Service + Agent Services → AGC Readiness Gate → APIM Sync + APIM Smoke Gate → Static Web App

Release gate notes:

- UI deployment is blocked unless backend deployment jobs are `success` or `skipped`.
- AGC readiness is validated before APIM sync by checking the configured GatewayClass and direct CRUD `/health` reachability on the approved AGC frontend hostname.
- APIM gateway URL is propagated from `azd` outputs and checked against live APIM to catch config drift.
- APIM smoke checks validate direct AGC CRUD health, APIM `GET /api/health`, `GET /api/products?limit=1`, `GET /api/categories`, CRUD CORS preflight, negative CRUD path behavior, and changed agent `GET /agents/<service>/health` before UI publish.
- APIM sync consumes the approved AGC hostname contract from azd outputs and fails closed if the backend drifts to IP-based or cluster-local targets.
- UI deployment runs pre/post smoke checks to ensure API health and SWA hostname reachability.

azd env set deployShared true -e <environment>
azd env set deployStatic true -e <environment>
azd env set location <location> -e <environment>
azd up -e <environment>
### Step 1: Deploy Shared Infrastructure

The shared infrastructure module creates all platform resources using AVM.

```bash
cd .infra/modules/shared-infrastructure

az deployment sub create \
  --name shared-infra-<environment> \
  --location <location> \
  --template-file shared-infrastructure-main.bicep \
  --parameters environment=<environment> location=<location>
```

**Or with azd**:

```bash
azd env set deployShared true -e <environment>
azd env set environment <environment> -e <environment>
azd env set location <location> -e <environment>
azd provision -e <environment>
```

**Resources created** (all AVM, ~25 minutes):

| # | Resource | Module | Purpose |
|---|----------|--------|---------|
| 1 | VNet (5 subnets) | `avm/res/network/virtual-network:0.7.2` | Network isolation |
| 2 | 5 NSGs | `avm/res/network/network-security-group:0.5.2` | Subnet security |
| 3 | 8 Private DNS Zones | `avm/res/network/private-dns-zone:0.8.0` | PE DNS resolution |
| 4 | Log Analytics | `avm/res/operational-insights/workspace:0.15.0` | Centralized logs |
| 5 | App Insights | `avm/res/insights/component:0.7.1` | APM telemetry |
| 6 | ACR (Premium) | `avm/res/container-registry/registry:0.9.3` | Container images |
| 7 | PostgreSQL Flexible Server | `avm/res/db-for-postgre-sql/flexible-server:0.15.0` | CRUD transactional data |
| 8 | Cosmos DB (agent warm memory) | `avm/res/document-db/database-account:0.18.0` | Agent session/history memory |
| 9 | Redis (Premium P1) | `avm/res/cache/redis:0.16.4` | Hot-tier memory |
| 10 | Storage Account | `avm/res/storage/storage-account:0.31.0` | Cold-tier memory |
| 11 | Event Hubs (5 topics) | `avm/res/event-hub/namespace:0.14.0` | Async events |
| 12 | Key Vault (Premium) | `avm/res/key-vault/vault:0.13.3` | Secrets |
| 13 | AI Foundry Project | `avm/ptn/ai-ml/ai-foundry:0.6.0` | AI/ML models |
| 14 | AKS (3 pools) | `avm/res/container-service/managed-cluster:0.12.0` | Compute |
| 15 | APIM | `avm/res/api-management/service:0.14.0` | API gateway |
| 16 | AGC controller identity | Native | ALB controller workload identity |
| — | 6-9 RBAC assignments | Native | Identity permissions |

If `agcSupportEnabled` is enabled for the environment, the shared stack also provisions:
- a delegated `agc` subnet sized for AGC association capacity,
- workload identity federation for `azure-alb-system/alb-controller-sa`,
- RBAC for AGC controller access to the AKS node resource group and delegated subnet.

During `azd provision`, the `postprovision` hook installs the ALB controller Helm chart and validates that GatewayClass `azure-alb-external` is present. No `ApplicationLoadBalancer` or workload route is created in this step.

**Private endpoints** are created for: ACR, Cosmos DB, Redis, Storage, Event Hubs, Key Vault, AI Services.

### Step 2: Provision Static Web App

```bash
cd .infra/modules/static-web-app

az deployment sub create \
  --name static-web-app-<environment> \
  --location <location> \
  --template-file static-web-app-main.bicep \
  --parameters environment=<environment> \
               projectName=holidaypeakhub405 \
               resourceGroupName=holidaypeakhub405-<environment>-rg
```

**Resources created** (~5 minutes):
- Azure Static Web Apps (Free tier for non-prod, Standard for prod)
- Custom domain (prod only)

Publish the UI with `.github/workflows/deploy-ui-swa.yml`. The canonical path is workflow-driven and validates the exact Static Web App identity before publishing.

### Step 3: Connect to AKS

```bash
az aks get-credentials \
  --resource-group holidaypeakhub405-<environment>-rg \
  --name holidaypeakhub405-<environment>-aks

kubectl get nodes
```

### Step 4: Deploy Services

```bash
# CRUD service first
azd deploy --service crud-service -e <environment>

# All agent services
azd deploy --all -e <environment>
```

### Outputs

After deployment, retrieve outputs:

```bash
az deployment sub show \
  --name shared-infra-<environment> \
  --query properties.outputs -o json
```

Key outputs:
- `aksClusterName` — AKS cluster name
- `acrLoginServer` — ACR login server URL
- `cosmosEndpoint` — Cosmos DB endpoint
- `keyVaultUri` — Key Vault URI
- `apimGatewayUrl` — APIM gateway URL
- `appInsightsConnectionString` — App Insights connection string
- `aiProjectName` — AI Foundry project name
- `agcSubnetId` — Delegated subnet reserved for AGC associations
- `agcControllerDeploymentMode` — Controller installation mode for downstream automation
- `agcGatewayClass` — GatewayClass to target in later Kubernetes routing issues
- `agcFrontendReference` — Equivalent frontend reference exported before any real AGC frontend exists

---

## Deployment Strategy 2: Per-Service Standalone (Demo)

### Overview

Each agent service deploys its own isolated set of resources. Suitable for single-service demos.

**Note**: This creates redundant resources per service and is significantly more expensive.

### Deploy a Single Agent Service

```bash
# Generate Bicep from template (if not already generated)
python cli.py generate-bicep --service ecommerce-catalog-search

cd .infra/modules/ecommerce-catalog-search

az deployment sub create \
  --name ecommerce-catalog-search-demo \
  --location eastus2 \
  --template-file ecommerce-catalog-search-main.bicep \
  --parameters appName=ecommerce-catalog-search \
               appImage=ghcr.io/azure-samples/ecommerce-catalog-search:latest
```

**Resources created per service** (~15 minutes):

| Resource | SKU | Purpose |
|----------|-----|---------|
| Cosmos DB | Standard | Chat memory (warm tier) |
| Redis | Standard C0 | Chat memory (hot tier) |
| Storage Account | Standard LRS | Chat memory (cold tier) |
| AI Search | Standard | Retrieval index |
| Azure OpenAI | S0 | GPT-4.1, GPT-4.1-mini, GPT-4.1-nano |
| AKS | Standard_B4ms (1 node) | Compute |

### Deploy All Agent Services (Demo)

```bash
python cli.py generate-bicep --apply-all
python cli.py deploy-all --location eastus2
```

---

## Service Inventory

### 22 Deployable Services

| # | Service | Domain | Type |
|---|---------|--------|------|
| 1 | crud-service | Core | REST API (CRUD operations) |
| 2 | crm-campaign-intelligence | CRM | Agent |
| 3 | crm-profile-aggregation | CRM | Agent |
| 4 | crm-segmentation-personalization | CRM | Agent |
| 5 | crm-support-assistance | CRM | Agent |
| 6 | ecommerce-cart-intelligence | eCommerce | Agent |
| 7 | ecommerce-catalog-search | eCommerce | Agent |
| 8 | ecommerce-checkout-support | eCommerce | Agent |
| 9 | ecommerce-order-status | eCommerce | Agent |
| 10 | ecommerce-product-detail-enrichment | eCommerce | Agent |
| 11 | inventory-alerts-triggers | Inventory | Agent |
| 12 | inventory-health-check | Inventory | Agent |
| 13 | inventory-jit-replenishment | Inventory | Agent |
| 14 | inventory-reservation-validation | Inventory | Agent |
| 15 | logistics-carrier-selection | Logistics | Agent |
| 16 | logistics-eta-computation | Logistics | Agent |
| 17 | logistics-returns-support | Logistics | Agent |
| 18 | logistics-route-issue-detection | Logistics | Agent |
| 19 | product-management-acp-transformation | Product Mgmt | Agent |
| 20 | product-management-assortment-optimization | Product Mgmt | Agent |
| 21 | product-management-consistency-validation | Product Mgmt | Agent |
| 22 | product-management-normalization-classification | Product Mgmt | Agent |

### Frontend

| Service | Type | Hosting |
|---------|------|---------|
| ui | Next.js 15 | Azure Static Web Apps |

---

## Environment Configuration

### Environment Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `environment` | Yes | `dev` | Target environment: `dev`, `staging`, `prod` |
| `location` | Yes | `eastus2` | Azure region |
| `projectName` | No | `holidaypeakhub` | Resource naming prefix |
| `keyVaultNameOverride` | No | `""` | Custom Key Vault name (3-24 chars) |
| `aksKubernetesVersion` | No | `""` | Specific K8s version (empty = Azure default) |

### Resource Group Naming

```
{projectName}-{environment}-rg
```

Examples: `holidaypeakhub405-dev-rg`, `holidaypeakhub405-prod-rg`

### azd Environment Variables

```bash
azd env set deployShared true -e <environment>
azd env set deployStatic true -e <environment>
azd env set environment <environment> -e <environment>
azd env set location <location> -e <environment>
azd env set K8S_NAMESPACE holiday-peak -e <environment>
azd env set IMAGE_PREFIX ghcr.io/azure-samples -e <environment>
azd env set IMAGE_TAG latest -e <environment>
```

---

## Post-Deployment Validation

### Shared Infrastructure

```bash
# AKS connectivity
kubectl get nodes
kubectl get namespaces

# Cosmos DB (Managed Identity token)
kubectl run test-cosmos --image=mcr.microsoft.com/azure-cli --restart=Never --rm -it \
  --command -- bash -c "curl -sH 'Metadata:true' \
    'http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://cosmos.azure.com' | python3 -m json.tool"

# Private endpoint DNS resolution
kubectl run test-dns --image=busybox --restart=Never --rm -it \
  --command -- nslookup holidaypeakhub405-<environment>-cosmos.documents.azure.com
```

### Static Web App

```bash
az staticwebapp show \
  --name holidaypeakhub405-ui-<environment> \
  --resource-group holidaypeakhub405-<environment>-rg \
  --query defaultHostname -o tsv
```

---

## Troubleshooting

### Deployment Failures

| Issue | Cause | Resolution |
|-------|-------|------------|
| AKS timeout (> 30 min) | Region capacity | Retry; try `eastus2` |
| `QuotaExceeded` | Insufficient vCPU quota | Request quota increase for Ddsv5 family |
| `NameNotAvailable` | Resource name conflict | Use `keyVaultNameOverride` parameter |
| Key Vault soft-delete name conflict (non-prod) | Previously deleted vault reserves name | `deploy-azd.yml` provision preflight auto-purges matching soft-deleted vault before `azd provision` |
| PostgreSQL Flexible Server is stopped (non-prod) | Cost-saving stop leaves control plane drift | `deploy-azd.yml` provision preflight starts the existing server and waits for `Ready` before `azd provision` |
| RBAC not propagated | Azure AD timing | Wait 5-10 minutes, retry |
| PE DNS resolution fails | DNS zone not linked | Verify Private DNS Zone VNet links |
| ACR pull fails | Missing role | Verify `AcrPull` role on kubelet identity |
| Bicep validation error | AVM version mismatch | Run `az bicep upgrade` |
| Cosmos Serverless limit | 1 GB partition limit | For prod, use provisioned throughput |

Preflight remediation guardrails:

- Applies only to non-production environments (`prod` and `production` are excluded).
- Performs only targeted reconciliation for known drift cases; infrastructure provisioning remains `azd provision` as source of truth.
- Never deletes active resources; only purges matching soft-deleted Key Vault tombstones.
- Fails fast if PostgreSQL cannot reach `Ready` to prevent unsafe partial deployments.

### Useful Debug Commands

```bash
# Check deployment status
az deployment sub show --name shared-infra-<environment> --query properties.provisioningState

# View deployment operations (find failures)
az deployment sub operation list --name shared-infra-<environment> --query "[?properties.provisioningState=='Failed']"

# AKS diagnostics
kubectl describe nodes
kubectl get events --sort-by='.lastTimestamp' -A

# Check RBAC assignments
az role assignment list --scope /subscriptions/<SUB_ID>/resourceGroups/holidaypeakhub405-<environment>-rg -o table
```

### Cleanup

```bash
# Delete entire resource group
az group delete --name holidaypeakhub405-<environment>-rg --yes --no-wait

# Or delete specific deployment
az deployment sub delete --name shared-infra-<environment>
```

---

## CI/CD Integration

Current workflow gate behavior:

- `.github/workflows/deploy-azd.yml` enforces backend and APIM readiness before `deploy-ui`.
- `.github/workflows/deploy-azd.yml` fails on Foundry readiness check failures instead of warning-only.
- `.github/workflows/deploy-ui-swa.yml` resolves APIM gateway URL from Azure and rejects mismatched manual `apiUrl` overrides.
- `.github/workflows/deploy-ui-swa.yml` includes pre/post deployment smoke checks (`/api/health`, `/api/products?limit=1`, `/api/categories`, and SWA home page).

### GitHub Actions Workflow (recommended)

```yaml
# .github/workflows/deploy-infra.yml
name: Deploy Infrastructure
on:
  push:
    branches: [main]
    paths: ['.infra/**']

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: dev
    steps:
      - uses: actions/checkout@v4
      - uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
      - run: |
          az deployment sub create \
            --name shared-infra-${{ github.run_number }} \
            --location eastus2 \
            --template-file .infra/modules/shared-infrastructure/shared-infrastructure-main.bicep \
            --parameters environment=${{ github.environment }} location=eastus2
```
