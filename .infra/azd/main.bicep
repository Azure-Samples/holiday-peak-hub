targetScope = 'subscription'

@description('Deploy shared infrastructure module.')
param deployShared bool = true

@description('Deploy static web app module.')
param deployStatic bool = false

param location string = 'eastus2'
param environment string = 'dev'
param projectName string = 'holidaypeakhub'
@description('Optional override for Key Vault name (3-24 chars, lowercase letters, numbers, and hyphens).')
param keyVaultNameOverride string = ''
@secure()
@description('Optional PostgreSQL admin password for CRUD database. Leave empty to auto-generate.')
param postgresAdminPassword string = ''
param resourceGroupName string = '${projectName}-${environment}-rg'

param appName string = 'holidaypeakhub-ui'
param repositoryUrl string = 'https://github.com/Azure-Samples/holiday-peak-hub'
param branch string = 'main'

module sharedInfra '../modules/shared-infrastructure/shared-infrastructure-main.bicep' = if (deployShared) {
  name: 'shared-infrastructure-azd'
  params: {
    location: location
    environment: environment
    projectName: projectName
    keyVaultNameOverride: keyVaultNameOverride
    postgresAdminPassword: postgresAdminPassword
    resourceGroupName: resourceGroupName
  }
}

module staticWebApp '../modules/static-web-app/static-web-app-main.bicep' = if (deployStatic) {
  name: 'static-web-app-azd'
  params: {
    location: location
    environment: environment
    appName: appName
    repositoryUrl: repositoryUrl
    branch: branch
    resourceGroupName: resourceGroupName
  }
}

output resourceGroupName string = resourceGroupName
output staticWebAppDefaultHostname string = deployStatic ? staticWebApp!.outputs.staticWebAppDefaultHostname : ''

// Propagate shared infrastructure outputs for azd env and Helm rendering
output AI_SERVICES_NAME string = deployShared ? sharedInfra.outputs.aiServicesName : ''
output PROJECT_NAME string = deployShared ? sharedInfra.outputs.aiProjectName : ''
output PROJECT_ENDPOINT string = deployShared ? 'https://${sharedInfra.outputs.aiServicesName}.cognitiveservices.azure.com' : ''
output COSMOS_ACCOUNT_URI string = deployShared ? sharedInfra.outputs.cosmosEndpoint : ''
output COSMOS_DATABASE string = deployShared ? sharedInfra.outputs.databaseName : ''
output KEY_VAULT_URI string = deployShared ? sharedInfra.outputs.keyVaultUri : ''
output REDIS_HOST string = deployShared ? sharedInfra.outputs.redisName : ''
output EVENT_HUB_NAMESPACE string = deployShared ? sharedInfra.outputs.eventHubsNamespaceName : ''
output APPLICATIONINSIGHTS_CONNECTION_STRING string = deployShared ? sharedInfra.outputs.appInsightsConnectionString : ''
output POSTGRES_HOST string = deployShared ? sharedInfra.outputs.postgresFqdn : ''
output POSTGRES_USER string = deployShared ? sharedInfra.outputs.postgresAdminUser : ''
output POSTGRES_DATABASE string = deployShared ? sharedInfra.outputs.postgresDatabaseName : ''
