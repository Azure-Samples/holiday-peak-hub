param(
    [string]$Environment = "dev",
    [string]$ProjectName = "holidaypeakhub405",
    [string]$Namespace = "holiday-peak",
    [switch]$SkipSeed
)

$ErrorActionPreference = "Stop"

$resourceGroup = "$ProjectName-$Environment-rg"
$aksName = "$ProjectName-$Environment-aks"
$appGwName = "$ProjectName-$Environment-appgw"
$postgresName = "$ProjectName-$Environment-postgres"
$apimBase = "https://$ProjectName-$Environment-apim.azure-api.net"
$apimName = "$ProjectName-$Environment-apim"

Write-Host "Starting AKS, Application Gateway, and PostgreSQL in '$resourceGroup'..."
az aks start -g "$resourceGroup" -n "$aksName" | Out-Null
az network application-gateway start -g "$resourceGroup" -n "$appGwName" | Out-Null
az postgres flexible-server start -g "$resourceGroup" -n "$postgresName" | Out-Null

Write-Host "Waiting for AKS to report Running..."
for ($i = 0; $i -lt 30; $i++) {
    $state = az aks show -g "$resourceGroup" -n "$aksName" --query "powerState.code" -o tsv
    if ($state -eq "Running") { break }
    Start-Sleep -Seconds 20
}

Write-Host "Re-running APIM reconciliation through App Gateway before validation..."
.\.infra\azd\hooks\sync-apim-agents.ps1 -ResourceGroup $resourceGroup -ApimName $apimName -Namespace $Namespace -ApiPathPrefix agents -UseIngress -AppGatewayName $appGwName -IncludeCrudService:$true

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
