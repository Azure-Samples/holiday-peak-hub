targetScope = 'resourceGroup'

param location string = resourceGroup().location
param projectName string = 'holidaypeakhub405'
param appName string = ''
param environment string = 'dev' // dev, staging, prod
param repositoryUrl string = 'https://github.com/Azure-Samples/holiday-peak-hub'
param branch string = 'main'

// Resource names
var staticWebAppBaseName = empty(appName) ? '${projectName}-ui' : appName
var staticWebAppName = '${staticWebAppBaseName}-${environment}'
var apimBaseUrl = 'https://${projectName}-${environment}-apim.azure-api.net'

// Azure Static Web Apps
resource staticWebApp 'Microsoft.Web/staticSites@2025-03-01' = {
  name: staticWebAppName
  location: location
  sku: {
    name: environment == 'prod' ? 'Standard' : 'Free'
    tier: environment == 'prod' ? 'Standard' : 'Free'
  }
  properties: {
    buildProperties: {
      appLocation: '/apps/ui'
      apiLocation: ''
      outputLocation: '.next'
      appBuildCommand: 'yarn build'
      skipGithubActionWorkflowGeneration: true
    }
    stagingEnvironmentPolicy: environment == 'prod' ? 'Enabled' : 'Disabled'
    allowConfigFileUpdates: true
    enterpriseGradeCdnStatus: environment == 'prod' ? 'Enabled' : 'Disabled'
  }
  tags: {
    Environment: environment
    Project: 'HolidayPeakHub'
    ManagedBy: 'Bicep'
    'azd-service-name': 'ui'
    'azd-env-name': environment
    SourceRepository: repositoryUrl
    SourceBranch: branch
  }
}

// Custom Domain (optional, for prod)
resource customDomain 'Microsoft.Web/staticSites/customDomains@2025-03-01' = if (environment == 'prod') {
  parent: staticWebApp
  name: 'www.holidaypeakhub.com'
  properties: {}
}

// App Settings
resource appSettings 'Microsoft.Web/staticSites/config@2025-03-01' = {
  parent: staticWebApp
  name: 'appsettings'
  properties: {
    NEXT_PUBLIC_API_BASE_URL: apimBaseUrl
    NEXT_PUBLIC_API_URL: apimBaseUrl
    NEXT_PUBLIC_CRUD_API_URL: apimBaseUrl
    NEXT_PUBLIC_ENVIRONMENT: environment
  }
}

// Outputs
output staticWebAppName string = staticWebApp.name
output staticWebAppDefaultHostname string = staticWebApp.properties.defaultHostname
output staticWebAppId string = staticWebApp.id
