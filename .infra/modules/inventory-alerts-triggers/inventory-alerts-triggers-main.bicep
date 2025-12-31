targetScope = 'subscription'

param subscriptionId string = subscription().subscriptionId
param location string
param appName string
param resourceGroupName string = '${appName}-rg'
param appImage string = 'ghcr.io/OWNER/inventory-alerts-triggers:latest'

resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: resourceGroupName
  location: location
}

module app './inventory-alerts-triggers.bicep' = {
  name: 'inventory-alerts-triggers-resources'
  scope: resourceGroup(subscriptionId, resourceGroupName)
  dependsOn: [
    rg
  ]
  params: {
    appName: appName
    location: location
    appImage: appImage
  }
}
