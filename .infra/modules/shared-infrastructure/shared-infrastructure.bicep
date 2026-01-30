targetScope = 'resourceGroup'

param location string = resourceGroup().location
param environment string = 'dev' // dev, staging, prod
param projectName string = 'holidaypeakhub'

// Naming convention with environment suffix
var envSuffix = environment == 'prod' ? '' : '-${environment}'
var safeProjectName = toLower(replace(projectName, '-', ''))

// Resource names
var aksClusterName = '${projectName}${envSuffix}-aks'
var acrName = take('${safeProjectName}${replace(envSuffix, '-', '')}acr', 50)
var cosmosAccountName = '${projectName}${envSuffix}-cosmos'
var databaseName = 'holiday-peak-db'
var eventHubsNamespaceName = '${projectName}${envSuffix}-eventhub'
var redisName = '${projectName}${envSuffix}-redis'
var storageAccountName = take('${safeProjectName}${replace(envSuffix, '-', '')}store', 24)
var keyVaultName = take('${projectName}${envSuffix}-kv', 24)
var apimName = '${projectName}${envSuffix}-apim'
var appInsightsName = '${projectName}${envSuffix}-insights'
var logAnalyticsName = '${projectName}${envSuffix}-logs'
var vnetName = '${projectName}${envSuffix}-vnet'

// Virtual Network with subnets
resource vnet 'Microsoft.Network/virtualNetworks@2023-09-01' = {
  name: vnetName
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: [
        '10.0.0.0/16'
      ]
    }
    subnets: [
      {
        name: 'aks-system'
        properties: {
          addressPrefix: '10.0.0.0/22'
          networkSecurityGroup: {
            id: aksSystemNsg.id
          }
        }
      }
      {
        name: 'aks-agents'
        properties: {
          addressPrefix: '10.0.4.0/22'
          networkSecurityGroup: {
            id: aksAgentsNsg.id
          }
        }
      }
      {
        name: 'aks-crud'
        properties: {
          addressPrefix: '10.0.8.0/24'
          networkSecurityGroup: {
            id: aksCrudNsg.id
          }
        }
      }
      {
        name: 'apim'
        properties: {
          addressPrefix: '10.0.9.0/24'
          networkSecurityGroup: {
            id: apimNsg.id
          }
        }
      }
      {
        name: 'private-endpoints'
        properties: {
          addressPrefix: '10.0.10.0/24'
          networkSecurityGroup: {
            id: privateEndpointsNsg.id
          }
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
    ]
  }
}

// Network Security Groups
resource aksSystemNsg 'Microsoft.Network/networkSecurityGroups@2023-09-01' = {
  name: 'aks-system-nsg'
  location: location
  properties: {
    securityRules: [
      {
        name: 'AllowAKSControlPlane'
        properties: {
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '443'
          sourceAddressPrefix: 'AzureCloud'
          destinationAddressPrefix: '*'
          access: 'Allow'
          priority: 100
          direction: 'Inbound'
        }
      }
    ]
  }
}

resource aksAgentsNsg 'Microsoft.Network/networkSecurityGroups@2023-09-01' = {
  name: 'aks-agents-nsg'
  location: location
  properties: {
    securityRules: []
  }
}

resource aksCrudNsg 'Microsoft.Network/networkSecurityGroups@2023-09-01' = {
  name: 'aks-crud-nsg'
  location: location
  properties: {
    securityRules: []
  }
}

resource apimNsg 'Microsoft.Network/networkSecurityGroups@2023-09-01' = {
  name: 'apim-nsg'
  location: location
  properties: {
    securityRules: [
      {
        name: 'AllowAPIMManagement'
        properties: {
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '3443'
          sourceAddressPrefix: 'ApiManagement'
          destinationAddressPrefix: 'VirtualNetwork'
          access: 'Allow'
          priority: 100
          direction: 'Inbound'
        }
      }
      {
        name: 'AllowHTTPS'
        properties: {
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '443'
          sourceAddressPrefix: 'Internet'
          destinationAddressPrefix: 'VirtualNetwork'
          access: 'Allow'
          priority: 110
          direction: 'Inbound'
        }
      }
    ]
  }
}

resource privateEndpointsNsg 'Microsoft.Network/networkSecurityGroups@2023-09-01' = {
  name: 'private-endpoints-nsg'
  location: location
  properties: {
    securityRules: []
  }
}

// Log Analytics Workspace
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 90
  }
}

// Application Insights
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    IngestionMode: 'LogAnalytics'
  }
}

// Azure Container Registry
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: {
    name: 'Premium' // Premium for geo-replication and private endpoints
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: 'Disabled' // Private endpoint only
    networkRuleBypassOptions: 'AzureServices'
  }
}

// Cosmos DB Account (shared across all services and agents)
resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2023-11-15' = {
  name: cosmosAccountName
  location: location
  kind: 'GlobalDocumentDB'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    databaseAccountOfferType: 'Standard'
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: environment == 'prod'
      }
    ]
    capabilities: [
      {
        name: 'EnableServerless' // Use serverless for dev, remove for prod
      }
    ]
    publicNetworkAccess: 'Disabled' // Private endpoint only
    enableAutomaticFailover: environment == 'prod'
    enableMultipleWriteLocations: false
    backupPolicy: {
      type: 'Continuous'
      continuousModeProperties: {
        tier: 'Continuous30Days'
      }
    }
  }
}

// Cosmos DB Database
resource cosmosDb 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2023-11-15' = {
  parent: cosmos
  name: databaseName
  properties: {
    resource: {
      id: databaseName
    }
  }
}

// Operational Data Containers (for CRUD service)
resource usersContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDb
  name: 'users'
  properties: {
    resource: {
      id: 'users'
      partitionKey: {
        paths: ['/user_id']
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        automatic: true
        includedPaths: [
          { path: '/*' }
        ]
      }
    }
  }
}

resource productsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDb
  name: 'products'
  properties: {
    resource: {
      id: 'products'
      partitionKey: {
        paths: ['/category_slug']
        kind: 'Hash'
      }
    }
  }
}

resource ordersContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDb
  name: 'orders'
  properties: {
    resource: {
      id: 'orders'
      partitionKey: {
        paths: ['/user_id']
        kind: 'Hash'
      }
    }
  }
}

resource cartContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDb
  name: 'cart'
  properties: {
    resource: {
      id: 'cart'
      partitionKey: {
        paths: ['/user_id']
        kind: 'Hash'
      }
      defaultTtl: 7776000 // 90 days
    }
  }
}

resource reviewsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDb
  name: 'reviews'
  properties: {
    resource: {
      id: 'reviews'
      partitionKey: {
        paths: ['/product_id']
        kind: 'Hash'
      }
    }
  }
}

resource addressesContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDb
  name: 'addresses'
  properties: {
    resource: {
      id: 'addresses'
      partitionKey: {
        paths: ['/user_id']
        kind: 'Hash'
      }
    }
  }
}

resource paymentMethodsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDb
  name: 'payment_methods'
  properties: {
    resource: {
      id: 'payment_methods'
      partitionKey: {
        paths: ['/user_id']
        kind: 'Hash'
      }
    }
  }
}

resource ticketsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDb
  name: 'tickets'
  properties: {
    resource: {
      id: 'tickets'
      partitionKey: {
        paths: ['/user_id']
        kind: 'Hash'
      }
    }
  }
}

resource shipmentsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDb
  name: 'shipments'
  properties: {
    resource: {
      id: 'shipments'
      partitionKey: {
        paths: ['/order_id']
        kind: 'Hash'
      }
    }
  }
}

resource auditLogsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDb
  name: 'audit_logs'
  properties: {
    resource: {
      id: 'audit_logs'
      partitionKey: {
        paths: ['/entity_type']
        kind: 'Hash'
      }
      defaultTtl: 7776000 // 90 days, then archive
    }
  }
}

// Redis Cache (shared - agents use different databases)
resource redis 'Microsoft.Cache/Redis@2023-08-01' = {
  name: redisName
  location: location
  properties: {
    sku: {
      name: 'Premium'
      family: 'P'
      capacity: 1 // 6GB
    }
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
    publicNetworkAccess: 'Disabled' // Private endpoint only
    redisConfiguration: {
      'maxmemory-policy': 'allkeys-lru'
    }
  }
}

// Storage Account (shared - agents use different containers)
resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    publicNetworkAccess: 'Disabled' // Private endpoint only
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'AzureServices'
    }
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storage
  name: 'default'
  properties: {
    deleteRetentionPolicy: {
      enabled: true
      days: 7
    }
  }
}

// Event Hubs Namespace (shared across all services)
resource eventHubsNamespace 'Microsoft.EventHub/namespaces@2023-01-01-preview' = {
  name: eventHubsNamespaceName
  location: location
  sku: {
    name: 'Standard'
    tier: 'Standard'
    capacity: 1
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    publicNetworkAccess: 'Disabled' // Private endpoint only
    minimumTlsVersion: '1.2'
  }
}

// Event Hub Topics
resource orderEventsHub 'Microsoft.EventHub/namespaces/eventhubs@2023-01-01-preview' = {
  parent: eventHubsNamespace
  name: 'order-events'
  properties: {
    messageRetentionInDays: 7
    partitionCount: 4
  }
}

resource inventoryEventsHub 'Microsoft.EventHub/namespaces/eventhubs@2023-01-01-preview' = {
  parent: eventHubsNamespace
  name: 'inventory-events'
  properties: {
    messageRetentionInDays: 7
    partitionCount: 4
  }
}

resource shipmentEventsHub 'Microsoft.EventHub/namespaces/eventhubs@2023-01-01-preview' = {
  parent: eventHubsNamespace
  name: 'shipment-events'
  properties: {
    messageRetentionInDays: 7
    partitionCount: 4
  }
}

resource paymentEventsHub 'Microsoft.EventHub/namespaces/eventhubs@2023-01-01-preview' = {
  parent: eventHubsNamespace
  name: 'payment-events'
  properties: {
    messageRetentionInDays: 7
    partitionCount: 4
  }
}

resource userEventsHub 'Microsoft.EventHub/namespaces/eventhubs@2023-01-01-preview' = {
  parent: eventHubsNamespace
  name: 'user-events'
  properties: {
    messageRetentionInDays: 7
    partitionCount: 2
  }
}

// Key Vault
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'premium'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true // Use RBAC instead of access policies
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enablePurgeProtection: true
    publicNetworkAccess: 'Disabled' // Private endpoint only
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'AzureServices'
    }
  }
}

// Azure Kubernetes Service
resource aks 'Microsoft.ContainerService/managedClusters@2024-01-01' = {
  name: aksClusterName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    dnsPrefix: '${projectName}${envSuffix}'
    kubernetesVersion: '1.29'
    enableRBAC: true
    aadProfile: {
      managed: true
      enableAzureRBAC: true
    }
    networkProfile: {
      networkPlugin: 'azure'
      networkPolicy: 'azure'
      serviceCidr: '10.1.0.0/16'
      dnsServiceIP: '10.1.0.10'
    }
    agentPoolProfiles: [
      {
        name: 'system'
        count: environment == 'prod' ? 3 : 1
        vmSize: 'Standard_D4s_v5'
        osType: 'Linux'
        mode: 'System'
        vnetSubnetID: '${vnet.id}/subnets/aks-system'
        enableAutoScaling: true
        minCount: 1
        maxCount: environment == 'prod' ? 5 : 3
      }
      {
        name: 'agents'
        count: environment == 'prod' ? 5 : 2
        vmSize: 'Standard_D8s_v5'
        osType: 'Linux'
        mode: 'User'
        vnetSubnetID: '${vnet.id}/subnets/aks-agents'
        enableAutoScaling: true
        minCount: 2
        maxCount: environment == 'prod' ? 20 : 10
        nodeTaints: [
          'workload=agents:NoSchedule'
        ]
      }
      {
        name: 'crud'
        count: environment == 'prod' ? 3 : 1
        vmSize: 'Standard_D4s_v5'
        osType: 'Linux'
        mode: 'User'
        vnetSubnetID: '${vnet.id}/subnets/aks-crud'
        enableAutoScaling: true
        minCount: 1
        maxCount: environment == 'prod' ? 10 : 5
        nodeTaints: [
          'workload=crud:NoSchedule'
        ]
      }
    ]
    oidcIssuerProfile: {
      enabled: true
    }
    securityProfile: {
      workloadIdentity: {
        enabled: true
      }
    }
    addonProfiles: {
      omsagent: {
        enabled: true
        config: {
          logAnalyticsWorkspaceResourceID: logAnalytics.id
        }
      }
      azureKeyvaultSecretsProvider: {
        enabled: true
      }
    }
  }
}

// API Management (Consumption tier for dev, Standard for prod)
resource apim 'Microsoft.ApiManagement/service@2023-05-01-preview' = {
  name: apimName
  location: location
  sku: {
    name: environment == 'prod' ? 'StandardV2' : 'Consumption'
    capacity: environment == 'prod' ? 1 : 0
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    publisherEmail: 'admin@holidaypeakhub.com'
    publisherName: 'Holiday Peak Hub'
    virtualNetworkType: environment == 'prod' ? 'Internal' : 'None'
    virtualNetworkConfiguration: environment == 'prod' ? {
      subnetResourceId: '${vnet.id}/subnets/apim'
    } : null
  }
}

// RBAC Assignments
// AKS -> ACR (pull images)
resource aksAcrPullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aks.id, acr.id, 'AcrPull')
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d') // AcrPull
    principalId: aks.properties.identityProfile.kubeletidentity.objectId
    principalType: 'ServicePrincipal'
  }
}

// AKS -> Cosmos DB (Data Contributor)
resource aksCosmosRole 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2023-11-15' = {
  parent: cosmos
  name: guid(aks.id, cosmos.id, 'CosmosDataContributor')
  properties: {
    roleDefinitionId: '${cosmos.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002' // Built-in Data Contributor
    principalId: aks.identity.principalId
    scope: cosmos.id
  }
}

// AKS -> Event Hubs (Data Sender/Receiver)
resource aksEventHubSenderRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aks.id, eventHubsNamespace.id, 'EventHubSender')
  scope: eventHubsNamespace
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '2b629674-e913-4c01-ae53-ef4638d8f975') // Azure Event Hubs Data Sender
    principalId: aks.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource aksEventHubReceiverRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aks.id, eventHubsNamespace.id, 'EventHubReceiver')
  scope: eventHubsNamespace
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a638d3c7-ab3a-418d-83e6-5f17a39d4fde') // Azure Event Hubs Data Receiver
    principalId: aks.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// AKS -> Key Vault (Secrets User)
resource aksKeyVaultRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aks.id, keyVault.id, 'KeyVaultSecretsUser')
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6') // Key Vault Secrets User
    principalId: aks.properties.addonProfiles.azureKeyvaultSecretsProvider.identity.objectId
    principalType: 'ServicePrincipal'
  }
}

// AKS -> Storage (Blob Data Contributor)
resource aksStorageRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aks.id, storage.id, 'BlobDataContributor')
  scope: storage
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe') // Storage Blob Data Contributor
    principalId: aks.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Outputs
output aksClusterName string = aks.name
output acrLoginServer string = acr.properties.loginServer
output cosmosAccountName string = cosmos.name
output cosmosEndpoint string = cosmos.properties.documentEndpoint
output databaseName string = databaseName
output eventHubsNamespaceName string = eventHubsNamespace.name
output redisName string = redis.name
output storageAccountName string = storage.name
output keyVaultName string = keyVault.name
output keyVaultUri string = keyVault.properties.vaultUri
output apimName string = apim.name
output apimGatewayUrl string = apim.properties.gatewayUrl
output appInsightsConnectionString string = appInsights.properties.ConnectionString
output appInsightsInstrumentationKey string = appInsights.properties.InstrumentationKey
output vnetId string = vnet.id
output vnetName string = vnet.name
