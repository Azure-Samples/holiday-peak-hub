targetScope = 'resourceGroup'

param appName string
param location string = resourceGroup().location
param appImage string = 'ghcr.io/OWNER/crm-segmentation-personalization:latest'

var safeApp = toLower(replace(replace(appName, '_', '-'), ' ', '-'))
var cosmosAccountName = '${safeApp}-cosmos'
var databaseName = '${safeApp}-db'
var containerName = 'warm-${safeApp}-chat-memory'
var redisName = 'hot-${safeApp}-chat-memory'
var storageAccountName = take(toLower(replace('cold${safeApp}chatmem', '-', '')), 24)
var blobContainerName = 'cold-${safeApp}-chat-memory'
var searchServiceName = 'search-${safeApp}'
var searchIndexName = 'agent-${safeApp}-retrieval'
var openaiName = 'aoai-${safeApp}'
var aksName = 'aks-${safeApp}'

resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2025-10-15' = {
  name: cosmosAccountName
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    locations: [
      {
        locationName: location
        failoverPriority: 0
      }
    ]
  }
}

resource cosmosDb 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2025-10-15' = {
  parent: cosmos
  name: databaseName
  properties: {
    resource: {
      id: databaseName
    }
  }
}

resource cosmosContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2025-10-15' = {
  parent: cosmosDb
  name: containerName
  properties: {
    resource: {
      id: containerName
      partitionKey: {
        paths: ['/pk']
        kind: 'Hash'
      }
    }
  }
}

resource redis 'Microsoft.Cache/Redis@2024-11-01' = {
  name: redisName
  location: location
  properties: {
    sku: {
      name: 'Standard'
      family: 'C'
      capacity: 0
    }
    enableNonSslPort: false
  }
}

resource storage 'Microsoft.Storage/storageAccounts@2025-08-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2025-08-01' = {
  parent: storage
  name: 'default'
  properties: {}
}

resource blobContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-08-01' = {
  parent: blobService
  name: blobContainerName
  properties: {
    publicAccess: 'None'
  }
}

resource searchService 'Microsoft.Search/searchServices@2025-05-01' = {
  name: searchServiceName
  location: location
  sku: {
    name: 'standard'
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
  }
}

resource searchIndex 'Microsoft.Search/searchServices/indexes@2025-05-01' = {
  parent: searchService
  name: searchIndexName
  properties: {
    fields: [
      {
        name: 'id'
        type: 'Edm.String'
        key: true
        filterable: true
        searchable: false
      }
      {
        name: 'content'
        type: 'Edm.String'
        searchable: true
      }
      {
        name: 'embedding'
        type: 'Collection(Edm.Single)'
        searchable: true
        vectorSearchDimensions: 1536
        vectorSearchConfiguration: 'default'
      }
    ]
    vectorSearch: {
      algorithms: [
        {
          name: 'default'
          kind: 'hnsw'
          hnswParameters: {
            metric: 'cosine'
            m: 4
            efConstruction: 400
          }
        }
      ]
    }
  }
}

resource openai 'Microsoft.CognitiveServices/accounts@2025-12-01' = {
  name: openaiName
  location: location
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: openaiName
  }
}

resource gpt41 'Microsoft.CognitiveServices/accounts/deployments@2025-12-01' = {
  parent: openai
  name: 'gpt-4-1'
  sku: {
    name: 'Standard'
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4.1'
      version: '2024-10-01'
    }
    raiPolicyName: 'Microsoft.Default'
  }
}

resource gpt41Mini 'Microsoft.CognitiveServices/accounts/deployments@2025-12-01' = {
  parent: openai
  name: 'gpt-4-1-mini'
  sku: {
    name: 'Standard'
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4.1-mini'
      version: '2024-10-01'
    }
    raiPolicyName: 'Microsoft.Default'
  }
}

resource gpt41Nano 'Microsoft.CognitiveServices/accounts/deployments@2025-12-01' = {
  parent: openai
  name: 'gpt-4-1-nano'
  sku: {
    name: 'Standard'
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4.1-nano'
      version: '2024-10-01'
    }
    raiPolicyName: 'Microsoft.Default'
  }
}

resource aks 'Microsoft.ContainerService/managedClusters@2026-01-01' = {
  name: aksName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    dnsPrefix: '${safeApp}-dns'
    agentPoolProfiles: [
      {
        name: 'system'
        count: 1
        vmSize: 'Standard_B4ms'
        osType: 'Linux'
        mode: 'System'
      }
    ]
    networkProfile: {
      networkPlugin: 'azure'
    }
  }
}

resource deployApp 'Microsoft.ContainerService/managedClusters/runCommands@2026-01-01' = {
  parent: aks
  name: 'deploy-${safeApp}'
  properties: {
    command: 'kubectl create deployment ${safeApp} --image=${appImage} --replicas=1 --dry-run=client -o yaml | kubectl apply -f -'
  }
}
