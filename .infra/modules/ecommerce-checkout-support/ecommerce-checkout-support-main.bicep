targetScope = 'subscription'

param subscriptionId string = subscription().subscriptionId
param location string
param appName string
param resourceGroupName string = '${appName}-rg'
param appImage string = 'ghcr.io/OWNER/ecommerce-checkout-support:latest'

resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: resourceGroupName
  location: location
}

module app './ecommerce-checkout-support.bicep' = {
  name: 'ecommerce-checkout-support-resources'
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
