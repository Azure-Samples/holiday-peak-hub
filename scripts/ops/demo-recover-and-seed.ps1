param(
    [string]$Environment = $(if ($env:AZURE_ENV_NAME) { $env:AZURE_ENV_NAME } else { '' }),
    [string]$ProjectName = "holidaypeakhub405",
    [string]$Namespace = "holiday-peak",
    [switch]$SkipSeed
)

$ErrorActionPreference = "Stop"

function Get-AzdEnvMap {
    param([Parameter(Mandatory = $true)][string]$EnvName)

    $map = @{}
    $lines = azd env get-values -e $EnvName 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $lines) {
        return $map
    }

    foreach ($line in $lines) {
        if ($line -match '^([A-Za-z0-9_]+)=(.*)$') {
            $key = $Matches[1]
            $value = $Matches[2].Trim('"')
            $map[$key] = $value
        }
    }

    return $map
}

function Try-StartAks {
    param(
        [Parameter(Mandatory = $true)][string]$ResourceGroup,
        [Parameter(Mandatory = $true)][string]$ClusterName
    )

    $powerState = az aks show -g $ResourceGroup -n $ClusterName --query "powerState.code" -o tsv 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $powerState) {
        throw "AKS cluster '$ClusterName' was not found in '$ResourceGroup'."
    }

    if ($powerState -eq "Running") {
        Write-Host "AKS '$ClusterName' is already running; continuing."
        return
    }

    az aks start -g $ResourceGroup -n $ClusterName --only-show-errors 2>$null *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to start AKS '$ClusterName'."
    }
}

function Try-StartPostgres {
    param(
        [Parameter(Mandatory = $true)][string]$ResourceGroup,
        [Parameter(Mandatory = $true)][string]$ServerName
    )

    $state = az postgres flexible-server show -g $ResourceGroup -n $ServerName --query "state" -o tsv 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $state) {
        throw "PostgreSQL server '$ServerName' was not found in '$ResourceGroup'."
    }

    if ($state -eq "Ready") {
        Write-Host "PostgreSQL '$ServerName' is already ready; continuing."
        return
    }

    az postgres flexible-server start -g $ResourceGroup -n $ServerName --only-show-errors 2>$null *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to start PostgreSQL '$ServerName'."
    }
}

function Try-StartApplicationGateway {
    param(
        [Parameter(Mandatory = $true)][string]$ResourceGroup,
        [Parameter(Mandatory = $true)][string]$GatewayName
    )

    az network application-gateway show -g $ResourceGroup -n $GatewayName --only-show-errors *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Application Gateway '$GatewayName' not found in '$ResourceGroup'; skipping (AGC mode)."
        return
    }

    az network application-gateway start -g $ResourceGroup -n $GatewayName --only-show-errors *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Application Gateway '$GatewayName' is already running or could not be started now; continuing."
    }
}

if ([string]::IsNullOrWhiteSpace($Environment)) {
    throw "Environment must be provided via -Environment or AZURE_ENV_NAME."
}

$resourceGroup = "$ProjectName-$Environment-rg"
$aksName = "$ProjectName-$Environment-aks"
$appGwName = "$ProjectName-$Environment-appgw"
$postgresName = "$ProjectName-$Environment-postgres"
$apimBase = "https://$ProjectName-$Environment-apim.azure-api.net"
$apimName = "$ProjectName-$Environment-apim"

$env:AZURE_ENV_NAME = $Environment
$azdVars = Get-AzdEnvMap -EnvName $Environment
if ($azdVars.ContainsKey("APIM_NAME") -and $azdVars["APIM_NAME"]) {
    $apimName = $azdVars["APIM_NAME"]
}
if ($azdVars.ContainsKey("APIM_GATEWAY_URL") -and $azdVars["APIM_GATEWAY_URL"]) {
    $apimBase = $azdVars["APIM_GATEWAY_URL"].TrimEnd('/')
}
if ($azdVars.ContainsKey("AGC_FRONTEND_HOSTNAME") -and $azdVars["AGC_FRONTEND_HOSTNAME"]) {
    $env:AGC_FRONTEND_HOSTNAME = $azdVars["AGC_FRONTEND_HOSTNAME"]
}
if ($azdVars.ContainsKey("AGC_FRONTEND_SCHEME") -and $azdVars["AGC_FRONTEND_SCHEME"]) {
    $env:AGC_FRONTEND_SCHEME = $azdVars["AGC_FRONTEND_SCHEME"]
}
if ($azdVars.ContainsKey("APIM_APPROVED_BACKEND_HOSTNAMES") -and $azdVars["APIM_APPROVED_BACKEND_HOSTNAMES"]) {
    $env:APIM_APPROVED_BACKEND_HOSTNAMES = $azdVars["APIM_APPROVED_BACKEND_HOSTNAMES"]
}

Write-Host "Starting AKS, Application Gateway, and PostgreSQL in '$resourceGroup'..."
Try-StartAks -ResourceGroup $resourceGroup -ClusterName $aksName
Try-StartApplicationGateway -ResourceGroup $resourceGroup -GatewayName $appGwName
Try-StartPostgres -ResourceGroup $resourceGroup -ServerName $postgresName

Write-Host "Waiting for AKS to report Running..."
for ($i = 0; $i -lt 30; $i++) {
    $state = az aks show -g "$resourceGroup" -n "$aksName" --query "powerState.code" -o tsv
    if ($state -eq "Running") { break }
    Start-Sleep -Seconds 20
}

Write-Host "Re-running APIM reconciliation through App Gateway before validation..."
.\.infra\azd\hooks\sync-apim-agents.ps1 -ResourceGroup $resourceGroup -ApimName $apimName -Namespace $Namespace -ApiPathPrefix agents -IncludeCrudService:$true

Write-Host "Validating APIM CRUD endpoints..."
$paths = @("/api/health", "/api/products?limit=1", "/api/categories")
foreach ($path in $paths) {
    $url = "$apimBase$path"
    $ok = $false
    for ($attempt = 1; $attempt -le 30; $attempt++) {
        try {
            $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 30
            if ($resp.StatusCode -eq 200) {
                $ok = $true
                break
            }
        }
        catch {
            Start-Sleep -Seconds 10
        }
    }

    if (-not $ok) {
        throw "Endpoint did not recover with HTTP 200: $url"
    }
}

Write-Host "APIM connectivity recovered."

if (-not $SkipSeed) {
    Write-Host "Re-seeding CRUD demo database data..."
    $env:AZURE_ENV_NAME = $Environment
    $env:K8S_NAMESPACE = $Namespace
    .\.infra\azd\hooks\seed-crud-demo-data.ps1 -FailOnError $true
}

Write-Host "Recovery flow completed for '$resourceGroup'."
