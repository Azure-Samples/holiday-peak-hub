targetScope = 'subscription'

param subscriptionId string = subscription().subscriptionId
param location string = 'eastus2' // Static Web Apps available regions
param environment string = 'dev' // dev, staging, prod
param projectName string = 'holidaypeakhub405'
param appName string = ''
param resourceGroupName string = '${projectName}-${environment}-rg'
param repositoryUrl string = 'https://github.com/Azure-Samples/holiday-peak-hub'
param branch string = 'main'

var staticWebAppBaseName = empty(appName) ? '${projectName}-ui' : appName

// Deploy Static Web App to existing resource group
module swa './static-web-app.bicep' = {
  name: 'static-web-app-deployment'
  scope: resourceGroup(subscriptionId, resourceGroupName)
  params: {
    location: location
    projectName: projectName
    appName: staticWebAppBaseName
    environment: environment
    repositoryUrl: repositoryUrl
    branch: branch
  }
}

// Outputs
output staticWebAppName string = swa.outputs.staticWebAppName
output staticWebAppDefaultHostname string = swa.outputs.staticWebAppDefaultHostname
