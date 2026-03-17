param(
    [string]$Environment = $(if ($env:AZURE_ENV_NAME) { $env:AZURE_ENV_NAME } else { '' }),
    [string]$Location = "centralus",
    [string]$ProjectName = "holidaypeakhub405"
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($Environment)) {
    throw "Environment must be provided via -Environment or AZURE_ENV_NAME."
}

$resourceGroup = "$ProjectName-$Environment-rg"

Write-Host "Configuring azd environment '$Environment' for single RG deployment..."
azd env set AZURE_LOCATION "$Location" -e "$Environment"
azd env set AZURE_ENV_NAME "$Environment" -e "$Environment"
azd env set AZURE_RESOURCE_GROUP "$resourceGroup" -e "$Environment"
azd env set resourceGroupName "$resourceGroup" -e "$Environment"
azd env set projectName "$ProjectName" -e "$Environment"

Write-Host "Provisioning and deploying services to resource group '$resourceGroup'..."
azd up -e "$Environment" --no-prompt

Write-Host "Provision flow completed for '$resourceGroup'."
