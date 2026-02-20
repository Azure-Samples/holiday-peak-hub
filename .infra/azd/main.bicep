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
