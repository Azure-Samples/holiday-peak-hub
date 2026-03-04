param(
    [Parameter(Mandatory = $true)]
    [string]$ServiceName
)

$namespace = if ($env:K8S_NAMESPACE) { $env:K8S_NAMESPACE } else { "holiday-peak" }
$imagePrefix = if ($env:IMAGE_PREFIX) { $env:IMAGE_PREFIX } else { "ghcr.io/azure-samples" }
$imageTag = if ($env:IMAGE_TAG) { $env:IMAGE_TAG } else { "latest" }
$kedaEnabled = if ($env:KEDA_ENABLED) { $env:KEDA_ENABLED } else { "false" }
$readinessPath = "/ready"

if ($ServiceName -eq "crud-service") {
  $readinessPath = "/health"
}

if ($ServiceName -ne "crud-service") {
  $requiredAgentVars = @(
    'REDIS_URL',
    'COSMOS_ACCOUNT_URI',
    'COSMOS_DATABASE',
    'COSMOS_CONTAINER',
    'BLOB_ACCOUNT_URL',
    'BLOB_CONTAINER',
    'CRUD_SERVICE_URL'
  )
  $missingAgentVars = @($requiredAgentVars | Where-Object { -not [Environment]::GetEnvironmentVariable($_) })
  if ($missingAgentVars.Count -gt 0) {
    throw "Missing required environment variables for APIM/private-memory standard ($ServiceName): $($missingAgentVars -join ', ')"
  }
}

if ($ServiceName -eq "crud-service" -and -not [Environment]::GetEnvironmentVariable('AGENT_APIM_BASE_URL')) {
  throw "Missing required environment variable for APIM-only standard (crud-service): AGENT_APIM_BASE_URL"
}

if ($ServiceName -eq "crud-service") {
  $postgresUser = [Environment]::GetEnvironmentVariable('POSTGRES_USER')
  $postgresAuthMode = [Environment]::GetEnvironmentVariable('POSTGRES_AUTH_MODE')
  if (-not $postgresAuthMode) {
    $postgresAuthMode = 'password'
  }

  if ($postgresAuthMode -ne 'entra' -and $postgresUser -match '-aks-agentpool$') {
    throw "Invalid POSTGRES_USER '$postgresUser' for POSTGRES_AUTH_MODE '$postgresAuthMode'. Use the PostgreSQL admin user (for example: crud_admin) for password auth mode."
  }
}

$serviceImageVarName = "SERVICE_$($ServiceName.ToUpper().Replace('-', '_'))_IMAGE_NAME"
$serviceImage = [Environment]::GetEnvironmentVariable($serviceImageVarName)

if ($serviceImage) {
  $lastColon = $serviceImage.LastIndexOf(':')
  if ($lastColon -gt 0) {
    $imagePrefix = $serviceImage.Substring(0, $lastColon)
    $imageTag = $serviceImage.Substring($lastColon + 1)
  } else {
    $imagePrefix = $serviceImage
  }
} else {
  $imagePrefix = "$imagePrefix/$ServiceName"
}

$repoRoot = Resolve-Path "$PSScriptRoot\..\..\.."
$chartPath = Join-Path $repoRoot ".kubernetes\chart"
$outDir = Join-Path $repoRoot ".kubernetes\rendered\$ServiceName"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$rendered = Join-Path $outDir "all.yaml"

$helmArgs = @(
  'template',
  $ServiceName,
  $chartPath,
  '--namespace',
  $namespace,
  '--set',
  "serviceName=$ServiceName",
  '--set',
  "image.repository=$imagePrefix",
  '--set',
  "image.tag=$imageTag",
  '--set',
  "keda.enabled=$kedaEnabled"
  '--set',
  "probes.readiness.path=$readinessPath"
)

if ($ServiceName -eq "crud-service") {
  $helmArgs += @(
    '--set',
    'service.type=LoadBalancer',
    '--set-string',
    'service.annotations.service\.beta\.kubernetes\.io/azure-load-balancer-internal=true'
  )
}

$envMappings = @{
  # Database
  POSTGRES_HOST = $env:POSTGRES_HOST
  POSTGRES_USER = $env:POSTGRES_USER
  POSTGRES_PASSWORD = $env:POSTGRES_PASSWORD
  POSTGRES_DATABASE = $env:POSTGRES_DATABASE
  POSTGRES_PORT = $env:POSTGRES_PORT
  POSTGRES_SSL = $env:POSTGRES_SSL

  # Messaging & Infrastructure
  EVENT_HUB_NAMESPACE = $env:EVENT_HUB_NAMESPACE
  KEY_VAULT_URI = $env:KEY_VAULT_URI
  REDIS_HOST = $env:REDIS_HOST
  CRUD_SERVICE_URL = $env:CRUD_SERVICE_URL
  AGENT_APIM_BASE_URL = $env:AGENT_APIM_BASE_URL
  AZURE_CLIENT_ID = $env:AZURE_CLIENT_ID
  AZURE_TENANT_ID = $env:AZURE_TENANT_ID

  # Azure AI Foundry
  PROJECT_ENDPOINT = $env:PROJECT_ENDPOINT
  PROJECT_NAME = $env:PROJECT_NAME
  FOUNDRY_AGENT_ID_FAST = $env:FOUNDRY_AGENT_ID_FAST
  FOUNDRY_AGENT_ID_RICH = $env:FOUNDRY_AGENT_ID_RICH
  MODEL_DEPLOYMENT_NAME_FAST = $env:MODEL_DEPLOYMENT_NAME_FAST
  MODEL_DEPLOYMENT_NAME_RICH = $env:MODEL_DEPLOYMENT_NAME_RICH
  FOUNDRY_STREAM = $env:FOUNDRY_STREAM
  FOUNDRY_STRICT_ENFORCEMENT = $env:FOUNDRY_STRICT_ENFORCEMENT
  FOUNDRY_AUTO_ENSURE_ON_STARTUP = $env:FOUNDRY_AUTO_ENSURE_ON_STARTUP

  # Memory tiers
  REDIS_URL = $env:REDIS_URL
  COSMOS_ACCOUNT_URI = $env:COSMOS_ACCOUNT_URI
  COSMOS_DATABASE = $env:COSMOS_DATABASE
  COSMOS_CONTAINER = $env:COSMOS_CONTAINER
  BLOB_ACCOUNT_URL = $env:BLOB_ACCOUNT_URL
  BLOB_CONTAINER = $env:BLOB_CONTAINER

  # Observability
  APPLICATIONINSIGHTS_CONNECTION_STRING = $env:APPLICATIONINSIGHTS_CONNECTION_STRING
}

foreach ($key in $envMappings.Keys) {
  $value = $envMappings[$key]
  if ($value) {
    $helmArgs += @('--set-string', "env.$key=$value")
  }
}

& helm @helmArgs | Out-File -FilePath $rendered -Encoding utf8

Write-Host "Rendered Helm manifests to $rendered"
