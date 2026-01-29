# Infrastructure Governance and Compliance Guidelines

**Version**: 1.0  
**Last Updated**: 2026-01-30  
**Owner**: Infrastructure Team

## Overview

This document defines the standards, policies, and compliance requirements for infrastructure provisioning, deployment, and operations in the Holiday Peak Hub project. All infrastructure code and operations must adhere to these guidelines to ensure security, scalability, reliability, and cost-efficiency.

## Table of Contents

1. [Infrastructure as Code](#infrastructure-as-code)
2. [Azure Services Standards](#azure-services-standards)
3. [Kubernetes Deployment](#kubernetes-deployment)
4. [Security and Compliance](#security-and-compliance)
5. [Networking Architecture](#networking-architecture)
6. [Data Persistence](#data-persistence)
7. [Monitoring and Observability](#monitoring-and-observability)
8. [Disaster Recovery](#disaster-recovery)
9. [Cost Management](#cost-management)
10. [CI/CD Pipeline](#cicd-pipeline)

---

## Infrastructure as Code

### Bicep Standards

**Reference**: [ADR-002: Azure Services](../architecture/adrs/adr-002-azure-services.md)

**Mandatory**: All infrastructure must be defined as code using Bicep.

✅ **DO**:
- Use Bicep for all Azure resource definitions
- Version control all infrastructure code
- Use modules for reusable components
- Add comprehensive comments
- Follow naming conventions

❌ **DO NOT**:
- Manually create resources via Azure Portal
- Use ARM templates (use Bicep instead)
- Mix Terraform and Bicep in same project
- Hard-code values (use parameters)

### File Structure

```
infrastructure/
├── bicep/
│   ├── main.bicep              # Main orchestration
│   ├── parameters/
│   │   ├── dev.json            # Dev environment
│   │   ├── staging.json        # Staging environment
│   │   └── prod.json           # Production environment
│   ├── modules/
│   │   ├── aks.bicep           # AKS cluster
│   │   ├── cosmos.bicep        # Cosmos DB
│   │   ├── redis.bicep         # Redis Cache
│   │   ├── storage.bicep       # Storage Account
│   │   ├── event-hub.bicep     # Event Hubs
│   │   ├── app-insights.bicep  # Application Insights
│   │   └── key-vault.bicep     # Key Vault
│   └── scripts/
│       ├── deploy.sh           # Deployment script
│       └── validate.sh         # Validation script
└── helm/
    ├── charts/
    │   ├── api-service/        # Generic service chart
    │   ├── background-worker/  # Worker chart
    │   └── frontend/           # Frontend chart
    └── values/
        ├── dev.yaml
        ├── staging.yaml
        └── prod.yaml
```

### Bicep Module Template

```bicep
// modules/aks.bicep
@description('AKS cluster name')
param clusterName string

@description('Location for all resources')
param location string = resourceGroup().location

@description('Kubernetes version')
param kubernetesVersion string = '1.28'

@description('Node pool configuration')
param nodePoolConfig object = {
  name: 'default'
  count: 3
  vmSize: 'Standard_D4s_v3'
  maxPods: 110
}

@description('Enable RBAC')
param enableRBAC bool = true

@description('Enable monitoring')
param enableMonitoring bool = true

@description('Log Analytics workspace ID')
param workspaceId string

resource aks 'Microsoft.ContainerService/managedClusters@2023-10-01' = {
  name: clusterName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    kubernetesVersion: kubernetesVersion
    dnsPrefix: '${clusterName}-dns'
    enableRBAC: enableRBAC
    agentPoolProfiles: [
      {
        name: nodePoolConfig.name
        count: nodePoolConfig.count
        vmSize: nodePoolConfig.vmSize
        maxPods: nodePoolConfig.maxPods
        mode: 'System'
        osType: 'Linux'
        type: 'VirtualMachineScaleSets'
        enableAutoScaling: true
        minCount: 2
        maxCount: 10
      }
    ]
    networkProfile: {
      networkPlugin: 'azure'
      serviceCidr: '10.0.0.0/16'
      dnsServiceIP: '10.0.0.10'
    }
    addonProfiles: {
      omsagent: {
        enabled: enableMonitoring
        config: {
          logAnalyticsWorkspaceResourceID: workspaceId
        }
      }
    }
  }
}

output aksId string = aks.id
output aksFqdn string = aks.properties.fqdn
output aksIdentityPrincipalId string = aks.identity.principalId
```

### Naming Conventions

**Resource Naming Pattern**: `{project}-{environment}-{resource-type}-{instance}`

**Examples**:
- AKS Cluster: `holidaypeak-prod-aks-01`
- Cosmos DB: `holidaypeak-prod-cosmos-01`
- Redis Cache: `holidaypeak-prod-redis-01`
- Storage Account: `holidaypeakprodsa01` (no hyphens for storage)
- Key Vault: `holidaypeak-prod-kv-01`

**Environment Codes**:
- `dev` - Development
- `stg` - Staging
- `prod` - Production

---

## Azure Services Standards

### Resource Group Organization

**Reference**: [ADR-002: Azure Services](../architecture/adrs/adr-002-azure-services.md)

**Structure**:
```
holidaypeak-prod-rg-core      # Core infrastructure (AKS, networking)
holidaypeak-prod-rg-data      # Data stores (Cosmos, Redis, Storage)
holidaypeak-prod-rg-apps      # Application resources (App Insights)
holidaypeak-prod-rg-identity  # Identity resources (Key Vault)
```

### Service Tier Selection

| Service | Tier | Justification |
|---------|------|---------------|
| **AKS** | Standard | Production SLA, RBAC, monitoring |
| **Cosmos DB** | Serverless/Provisioned | Autoscale based on workload |
| **Redis Cache** | Premium | Persistence, clustering, geo-replication |
| **Storage Account** | Standard LRS/GRS | Cost-effective, geo-redundant |
| **Event Hubs** | Standard | Auto-inflate, capture |
| **Application Insights** | Standard | Full telemetry, 90-day retention |

### Regional Deployment

**Primary Region**: East US  
**Secondary Region**: West US (DR)

**Multi-Region Resources**:
- Cosmos DB (global distribution)
- Storage Account (GRS)
- Azure Front Door (CDN)

---

## Kubernetes Deployment

### AKS Configuration

**Reference**: [ADR-009: AKS Deployment](../architecture/adrs/adr-009-aks-deployment.md)

**Cluster Specifications**:
```yaml
# Production AKS Configuration
kubernetes_version: "1.28"
node_pools:
  - name: system
    vm_size: Standard_D4s_v3
    node_count: 3
    min_count: 2
    max_count: 5
    mode: System
    
  - name: apps
    vm_size: Standard_D8s_v3
    node_count: 3
    min_count: 3
    max_count: 20
    mode: User
    taints:
      - workload=apps:NoSchedule
    
  - name: memory
    vm_size: Standard_E8s_v3
    node_count: 2
    min_count: 2
    max_count: 10
    mode: User
    taints:
      - workload=memory:NoSchedule

network:
  plugin: azure
  service_cidr: 10.0.0.0/16
  dns_service_ip: 10.0.0.10
  pod_cidr: 10.244.0.0/16

addons:
  - azure_policy
  - azure_keyvault_secrets_provider
  - monitoring
  - ingress_application_gateway
```

### Helm Chart Standards

**Service Chart Template**:
```yaml
# charts/api-service/values.yaml
replicaCount: 3

image:
  repository: holidaypeak.azurecr.io/api-service
  pullPolicy: IfNotPresent
  tag: "" # Overridden in CI/CD

resources:
  limits:
    cpu: 1000m
    memory: 1Gi
  requests:
    cpu: 500m
    memory: 512Mi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

service:
  type: ClusterIP
  port: 80
  targetPort: 8000

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: api.holidaypeak.com
      paths:
        - path: /
          pathType: Prefix

env:
  - name: REDIS_URL
    valueFrom:
      secretKeyRef:
        name: redis-credentials
        key: connection-string
  
  - name: COSMOS_ACCOUNT_URI
    valueFrom:
      secretKeyRef:
        name: cosmos-credentials
        key: account-uri

livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5

podAnnotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8000"
  prometheus.io/path: "/metrics"
```

### KEDA Scaling

**Reference**: [ADR-009: AKS with KEDA](../architecture/adrs/adr-009-aks-deployment.md)

```yaml
# KEDA ScaledObject for Event Hub scaling
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: cart-intelligence-scaler
  namespace: production
spec:
  scaleTargetRef:
    name: cart-intelligence
  minReplicaCount: 2
  maxReplicaCount: 50
  triggers:
    - type: azure-eventhub
      metadata:
        connectionFromEnv: EVENTHUB_CONNECTION_STRING
        consumerGroup: cart-intelligence
        unprocessedEventThreshold: '64'
        activationUnprocessedEventThreshold: '10'
        
    - type: cpu
      metadataType: Utilization
      metadata:
        value: "70"
        
    - type: memory
      metadataType: Utilization
      metadata:
        value: "80"
```

### Deployment Strategies

**Canary Deployment**:
```yaml
# Argo Rollouts configuration
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: cart-intelligence
spec:
  replicas: 10
  strategy:
    canary:
      steps:
        - setWeight: 10
        - pause: {duration: 5m}
        - setWeight: 30
        - pause: {duration: 5m}
        - setWeight: 60
        - pause: {duration: 5m}
        - setWeight: 100
      trafficRouting:
        nginx:
          stableIngress: cart-intelligence
      analysis:
        templates:
          - templateName: success-rate
        startingStep: 2
        args:
          - name: service-name
            value: cart-intelligence
```

---

## Security and Compliance

### Azure Key Vault

**Secret Management**:
```bicep
// modules/key-vault.bicep
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'premium'  // Premium for HSM-backed keys
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enablePurgeProtection: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'AzureServices'
      virtualNetworkRules: [
        {
          id: subnetId
          ignoreMissingVnetServiceEndpoint: false
        }
      ]
    }
  }
}
```

**Secret Access Policy**:
- Use Managed Identity for all services
- Grant least privilege access
- Rotate secrets every 90 days
- Audit all secret access

### Network Security

**Network Policies**:
```yaml
# Network policy for service isolation
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: cart-intelligence-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: cart-intelligence
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: production
        - podSelector:
            matchLabels:
              app: api-gateway
      ports:
        - protocol: TCP
          port: 8000
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              name: production
        - podSelector:
            matchLabels:
              app: redis
      ports:
        - protocol: TCP
          port: 6379
    - to:
        - podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
```

### RBAC Configuration

```yaml
# Kubernetes RBAC for service accounts
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: app-service-role
  namespace: production
rules:
  - apiGroups: [""]
    resources: ["secrets", "configmaps"]
    verbs: ["get", "list"]
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list", "watch"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: app-service-binding
  namespace: production
subjects:
  - kind: ServiceAccount
    name: cart-intelligence
    namespace: production
roleRef:
  kind: Role
  name: app-service-role
  apiGroup: rbac.authorization.k8s.io
```

---

## Networking Architecture

### Virtual Network Design

```bicep
// VNet configuration
resource vnet 'Microsoft.Network/virtualNetworks@2023-06-01' = {
  name: vnetName
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: [
        '10.0.0.0/16'  // Main VNet CIDR
      ]
    }
    subnets: [
      {
        name: 'aks-subnet'
        properties: {
          addressPrefix: '10.0.0.0/20'  // AKS nodes
          privateEndpointNetworkPolicies: 'Disabled'
          privateLinkServiceNetworkPolicies: 'Disabled'
        }
      }
      {
        name: 'data-subnet'
        properties: {
          addressPrefix: '10.0.16.0/24'  // Data services
          serviceEndpoints: [
            {
              service: 'Microsoft.Storage'
            }
            {
              service: 'Microsoft.AzureCosmosDB'
            }
          ]
        }
      }
      {
        name: 'private-endpoints-subnet'
        properties: {
          addressPrefix: '10.0.17.0/24'  // Private endpoints
          privateEndpointNetworkPolicies: 'Enabled'
        }
      }
    ]
  }
}
```

### Private Endpoints

**Required for**:
- Cosmos DB
- Storage Account
- Redis Cache
- Key Vault
- Container Registry

```bicep
// Private endpoint for Cosmos DB
resource cosmosPrivateEndpoint 'Microsoft.Network/privateEndpoints@2023-06-01' = {
  name: '${cosmosAccountName}-pe'
  location: location
  properties: {
    subnet: {
      id: privateEndpointSubnetId
    }
    privateLinkServiceConnections: [
      {
        name: '${cosmosAccountName}-plsc'
        properties: {
          privateLinkServiceId: cosmosAccount.id
          groupIds: [
            'Sql'
          ]
        }
      }
    ]
  }
}
```

### Ingress Configuration

```yaml
# NGINX Ingress Controller
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-ingress
  namespace: production
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    nginx.ingress.kubernetes.io/cors-allow-origin: "https://holidaypeak.com"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - api.holidaypeak.com
      secretName: api-tls-secret
  rules:
    - host: api.holidaypeak.com
      http:
        paths:
          - path: /catalog
            pathType: Prefix
            backend:
              service:
                name: catalog-search
                port:
                  number: 80
          - path: /cart
            pathType: Prefix
            backend:
              service:
                name: cart-intelligence
                port:
                  number: 80
```

---

## Data Persistence

### Cosmos DB Configuration

**Reference**: [ADR-002: Azure Services](../architecture/adrs/adr-002-azure-services.md)

```bicep
resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2023-11-15' = {
  name: cosmosAccountName
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
      maxIntervalInSeconds: 5
      maxStalenessPrefix: 100
    }
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: true
      }
      {
        locationName: secondaryLocation
        failoverPriority: 1
        isZoneRedundant: false
      }
    ]
    backupPolicy: {
      type: 'Continuous'
      continuousModeProperties: {
        tier: 'Continuous30Days'
      }
    }
    enableAutomaticFailover: true
    enableMultipleWriteLocations: false
    capabilities: [
      {
        name: 'EnableServerless'  // Use serverless for dev/test
      }
    ]
  }
}

resource cosmosDatabase 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2023-11-15' = {
  parent: cosmosAccount
  name: databaseName
  properties: {
    resource: {
      id: databaseName
    }
  }
}

resource container 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDatabase
  name: containerName
  properties: {
    resource: {
      id: containerName
      partitionKey: {
        paths: [
          '/userId'
        ]
        kind: 'Hash'
      }
      indexingPolicy: {
        automatic: true
        indexingMode: 'consistent'
        includedPaths: [
          {
            path: '/*'
          }
        ]
        excludedPaths: [
          {
            path: '/"_etag"/?'
          }
        ]
      }
      defaultTtl: 2592000  // 30 days
    }
  }
}
```

### Redis Cache Configuration

```bicep
resource redis 'Microsoft.Cache/redis@2023-08-01' = {
  name: redisName
  location: location
  properties: {
    sku: {
      name: 'Premium'
      family: 'P'
      capacity: 1
    }
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
    redisConfiguration: {
      'maxmemory-policy': 'allkeys-lru'
      'maxmemory-reserved': '50'
      'maxfragmentationmemory-reserved': '50'
    }
    redisVersion: '6'
    publicNetworkAccess: 'Disabled'
  }
}
```

### Storage Account Configuration

```bicep
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_GRS'  // Geo-redundant
  }
  properties: {
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    allowBlobPublicAccess: false
    encryption: {
      services: {
        blob: {
          enabled: true
          keyType: 'Account'
        }
      }
      keySource: 'Microsoft.Storage'
    }
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Deny'
      virtualNetworkRules: [
        {
          id: dataSubnetId
          action: 'Allow'
        }
      ]
    }
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    deleteRetentionPolicy: {
      enabled: true
      days: 30
    }
    containerDeleteRetentionPolicy: {
      enabled: true
      days: 30
    }
  }
}
```

---

## Monitoring and Observability

### Application Insights

```bicep
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: workspaceId
    RetentionInDays: 90
    IngestionMode: 'LogAnalytics'
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}
```

### Log Analytics Queries

**High Memory Usage**:
```kusto
Perf
| where ObjectName == "K8SContainer"
| where CounterName == "memoryWorkingSetBytes"
| summarize AvgMemoryMB = avg(CounterValue)/1024/1024 by bin(TimeGenerated, 5m), InstanceName
| where AvgMemoryMB > 900  // Alert threshold
| render timechart
```

**Failed Requests**:
```kusto
requests
| where success == false
| where timestamp > ago(1h)
| summarize count() by resultCode, operation_Name
| order by count_ desc
```

### Prometheus Metrics

**ServiceMonitor for Prometheus**:
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: cart-intelligence-metrics
  namespace: production
spec:
  selector:
    matchLabels:
      app: cart-intelligence
  endpoints:
    - port: metrics
      path: /metrics
      interval: 30s
```

---

## Disaster Recovery

### Backup Strategy

**Cosmos DB**:
- Continuous backup (30 days)
- Point-in-time restore
- Geo-replication to secondary region

**Redis Cache**:
- Persistence enabled
- Export to Storage Account daily
- Secondary cache in DR region

**Storage Account**:
- Geo-redundant storage (GRS)
- Immutable blob storage for compliance

### Recovery Time Objectives

| Service | RPO | RTO |
|---------|-----|-----|
| Cosmos DB | < 5 minutes | < 1 hour |
| Redis Cache | < 15 minutes | < 30 minutes |
| Storage Account | < 1 hour | < 2 hours |
| AKS | N/A (stateless) | < 30 minutes |

### DR Runbook

1. **Detection**: Monitoring alerts trigger DR procedure
2. **Assessment**: Validate extent of outage
3. **Failover**: Execute regional failover (automated)
4. **Verification**: Validate all services in DR region
5. **Communication**: Notify stakeholders
6. **Failback**: Return to primary region when resolved

---

## Cost Management

### Budget Alerts

```bicep
resource budget 'Microsoft.Consumption/budgets@2023-05-01' = {
  name: 'holidaypeak-monthly-budget'
  properties: {
    category: 'Cost'
    amount: 10000  // $10K/month
    timeGrain: 'Monthly'
    timePeriod: {
      startDate: '2026-01-01'
    }
    notifications: {
      actual_GreaterThan_80_Percent: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 80
        contactEmails: [
          'devops@holidaypeak.com'
        ]
      }
    }
  }
}
```

### Cost Optimization

**AKS**:
- Use spot instances for non-critical workloads
- Enable cluster autoscaler
- Right-size node pools

**Cosmos DB**:
- Use serverless for dev/test
- Use provisioned throughput with autoscale for prod
- Implement TTL policies

**Storage**:
- Use lifecycle management policies
- Archive cold data to cool/archive tiers
- Delete unused blobs

### Resource Tags

**Mandatory Tags**:
```bicep
var commonTags = {
  environment: environment
  project: 'holidaypeak'
  costCenter: 'engineering'
  owner: 'devops@holidaypeak.com'
  managedBy: 'bicep'
}
```

---

## CI/CD Pipeline

### GitHub Actions Workflow

```yaml
name: Deploy Infrastructure

on:
  push:
    branches:
      - main
    paths:
      - 'infrastructure/**'
  workflow_dispatch:

env:
  AZURE_SUBSCRIPTION_ID: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
  RESOURCE_GROUP: holidaypeak-prod-rg-core

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      
      - name: Validate Bicep
        run: |
          az bicep build --file infrastructure/bicep/main.bicep
          az deployment group validate \
            --resource-group ${{ env.RESOURCE_GROUP }} \
            --template-file infrastructure/bicep/main.bicep \
            --parameters infrastructure/bicep/parameters/prod.json

  deploy:
    needs: validate
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4
      
      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      
      - name: Deploy Infrastructure
        run: |
          az deployment group create \
            --resource-group ${{ env.RESOURCE_GROUP }} \
            --template-file infrastructure/bicep/main.bicep \
            --parameters infrastructure/bicep/parameters/prod.json \
            --mode Incremental
      
      - name: Get AKS Credentials
        run: |
          az aks get-credentials \
            --resource-group ${{ env.RESOURCE_GROUP }} \
            --name holidaypeak-prod-aks-01
      
      - name: Deploy Helm Charts
        run: |
          helm upgrade --install cart-intelligence \
            infrastructure/helm/charts/api-service \
            -f infrastructure/helm/values/prod.yaml \
            --namespace production \
            --create-namespace
```

---

## Compliance Requirements

### Azure Policy

```bicep
// Enforce required tags
resource tagPolicy 'Microsoft.Authorization/policyAssignments@2023-04-01' = {
  name: 'enforce-tags'
  properties: {
    policyDefinitionId: '/providers/Microsoft.Authorization/policyDefinitions/1e30110a-5ceb-460c-a204-c1c3969c6d62'
    parameters: {
      tagNames: {
        value: [
          'environment'
          'project'
          'costCenter'
        ]
      }
    }
  }
}

// Deny public access to storage accounts
resource storagePolicy 'Microsoft.Authorization/policyAssignments@2023-04-01' = {
  name: 'deny-storage-public-access'
  properties: {
    policyDefinitionId: '/providers/Microsoft.Authorization/policyDefinitions/4fa4b6c0-31ca-4c0d-b10d-24b96f62a751'
  }
}
```

### Compliance Standards

- **SOC 2 Type II**: Annual audit
- **PCI DSS**: If handling payment data
- **GDPR**: Data privacy for EU customers
- **HIPAA**: If handling health data

---

## References

### Architecture Decision Records

- [ADR-002: Azure Services](../architecture/adrs/adr-002-azure-services.md)
- [ADR-009: AKS Deployment](../architecture/adrs/adr-009-aks-deployment.md)

### Documentation

- [Azure Well-Architected Framework](https://learn.microsoft.com/azure/well-architected/)
- [AKS Best Practices](https://learn.microsoft.com/azure/aks/best-practices)
- [Cosmos DB Best Practices](https://learn.microsoft.com/azure/cosmos-db/best-practice-dotnet)

---

## Revision History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-01-30 | Initial documentation | Infrastructure Team |
