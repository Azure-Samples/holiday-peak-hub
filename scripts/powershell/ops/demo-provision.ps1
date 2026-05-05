param(
    [string]$Environment = $(if ($env:AZURE_ENV_NAME) { $env:AZURE_ENV_NAME } else { '' }),
    [string]$Location = "centralus",
    [string]$ProjectName = "holidaypeakhub405"
)

$ErrorActionPreference = "Stop"
$canonicalProjectName = "holidaypeakhub405"

if ([string]::IsNullOrWhiteSpace($Environment)) {
    throw "Environment must be provided via -Environment or AZURE_ENV_NAME."
}

if ($ProjectName -ne $canonicalProjectName) {
    throw "ProjectName must be '$canonicalProjectName'. Received '$ProjectName'."
}

$resourceGroup = "$ProjectName-$Environment-rg"
$canonicalEnvGuardScript = Join-Path -Path $PSScriptRoot -ChildPath "..\..\.infra\azd\hooks\assert-canonical-azd-env.ps1"

Write-Host "Configuring azd environment '$Environment' for single RG deployment..."
azd env set AZURE_LOCATION "$Location" -e "$Environment"
azd env set AZURE_ENV_NAME "$Environment" -e "$Environment"
azd env set AZURE_RESOURCE_GROUP "$resourceGroup" -e "$Environment"
azd env set resourceGroupName "$resourceGroup" -e "$Environment"
azd env set projectName "$ProjectName" -e "$Environment"

Write-Host "Validating canonical project/resource-group names in azd environment '$Environment'..."
& $canonicalEnvGuardScript -Environment "$Environment"

Write-Host "Provisioning and deploying services to resource group '$resourceGroup'..."
azd up -e "$Environment" --no-prompt

Write-Host "Provision flow completed for '$resourceGroup'."
