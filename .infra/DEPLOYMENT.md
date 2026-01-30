# Infrastructure Deployment Guide

This guide walks you through deploying the Holiday Peak Hub infrastructure to Azure.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│ Azure Subscription                                               │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Resource Group: holidaypeakhub-{env}-rg                      │ │
│ │                                                               │ │
│ │ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │ │
│ │ │ AKS Cluster │  │ Cosmos DB   │  │ Event Hubs  │          │ │
│ │ │ 3 node pools│  │ 10 containers│  │ 5 topics    │          │ │
│ │ └─────────────┘  └─────────────┘  └─────────────┘          │ │
│ │                                                               │ │
│ │ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │ │
│ │ │ Redis Cache │  │ Storage Acct│  │ Key Vault   │          │ │
│ │ │ Premium 6GB │  │ Blob Storage│  │ Secrets     │          │ │
│ │ └─────────────┘  └─────────────┘  └─────────────┘          │ │
│ │                                                               │ │
│ │ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │ │
│ │ │ ACR         │  │ APIM        │  │ VNet + NSG  │          │ │
│ │ │ Premium     │  │ Consumption │  │ 5 subnets   │          │ │
│ │ └─────────────┘  └─────────────┘  └─────────────┘          │ │
│ │                                                               │ │
│ │ ┌─────────────┐  ┌─────────────┐                            │ │
│ │ │ App Insights│  │ Log Analytics│                            │ │
│ │ │ Monitoring  │  │ Workspace    │                            │ │
│ │ └─────────────┘  └─────────────┘                            │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Azure Static Web Apps (Separate RG)                             │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ holidaypeakhub-ui-{env}                                      │ │
│ │ - Next.js Frontend                                           │ │
│ │ - GitHub Actions CI/CD                                       │ │
│ │ - Global CDN                                                 │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

1. **Azure CLI** installed and authenticated
   ```bash
   az version  # Should be 2.50.0 or later
   az login
   ```

2. **Azure Subscription** with Owner or Contributor role
   ```bash
   az account show
   az account set --subscription <subscription-id>
   ```

3. **Resource Providers** registered
   ```bash
   az provider register --namespace Microsoft.ContainerService
   az provider register --namespace Microsoft.DocumentDB
   az provider register --namespace Microsoft.EventHub
   az provider register --namespace Microsoft.Cache
   az provider register --namespace Microsoft.Storage
   az provider register --namespace Microsoft.KeyVault
   az provider register --namespace Microsoft.ApiManagement
   az provider register --namespace Microsoft.ContainerRegistry
   az provider register --namespace Microsoft.Network
   az provider register --namespace Microsoft.Insights
   az provider register --namespace Microsoft.OperationalInsights
   az provider register --namespace Microsoft.Web
   ```

4. **Permissions** required:
   - `Microsoft.Authorization/roleAssignments/write` (for RBAC)
   - `Microsoft.Resources/deployments/write` (for deployments)

## Deployment Steps

### Step 1: Deploy Shared Infrastructure (Dev Environment)

This creates: AKS, ACR, Cosmos DB, Event Hubs, Redis, Storage, Key Vault, APIM, VNet, Application Insights

```bash
# From repo root
cd .infra/modules/shared-infrastructure

# Deploy to dev environment (uses serverless Cosmos DB, consumption APIM)
az deployment sub create \
  --name shared-infra-dev-$(date +%Y%m%d-%H%M%S) \
  --location eastus \
  --template-file shared-infrastructure-main.bicep \
  --parameters environment=dev \
               projectName=holidaypeakhub

# Save outputs
az deployment sub show \
  --name shared-infra-dev-<timestamp> \
  --query properties.outputs \
  > ../../../outputs/shared-infra-dev.json
```

**Expected Duration**: 15-25 minutes

**Estimated Monthly Cost (Dev)**: ~$500-700

### Step 2: Verify Shared Infrastructure

```bash
# Get resource group name
RG_NAME="holidaypeakhub-dev-rg"

# List all resources
az resource list --resource-group $RG_NAME --output table

# Verify AKS cluster
az aks show --resource-group $RG_NAME --name holidaypeakhub-dev-aks --query "provisioningState"

# Verify Cosmos DB
az cosmosdb show --resource-group $RG_NAME --name holidaypeakhub-dev-cosmos --query "provisioningState"

# Verify Event Hubs
az eventhubs namespace show --resource-group $RG_NAME --name holidaypeakhub-dev-eventhub --query "provisioningState"
```

### Step 3: Connect to AKS Cluster

```bash
# Get AKS credentials
az aks get-credentials \
  --resource-group holidaypeakhub-dev-rg \
  --name holidaypeakhub-dev-aks \
  --overwrite-existing

# Verify connection
kubectl get nodes
kubectl get namespaces

# Verify node pools
kubectl get nodes -L agentpool
```

Expected output:
```
NAME                                 STATUS   ROLES   AGE   VERSION   AGENTPOOL
aks-agents-12345678-vmss000000       Ready    agent   5m    v1.29.x   agents
aks-agents-12345678-vmss000001       Ready    agent   5m    v1.29.x   agents
aks-crud-12345678-vmss000000         Ready    agent   5m    v1.29.x   crud
aks-system-12345678-vmss000000       Ready    agent   5m    v1.29.x   system
```

### Step 4: Verify RBAC and Connectivity

```bash
# Test Cosmos DB access from AKS (creates a test pod)
kubectl run test-cosmos \
  --image=mcr.microsoft.com/azure-cli \
  --restart=Never \
  --rm -it \
  --command -- bash -c "
    curl -H 'Metadata:true' 'http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://cosmos.azure.com' | jq .access_token
  "

# Test Event Hubs access
kubectl run test-eventhub \
  --image=mcr.microsoft.com/azure-cli \
  --restart=Never \
  --rm -it \
  --command -- bash -c "
    curl -H 'Metadata:true' 'http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://eventhubs.azure.net' | jq .access_token
  "
```

### Step 5: Store Secrets in Key Vault

```bash
# Set Key Vault name
KV_NAME="holidaypeakhub-dev-kv"

# Store Stripe API key (use test key for dev)
az keyvault secret set \
  --vault-name $KV_NAME \
  --name stripe-secret-key \
  --value "sk_test_YOUR_STRIPE_TEST_KEY"

# Store SendGrid API key (optional, for email notifications)
az keyvault secret set \
  --vault-name $KV_NAME \
  --name sendgrid-api-key \
  --value "SG.YOUR_SENDGRID_API_KEY"

# Store Microsoft Entra ID credentials (after app registration)
az keyvault secret set \
  --vault-name $KV_NAME \
  --name entra-tenant-id \
  --value "YOUR_TENANT_ID"

az keyvault secret set \
  --vault-name $KV_NAME \
  --name entra-client-id \
  --value "YOUR_CLIENT_ID"

az keyvault secret set \
  --vault-name $KV_NAME \
  --name entra-client-secret \
  --value "YOUR_CLIENT_SECRET"
```

### Step 6: Deploy Static Web App (Frontend)

```bash
cd .infra/modules/static-web-app

# Deploy to dev environment
az deployment sub create \
  --name static-web-app-dev-$(date +%Y%m%d-%H%M%S) \
  --location eastus2 \
  --template-file static-web-app-main.bicep \
  --parameters environment=dev \
               appName=holidaypeakhub-ui \
               resourceGroupName=holidaypeakhub-dev-rg \
               repositoryUrl='https://github.com/Azure-Samples/holiday-peak-hub' \
               branch='main'

# Get deployment token (for GitHub Actions)
DEPLOYMENT_TOKEN=$(az deployment sub show \
  --name static-web-app-dev-<timestamp> \
  --query properties.outputs.deploymentToken.value -o tsv)

echo "Deployment Token: $DEPLOYMENT_TOKEN"
```

### Step 7: Configure GitHub Actions for Frontend

```bash
# Install GitHub CLI (if not installed)
# https://cli.github.com/

# Authenticate with GitHub
gh auth login

# Set Static Web App deployment token as secret
gh secret set AZURE_STATIC_WEB_APPS_API_TOKEN_DEV \
  --body "$DEPLOYMENT_TOKEN" \
  --repo Azure-Samples/holiday-peak-hub
```

### Step 8: Update Frontend Configuration

Update `apps/ui/next.config.js`:

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export', // Enable static export
  images: {
    unoptimized: true, // Disable Next.js Image Optimization
  },
  trailingSlash: true,
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL || 'https://holidaypeakhub-dev-apim.azure-api.net',
    NEXT_PUBLIC_ENVIRONMENT: process.env.NEXT_PUBLIC_ENVIRONMENT || 'dev',
  },
}

module.exports = nextConfig
```

Commit and push to trigger deployment:
```bash
git add apps/ui/next.config.js
git commit -m "Configure Next.js for Azure Static Web Apps"
git push origin main
```

## Production Deployment

### Deploy to Production

```bash
# Deploy shared infrastructure (production tier)
az deployment sub create \
  --name shared-infra-prod-$(date +%Y%m%d-%H%M%S) \
  --location eastus \
  --template-file .infra/modules/shared-infrastructure/shared-infrastructure-main.bicep \
  --parameters environment=prod \
               projectName=holidaypeakhub

# Deploy Static Web App (Standard tier)
az deployment sub create \
  --name static-web-app-prod-$(date +%Y%m%d-%H%M%S) \
  --location eastus2 \
  --template-file .infra/modules/static-web-app/static-web-app-main.bicep \
  --parameters environment=prod \
               appName=holidaypeakhub-ui \
               resourceGroupName=holidaypeakhub-prod-rg \
               repositoryUrl='https://github.com/Azure-Samples/holiday-peak-hub' \
               branch='main'
```

**Expected Duration**: 25-35 minutes

**Estimated Monthly Cost (Prod)**: ~$3,000-5,000

### Production-Specific Configuration

1. **Remove Cosmos DB Serverless** - Edit `shared-infrastructure.bicep` and remove:
   ```bicep
   capabilities: [
     {
       name: 'EnableServerless'
     }
   ]
   ```

2. **Enable Multi-Region** - Add secondary region:
   ```bicep
   locations: [
     {
       locationName: location
       failoverPriority: 0
       isZoneRedundant: true
     }
     {
       locationName: 'westeurope'
       failoverPriority: 1
       isZoneRedundant: true
     }
   ]
   ```

3. **Configure Custom Domain** - Follow `.infra/modules/static-web-app/README.md`

## Validation Checklist

After deployment, verify:

- [ ] AKS cluster running with 3 node pools
- [ ] Cosmos DB accessible from AKS pods (Managed Identity)
- [ ] Event Hubs accessible from AKS pods
- [ ] Redis accessible from AKS pods
- [ ] Key Vault secrets retrievable from AKS
- [ ] ACR pull working from AKS
- [ ] APIM gateway accessible (test endpoint: `https://<apim-name>.azure-api.net`)
- [ ] Application Insights receiving telemetry
- [ ] Static Web App deployed and accessible
- [ ] Private endpoints created (no public access to PaaS services)

## Cleanup

To delete all resources:

```bash
# Delete dev environment
az group delete --name holidaypeakhub-dev-rg --yes --no-wait

# Delete production environment
az group delete --name holidaypeakhub-prod-rg --yes --no-wait
```

## Troubleshooting

### Issue: AKS Deployment Timeout
**Solution**: AKS provisioning can take 15-20 minutes. Check deployment status:
```bash
az deployment sub show --name shared-infra-dev-<timestamp> --query properties.provisioningState
```

### Issue: RBAC Permissions Not Working
**Solution**: Wait 5-10 minutes for Azure AD propagation. Verify role assignment:
```bash
AKS_PRINCIPAL_ID=$(az aks show -g holidaypeakhub-dev-rg -n holidaypeakhub-dev-aks --query identity.principalId -o tsv)
az role assignment list --assignee $AKS_PRINCIPAL_ID --all
```

### Issue: Private Endpoint DNS Not Resolving
**Solution**: Verify private DNS zone and link:
```bash
az network private-dns zone list -g holidaypeakhub-dev-rg --output table
az network private-dns link vnet list -g holidaypeakhub-dev-rg -z privatelink.documents.azure.com --output table
```

### Issue: Cosmos DB Serverless Quota Exceeded
**Solution**: Dev environment uses serverless (limited to 5,000 RU/s). For higher throughput, switch to provisioned:
```bash
az cosmosdb update \
  --resource-group holidaypeakhub-dev-rg \
  --name holidaypeakhub-dev-cosmos \
  --default-consistency-level Session \
  --capabilities DisableServerless
```

## Next Steps

1. **Deploy CRUD Service** - See Phase 1.2 in backend_plan.md
2. **Deploy Agent Services** - Update agent modules to reference shared infrastructure
3. **Configure APIM** - Define API routes and policies (Phase 7)
4. **Set up CI/CD** - GitHub Actions workflows for services (Phase 10)

## Cost Monitoring

Set up budget alerts:

```bash
az consumption budget create \
  --budget-name holidaypeakhub-dev-budget \
  --amount 1000 \
  --time-grain Monthly \
  --start-date $(date +%Y-%m-01) \
  --end-date $(date -d "1 year" +%Y-%m-01) \
  --resource-group holidaypeakhub-dev-rg \
  --notifications '[{"enabled":true,"operator":"GreaterThan","threshold":80,"contactEmails":["admin@holidaypeakhub.com"]}]'
```

## Support

For issues or questions:
- Check `.infra/modules/shared-infrastructure/README.md`
- Check `.infra/modules/static-web-app/README.md`
- Review ADRs in `docs/architecture/ADRs.md`
- Contact DevOps team
