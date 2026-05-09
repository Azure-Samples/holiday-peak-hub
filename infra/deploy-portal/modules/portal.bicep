// deploy-portal/modules/portal.bicep — service-side infrastructure module.
//
// Issue #1027 / Epic #1039. v1 skeleton; do NOT deploy in production until
// pen-test passes.

@description('Short environment name.')
param environmentName string

@description('Primary location.')
param location string

@description('Tags.')
param tags object

@description('Deploy-portal API container image.')
param apiImage string

@description('Active deployments per Entra OID per 24 h.')
param activeDeploymentsPer24h int

@description('Total deployments per Entra OID per 30 days.')
param totalDeploymentsPer30d int

@description('Pre-flight rate per OID per minute.')
param preflightRatePerMinute int

var prefix = 'hph-deploy-${environmentName}'

resource law 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'law-${prefix}'
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
    workspaceCapping: {
      dailyQuotaGb: 1
    }
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'ai-${prefix}'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: law.id
  }
}

resource keyVault 'Microsoft.KeyVault/vaults@2024-04-01-preview' = {
  name: 'kv-${replace(prefix, '-', '')}'
  location: location
  tags: tags
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    publicNetworkAccess: 'Disabled'
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'AzureServices'
    }
  }
}

resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-08-15' = {
  name: 'cosmos-${prefix}'
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    enableFreeTier: false
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    consistencyPolicy: { defaultConsistencyLevel: 'Session' }
    capabilities: [
      { name: 'EnableServerless' }
    ]
    publicNetworkAccess: 'Enabled' // narrowed by network ACLs in v2
  }
}

resource cosmosDb 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-08-15' = {
  parent: cosmos
  name: 'deploy-portal'
  properties: {
    resource: { id: 'deploy-portal' }
  }
}

resource deploymentsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-08-15' = {
  parent: cosmosDb
  name: 'deployments'
  properties: {
    resource: {
      id: 'deployments'
      partitionKey: {
        paths: [ '/userOid' ]
        kind: 'Hash'
      }
      defaultTtl: 60 * 60 * 24 * 30 // 30-day retention per #1036.
    }
  }
}

resource cae 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: 'cae-${prefix}'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: law.properties.customerId
        sharedKey: listKeys(law.id, '2023-09-01').primarySharedKey
      }
    }
  }
}

resource api 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'ca-${prefix}-api'
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }
  properties: {
    managedEnvironmentId: cae.id
    configuration: {
      ingress: {
        external: false // exposed only via APIM
        targetPort: 8080
        transport: 'auto'
      }
      secrets: []
    }
    template: {
      containers: [
        {
          name: 'api'
          image: apiImage
          resources: {
            cpu: json('0.5')
            memory: '1.0Gi'
          }
          env: [
            { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsights.properties.ConnectionString }
            { name: 'COSMOS_DATABASE', value: cosmosDb.name }
            { name: 'COSMOS_ENDPOINT', value: cosmos.properties.documentEndpoint }
            { name: 'KEYVAULT_URI', value: keyVault.properties.vaultUri }
            { name: 'RATE_ACTIVE_24H', value: string(activeDeploymentsPer24h) }
            { name: 'RATE_TOTAL_30D', value: string(totalDeploymentsPer30d) }
            { name: 'RATE_PREFLIGHT_PER_MIN', value: string(preflightRatePerMinute) }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 5
      }
    }
  }
}

resource apim 'Microsoft.ApiManagement/service@2023-09-01-preview' = {
  name: 'apim-${prefix}'
  location: location
  tags: tags
  sku: { name: 'Consumption', capacity: 0 }
  properties: {
    publisherEmail: 'noreply@example.invalid'
    publisherName: 'Holiday Peak Hub deploy-portal'
    customProperties: {}
  }
}

output apiHost string = api.properties.configuration.ingress.fqdn
output apimGatewayUrl string = apim.properties.gatewayUrl
output keyVaultUri string = keyVault.properties.vaultUri
output cosmosDatabaseName string = cosmosDb.name
