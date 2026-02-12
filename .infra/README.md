# Infrastructure Management

This folder contains all infrastructure-as-code (Bicep) and deployment tooling for Holiday Peak Hub.

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
│   └── [21 agent modules]/      # Agent-specific resources (keep pairwise)
└── templates/
    ├── app.bicep.tpl            # Bicep template for agent services
    ├── main.bicep.tpl           # Main Bicep template wrapper
    └── Dockerfile.template      # Multi-stage Dockerfile template
```

## 🚀 Quick Start

## ✅ Provisioning Strategies

We support two infrastructure provisioning strategies:

### 1) Demo (per-service)
- Each service deploys its own resources for a fast, isolated demo.
- Use the Python CLI (`python cli.py deploy` / `deploy-all`).
- Suitable for quick demos and lightweight validation.

### 2) Production (shared infrastructure)
- Single shared stack (AKS, Cosmos DB, Redis, Storage, Event Hubs, Foundry, APIM, etc.).
- Services deploy as workloads into the shared AKS and reference shared data/memory.
- Use the shared-infrastructure module first, then deploy services.

**CLI Shortcut**:

```bash
python cli.py deploy-shared --environment dev --location eastus2
```

**Shared AKS Workloads (Helm)**:

```bash
python cli.py deploy-shared-services \
  --namespace holiday-peak \
  --image-prefix ghcr.io/azure-samples \
  --image-tag latest
```

### 0. Deploy Shared Infrastructure (Demo)

```bash
cd modules/shared-infrastructure

az deployment sub create \
  --name shared-infra-demo \
  --location eastus2 \
  --template-file shared-infrastructure-main.bicep \
  --parameters environment=demo location=eastus2
```

**What this creates**: Same shared stack as dev, in the demo environment

### 0b. Deploy Frontend (Demo)

```bash
cd modules/static-web-app

az deployment sub create \
  --name static-web-app-demo \
  --location eastus2 \
  --template-file static-web-app-main.bicep \
  --parameters environment=demo \
               resourceGroupName=holidaypeakhub-demo-rg
```

### 1. Deploy Shared Infrastructure (Dev)

```bash
cd modules/shared-infrastructure

az deployment sub create \
  --name shared-infra-dev \
  --location eastus \
  --template-file shared-infrastructure-main.bicep \
  --parameters environment=dev
```

**What this creates**: AKS cluster, Cosmos DB, Event Hubs, Redis, Storage, Key Vault, APIM, VNet, Application Insights

**Duration**: ~20 minutes | **Cost**: ~$540/month

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

**What this creates**: Azure Static Web Apps with GitHub Actions CI/CD

**CLI Shortcut**:

```bash
python cli.py deploy-static-web-app --environment dev --location eastus2
```

**Duration**: ~5 minutes | **Cost**: Free (dev)

### 3. Connect to AKS

```bash
az aks get-credentials \
  --resource-group holidaypeakhub-dev-rg \
  --name holidaypeakhub-dev-aks

kubectl get nodes  # Verify connection
```

---

## ✅ Deploy Everything (Demo or Dev)

Use this checklist to deploy the full stack in order.

1) Shared infrastructure

```bash
cd modules/shared-infrastructure

# Demo
az deployment sub create \
  --name shared-infra-demo \
  --location eastus2 \
  --template-file shared-infrastructure-main.bicep \
  --parameters environment=demo location=eastus2

# Dev
az deployment sub create \
  --name shared-infra-dev \
  --location eastus2 \
  --template-file shared-infrastructure-main.bicep \
  --parameters environment=dev location=eastus2
```

2) Static Web App

```bash
cd modules/static-web-app

# Demo
az deployment sub create \
  --name static-web-app-demo \
  --location eastus2 \
  --template-file static-web-app-main.bicep \
  --parameters environment=demo \
               resourceGroupName=holidaypeakhub-demo-rg

# Dev
az deployment sub create \
  --name static-web-app-dev \
  --location eastus2 \
  --template-file static-web-app-main.bicep \
  --parameters environment=dev \
               resourceGroupName=holidaypeakhub-dev-rg
```

3) Agent services (AKS workloads)

```bash
# Generate Bicep modules if missing
python cli.py generate-bicep --apply-all

# Deploy all agent modules (update image path as needed)
python cli.py deploy-all \
  --location eastus2 \
  --resource-group holidaypeakhub-demo-rg \
  --app-image ghcr.io/azure-samples/<service>:latest
```

4) CRUD service (AKS workload)

```bash
python cli.py deploy \
  --service crud-service \
  --location eastus2 \
  --resource-group holidaypeakhub-demo-rg \
  --app-image ghcr.io/azure-samples/crud-service:latest
```

5) Connect to AKS

```bash
az aks get-credentials \
  --resource-group holidaypeakhub-demo-rg \
  --name holidaypeakhub-demo-aks

kubectl get nodes
```

**CLI Shortcut (shared infra + static web app)**:

```bash
python cli.py deploy-full --environment dev --location eastus2
```

**CLI Shortcut (shared infra + static web app + all services)**:

```bash
python cli.py deploy-shared-all \
  --environment dev \
  --location eastus2 \
  --namespace holiday-peak \
  --image-prefix ghcr.io/azure-samples \
  --image-tag latest
```

---

## 📚 Documentation

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Comprehensive deployment guide with prerequisites, step-by-step instructions, and troubleshooting
- **[SUMMARY.md](SUMMARY.md)** - Implementation summary, architecture decisions, cost breakdown
- **[modules/shared-infrastructure/README.md](modules/shared-infrastructure/README.md)** - Shared infrastructure architecture and usage
- **[modules/static-web-app/README.md](modules/static-web-app/README.md)** - Frontend deployment and configuration

---

## 🏗️ Architecture Overview

### Hybrid "Pairwise" Approach

**Shared Infrastructure** (Cost Optimization):
- 1 AKS cluster with 3 node pools (system, agents, crud)
- 1 Cosmos DB account with operational + agent memory containers
- 1 Redis Cache (agents use different databases)
- 1 Storage Account (agents use different blob containers)
- 1 Event Hubs namespace (5 topics)
- Shared: ACR, Key Vault, APIM, VNet, Application Insights

**Agent-Specific Resources** (Isolation):
- Cosmos DB containers: `warm-{agent}-chat-memory`
- Redis databases: 0=CRUD, 1-21=agents
- Blob containers: `cold-{agent}-chat-memory`
- Azure Search (only if needed)
- OpenAI deployments (only if needed)

**Benefits**:
- 💰 85% cost reduction (~$3,800/month savings)
- 🔒 Agent independence (isolated memory)
- 🚀 Easy deployment (single cluster)
- 📊 Simplified operations

---

## 🛠️ CLI Tool Usage

> Note: The CLI-based `deploy` and `deploy-all` flows follow the **demo (per-service)** strategy.

The `deploy-shared-services` and `deploy-shared-all` commands target **shared AKS** and require:

- An active AKS kubeconfig (`az aks get-credentials ...`)
- Helm installed and available in `PATH`

### Generate Bicep Modules

```bash
# One agent
python cli.py generate-bicep --service ecommerce-catalog-search

# All agents
python cli.py generate-bicep --apply-all
```

### Generate Dockerfiles

```bash
# One agent
python cli.py generate-dockerfile --service ecommerce-catalog-search

# All agents
python cli.py generate-dockerfile --apply-all
```

### Deploy Agent

```bash
python cli.py deploy \
  --service ecommerce-catalog-search \
  --location eastus \
  --resource-group holidaypeakhub-dev-rg \
  --app-image ghcr.io/azure-samples/ecommerce-catalog-search:latest
```

---

## 💰 Cost Estimates

### Dev Environment
| Component | Cost/Month |
|-----------|-----------|
| Shared Infrastructure | ~$540 |
| Static Web App | Free |
| **Total** | **~$540** |

### Production Environment
| Component | Cost/Month |
|-----------|-----------|
| Shared Infrastructure | ~$3,900 |
| Static Web App | ~$9 + bandwidth |
| **Total** | **~$3,910** |

---

## 🔐 Security Features

- ✅ No public endpoints (private endpoints only)
- ✅ Managed Identity (passwordless authentication)
- ✅ Key Vault for secrets
- ✅ VNet isolation with NSG
- ✅ TLS 1.2 minimum
- ✅ RBAC everywhere
- ✅ Soft delete enabled (90-day recovery)
- ✅ Continuous backup (Cosmos DB 30-day restore)

---

## 📦 Modules

### ✅ Shared Infrastructure

**Path**: `modules/shared-infrastructure/`

**Resources**:
- Azure Kubernetes Service (3 node pools)
- Azure Container Registry
- Cosmos DB Account (10 operational containers)
- Event Hubs Namespace (5 topics)
- Redis Cache Premium
- Storage Account
- Key Vault
- API Management
- Virtual Network + NSG
- Application Insights
- Log Analytics Workspace

**Deploy**: See [modules/shared-infrastructure/README.md](modules/shared-infrastructure/README.md)

---

### ✅ Static Web App

**Path**: `modules/static-web-app/`

**Resources**:
- Azure Static Web Apps (Next.js hosting)
- GitHub Actions CI/CD
- Custom domain support (prod)

**Deploy**: See [modules/static-web-app/README.md](modules/static-web-app/README.md)

---

### 🔄 Agent Modules (Unchanged)

**Path**: `modules/{agent-name}/`

**No refactoring needed!** Keep existing agent modules as-is. They will:
- Reference shared Cosmos DB account (create their own containers)
- Reference shared Redis cache (use dedicated databases)
- Reference shared Storage account (create their own blob containers)
- Deploy to shared AKS cluster

---

## 🧪 Testing

### Validate Shared Infrastructure

```bash
# Check AKS
kubectl get nodes
kubectl get namespaces

# Test Cosmos DB access
kubectl run test-cosmos --image=mcr.microsoft.com/azure-cli --restart=Never --rm -it \
  --command -- bash -c "curl -H 'Metadata:true' 'http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://cosmos.azure.com'"

# Test Event Hubs access
kubectl run test-eventhub --image=mcr.microsoft.com/azure-cli --restart=Never --rm -it \
  --command -- bash -c "curl -H 'Metadata:true' 'http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://eventhubs.azure.net'"
```

### Validate Static Web App

```bash
# Get URL
az staticwebapp show \
  --name holidaypeakhub-ui-dev \
  --resource-group holidaypeakhub-dev-rg \
  --query defaultHostname -o tsv

# Test
curl https://<static-web-app-url>
```

---

## 🚨 Troubleshooting

### Common Issues

1. **AKS deployment timeout**
   - Solution: AKS takes 15-20 minutes. Be patient.

2. **RBAC permissions not working**
   - Solution: Wait 5-10 minutes for Azure AD propagation.

3. **Private endpoint DNS not resolving**
   - Solution: Verify private DNS zone and VNet link.

4. **Cosmos DB quota exceeded (serverless)**
   - Solution: Switch to provisioned throughput for higher RU/s.

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed troubleshooting.

---

## 📝 Next Steps

1. ✅ Deploy shared infrastructure to Azure
2. ✅ Deploy Static Web App
3. ✅ CRUD service created (see `docs/architecture/crud-service-implementation.md`)
4. 🔄 Deploy agent services to shared AKS
5. 🔄 Configure APIM routes
6. 🔄 Set up CI/CD pipelines

---

## 🤝 Contributing

When adding new infrastructure:

1. Create module in `modules/{name}/`
2. Include `{name}.bicep` and `{name}-main.bicep`
3. Write comprehensive `README.md`
4. Update this file
5. Test deployment to dev environment
6. Document in `DEPLOYMENT.md`

---

## 📞 Support

- **Deployment Guide**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **Architecture**: [SUMMARY.md](SUMMARY.md)
- **Implementation Roadmap**: [../docs/IMPLEMENTATION_ROADMAP.md](../docs/IMPLEMENTATION_ROADMAP.md)
- **ADRs**: [../docs/architecture/ADRs.md](../docs/architecture/ADRs.md)

