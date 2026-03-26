#!/usr/bin/env pwsh
param(
    [string]$Environment = $(if ($env:AZURE_ENV_NAME) { $env:AZURE_ENV_NAME } else { '' })
)

$ErrorActionPreference = 'Stop'

$canonicalProjectName = 'holidaypeakhub405'

if ([string]::IsNullOrWhiteSpace($Environment)) {
    throw "Environment must be provided via -Environment or AZURE_ENV_NAME."
}

$expectedResourceGroup = "$canonicalProjectName-$Environment-rg"

$rawValues = azd env get-values -e "$Environment"
if ($LASTEXITCODE -ne 0) {
    throw "Failed to resolve azd environment values for '$Environment'."
}

$values = @{}
foreach ($line in $rawValues) {
    if ([string]::IsNullOrWhiteSpace($line)) {
        continue
    }

    $trimmed = $line.Trim()
    if ($trimmed.StartsWith('#')) {
        continue
    }

    if ($trimmed -match '^([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
        $key = $matches[1]
        $value = $matches[2]

        if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
            $value = $value.Substring(1, $value.Length - 2)
        }

        $values[$key] = $value
    }
}

function Get-RequiredEnvValue {
    param(
        [string]$Name
    )

    if (-not $values.ContainsKey($Name) -or [string]::IsNullOrWhiteSpace($values[$Name])) {
        throw "Required azd environment value '$Name' is missing for '$Environment'."
    }

    return $values[$Name]
}

$resolvedProjectName = Get-RequiredEnvValue -Name 'projectName'
$resolvedResourceGroupName = Get-RequiredEnvValue -Name 'resourceGroupName'
$resolvedAzureResourceGroup = Get-RequiredEnvValue -Name 'AZURE_RESOURCE_GROUP'

if ($resolvedProjectName -ne $canonicalProjectName) {
    throw "Invalid projectName '$resolvedProjectName'. Expected '$canonicalProjectName'."
}

if ($resolvedResourceGroupName -ne $expectedResourceGroup) {
    throw "Invalid resourceGroupName '$resolvedResourceGroupName'. Expected '$expectedResourceGroup'."
}

if ($resolvedAzureResourceGroup -ne $expectedResourceGroup) {
    throw "Invalid AZURE_RESOURCE_GROUP '$resolvedAzureResourceGroup'. Expected '$expectedResourceGroup'."
}

Write-Host "Canonical azd naming guard passed for environment '$Environment'."