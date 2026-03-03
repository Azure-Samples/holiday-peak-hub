targetScope = 'resourceGroup'

param location string = resourceGroup().location
param environment string = 'dev' // dev, staging, prod
@minLength(5)
param projectName string = 'holidaypeakhub'
@description('Optional override for Key Vault name (3-24 chars, lowercase letters, numbers, and hyphens). Leave empty to use default naming.')
param keyVaultNameOverride string = ''
@description('AKS Kubernetes version; leave empty to use Azure default')
param aksKubernetesVersion string = ''
@secure()
@description('PostgreSQL administrator password for CRUD transactional database. Leave empty to auto-generate a deterministic dev password.')
param postgresAdminPassword string = ''

// Naming convention with environment suffix
var envSuffix = environment == 'prod' ? '' : '-${environment}'
var safeProjectName = toLower(replace(projectName, '-', ''))

// Resource names
var aksClusterName = '${projectName}${envSuffix}-aks'
var acrName = take('${safeProjectName}${replace(envSuffix, '-', '')}acr', 50)
var cosmosAccountName = '${projectName}${envSuffix}-cosmos'
var databaseName = 'holiday-peak-db'
var postgresServerName = '${projectName}${envSuffix}-postgres'
var postgresDatabaseName = 'holiday_peak_crud'
var postgresAdminUser = 'crud_admin'
var postgresAdminPasswordSecretName = 'postgres-admin-password'
var resolvedPostgresAdminPassword = empty(postgresAdminPassword)
  ? '${take(uniqueString(resourceGroup().id, projectName, environment), 16)}Aa!12345'
  : postgresAdminPassword
var eventHubsNamespaceName = '${projectName}${envSuffix}-eventhub'
var redisName = '${projectName}${envSuffix}-redis'
var storageAccountName = take('${safeProjectName}${replace(envSuffix, '-', '')}store', 24)
var keyVaultName = empty(keyVaultNameOverride)
  ? take('${projectName}${envSuffix}-kv', 24)
  : toLower(keyVaultNameOverride)
var apimName = '${projectName}${envSuffix}-apim'
var appGwName = '${projectName}${envSuffix}-appgw'
var appInsightsName = '${projectName}${envSuffix}-insights'
var logAnalyticsName = '${projectName}${envSuffix}-logs'
var vnetName = '${projectName}${envSuffix}-vnet'
var aiServicesName = take('${safeProjectName}${replace(envSuffix, '-', '')}ais', 24)
var aiProjectSuffix = substring(uniqueString(resourceGroup().id), 0, 3)
var aiProjectInstanceName = 'aip${take(safeProjectName, 6)}${aiProjectSuffix}'
var aiProjectFriendlyName = '${projectName}${envSuffix} Foundry Project'
var aiProjectDescription = 'Holiday Peak Hub Foundry project for ${environment}.'
var aiFoundryBaseName = take('${safeProjectName}${replace(envSuffix, '-', '')}', 12)
var aiFoundryLocation = 'westus3'
var tags = {
  Project: projectName
  Environment: environment
}
// Network Security Groups (AVM)
module aksSystemNsg 'br/public:avm/res/network/network-security-group:0.5.2' = {
  name: 'nsg-aks-system'
  params: {
    name: 'aks-system-nsg'
    location: location
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
    tags: tags
  }
}

module aksAgentsNsg 'br/public:avm/res/network/network-security-group:0.5.2' = {
  name: 'nsg-aks-agents'
  params: {
    name: 'aks-agents-nsg'
    location: location
    securityRules: []
    tags: tags
  }
}

module aksCrudNsg 'br/public:avm/res/network/network-security-group:0.5.2' = {
  name: 'nsg-aks-crud'
  params: {
    name: 'aks-crud-nsg'
    location: location
    securityRules: []
    tags: tags
  }
}

// Application Gateway NSG for AGIC (required for ingress traffic)
module appGwNsg 'br/public:avm/res/network/network-security-group:0.5.2' = {
  name: 'nsg-appgw'
  params: {
    name: 'appgw-nsg'
    location: location
    securityRules: [
      {
        name: 'AllowGatewayManager'
        properties: {
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '65200-65535'
          sourceAddressPrefix: 'GatewayManager'
          destinationAddressPrefix: '*'
          access: 'Allow'
          priority: 100
          direction: 'Inbound'
        }
      }
      {
        name: 'AllowHTTP'
        properties: {
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '80'
          sourceAddressPrefix: 'Internet'
          destinationAddressPrefix: '*'
          access: 'Allow'
          priority: 110
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
          destinationAddressPrefix: '*'
          access: 'Allow'
          priority: 120
          direction: 'Inbound'
        }
      }
      {
        name: 'AllowAzureLoadBalancer'
        properties: {
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '*'
          sourceAddressPrefix: 'AzureLoadBalancer'
          destinationAddressPrefix: '*'
          access: 'Allow'
          priority: 130
          direction: 'Inbound'
        }
      }
    ]
    tags: tags
  }
}

module apimNsg 'br/public:avm/res/network/network-security-group:0.5.2' = {
  name: 'nsg-apim'
  params: {
    name: 'apim-nsg'
    location: location
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
    tags: tags
  }
}

module privateEndpointsNsg 'br/public:avm/res/network/network-security-group:0.5.2' = {
  name: 'nsg-private-endpoints'
  params: {
    name: 'private-endpoints-nsg'
    location: location
    securityRules: []
    tags: tags
  }
}

// Virtual Network with subnets (AVM)
module vnet 'br/public:avm/res/network/virtual-network:0.7.2' = {
  name: 'vnet'
  params: {
    name: vnetName
    location: location
    addressPrefixes: [
      '10.0.0.0/16'
    ]
    subnets: [
      {
        name: 'aks-system'
        addressPrefix: '10.0.0.0/22'
        networkSecurityGroupResourceId: aksSystemNsg.outputs.resourceId
      }
      {
        name: 'aks-agents'
        addressPrefix: '10.0.4.0/22'
        networkSecurityGroupResourceId: aksAgentsNsg.outputs.resourceId
      }
      {
        name: 'aks-crud'
        addressPrefix: '10.0.8.0/24'
        networkSecurityGroupResourceId: aksCrudNsg.outputs.resourceId
      }
      {
        name: 'apim'
        addressPrefix: '10.0.9.0/24'
        networkSecurityGroupResourceId: apimNsg.outputs.resourceId
      }
      {
        name: 'appgw'
        addressPrefix: '10.0.11.0/24'
        networkSecurityGroupResourceId: appGwNsg.outputs.resourceId
      }
      {
        name: 'private-endpoints'
        addressPrefix: '10.0.10.0/24'
        networkSecurityGroupResourceId: privateEndpointsNsg.outputs.resourceId
        privateEndpointNetworkPolicies: 'Disabled'
      }
    ]
    tags: tags
  }
}

var subnetResourceIds = vnet.outputs.subnetResourceIds
var aksSystemSubnetId = subnetResourceIds[0]
var aksAgentsSubnetId = subnetResourceIds[1]
var aksCrudSubnetId = subnetResourceIds[2]
var apimSubnetId = subnetResourceIds[3]
var appGwSubnetId = subnetResourceIds[4]
var peSubnetId = subnetResourceIds[5]

// Private DNS Zones (AVM) — required for private endpoints
module acrPrivateDnsZone 'br/public:avm/res/network/private-dns-zone:0.8.0' = {
  name: 'acr-private-dns'
  params: {
    name: 'privatelink.azurecr.io'
    virtualNetworkLinks: [
      {
        virtualNetworkResourceId: vnet.outputs.resourceId
      }
    ]
    tags: tags
  }
}

module cosmosPrivateDnsZone 'br/public:avm/res/network/private-dns-zone:0.8.0' = {
  name: 'cosmos-private-dns'
  params: {
    name: 'privatelink.documents.azure.com'
    virtualNetworkLinks: [
      {
        virtualNetworkResourceId: vnet.outputs.resourceId
      }
    ]
    tags: tags
  }
}

module postgresPrivateDnsZone 'br/public:avm/res/network/private-dns-zone:0.8.0' = {
  name: 'postgres-private-dns'
  params: {
    name: 'privatelink.postgres.database.azure.com'
    virtualNetworkLinks: [
      {
        virtualNetworkResourceId: vnet.outputs.resourceId
      }
    ]
    tags: tags
  }
}

module redisPrivateDnsZone 'br/public:avm/res/network/private-dns-zone:0.8.0' = {
  name: 'redis-private-dns'
  params: {
    name: 'privatelink.redis.cache.windows.net'
    virtualNetworkLinks: [
      {
        virtualNetworkResourceId: vnet.outputs.resourceId
      }
    ]
    tags: tags
  }
}

module storagePrivateDnsZone 'br/public:avm/res/network/private-dns-zone:0.8.0' = {
  name: 'storage-private-dns'
  params: {
    name: 'privatelink.blob.${az.environment().suffixes.storage}'
    virtualNetworkLinks: [
      {
        virtualNetworkResourceId: vnet.outputs.resourceId
      }
    ]
    tags: tags
  }
}

module eventHubsPrivateDnsZone 'br/public:avm/res/network/private-dns-zone:0.8.0' = {
  name: 'eventhubs-private-dns'
  params: {
    name: 'privatelink.servicebus.windows.net'
    virtualNetworkLinks: [
      {
        virtualNetworkResourceId: vnet.outputs.resourceId
      }
    ]
    tags: tags
  }
}

module keyVaultPrivateDnsZone 'br/public:avm/res/network/private-dns-zone:0.8.0' = {
  name: 'keyvault-private-dns'
  params: {
    name: 'privatelink.vaultcore.azure.net'
    virtualNetworkLinks: [
      {
        virtualNetworkResourceId: vnet.outputs.resourceId
      }
    ]
    tags: tags
  }
}

module aiServicesPrivateDnsZone 'br/public:avm/res/network/private-dns-zone:0.8.0' = {
  name: 'aiservices-private-dns'
  params: {
    name: 'privatelink.cognitiveservices.azure.com'
    virtualNetworkLinks: [
      {
        virtualNetworkResourceId: vnet.outputs.resourceId
      }
    ]
    tags: tags
  }
}

// Log Analytics Workspace (AVM)
module logAnalytics 'br/public:avm/res/operational-insights/workspace:0.15.0' = {
  name: 'log-analytics'
  params: {
    name: logAnalyticsName
    location: location
    skuName: 'PerGB2018'
    dataRetention: 90
    tags: tags
  }
}

// Application Insights (AVM)
module appInsights 'br/public:avm/res/insights/component:0.7.1' = {
  name: 'app-insights'
  params: {
    name: appInsightsName
    location: location
    applicationType: 'web'
    ingestionMode: 'LogAnalytics'
    workspaceResourceId: logAnalytics.outputs.resourceId
    tags: tags
  }
}

// Azure Container Registry (AVM)
module acr 'br/public:avm/res/container-registry/registry:0.9.3' = {
  name: 'acr'
  params: {
    #disable-next-line BCP334 // projectName @minLength(5) ensures acrName >= 8 chars
    name: acrName
    location: location
    acrSku: 'Premium'
    acrAdminUserEnabled: false
    publicNetworkAccess: 'Disabled'
    networkRuleBypassOptions: 'AzureServices'
    managedIdentities: {
      systemAssigned: true
    }
    privateEndpoints: [
      {
        subnetResourceId: peSubnetId
        privateDnsZoneGroup: {
          privateDnsZoneGroupConfigs: [
            {
              privateDnsZoneResourceId: acrPrivateDnsZone.outputs.resourceId
            }
          ]
        }
      }
    ]
    tags: tags
  }
}

// Cosmos DB Account + SQL DB (AVM)
// Cosmos hosts agent warm memory containers and Product Truth Layer containers.
var cosmosContainers = [
  {
    name: 'products'
    paths: ['/categoryId']
  }
  {
    name: 'attributes_truth'
    paths: ['/entityId']
  }
  {
    name: 'attributes_proposed'
    paths: ['/entityId']
  }
  {
    name: 'assets'
    paths: ['/productId']
  }
  {
    name: 'evidence'
    paths: ['/entityId']
  }
  {
    name: 'schemas'
    paths: ['/categoryId']
  }
  {
    name: 'mappings'
    paths: ['/protocolVersion']
  }
  {
    name: 'audit'
    paths: ['/entityId']
  }
  {
    name: 'config'
    paths: ['/tenantId']
  }
]

module cosmos 'br/public:avm/res/document-db/database-account:0.18.0' = {
  name: 'cosmos'
  params: {
    name: cosmosAccountName
    location: location
    databaseAccountOfferType: 'Standard'
    defaultConsistencyLevel: 'Session'
    failoverLocations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: environment == 'prod'
      }
    ]
    capabilitiesToAdd: environment == 'prod' ? [] : [
      'EnableServerless'
    ]
    networkRestrictions: {
      publicNetworkAccess: 'Disabled'
      ipRules: []
      virtualNetworkRules: []
    }
    enableAutomaticFailover: environment == 'prod'
    enableMultipleWriteLocations: false
    backupPolicyType: 'Continuous'
    backupPolicyContinuousTier: 'Continuous30Days'
    managedIdentities: {
      systemAssigned: true
    }
    privateEndpoints: [
      {
        subnetResourceId: peSubnetId
        service: 'Sql'
        privateDnsZoneGroup: {
          privateDnsZoneGroupConfigs: [
            {
              privateDnsZoneResourceId: cosmosPrivateDnsZone.outputs.resourceId
            }
          ]
        }
      }
    ]
    sqlDatabases: [
      {
        name: databaseName
        containers: cosmosContainers
      }
    ]
    tags: tags
  }
}

// Azure Database for PostgreSQL Flexible Server (AVM) - CRUD transactional database
module postgres 'br/public:avm/res/db-for-postgre-sql/flexible-server:0.15.0' = {
  name: 'postgres'
  params: {
    name: postgresServerName
    location: location
    availabilityZone: environment == 'prod' ? 1 : -1
    skuName: environment == 'prod' ? 'Standard_D4ds_v5' : 'Standard_B2s'
    tier: environment == 'prod' ? 'GeneralPurpose' : 'Burstable'
    version: '16'
    administratorLogin: postgresAdminUser
    administratorLoginPassword: resolvedPostgresAdminPassword
    backupRetentionDays: environment == 'prod' ? 14 : 7
    geoRedundantBackup: environment == 'prod' ? 'Enabled' : 'Disabled'
    highAvailability: environment == 'prod' ? 'ZoneRedundant' : 'Disabled'
    storageSizeGB: environment == 'prod' ? 128 : 32
    publicNetworkAccess: 'Disabled'
    databases: [
      {
        name: postgresDatabaseName
      }
    ]
    privateEndpoints: [
      {
        subnetResourceId: peSubnetId
        privateDnsZoneGroup: {
          privateDnsZoneGroupConfigs: [
            {
              privateDnsZoneResourceId: postgresPrivateDnsZone.outputs.resourceId
            }
          ]
        }
      }
    ]
    tags: tags
  }
}

// Redis Cache (AVM)
module redis 'br/public:avm/res/cache/redis:0.16.4' = {
  name: 'redis'
  params: {
    name: redisName
    location: location
    skuName: 'Premium'
    capacity: 1
    minimumTlsVersion: '1.2'
    publicNetworkAccess: 'Disabled'
    redisConfiguration: {
      'maxmemory-policy': 'allkeys-lru'
    }
    privateEndpoints: [
      {
        subnetResourceId: peSubnetId
        privateDnsZoneGroup: {
          privateDnsZoneGroupConfigs: [
            {
              privateDnsZoneResourceId: redisPrivateDnsZone.outputs.resourceId
            }
          ]
        }
      }
    ]
    tags: tags
  }
}

// Storage Account (AVM)
module storage 'br/public:avm/res/storage/storage-account:0.31.0' = {
  name: 'storage'
  params: {
    name: storageAccountName
    location: location
    kind: 'StorageV2'
    skuName: 'Standard_LRS'
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    publicNetworkAccess: 'Disabled'
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'AzureServices'
    }
    managedIdentities: {
      systemAssigned: true
    }
    privateEndpoints: [
      {
        subnetResourceId: peSubnetId
        service: 'blob'
        privateDnsZoneGroup: {
          privateDnsZoneGroupConfigs: [
            {
              privateDnsZoneResourceId: storagePrivateDnsZone.outputs.resourceId
            }
          ]
        }
      }
    ]
    blobServices: {
      deleteRetentionPolicyEnabled: true
      deleteRetentionPolicyDays: 7
    }
    tags: tags
  }
}

// Event Hubs Namespace + Hubs (AVM)
module eventHubs 'br/public:avm/res/event-hub/namespace:0.14.0' = {
  name: 'event-hubs'
  params: {
    name: eventHubsNamespaceName
    location: location
    skuName: 'Standard'
    skuCapacity: 1
    minimumTlsVersion: '1.2'
    publicNetworkAccess: 'Disabled'
    managedIdentities: {
      systemAssigned: true
    }
    privateEndpoints: [
      {
        subnetResourceId: peSubnetId
        privateDnsZoneGroup: {
          privateDnsZoneGroupConfigs: [
            {
              privateDnsZoneResourceId: eventHubsPrivateDnsZone.outputs.resourceId
            }
          ]
        }
      }
    ]
    eventhubs: [
      {
        name: 'order-events'
        messageRetentionInDays: 7
        partitionCount: 4
      }
      {
        name: 'inventory-events'
        messageRetentionInDays: 7
        partitionCount: 4
      }
      {
        name: 'shipment-events'
        messageRetentionInDays: 7
        partitionCount: 4
      }
      {
        name: 'payment-events'
        messageRetentionInDays: 7
        partitionCount: 4
      }
      {
        name: 'user-events'
        messageRetentionInDays: 7
        partitionCount: 2
      }
    ]
    tags: tags
  }
}

// Key Vault (AVM)
module keyVault 'br/public:avm/res/key-vault/vault:0.13.3' = {
  name: 'key-vault'
  params: {
    name: keyVaultName
    location: location
    sku: 'premium'
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enablePurgeProtection: true
    publicNetworkAccess: 'Disabled'
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'AzureServices'
    }
    privateEndpoints: [
      {
        subnetResourceId: peSubnetId
        privateDnsZoneGroup: {
          privateDnsZoneGroupConfigs: [
            {
              privateDnsZoneResourceId: keyVaultPrivateDnsZone.outputs.resourceId
            }
          ]
        }
      }
    ]
    tags: tags
  }
}

// Azure AI Foundry Project (AVM)
module aiFoundry 'br/public:avm/ptn/ai-ml/ai-foundry:0.6.0' = {
  name: 'ai-foundry'
  params: {
    #disable-next-line BCP334 // projectName @minLength(5) ensures aiFoundryBaseName >= 5 chars
    baseName: aiFoundryBaseName
    location: aiFoundryLocation
    includeAssociatedResources: true
    aiFoundryConfiguration: {
      accountName: aiServicesName
      location: aiFoundryLocation
      sku: 'S0'
      project: {
        name: aiProjectInstanceName
        displayName: aiProjectFriendlyName
        desc: aiProjectDescription
      }
    }
    keyVaultConfiguration: {
      existingResourceId: keyVault.outputs.resourceId
    }
    storageAccountConfiguration: {
      existingResourceId: storage.outputs.resourceId
    }
    cosmosDbConfiguration: {
      existingResourceId: cosmos.outputs.resourceId
    }
  }
}

// Application Gateway for AGIC (Ingress Controller)
var appGwSkuName = environment == 'prod' ? 'WAF_v2' : 'Standard_v2'
var appGwCapacity = environment == 'prod' ? 2 : 1
var appGwPublicIpName = '${appGwName}-pip'

resource appGwPublicIp 'Microsoft.Network/publicIPAddresses@2023-09-01' = {
  name: appGwPublicIpName
  location: location
  sku: {
    name: 'Standard'
    tier: 'Regional'
  }
  properties: {
    publicIPAllocationMethod: 'Static'
    publicIPAddressVersion: 'IPv4'
  }
  tags: tags
}

resource appGateway 'Microsoft.Network/applicationGateways@2023-09-01' = {
  name: appGwName
  location: location
  properties: {
    sku: {
      name: appGwSkuName
      tier: appGwSkuName
      capacity: appGwCapacity
    }
    gatewayIPConfigurations: [
      {
        name: 'appGatewayIpConfig'
        properties: {
          subnet: {
            id: appGwSubnetId
          }
        }
      }
    ]
    frontendIPConfigurations: [
      {
        name: 'appGwPublicFrontendIp'
        properties: {
          publicIPAddress: {
            id: appGwPublicIp.id
          }
        }
      }
    ]
    frontendPorts: [
      {
        name: 'port_80'
        properties: {
          port: 80
        }
      }
      {
        name: 'port_443'
        properties: {
          port: 443
        }
      }
    ]
    backendAddressPools: [
      {
        name: 'defaultAddressPool'
        properties: {
          backendAddresses: []
        }
      }
    ]
    backendHttpSettingsCollection: [
      {
        name: 'defaultHttpSettings'
        properties: {
          port: 80
          protocol: 'Http'
          cookieBasedAffinity: 'Disabled'
          requestTimeout: 30
          pickHostNameFromBackendAddress: true
          probe: {
            id: resourceId('Microsoft.Network/applicationGateways/probes', appGwName, 'defaultProbe')
          }
        }
      }
    ]
    probes: [
      {
        name: 'defaultProbe'
        properties: {
          protocol: 'Http'
          path: '/health'
          interval: 30
          timeout: 30
          unhealthyThreshold: 3
          pickHostNameFromBackendHttpSettings: true
          minServers: 0
        }
      }
    ]
    httpListeners: [
      {
        name: 'httpListener'
        properties: {
          frontendIPConfiguration: {
            id: resourceId('Microsoft.Network/applicationGateways/frontendIPConfigurations', appGwName, 'appGwPublicFrontendIp')
          }
          frontendPort: {
            id: resourceId('Microsoft.Network/applicationGateways/frontendPorts', appGwName, 'port_80')
          }
          protocol: 'Http'
        }
      }
    ]
    requestRoutingRules: [
      {
        name: 'defaultRule'
        properties: {
          ruleType: 'Basic'
          priority: 100
          httpListener: {
            id: resourceId('Microsoft.Network/applicationGateways/httpListeners', appGwName, 'httpListener')
          }
          backendAddressPool: {
            id: resourceId('Microsoft.Network/applicationGateways/backendAddressPools', appGwName, 'defaultAddressPool')
          }
          backendHttpSettings: {
            id: resourceId('Microsoft.Network/applicationGateways/backendHttpSettingsCollection', appGwName, 'defaultHttpSettings')
          }
        }
      }
    ]
  }
  tags: tags
}

// Azure Kubernetes Service (AVM)
module aks 'br/public:avm/res/container-service/managed-cluster:0.12.0' = {
  name: 'aks'
  params: {
    name: aksClusterName
    location: location
    enableRBAC: true
    aadProfile: {
      managed: true
      enableAzureRBAC: true
    }
    managedIdentities: {
      systemAssigned: true
    }
    networkPlugin: 'azure'
    networkPolicy: 'azure'
    serviceCidr: '10.1.0.0/16'
    dnsServiceIP: '10.1.0.10'
    kubernetesVersion: empty(aksKubernetesVersion) ? null : aksKubernetesVersion
    publicNetworkAccess: 'Enabled'
    disableLocalAccounts: true
    monitoringWorkspaceResourceId: logAnalytics.outputs.resourceId
    omsAgentEnabled: true
    enableKeyvaultSecretsProvider: true
    enableOidcIssuerProfile: true
    ingressApplicationGatewayEnabled: true
    appGatewayResourceId: appGateway.id
    primaryAgentPoolProfiles: [
      {
        name: 'system'
        count: environment == 'prod' ? 3 : 1
        vmSize: 'Standard_D8ds_v5'
        osType: 'Linux'
        mode: 'System'
        vnetSubnetResourceId: aksSystemSubnetId
        enableAutoScaling: true
        minCount: 1
        maxCount: environment == 'prod' ? 5 : 3
      }
    ]
    agentPools: [
      {
        name: 'agents'
        count: environment == 'prod' ? 5 : 2
        vmSize: 'Standard_D8ds_v5'
        osType: 'Linux'
        mode: 'User'
        vnetSubnetResourceId: aksAgentsSubnetId
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
        vmSize: 'Standard_D8ds_v5'
        osType: 'Linux'
        mode: 'User'
        vnetSubnetResourceId: aksCrudSubnetId
        enableAutoScaling: true
        minCount: 1
        maxCount: environment == 'prod' ? 10 : 5
        nodeTaints: [
          'workload=crud:NoSchedule'
        ]
      }
    ]
    tags: tags
  }
}

// API Management (AVM) — Consumption tier for dev, StandardV2 for prod
var apimSkuName = environment == 'prod' ? 'StandardV2' : 'Developer'
var apimSkuCapacity = environment == 'prod' ? 1 : 1
var apimVirtualNetworkType = environment == 'prod' ? 'None' : 'External'
var apimSubnetResourceId = environment == 'prod' ? '' : apimSubnetId

module apim 'br/public:avm/res/api-management/service:0.14.0' = {
  name: 'apim'
  params: {
    name: apimName
    location: location
    sku: apimSkuName
    skuCapacity: apimSkuCapacity
    publisherEmail: 'admin@holidaypeakhub.com'
    publisherName: 'Holiday Peak Hub'
    virtualNetworkType: apimVirtualNetworkType
    subnetResourceId: apimSubnetResourceId
    managedIdentities: {
      systemAssigned: true
    }
    tags: tags
  }
}

resource acrResource 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  #disable-next-line BCP334 // projectName @minLength(5) ensures acrName >= 8 chars
  name: acrName
}

resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2023-11-15' existing = {
  name: cosmosAccountName
}

resource eventHubsNamespaceResource 'Microsoft.EventHub/namespaces@2023-01-01-preview' existing = {
  name: eventHubsNamespaceName
}

resource keyVaultResource 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

resource postgresPasswordSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVaultResource
  name: postgresAdminPasswordSecretName
  properties: {
    value: resolvedPostgresAdminPassword
  }
  dependsOn: [
    keyVault
    postgres
  ]
}

resource storageResource 'Microsoft.Storage/storageAccounts@2023-01-01' existing = {
  name: storageAccountName
}

// RBAC Assignments
// AKS -> ACR (pull images)
resource aksAcrPullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, aksClusterName, acrName, 'AcrPull')
  scope: acrResource
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d') // AcrPull
    principalId: aks.outputs.?kubeletIdentityObjectId ?? ''
    principalType: 'ServicePrincipal'
  }
  dependsOn: [
    acr
  ]
}

// AKS -> Cosmos DB (Data Contributor)
resource aksCosmosRole 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2023-11-15' = {
  parent: cosmosAccount
  name: guid(resourceGroup().id, aksClusterName, cosmosAccountName, 'CosmosDataContributor')
  properties: {
    roleDefinitionId: '${cosmosAccount.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002' // Built-in Data Contributor
    principalId: aks.outputs.?systemAssignedMIPrincipalId ?? ''
    scope: cosmosAccount.id
  }
  dependsOn: [
    cosmos
  ]
}

// AKS -> Event Hubs (Data Sender/Receiver)
resource aksEventHubSenderRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, aksClusterName, eventHubsNamespaceName, 'EventHubSender')
  scope: eventHubsNamespaceResource
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '2b629674-e913-4c01-ae53-ef4638d8f975') // Azure Event Hubs Data Sender
    principalId: aks.outputs.?systemAssignedMIPrincipalId ?? ''
    principalType: 'ServicePrincipal'
  }
  dependsOn: [
    eventHubs
  ]
}

resource aksEventHubReceiverRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, aksClusterName, eventHubsNamespaceName, 'EventHubReceiver')
  scope: eventHubsNamespaceResource
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a638d3c7-ab3a-418d-83e6-5f17a39d4fde') // Azure Event Hubs Data Receiver
    principalId: aks.outputs.?systemAssignedMIPrincipalId ?? ''
    principalType: 'ServicePrincipal'
  }
  dependsOn: [
    eventHubs
  ]
}

// AKS -> Key Vault (Secrets User)
resource aksKeyVaultRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, aksClusterName, keyVaultName, 'KeyVaultSecretsUser')
  scope: keyVaultResource
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6') // Key Vault Secrets User
    principalId: aks.outputs.?keyvaultIdentityObjectId ?? ''
    principalType: 'ServicePrincipal'
  }
  dependsOn: [
    keyVault
  ]
}

// AKS -> Storage (Blob Data Contributor)
resource aksStorageRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, aksClusterName, storageAccountName, 'BlobDataContributor')
  scope: storageResource
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe') // Storage Blob Data Contributor
    principalId: aks.outputs.?systemAssignedMIPrincipalId ?? ''
    principalType: 'ServicePrincipal'
  }
  dependsOn: [
    storage
  ]
}

// Outputs
output aksClusterName string = aks.outputs.name
output acrLoginServer string = acr.outputs.loginServer
output cosmosAccountName string = cosmos.outputs.name
output cosmosEndpoint string = cosmos.outputs.endpoint
output databaseName string = databaseName
output postgresServerName string = postgres.outputs.name
output postgresFqdn string = postgres.outputs.?fqdn ?? ''
output postgresDatabaseName string = postgresDatabaseName
output postgresAdminUser string = postgresAdminUser
output eventHubsNamespaceName string = eventHubs.outputs.name
output redisName string = redis.outputs.name
output storageAccountName string = storage.outputs.name
output keyVaultName string = keyVault.outputs.name
output keyVaultUri string = keyVault.outputs.uri
output apimName string = apim.outputs.name
output apimGatewayUrl string = 'https://${apimName}.azure-api.net'
output aiServicesName string = aiFoundry.outputs.aiServicesName
output aiProjectName string = aiFoundry.outputs.aiProjectName
output appInsightsConnectionString string = appInsights.outputs.connectionString
output appInsightsInstrumentationKey string = appInsights.outputs.instrumentationKey
output vnetId string = vnet.outputs.resourceId
output vnetName string = vnet.outputs.name
output appGwName string = appGateway.name
output appGwPublicIp string = appGwPublicIp.properties.ipAddress
output appGwResourceId string = appGateway.id
