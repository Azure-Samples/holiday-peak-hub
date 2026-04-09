#!/usr/bin/env pwsh
param(
    [string]$Environment = $(if ($env:AZURE_ENV_NAME) { $env:AZURE_ENV_NAME } else { '' })
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($Environment)) {
    throw "Environment must be provided via -Environment or AZURE_ENV_NAME."
}

$rawValues = azd env get-values -e "$Environment" 2>$null
$values = @{}
foreach ($line in $rawValues) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    $trimmed = $line.Trim()
    if ($trimmed.StartsWith('#')) { continue }
    if ($trimmed -match '^([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
        $key = $matches[1]
        $value = $matches[2]
        if (($value.StartsWith('"') -and $value.EndsWith('"')) -or
            ($value.StartsWith("'") -and $value.EndsWith("'"))) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        $values[$key] = $value
    }
}

# AZURE_LOCATION defaults to 'eastus2'.
if (-not $values.ContainsKey('AZURE_LOCATION') -or [string]::IsNullOrWhiteSpace($values['AZURE_LOCATION'])) {
    Write-Host "AZURE_LOCATION not set - defaulting to 'eastus2'."
    azd env set AZURE_LOCATION 'eastus2' -e "$Environment"
    $values['AZURE_LOCATION'] = 'eastus2'
}

# projectName defaults to the azd environment name.
if (-not $values.ContainsKey('projectName') -or [string]::IsNullOrWhiteSpace($values['projectName'])) {
    Write-Host "projectName not set - defaulting to AZURE_ENV_NAME '$Environment'."
    azd env set projectName "$Environment" -e "$Environment"
    $values['projectName'] = $Environment
}

# environment (dev/staging/prod) defaults to 'dev'.
if (-not $values.ContainsKey('environment') -or [string]::IsNullOrWhiteSpace($values['environment'])) {
    Write-Host "environment not set - defaulting to 'dev'."
    azd env set environment 'dev' -e "$Environment"
    $values['environment'] = 'dev'
}

$projectName = $values['projectName']
$env = $values['environment']
$expectedResourceGroup = "$projectName-$env-rg"

# resourceGroupName defaults to <projectName>-<environment>-rg.
if (-not $values.ContainsKey('resourceGroupName') -or [string]::IsNullOrWhiteSpace($values['resourceGroupName'])) {
    Write-Host "resourceGroupName not set - defaulting to '$expectedResourceGroup'."
    azd env set resourceGroupName "$expectedResourceGroup" -e "$Environment"
}

# AZURE_RESOURCE_GROUP defaults to the same value.
if (-not $values.ContainsKey('AZURE_RESOURCE_GROUP') -or [string]::IsNullOrWhiteSpace($values['AZURE_RESOURCE_GROUP'])) {
    Write-Host "AZURE_RESOURCE_GROUP not set - defaulting to '$expectedResourceGroup'."
    azd env set AZURE_RESOURCE_GROUP "$expectedResourceGroup" -e "$Environment"
}

Write-Host "Azd environment defaults resolved for '$Environment': projectName=$projectName, environment=$env, resourceGroup=$expectedResourceGroup"

Write-Host "Canonical azd naming guard passed for environment '$Environment'."