param(
    [string]$EnvironmentName = $(if ($env:AZURE_ENV_NAME) { $env:AZURE_ENV_NAME } else { 'dev' }),
    [string]$OutputPath,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path "$PSScriptRoot\..\..\.."
if (-not $OutputPath) {
    $OutputPath = Join-Path $repoRoot 'apps/crud-service/.env'
}

function Parse-AzdValues {
    param([string]$EnvName)

    $content = azd env get-values -e $EnvName 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $content) {
        throw "Failed to read azd env values for environment '$EnvName'."
    }

    $map = @{}
    foreach ($line in $content) {
        if ($line -match '^\s*([^=\s]+)=(.*)$') {
            $key = $Matches[1].Trim()
            $value = $Matches[2].Trim().Trim('"')
            $map[$key] = $value
        }
    }
    return $map
}

function First-Value {
    param(
        [hashtable]$Map,
        [string[]]$Keys,
        [string]$DefaultValue = ''
    )

    foreach ($key in $Keys) {
        if ($Map.ContainsKey($key) -and $Map[$key]) {
            return "$($Map[$key])"
        }
    }
    return $DefaultValue
}

function Ensure-Suffix {
    param(
        [string]$Value,
        [string]$Suffix
    )

    if (-not $Value) {
        return ''
    }
    if ($Value.Contains('.')) {
        return $Value
    }
    return "$Value$Suffix"
}

function Resolve-ApimGatewayUrl {
    param(
        [hashtable]$Map,
        [string]$ResourceGroup
    )

    $gatewayUrl = First-Value -Map $Map -Keys @('AGENT_APIM_BASE_URL', 'APIM_GATEWAY_URL', 'apimGatewayUrl')
    if ($gatewayUrl) {
        return $gatewayUrl
    }

    $apimName = First-Value -Map $Map -Keys @('APIM_NAME', 'apimName')
    if (-not $apimName -and $ResourceGroup) {
        $apimName = az apim list --resource-group $ResourceGroup --query "[0].name" -o tsv 2>$null
    }

    if ($apimName) {
        return "https://$apimName.azure-api.net"
    }

    return ''
}

$values = Parse-AzdValues -EnvName $EnvironmentName

$resourceGroup = First-Value -Map $values -Keys @('AZURE_RESOURCE_GROUP', 'resourceGroupName')
$environment = First-Value -Map $values -Keys @('ENVIRONMENT', 'environment') -DefaultValue $EnvironmentName

$postgresHost = First-Value -Map $values -Keys @('POSTGRES_HOST', 'postgresFqdn', 'POSTGRES_FQDN')
$postgresDatabase = First-Value -Map $values -Keys @('POSTGRES_DATABASE', 'postgresDatabaseName') -DefaultValue 'holiday_peak_crud'
$postgresAuthMode = First-Value -Map $values -Keys @('POSTGRES_AUTH_MODE', 'postgresAuthMode') -DefaultValue 'password'
$postgresAdminUser = First-Value -Map $values -Keys @('POSTGRES_ADMIN_USER', 'postgresAdminUser') -DefaultValue 'crud_admin'
$postgresUser = First-Value -Map $values -Keys @('POSTGRES_USER')
if ($postgresAuthMode -eq 'password') {
    $postgresUser = $postgresAdminUser
}
elseif (-not $postgresUser -or $postgresUser -eq $postgresAdminUser -or $postgresUser -eq 'crud_admin') {
    $aksClusterName = First-Value -Map $values -Keys @('AZURE_AKS_CLUSTER_NAME', 'AKS_CLUSTER_NAME', 'aksClusterName')
    if ($aksClusterName) {
        $postgresUser = "$aksClusterName-agentpool"
    }
    else {
        $projectName = First-Value -Map $values -Keys @('projectName', 'PROJECT_NAME')
        if ($projectName) {
            if ($environment -eq 'prod') {
                $postgresUser = "$projectName-aks-agentpool"
            }
            else {
                $postgresUser = "$projectName-$environment-aks-agentpool"
            }
        }
        else {
            $postgresUser = "crud-$environment-aks-agentpool"
        }
    }
}

$eventHubNamespace = Ensure-Suffix -Value (First-Value -Map $values -Keys @('EVENT_HUB_NAMESPACE', 'eventHubsNamespaceName')) -Suffix '.servicebus.windows.net'
$keyVaultUri = First-Value -Map $values -Keys @('KEY_VAULT_URI', 'keyVaultUri')
$redisHost = Ensure-Suffix -Value (First-Value -Map $values -Keys @('REDIS_HOST', 'redisName')) -Suffix '.redis.cache.windows.net'
$redisPassword = First-Value -Map $values -Keys @('REDIS_PASSWORD')
$redisPasswordSecretName = First-Value -Map $values -Keys @('REDIS_PASSWORD_SECRET_NAME', 'redisPasswordSecretName') -DefaultValue 'redis-primary-key'
$apimGatewayUrl = Resolve-ApimGatewayUrl -Map $values -ResourceGroup $resourceGroup
$entraTenantId = First-Value -Map $values -Keys @('ENTRA_TENANT_ID', 'NEXT_PUBLIC_ENTRA_TENANT_ID')
$entraClientId = First-Value -Map $values -Keys @('ENTRA_CLIENT_ID', 'NEXT_PUBLIC_ENTRA_CLIENT_ID')

$outputDir = Split-Path -Parent $OutputPath
if (-not (Test-Path $outputDir)) {
    New-Item -Path $outputDir -ItemType Directory -Force | Out-Null
}

if ((Test-Path $OutputPath) -and (-not $Force)) {
    throw "Output file already exists: $OutputPath. Re-run with -Force to overwrite."
}

$content = @"
# Auto-generated from azd env '$EnvironmentName'
# Source: azd env get-values -e $EnvironmentName

ENVIRONMENT=$environment
SERVICE_NAME=crud-service
LOG_LEVEL=INFO

POSTGRES_HOST=$postgresHost
POSTGRES_PORT=5432
POSTGRES_DATABASE=$postgresDatabase
POSTGRES_AUTH_MODE=$postgresAuthMode
POSTGRES_USER=$postgresUser
POSTGRES_PASSWORD=
POSTGRES_PASSWORD_SECRET_NAME=postgres-admin-password
POSTGRES_ENTRA_SCOPE=https://ossrdbms-aad.database.windows.net/.default
POSTGRES_SSL=true

EVENT_HUB_NAMESPACE=$eventHubNamespace
KEY_VAULT_URI=$keyVaultUri
REDIS_HOST=$redisHost
REDIS_PASSWORD=$redisPassword
REDIS_PASSWORD_SECRET_NAME=$redisPasswordSecretName
REDIS_PORT=6380
REDIS_DB=0
REDIS_SSL=true

ENTRA_TENANT_ID=$entraTenantId
ENTRA_CLIENT_ID=$entraClientId
ENTRA_CLIENT_SECRET=
ENTRA_ISSUER=

ENABLE_AGENT_FALLBACK=true
AGENT_TIMEOUT_SECONDS=0.5
AGENT_RETRY_ATTEMPTS=2
AGENT_CIRCUIT_FAILURE_THRESHOLD=5
AGENT_CIRCUIT_RECOVERY_SECONDS=60

AGENT_APIM_BASE_URL=$apimGatewayUrl

PRODUCT_ENRICHMENT_AGENT_URL=
CART_INTELLIGENCE_AGENT_URL=
INVENTORY_HEALTH_AGENT_URL=
CHECKOUT_SUPPORT_AGENT_URL=

APP_INSIGHTS_CONNECTION_STRING=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
SENDGRID_API_KEY=
"@

Set-Content -Path $OutputPath -Value $content -Encoding UTF8
Write-Host "Generated CRUD env file at: $OutputPath"
