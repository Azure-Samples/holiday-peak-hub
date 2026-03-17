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
@description('Enable the legacy AKS Web App Routing addon. Keep disabled for the AGC target edge posture.')
param aksWebApplicationRoutingEnabled bool = false
@description('Enable Application Gateway for Containers shared-infrastructure prerequisites for the dev environment.')
param agcSupportEnabled bool = environment == 'dev'
@description('CIDR prefix for the delegated AGC subnet. Must provide at least 256 available IPs.')
param agcSubnetAddressPrefix string = '10.0.11.0/24'
@secure()
@description('Optional PostgreSQL admin password for CRUD database. Leave empty to auto-generate.')
param postgresAdminPassword string = ''
param resourceGroupName string = '${projectName}-${environment}-rg'

param appName string = 'holidaypeakhub-ui'
param repositoryUrl string = 'https://github.com/Azure-Samples/holiday-peak-hub'
param branch string = 'main'

// Keep deployment-facing auth/user outputs explicit and deterministic.
var postgresAuthMode = 'password'
var postgresWorkloadUser = 'crud_workload'

module sharedInfra '../modules/shared-infrastructure/shared-infrastructure-main.bicep' = if (deployShared) {
  name: 'shared-infrastructure-azd'
  params: {
    location: location
    environment: environment
    projectName: projectName
    keyVaultNameOverride: keyVaultNameOverride
    aksWebApplicationRoutingEnabled: aksWebApplicationRoutingEnabled
    agcSupportEnabled: agcSupportEnabled
    agcSubnetAddressPrefix: agcSubnetAddressPrefix
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
output APIM_NAME string = deployShared ? sharedInfra!.outputs.apimName : ''
output AKS_CLUSTER_NAME string = deployShared ? sharedInfra!.outputs.aksClusterName : ''
output APIM_GATEWAY_URL string = deployShared ? sharedInfra!.outputs.apimGatewayUrl : ''

// Propagate shared infrastructure outputs for azd env and Helm rendering
output AI_SERVICES_NAME string = deployShared ? sharedInfra!.outputs.aiServicesName : ''
output AI_SEARCH_NAME string = deployShared ? sharedInfra!.outputs.aiSearchName : ''
output AI_SEARCH_ENDPOINT string = deployShared ? sharedInfra!.outputs.aiSearchEndpoint : ''
output AI_SEARCH_INDEX string = deployShared ? sharedInfra!.outputs.aiSearchIndexName : ''
output AI_SEARCH_AUTH_MODE string = deployShared ? sharedInfra!.outputs.aiSearchAuthMode : ''
output PROJECT_NAME string = deployShared ? sharedInfra!.outputs.aiProjectName : ''
output PROJECT_ENDPOINT string = deployShared ? 'https://${sharedInfra!.outputs.aiServicesName}.cognitiveservices.azure.com' : ''
output COSMOS_ACCOUNT_URI string = deployShared ? sharedInfra!.outputs.cosmosEndpoint : ''
output COSMOS_DATABASE string = deployShared ? sharedInfra!.outputs.databaseName : ''
output KEY_VAULT_URI string = deployShared ? sharedInfra!.outputs.keyVaultUri : ''
output REDIS_HOST string = deployShared ? sharedInfra!.outputs.redisName : ''
output EVENT_HUB_NAMESPACE string = deployShared ? sharedInfra!.outputs.eventHubsNamespaceName : ''
output APPLICATIONINSIGHTS_CONNECTION_STRING string = deployShared ? sharedInfra!.outputs.appInsightsConnectionString : ''
output POSTGRES_HOST string = deployShared ? sharedInfra!.outputs.postgresFqdn : ''
output POSTGRES_USER string = deployShared ? postgresWorkloadUser : ''
output POSTGRES_ADMIN_USER string = deployShared ? sharedInfra!.outputs.postgresAdminUser : ''
output POSTGRES_AUTH_MODE string = deployShared ? postgresAuthMode : ''
output POSTGRES_DATABASE string = deployShared ? sharedInfra!.outputs.postgresDatabaseName : ''
output AGC_SUPPORT_ENABLED string = deployShared && sharedInfra!.outputs.agcSupportEnabled ? 'true' : 'false'
output AGC_SUBNET_ID string = deployShared ? sharedInfra!.outputs.agcSubnetId : ''
output AGC_SUBNET_NAME string = deployShared ? sharedInfra!.outputs.agcSubnetName : ''
output AGC_SUBNET_PREFIX string = deployShared ? sharedInfra!.outputs.agcSubnetAddressPrefix : ''
output AGC_CONTROLLER_DEPLOYMENT_MODE string = deployShared ? sharedInfra!.outputs.agcControllerDeploymentMode : ''
output AGC_GATEWAY_CLASS string = deployShared ? sharedInfra!.outputs.agcGatewayClass : ''
output AGC_CONTROLLER_IDENTITY_NAME string = deployShared ? sharedInfra!.outputs.agcControllerIdentityName : ''
output AGC_CONTROLLER_IDENTITY_CLIENT_ID string = deployShared ? sharedInfra!.outputs.agcControllerIdentityClientId : ''
output AGC_CONTROLLER_IDENTITY_PRINCIPAL_ID string = deployShared ? sharedInfra!.outputs.agcControllerIdentityPrincipalId : ''
output AGC_FRONTEND_HOSTNAME string = deployShared ? sharedInfra!.outputs.agcFrontendHostname : ''
output AGC_FRONTEND_REFERENCE string = deployShared ? sharedInfra!.outputs.agcFrontendReference : ''
output AKS_OIDC_ISSUER_URL string = deployShared ? sharedInfra!.outputs.aksOidcIssuerUrl : ''
output AKS_NODE_RESOURCE_GROUP string = deployShared ? sharedInfra!.outputs.aksNodeResourceGroup : ''
