targetScope = 'subscription'

param subscriptionId string = subscription().subscriptionId
param location string = 'eastus2' // Static Web Apps available regions
param environment string = 'dev' // dev, staging, prod
param appName string = 'holidaypeakhub-ui'
param resourceGroupName string = 'holidaypeakhub-${environment}-rg'
param repositoryUrl string = 'https://github.com/Azure-Samples/holiday-peak-hub'
param branch string = 'main'

// Deploy Static Web App to existing resource group
module swa './static-web-app.bicep' = {
  name: 'static-web-app-deployment'
  scope: resourceGroup(subscriptionId, resourceGroupName)
  params: {
    location: location
    appName: appName
    environment: environment
    repositoryUrl: repositoryUrl
    branch: branch
  }
}

// Outputs
output staticWebAppName string = swa.outputs.staticWebAppName
output staticWebAppDefaultHostname string = swa.outputs.staticWebAppDefaultHostname
output deploymentToken string = swa.outputs.deploymentToken
