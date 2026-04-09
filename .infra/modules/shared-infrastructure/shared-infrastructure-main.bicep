targetScope = 'subscription'

param subscriptionId string = subscription().subscriptionId
param location string = 'eastus2'
param environment string = 'dev' // dev, staging, prod
param projectName string = 'holidaypeakhub405'
@description('Optional override for Key Vault name (3-24 chars, lowercase letters, numbers, and hyphens). Leave empty to use default naming.')
param keyVaultNameOverride string = ''
@description('Enable the legacy AKS Web App Routing addon. Keep disabled for the AGC target edge posture.')
param aksWebApplicationRoutingEnabled bool = false
@description('Enable Application Gateway for Containers shared-infrastructure prerequisites for the dev environment.')
param agcSupportEnabled bool = environment == 'dev'
@description('CIDR prefix for the delegated AGC subnet. Must provide at least 256 available IPs.')
param agcSubnetAddressPrefix string = '10.0.12.0/24'
@secure()
@description('Optional PostgreSQL administrator password for CRUD database.')
param postgresAdminPassword string = ''
@description('Optional email receiver for infrastructure alerts action group.')
param alertNotificationEmail string = ''
@secure()
@description('Optional Microsoft Teams incoming webhook URL for infrastructure alerts action group.')
param alertTeamsWebhookUrl string = ''
@description('Initial node count for AKS system and user pools. Set by the pre-provision hook based on VM SKU zone availability.')
param aksNodeCount int = 1
@description('Availability zones for AKS node pools. Parsed from JSON string at the azd layer.')
param aksAvailabilityZones array = [1, 2, 3]
param resourceGroupName string = '${projectName}-${environment}-rg'

// Create Resource Group
resource rg 'Microsoft.Resources/resourceGroups@2025-04-01' = {
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
    keyVaultNameOverride: keyVaultNameOverride
    aksWebApplicationRoutingEnabled: aksWebApplicationRoutingEnabled
    agcSupportEnabled: agcSupportEnabled
    agcSubnetAddressPrefix: agcSubnetAddressPrefix
    postgresAdminPassword: postgresAdminPassword
    alertNotificationEmail: alertNotificationEmail
    alertTeamsWebhookUrl: alertTeamsWebhookUrl
    aksNodeCount: aksNodeCount
    aksAvailabilityZones: aksAvailabilityZones
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
output postgresServerName string = sharedInfra.outputs.postgresServerName
output postgresFqdn string = sharedInfra.outputs.postgresFqdn
output postgresDatabaseName string = sharedInfra.outputs.postgresDatabaseName
output postgresAdminUser string = sharedInfra.outputs.postgresAdminUser
output eventHubsNamespaceName string = sharedInfra.outputs.eventHubsNamespaceName
output platformJobsNamespaceName string = sharedInfra.outputs.platformJobsNamespaceName
output redisName string = sharedInfra.outputs.redisName
#disable-next-line outputs-should-not-contain-secrets
output redisPasswordSecretName string = sharedInfra.outputs.redisPasswordSecretName
output storageAccountName string = sharedInfra.outputs.storageAccountName
output keyVaultName string = sharedInfra.outputs.keyVaultName
output keyVaultUri string = sharedInfra.outputs.keyVaultUri
output apimName string = sharedInfra.outputs.apimName
output apimGatewayUrl string = sharedInfra.outputs.apimGatewayUrl
output appInsightsConnectionString string = sharedInfra.outputs.appInsightsConnectionString
output vnetName string = sharedInfra.outputs.vnetName
output aiProjectName string = sharedInfra.outputs.aiProjectName
output aiServicesName string = sharedInfra.outputs.aiServicesName
output aiSearchName string = sharedInfra.outputs.aiSearchName
output aiSearchEndpoint string = sharedInfra.outputs.aiSearchEndpoint
output aiSearchIndexName string = sharedInfra.outputs.aiSearchIndexName
output aiSearchVectorIndexName string = sharedInfra.outputs.aiSearchVectorIndexName
output aiSearchIndexerName string = sharedInfra.outputs.aiSearchIndexerName
output embeddingDeploymentName string = sharedInfra.outputs.embeddingDeploymentName
output aiSearchAuthMode string = sharedInfra.outputs.aiSearchAuthMode
output agcSupportEnabled bool = sharedInfra.outputs.agcSupportEnabled
output agcSubnetId string = sharedInfra.outputs.agcSubnetId
output agcSubnetName string = sharedInfra.outputs.agcSubnetName
output agcSubnetAddressPrefix string = sharedInfra.outputs.agcSubnetAddressPrefix
output agcControllerDeploymentMode string = sharedInfra.outputs.agcControllerDeploymentMode
output agcGatewayClass string = sharedInfra.outputs.agcGatewayClass
output agcControllerIdentityName string = sharedInfra.outputs.agcControllerIdentityName
output agcControllerIdentityClientId string = sharedInfra.outputs.agcControllerIdentityClientId
output agcControllerIdentityPrincipalId string = sharedInfra.outputs.agcControllerIdentityPrincipalId
output agcFrontendHostname string = sharedInfra.outputs.agcFrontendHostname
output agcFrontendReference string = sharedInfra.outputs.agcFrontendReference
output aksOidcIssuerUrl string = sharedInfra.outputs.aksOidcIssuerUrl
output aksNodeResourceGroup string = sharedInfra.outputs.aksNodeResourceGroup
output monitoringActionGroupId string = sharedInfra.outputs.monitoringActionGroupId
output monitoringActionGroupName string = sharedInfra.outputs.monitoringActionGroupName
output agentsWorkloadIdentityClientId string = sharedInfra.outputs.agentsWorkloadIdentityClientId
output crudWorkloadIdentityClientId string = sharedInfra.outputs.crudWorkloadIdentityClientId
