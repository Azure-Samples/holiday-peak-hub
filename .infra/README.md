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

- Single shared stack: AKS, Cosmos DB, Redis, Storage, Event Hubs, AI Foundry, APIM, Key Vault, ACR, VNet, App Insights.
- Services reference shared data stores and memory tiers.
- **Cost**: ~85% reduction vs. per-service deployment.

**azd provisioning**:

```bash
azd env set deployShared true -e dev
azd env set deployStatic false -e dev
azd env set environment dev -e dev
azd env set location eastus2 -e dev
azd provision -e dev
```

**azd service deployment**:

```bash
azd deploy --service crud-service -e dev
azd deploy --all -e dev
```

---

## 🏗️ Architecture Overview

### Shared Infrastructure Resources

All resources use AVM (Azure Verified Modules) and deploy to **eastus2** by default.

| Resource | AVM Module | Purpose |
|----------|-----------|---------|
| AKS (3 node pools) | `avm/res/container-service/managed-cluster:0.12.0` | Compute for all services |
| ACR (Premium) | `avm/res/container-registry/registry:0.9.3` | Container image registry |
| Cosmos DB (12 containers) | `avm/res/document-db/database-account:0.18.0` | Operational data + agent memory |
| Redis Cache (Premium) | `avm/res/cache/redis:0.16.4` | Hot-tier agent memory |
| Storage Account | `avm/res/storage/storage-account:0.31.0` | Cold-tier agent memory |
| Event Hubs (5 topics) | `avm/res/event-hub/namespace:0.14.0` | Async event streaming |
| Key Vault (Premium) | `avm/res/key-vault/vault:0.13.3` | Secrets + certificates |
| API Management | `avm/res/api-management/service:0.14.0` | API gateway |
| AI Foundry Project | `avm/ptn/ai-ml/ai-foundry:0.6.0` | AI/ML model management |
| VNet (5 subnets) | `avm/res/network/virtual-network:0.7.2` | Network isolation |
| 5 NSGs | `avm/res/network/network-security-group:0.5.2` | Subnet-level security |
| 7 Private DNS Zones | `avm/res/network/private-dns-zone:0.8.0` | Private endpoint DNS resolution |
| Log Analytics | `avm/res/operational-insights/workspace:0.15.0` | Centralized logging |
| App Insights | `avm/res/insights/component:0.7.1` | Application monitoring |

### Cosmos DB Containers (12)

| Container | Partition Key | Purpose |
|-----------|--------------|---------|
| `users` | `/user_id` | User profiles |
| `products` | `/category_slug` | Product catalog |
| `orders` | `/user_id` | Order history |
| `cart` | `/user_id` | Shopping cart (90-day TTL) |
| `reviews` | `/product_id` | Product reviews |
| `addresses` | `/user_id` | Shipping addresses |
| `payment_methods` | `/user_id` | Payment instruments |
| `checkout_sessions` | `/user_id` | Active checkouts |
| `payment_tokens` | `/user_id` | Payment tokens |
| `tickets` | `/user_id` | Support tickets |
| `shipments` | `/order_id` | Shipment tracking |
| `audit_logs` | `/entity_type` | Audit trail (90-day TTL) |

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
  --name shared-infra-dev \
  --location eastus2 \
  --template-file shared-infrastructure-main.bicep \
  --parameters environment=dev location=eastus2
```

**What this creates**: AKS cluster (3 pools), ACR, Cosmos DB (12 containers), Event Hubs (5 topics), Redis, Storage, Key Vault, APIM, AI Foundry Project, VNet (5 subnets + 5 NSGs), 7 Private DNS Zones with Private Endpoints, App Insights, Log Analytics, 6 RBAC assignments

**Duration**: ~25 minutes | **Cost**: see [Cost Estimates](#-cost-estimates)

### 2. Deploy Frontend (Static Web App)

```bash
cd modules/static-web-app

az deployment sub create \
  --name static-web-app-dev \
  --location eastus2 \
  --template-file static-web-app-main.bicep \
  --parameters environment=dev \
               resourceGroupName=holidaypeakhub-dev-rg
```

**Duration**: ~5 minutes | **Cost**: Free (dev), ~$9/month (prod)

### 3. Connect to AKS

```bash
az aks get-credentials \
  --resource-group holidaypeakhub-dev-rg \
  --name holidaypeakhub-dev-aks

kubectl get nodes  # Verify connection
```

### 4. Deploy Services

```bash
# Deploy CRUD service first
azd deploy --service crud-service -e dev

# Deploy all agent services
azd deploy --all -e dev
```

---

## ✅ Deploy Everything (Demo or Dev)

Use this checklist to deploy the full stack in order.

**1) Shared infrastructure**

```bash
cd modules/shared-infrastructure

az deployment sub create \
  --name shared-infra-dev \
  --location eastus2 \
  --template-file shared-infrastructure-main.bicep \
  --parameters environment=dev location=eastus2
```

**2) Static Web App**

```bash
cd modules/static-web-app

az deployment sub create \
  --name static-web-app-dev \
  --location eastus2 \
  --template-file static-web-app-main.bicep \
  --parameters environment=dev \
               resourceGroupName=holidaypeakhub-dev-rg
```

**3) Services (AKS workloads)**

```bash
az aks get-credentials \
  --resource-group holidaypeakhub-dev-rg \
  --name holidaypeakhub-dev-aks

azd deploy --service crud-service -e dev
azd deploy --all -e dev
```

**azd Shortcut (provision + deploy)**:

```bash
azd env set deployShared true -e dev
azd env set deployStatic true -e dev
azd env set location eastus2 -e dev
azd up -e dev
```

---

## 🚀 Deploy Services with azd

Before deploying services, configure AKS credentials:

```bash
az aks get-credentials \
  --resource-group holidaypeakhub-dev-rg \
  --name holidaypeakhub-dev-aks
```

Deploy a single service:

```bash
azd deploy --service crud-service -e dev
```

Deploy all services:

```bash
azd deploy --all -e dev
```

Optional env overrides (stored in `.azure/<env>/.env`):

```bash
azd env set K8S_NAMESPACE holiday-peak -e dev
azd env set IMAGE_PREFIX ghcr.io/azure-samples -e dev
azd env set IMAGE_TAG latest -e dev
azd env set KEDA_ENABLED false -e dev
```

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
| Cosmos DB (Serverless) | ~$5-50 | Pay-per-request |
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
| Cosmos DB (Provisioned) | ~$400 | Zone-redundant |
| Redis Cache (Premium P1) | ~$225 | |
| APIM (StandardV2) | ~$175 | Internal VNet |
| Other services | ~$100 | Storage, EH, KV, monitoring |
| Static Web App (Standard) | ~$9 | + bandwidth |
| **Total** | **~$4,400** | |

---

## 🔐 Security Features

- ✅ Private endpoints for all data services (Cosmos DB, Redis, Storage, Event Hubs, Key Vault, ACR, AI Services)
- ✅ 7 Private DNS Zones with VNet links for endpoint resolution
- ✅ Managed Identity (passwordless authentication) — no connection strings
- ✅ Key Vault Premium for secrets and certificates
- ✅ VNet isolation with 5 dedicated NSGs
- ✅ TLS 1.2 minimum on all services
- ✅ RBAC-based authorization (6 role assignments)
- ✅ Soft delete enabled (Key Vault 90-day + purge protection)
- ✅ Continuous backup (Cosmos DB 30-day point-in-time restore)
- ✅ Network ACLs: default deny + Azure Services bypass

---

## 📦 Modules

### ✅ Shared Infrastructure

**Path**: `modules/shared-infrastructure/`

**Resources** (all AVM):
- Azure Kubernetes Service (3 node pools: system, agents, crud)
- Azure Container Registry (Premium)
- Cosmos DB Account (12 operational containers)
- Event Hubs Namespace (5 topics)
- Redis Cache (Premium)
- Storage Account
- Key Vault (Premium)
- API Management (AVM — Consumption/StandardV2)
- AI Foundry Project (pattern module)
- Virtual Network (5 subnets) + 5 Network Security Groups
- 7 Private DNS Zones + Private Endpoints
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

# Test Cosmos DB access via Managed Identity
kubectl run test-cosmos --image=mcr.microsoft.com/azure-cli --restart=Never --rm -it \
  --command -- bash -c "curl -H 'Metadata:true' \
    'http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://cosmos.azure.com'"

# Test Event Hubs access via Managed Identity
kubectl run test-eventhub --image=mcr.microsoft.com/azure-cli --restart=Never --rm -it \
  --command -- bash -c "curl -H 'Metadata:true' \
    'http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://eventhubs.azure.net'"
```

### Validate Private Endpoints

```bash
# From within AKS, verify DNS resolution to private IPs
kubectl run test-dns --image=busybox --restart=Never --rm -it \
  --command -- nslookup holidaypeakhub-dev-cosmos.documents.azure.com
```

### Validate Static Web App

```bash
az staticwebapp show \
  --name holidaypeakhub-ui-dev \
  --resource-group holidaypeakhub-dev-rg \
  --query defaultHostname -o tsv
```

---

## 🚨 Troubleshooting

### Common Issues

1. **AKS deployment timeout** — AKS takes 15-25 minutes. Be patient.
2. **RBAC permissions not working** — Wait 5-10 minutes for Azure AD propagation.
3. **Private endpoint DNS not resolving** — Verify Private DNS Zone VNet links are active.
4. **Cosmos DB quota exceeded (serverless)** — Switch to provisioned throughput for higher RU/s.
5. **ACR pull failures** — Verify `AcrPull` role assignment and Private Endpoint connectivity.

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

