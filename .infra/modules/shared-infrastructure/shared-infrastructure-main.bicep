targetScope = 'subscription'

param subscriptionId string = subscription().subscriptionId
param location string = 'eastus'
param environment string = 'dev' // dev, staging, prod
param projectName string = 'holidaypeakhub'
param resourceGroupName string = '${projectName}-${environment}-rg'

// Create Resource Group
resource rg 'Microsoft.Resources/resourceGroups@2023-07-01' = {
  name: resourceGroupName
  location: location
  tags: {
    Environment: environment
    Project: projectName
    ManagedBy: 'Bicep'
  }
}

// Deploy Shared Infrastructure
module sharedInfra './shared-infrastructure.bicep' = {
  name: 'shared-infrastructure-deployment'
  scope: resourceGroup(subscriptionId, resourceGroupName)
  params: {
    location: location
    environment: environment
    projectName: projectName
  }
  dependsOn: [
    rg
  ]
}

// Outputs
output resourceGroupName string = rg.name
output aksClusterName string = sharedInfra.outputs.aksClusterName
output acrLoginServer string = sharedInfra.outputs.acrLoginServer
output cosmosAccountName string = sharedInfra.outputs.cosmosAccountName
output cosmosEndpoint string = sharedInfra.outputs.cosmosEndpoint
output databaseName string = sharedInfra.outputs.databaseName
output eventHubsNamespaceName string = sharedInfra.outputs.eventHubsNamespaceName
output redisName string = sharedInfra.outputs.redisName
output storageAccountName string = sharedInfra.outputs.storageAccountName
output keyVaultName string = sharedInfra.outputs.keyVaultName
output keyVaultUri string = sharedInfra.outputs.keyVaultUri
output apimName string = sharedInfra.outputs.apimName
output apimGatewayUrl string = sharedInfra.outputs.apimGatewayUrl
output appInsightsConnectionString string = sharedInfra.outputs.appInsightsConnectionString
output vnetName string = sharedInfra.outputs.vnetName
