// deploy-portal — Bicep skeleton for the one-click deployment portal
// (Issue #1027 / Epic #1039).
//
// Scope: provisions the deployment-portal SERVICE infrastructure (Container
// Apps, APIM, Key Vault, Cosmos for deployment metadata). It does NOT
// provision anything in the customer's subscription — that happens at
// runtime via OBO + ARM template passthrough (#1031).
//
// Hard rules from Epic #1039:
//   - Service identity has ZERO RBAC on customer subscriptions.
//   - All secrets in Key Vault.
//   - APIM rate-limits per-OID at the edge.
//   - Cosmos region is customer-pinnable; defaults to West Europe.
//   - All logs scrub subscription IDs and emails (#1035).
//
// This is a v1 skeleton — parameters are documented but the actual
// deployment is gated by feature flag until Issue #1031 (OBO + ARM
// kickoff) lands and a third-party penetration test passes.
//
// To preview a what-if without deploying:
//   az deployment sub what-if -l westeurope -f infra/deploy-portal/main.bicep \
//     -p environmentName=demo
//
// To deploy (NOT YET PRODUCTION-READY):
//   az deployment sub create -l westeurope -f infra/deploy-portal/main.bicep \
//     -p environmentName=demo

targetScope = 'subscription'

@description('Short environment name (demo, staging, prod). Lowercase.')
@minLength(2)
@maxLength(8)
param environmentName string

@description('Primary location for the deploy-portal service. Default: West Europe per data-residency policy.')
@allowed([
  'westeurope'
  'eastus2'
  'brazilsouth'
])
param location string = 'westeurope'

@description('Tags applied to every resource in the deploy-portal scope.')
param tags object = {
  product: 'holiday-peak-hub'
  surface: 'deploy-portal'
  ownership: 'platform-engineering'
  'data-classification': 'service-metadata-only'
}

@description('Container image for the deploy-portal API. Set per-environment.')
param apiImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

@description('Maximum active concurrent deployments per Entra OID per 24 h.')
param activeDeploymentsPer24h int = 3

@description('Maximum total deployments per Entra OID per 30 days.')
param totalDeploymentsPer30d int = 10

@description('Pre-flight rate (per OID per minute).')
param preflightRatePerMinute int = 1

var resourceGroupName = 'rg-hph-deploy-portal-${environmentName}'

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

module portal 'modules/portal.bicep' = {
  scope: rg
  name: 'deploy-portal-${environmentName}'
  params: {
    environmentName: environmentName
    location: location
    tags: tags
    apiImage: apiImage
    activeDeploymentsPer24h: activeDeploymentsPer24h
    totalDeploymentsPer30d: totalDeploymentsPer30d
    preflightRatePerMinute: preflightRatePerMinute
  }
}

output deployPortalApiHost string = portal.outputs.apiHost
output deployPortalApimGateway string = portal.outputs.apimGatewayUrl
output deployPortalKeyVaultUri string = portal.outputs.keyVaultUri
output cosmosDatabaseName string = portal.outputs.cosmosDatabaseName
