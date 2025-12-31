targetScope = 'subscription'

param subscriptionId string = subscription().subscriptionId
param location string
param appName string
param resourceGroupName string = '${appName}-rg'
param appImage string = 'ghcr.io/OWNER/logistics-carrier-selection:latest'

resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: resourceGroupName
  location: location
}

module app './logistics-carrier-selection.bicep' = {
  name: 'logistics-carrier-selection-resources'
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
