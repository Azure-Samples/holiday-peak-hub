targetScope = 'resourceGroup'

param location string = resourceGroup().location
param appName string = 'holidaypeakhub-ui'
param environment string = 'dev' // dev, staging, prod
param repositoryUrl string = 'https://github.com/Azure-Samples/holiday-peak-hub'
param branch string = 'main'

// Resource names
var staticWebAppName = '${appName}-${environment}'

// Azure Static Web Apps
resource staticWebApp 'Microsoft.Web/staticSites@2023-01-01' = {
  name: staticWebAppName
  location: location
  sku: {
    name: environment == 'prod' ? 'Standard' : 'Free'
    tier: environment == 'prod' ? 'Standard' : 'Free'
  }
  properties: {
    repositoryUrl: repositoryUrl
    branch: branch
    buildProperties: {
      appLocation: '/apps/ui' // Next.js app location
      apiLocation: '' // No API functions in SWA
      outputLocation: 'out' // Next.js static export output directory
      appBuildCommand: 'npm run build'
      skipGithubActionWorkflowGeneration: false
    }
    stagingEnvironmentPolicy: environment == 'prod' ? 'Enabled' : 'Disabled'
    allowConfigFileUpdates: true
    enterpriseGradeCdnStatus: environment == 'prod' ? 'Enabled' : 'Disabled'
  }
  tags: {
    Environment: environment
    Project: 'HolidayPeakHub'
    ManagedBy: 'Bicep'
  }
}

// Custom Domain (optional, for prod)
resource customDomain 'Microsoft.Web/staticSites/customDomains@2023-01-01' = if (environment == 'prod') {
  parent: staticWebApp
  name: 'www.holidaypeakhub.com'
  properties: {}
}

// App Settings
resource appSettings 'Microsoft.Web/staticSites/config@2023-01-01' = {
  parent: staticWebApp
  name: 'appsettings'
  properties: {
    NEXT_PUBLIC_API_BASE_URL: environment == 'prod' ? 'https://api.holidaypeakhub.com' : 'https://holidaypeakhub-dev-apim.azure-api.net'
    NEXT_PUBLIC_ENVIRONMENT: environment
  }
}

// Outputs
output staticWebAppName string = staticWebApp.name
output staticWebAppDefaultHostname string = staticWebApp.properties.defaultHostname
output staticWebAppId string = staticWebApp.id
output deploymentToken string = listSecrets(staticWebApp.id, staticWebApp.apiVersion).properties.apiKey
