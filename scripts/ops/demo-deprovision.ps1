param(
    [string]$Environment = $(if ($env:AZURE_ENV_NAME) { $env:AZURE_ENV_NAME } else { '' }),
    [string]$ProjectName = "holidaypeakhub405",
    [switch]$DeleteResourceGroup
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($Environment)) {
    throw "Environment must be provided via -Environment or AZURE_ENV_NAME."
}

$resourceGroup = "$ProjectName-$Environment-rg"
$aksName = "$ProjectName-$Environment-aks"
$appGwName = "$ProjectName-$Environment-appgw"
$postgresName = "$ProjectName-$Environment-postgres"

if ($DeleteResourceGroup) {
    Write-Host "Deleting resource group '$resourceGroup'..."
    az group delete -n "$resourceGroup" --yes --no-wait
    Write-Host "Deletion started for '$resourceGroup'."
    exit 0
}

Write-Host "Stopping cost-intensive services in '$resourceGroup'..."
az aks stop -g "$resourceGroup" -n "$aksName" | Out-Null
az network application-gateway stop -g "$resourceGroup" -n "$appGwName" | Out-Null
az postgres flexible-server stop -g "$resourceGroup" -n "$postgresName" | Out-Null

Write-Host "Deprovision (pause) flow completed for '$resourceGroup'."
