#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Ensures the shared Azure AI Search index exists after the search service is reachable.

.DESCRIPTION
    This script runs as an azd postprovision hook. It avoids nested ARM timing
    issues by creating or updating the shared catalog index only after the Azure
    AI Search service is available via the management plane.
#>
param(
    [string]$ResourceGroup = $env:AZURE_RESOURCE_GROUP,
    [string]$SearchServiceName = $env:AI_SEARCH_NAME,
    [string]$IndexName = $env:AI_SEARCH_INDEX
)

$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path "$PSScriptRoot\..\..\.."

function Get-EnvValueFromFile {
    param([string]$FilePath, [string]$Key)
    if (-not (Test-Path $FilePath)) { return '' }
    foreach ($line in Get-Content $FilePath) {
        if ($line -match "^$Key=(.*)$") { return $Matches[1].Trim('"') }
    }
    return ''
}

function Resolve-FromAzdEnv {
    param([string[]]$Keys)
    if (-not $env:AZURE_ENV_NAME) { return '' }

    $envFile = Join-Path $repoRoot ".azure\$($env:AZURE_ENV_NAME)\.env"
    foreach ($key in $Keys) {
        $value = Get-EnvValueFromFile -FilePath $envFile -Key $key
        if ($value) { return $value }
    }

    return ''
}

if (-not $ResourceGroup) {
    $ResourceGroup = Resolve-FromAzdEnv -Keys @('AZURE_RESOURCE_GROUP', 'resourceGroupName')
}

if (-not $SearchServiceName) {
    $SearchServiceName = Resolve-FromAzdEnv -Keys @('AI_SEARCH_NAME', 'aiSearchName')
}

if (-not $IndexName) {
    $IndexName = Resolve-FromAzdEnv -Keys @('AI_SEARCH_INDEX', 'aiSearchIndexName')
}

if (-not $ResourceGroup) {
    Write-Error 'Resource group could not be resolved. Set AZURE_RESOURCE_GROUP or run inside an azd environment.'
    exit 1
}

if (-not $SearchServiceName) {
    $SearchServiceName = az resource list --resource-group $ResourceGroup --resource-type Microsoft.Search/searchServices --query '[0].name' -o tsv 2>$null
}

if (-not $SearchServiceName) {
    Write-Error 'Azure AI Search service name could not be resolved. Set AI_SEARCH_NAME.'
    exit 1
}

if (-not $IndexName) {
    $IndexName = 'catalog-products'
}

Write-Host "Ensuring Azure AI Search index '$IndexName' on service '$SearchServiceName' (RG: $ResourceGroup)"

$serviceId = ''
for ($attempt = 1; $attempt -le 18; $attempt++) {
    $serviceId = az resource show --resource-group $ResourceGroup --resource-type Microsoft.Search/searchServices --name $SearchServiceName --query id -o tsv 2>$null
    if ($LASTEXITCODE -eq 0 -and $serviceId) {
        break
    }

    if ($attempt -eq 18) {
        Write-Error "Azure AI Search service '$SearchServiceName' was not reachable after waiting for postprovision readiness."
        exit 1
    }

    Start-Sleep -Seconds 10
}

$searchEndpoint = az resource show --ids $serviceId --query properties.endpoint -o tsv
$adminKey = az rest --only-show-errors --method post --uri "https://management.azure.com$serviceId/listAdminKeys?api-version=2022-09-01" --query primaryKey -o tsv
$indexUri = "$searchEndpoint/indexes('$IndexName')?api-version=2024-07-01"

$indexDefinition = @{
    name = $IndexName
    fields = @(
        @{ name = 'id'; type = 'Edm.String'; key = $true; filterable = $true; searchable = $false }
        @{ name = 'sku'; type = 'Edm.String'; searchable = $true; filterable = $true }
        @{ name = 'title'; type = 'Edm.String'; searchable = $true }
        @{ name = 'description'; type = 'Edm.String'; searchable = $true }
        @{ name = 'content'; type = 'Edm.String'; searchable = $true }
        @{ name = 'category'; type = 'Edm.String'; searchable = $true; filterable = $true }
        @{ name = 'brand'; type = 'Edm.String'; searchable = $true; filterable = $true }
        @{ name = 'availability'; type = 'Edm.String'; filterable = $true }
        @{ name = 'price'; type = 'Edm.Double'; filterable = $true; sortable = $true }
    )
} | ConvertTo-Json -Depth 8 -Compress

for ($attempt = 1; $attempt -le 12; $attempt++) {
    try {
        Invoke-RestMethod -Method Put -Uri $indexUri -Headers @{ 'api-key' = $adminKey; 'Content-Type' = 'application/json' } -Body $indexDefinition | Out-Null
        Write-Host "Azure AI Search index '$IndexName' is ready."
        exit 0
    }

    catch {
        if ($attempt -eq 12) {
            Write-Error "Failed to create or update Azure AI Search index '$IndexName' on service '$SearchServiceName': $($_.Exception.Message)"
            exit 1
        }
    }

    Start-Sleep -Seconds 10
}