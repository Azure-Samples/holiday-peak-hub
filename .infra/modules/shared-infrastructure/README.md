# Shared Infrastructure Module

This module provisions **shared infrastructure** for Holiday Peak Hub that is used by all services (CRUD service + 21 agent services).
Provisioning is implemented with Azure Verified Modules (AVM) for consistent, supportable resource definitions.
AVM module versions are pinned per resource in the shared infrastructure Bicep file to ensure compatibility with the registry.

## Architecture Decision

**Agent Resources: Pairwise Approach**

- Each agent **keeps its own memory resources** (Cosmos containers, Redis DBs, Blob containers)
- Agents **share the underlying accounts** (Cosmos DB account, PostgreSQL server, Redis Cache, Storage Account)
- This approach balances **isolation** (agent independence) with **cost optimization** (shared infrastructure)

## What's Shared

This module creates **ONE instance** of each resource, shared across all services:

### Compute & Container

- **Azure Kubernetes Service (AKS)** - Single cluster with 3 node pools:
  - `system` - System workloads (1-5 nodes)
  - `agents` - Agent services with taint `workload=agents:NoSchedule` (2-20 nodes)
  - `crud` - CRUD service with taint `workload=crud:NoSchedule` (1-10 nodes)
- **Azure Container Registry (ACR)** - Container image registry (Premium tier)

### Data & Storage

- **Azure Database for PostgreSQL Flexible Server** - CRUD transactional datastore (`holiday_peak_crud` database)
- **Cosmos DB Account** - Shared account for **agent warm memory** containers (`warm-{agent-name}-chat-memory`)
- **Redis Cache** - Shared Premium 6GB cache with multiple databases:
  - Database 0: CRUD service cache
  - Database 1-21: Agent hot memory (one per agent)
- **Storage Account** - Shared blob storage with containers:
  - `cold-memory` - Shared cold storage root
  - `cold-{agent-name}-chat-memory` - Agent-specific cold storage (created by agent modules)

### Messaging & Events

- **Event Hubs Namespace** - Shared namespace with topics:
  - `order-events` - Order lifecycle events
  - `inventory-events` - Inventory updates
  - `shipment-events` - Shipment tracking events
  - `payment-events` - Payment processing events
  - `user-events` - User activity events

### Security & Secrets

- **Key Vault** - Centralized secrets management (Premium tier with RBAC)
- **Managed Identity** - AKS uses System-Assigned MI for passwordless auth
- **PostgreSQL secret sync** - `postgres-admin-password` is stored in Key Vault for CRUD runtime retrieval

### Networking

- **Virtual Network** - 10.0.0.0/16 with subnets:
  - `aks-system` - 10.0.0.0/22 (System node pool)
  - `aks-agents` - 10.0.4.0/22 (Agent node pool)
  - `aks-crud` - 10.0.8.0/24 (CRUD node pool)
  - `apim` - 10.0.9.0/24 (API Management)
  - `private-endpoints` - 10.0.10.0/24 (Private endpoints for PaaS services)
  - `agc` - 10.0.11.0/24 by default (Application Gateway for Containers delegated subnet, delegated to `Microsoft.ServiceNetworking/trafficControllers`)
- **Network Security Groups** - One per subnet, including the delegated AGC subnet when AGC support is enabled
- **Private Endpoints** - PaaS services are private by default; Azure AI Foundry is the intentional public-access exception

### AGC Controller Prerequisites

- **AGC delegated subnet** - Created in shared infrastructure for dev by default and exported for downstream routing work
- **ALB controller identity** - User-assigned managed identity with workload identity federation for `azure-alb-system/alb-controller-sa`
- **AGC RBAC** - Reader and AppGw for Containers Configuration Manager on the AKS node resource group, plus Network Contributor on the delegated AGC subnet
- **Deployment mode** - ALB controller is installed through the supported Helm + workload identity path during `azd provision` postprovision hooks
- **Scope boundary** - This module does not create `ApplicationLoadBalancer`, `Gateway`, `HTTPRoute`, or `Ingress` resources

### API Gateway

- **Azure API Management** - API gateway for all services:
  - Consumption tier (dev/staging)
  - StandardV2 tier (prod)
  - VNet integration in prod
- **Application Gateway for Containers prerequisites** - Prepared in dev without forcing any workload cutover; downstream issues publish routes and perform migration

### AI Platform

- **Azure AI Foundry** - Shared Foundry resource and hub for agents and model deployments
  - Deployed in **West US 3** (`westus3`) for Azure AI Agent Service compatibility
  - **Public network access enabled** for agent service operations

### Observability

- **Application Insights** - Distributed tracing, metrics, logs
- **Log Analytics Workspace** - Centralized logging (90-day retention)

## RBAC Assignments

The module automatically configures **passwordless authentication** using Managed Identity:

- **AKS → ACR**: `AcrPull` (pull container images)
- **AKS → Cosmos DB**: `Cosmos DB Data Contributor` (agent warm memory)
- **AKS → Event Hubs**: `Event Hubs Data Sender/Receiver` (publish/subscribe events)
- **AKS → Key Vault**: `Key Vault Secrets User` (read secrets)
- **AKS → Storage**: `Storage Blob Data Contributor` (read/write blobs)

## Deployment

### Prerequisites

- Azure CLI installed and authenticated
- Subscription with Owner or Contributor role

### Demo Environment (Step-by-Step)

1) Deploy shared infrastructure

```bash
az deployment sub create \
  --location eastus2 \
  --template-file .infra/modules/shared-infrastructure/shared-infrastructure-main.bicep \
  --parameters environment=demo location=eastus2
```

2) Deploy Static Web App

```bash
az deployment sub create \
  --location eastus2 \
  --template-file .infra/modules/static-web-app/static-web-app-main.bicep \
  --parameters environment=demo \
               resourceGroupName=holidaypeakhub-demo-rg
```

3) Deploy services (demo strategy)

```bash
# Example: deploy one service
python .infra/cli.py deploy \
  --service ecommerce-catalog-search \
  --location eastus2 \
  --resource-group holidaypeakhub-demo-rg \
  --app-image ghcr.io/azure-samples/ecommerce-catalog-search:latest

# Or deploy all services
python .infra/cli.py deploy-all \
  --location eastus2 \
  --resource-group holidaypeakhub-demo-rg \
  --app-image ghcr.io/azure-samples/<service>:latest
```

4) Connect to AKS

```bash
az aks get-credentials \
  --resource-group holidaypeakhub-demo-rg \
  --name holidaypeakhub-demo-aks

kubectl get nodes
```

### Deploy Shared Infrastructure

```bash
# Dev environment
az deployment sub create \
  --location eastus \
  --template-file .infra/modules/shared-infrastructure/shared-infrastructure-main.bicep \
  --parameters environment=dev

# Production environment
az deployment sub create \
  --location eastus \
  --template-file .infra/modules/shared-infrastructure/shared-infrastructure-main.bicep \
  --parameters environment=prod
```

### Connect to AKS

```bash
# Get credentials
az aks get-credentials \
  --resource-group holidaypeakhub-dev-rg \
  --name holidaypeakhub-dev-aks

# Verify connection
kubectl get nodes
```

### Access Key Vault

```bash
# List secrets (requires RBAC permissions)
az keyvault secret list \
  --vault-name holidaypeakhub-dev-kv

# Get secret value
az keyvault secret show \
  --vault-name holidaypeakhub-dev-kv \
  --name stripe-secret-key \
  --query value -o tsv
```

## Cost Optimization

### Dev Environment (Serverless/Low Tier)
- **PostgreSQL**: Burstable SKU for dev (`Standard_B2s`)
- **Cosmos DB**: Serverless mode (agent warm memory only)
- **Redis**: Premium P1 (6GB)
- **AKS**: 1 system node, 2 agent nodes, 1 CRUD node (autoscaling disabled)
- **APIM**: Consumption tier (pay per million calls)
- **Estimated Monthly Cost**: ~$500-700/month

### Production Environment (High Availability)
- **PostgreSQL**: GeneralPurpose SKU with HA for prod
- **Cosmos DB**: Provisioned throughput with autoscale (agent warm memory)
- **Redis**: Premium P1 with geo-replication
- **AKS**: 3 system nodes, 5 agent nodes, 3 CRUD nodes (autoscaling enabled)
- **APIM**: StandardV2 tier with VNet integration
- **Estimated Monthly Cost**: ~$3,000-5,000/month (depends on traffic)

## Agent Module Integration

Agents use the shared infrastructure and create their own memory containers:

```bicep
// Agent Bicep module example
param sharedCosmosAccountName string
param sharedRedisName string
param sharedStorageAccountName string
param agentName string = 'ecommerce-catalog-search'

// Reference shared Cosmos DB account
resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2023-11-15' existing = {
  name: sharedCosmosAccountName
}

// Create agent-specific container
resource agentMemoryContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDb
  name: 'warm-${agentName}-chat-memory'
  properties: {
    resource: {
      id: 'warm-${agentName}-chat-memory'
      partitionKey: {
        paths: ['/pk']
        kind: 'Hash'
      }
    }
  }
}
```

## Next Steps

1. **Deploy CRUD Service** - See `.infra/modules/crud-service/`
2. **Deploy Agent Services** - Update agent modules to reference shared infrastructure
3. **Configure APIM** - Define API routes and policies
4. **Deploy Frontend** - See `.infra/modules/static-web-app/`

## Troubleshooting

### Private Endpoint DNS Resolution
If services can't connect to PostgreSQL/Cosmos DB/Redis/Event Hubs:
1. Verify private endpoints are created: `az network private-endpoint list -g <rg>`
2. Check AKS CoreDNS is using Azure DNS: `kubectl get configmap coredns -n kube-system -o yaml`
3. Test DNS resolution from pod: `kubectl run -it --rm debug --image=busybox --restart=Never -- nslookup <postgres-server>.postgres.database.azure.com`

### RBAC Permissions
If AKS pods can't access resources:
1. Verify role assignments: `az role assignment list --assignee <aks-managed-identity-client-id>`
2. Check AKS Managed Identity: `az aks show -g <rg> -n <aks> --query identity`
3. Ensure Workload Identity is enabled: `az aks show -g <rg> -n <aks> --query oidcIssuerProfile.enabled`

## Security Notes

- ✅ PaaS services use private endpoints by default
- ⚠️ Azure AI Foundry intentionally uses public network access to support agent provisioning/invocation
- ✅ **Credential isolation** - PostgreSQL admin password is injected via deployment and should be stored in Key Vault
- ✅ **Secrets in Key Vault** - No hardcoded credentials
- ✅ **TLS 1.2 minimum** - All services enforce secure connections
- ✅ **Soft delete enabled** - Key Vault and Storage have soft delete (90 days)
- ✅ **Continuous backup** - PostgreSQL and Cosmos DB support point-in-time restore
