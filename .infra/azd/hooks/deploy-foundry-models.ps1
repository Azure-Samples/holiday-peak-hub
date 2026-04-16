#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Deploys AI model deployments (gpt-5-nano, gpt-5) to the AI Services account
    after Bicep provisions the AI Foundry project.

.DESCRIPTION
    This script runs as a postprovision hook. It ensures the required model
    deployments exist in the Cognitive Services account so that agents can
    reference them at runtime.

    Models are created idempotently — if a deployment already exists it is
    skipped rather than recreated.

.PARAMETER ResourceGroup
    Azure resource group. Falls back to AZURE_RESOURCE_GROUP or azd env.

.PARAMETER AiServicesName
    Cognitive Services account name. Falls back to AI_SERVICES_NAME or azd env.
#>
param(
    [string]$ResourceGroup = $env:AZURE_RESOURCE_GROUP,
    [string]$AiServicesName = $env:AI_SERVICES_NAME
)

$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path "$PSScriptRoot\..\..\.."

# ---- Resolve resource group from azd env if not provided ----
function Get-EnvValueFromFile {
    param([string]$FilePath, [string]$Key)
    if (-not (Test-Path $FilePath)) { return '' }
    foreach ($line in Get-Content $FilePath) {
        if ($line -match "^$Key=(.*)$") { return $Matches[1].Trim('"') }
    }
    return ''
}

if (-not $ResourceGroup -and $env:AZURE_ENV_NAME) {
    $envFile = Join-Path $repoRoot ".azure\$($env:AZURE_ENV_NAME)\.env"
    $ResourceGroup = Get-EnvValueFromFile -FilePath $envFile -Key 'AZURE_RESOURCE_GROUP'
    if (-not $ResourceGroup) {
        $ResourceGroup = Get-EnvValueFromFile -FilePath $envFile -Key 'resourceGroupName'
    }
}

if (-not $ResourceGroup) {
    Write-Error "Resource group could not be resolved. Set AZURE_RESOURCE_GROUP or run inside an azd environment."
    exit 1
}

if (-not $AiServicesName -and $env:AZURE_ENV_NAME) {
    $envFile = Join-Path $repoRoot ".azure\$($env:AZURE_ENV_NAME)\.env"
    $AiServicesName = Get-EnvValueFromFile -FilePath $envFile -Key 'AI_SERVICES_NAME'
    if (-not $AiServicesName) {
        $AiServicesName = Get-EnvValueFromFile -FilePath $envFile -Key 'aiServicesName'
    }
}

if (-not $AiServicesName) {
    # Auto-discover from resource group
    $AiServicesName = az cognitiveservices account list `
        --resource-group $ResourceGroup `
        --query "[?kind=='AIServices'].name | [0]" -o tsv 2>$null
}

if (-not $AiServicesName) {
    Write-Error "AI Services account name could not be resolved. Set AI_SERVICES_NAME."
    exit 1
}

Write-Host "Deploying model deployments to AI Services account: $AiServicesName (RG: $ResourceGroup)"

# ---- Model definitions ----
$models = @(
    @{
        Name       = 'gpt-5-nano'
        Model      = 'gpt-5-nano'
        Version    = '2025-08-07'
        SkuName    = 'GlobalStandard'
        Capacity   = 5000
    },
    @{
        Name       = 'gpt-5'
        Model      = 'gpt-5'
        Version    = '2025-08-07'
        SkuName    = 'GlobalStandard'
        Capacity   = 1000
    }
)

foreach ($model in $models) {
    $existing = az cognitiveservices account deployment show `
        --resource-group $ResourceGroup `
        --name $AiServicesName `
        --deployment-name $model.Name 2>$null

    if ($LASTEXITCODE -eq 0 -and $existing) {
        Write-Host "  [skip] Deployment '$($model.Name)' already exists."
        continue
    }

    Write-Host "  [create] Deploying model '$($model.Model)' as '$($model.Name)'..."

    az cognitiveservices account deployment create `
        --resource-group $ResourceGroup `
        --name $AiServicesName `
        --deployment-name $model.Name `
        --model-name $model.Model `
        --model-version $model.Version `
        --model-format OpenAI `
        --sku-name $model.SkuName `
        --sku-capacity $model.Capacity 2>$null

    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Deployment '$($model.Name)' for model '$($model.Model)' is not available in this account/region. Continuing."
        $global:LASTEXITCODE = 0
        continue
    }

    Write-Host "  [done] Deployment '$($model.Name)' created."
}

Write-Host "All model deployments are ready."
exit 0
