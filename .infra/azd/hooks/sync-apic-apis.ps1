#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Imports APIs from APIM into Azure API Center for centralized governance and discovery.

.DESCRIPTION
    Runs after APIM sync to import all registered APIs into API Center.
    Uses az apic import-from-apim to bulk-import APIs, then applies
    domain metadata (CRM, eCommerce, Inventory, Logistics, Product Management,
    Truth Layer, Search) for discoverability.
#>
param(
    [string]$ResourceGroup = $env:AZURE_RESOURCE_GROUP,
    [string]$ApicName = $env:APIC_NAME,
    [string]$ApimName = $env:APIM_NAME,
    [string]$SubscriptionId = $env:AZURE_SUBSCRIPTION_ID,
    [switch]$Preview
)

$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Resolve names from resource group when not provided
# ---------------------------------------------------------------------------
if (-not $ResourceGroup) {
    Write-Error 'AZURE_RESOURCE_GROUP is required.'
    exit 1
}

if (-not $ApicName) {
    $apicResources = az resource list --resource-group $ResourceGroup --resource-type 'Microsoft.ApiCenter/services' --query '[].name' -o tsv 2>$null
    if ($apicResources) {
        $ApicName = ($apicResources -split "`n")[0].Trim()
        Write-Host "Resolved API Center name: $ApicName"
    }
    else {
        Write-Error 'No API Center found in resource group. Provision infrastructure first.'
        exit 1
    }
}

if (-not $ApimName) {
    $apimResources = az resource list --resource-group $ResourceGroup --resource-type 'Microsoft.ApiManagement/service' --query '[].name' -o tsv 2>$null
    if ($apimResources) {
        $ApimName = ($apimResources -split "`n")[0].Trim()
        Write-Host "Resolved APIM name: $ApimName"
    }
    else {
        Write-Error 'No API Management found in resource group. Provision infrastructure first.'
        exit 1
    }
}

if (-not $SubscriptionId) {
    $SubscriptionId = az account show --query 'id' -o tsv 2>$null
    if (-not $SubscriptionId) {
        Write-Error 'Unable to resolve subscription ID. Ensure Azure CLI is logged in.'
        exit 1
    }
}

# ---------------------------------------------------------------------------
# Ensure apic extension is available
# ---------------------------------------------------------------------------
$apicExtension = az extension list --query "[?name=='apic-extension'].name" -o tsv 2>$null
if (-not $apicExtension) {
    Write-Host 'Installing apic-extension CLI extension...'
    az extension add --name apic-extension --yes 2>$null
}

# ---------------------------------------------------------------------------
# Domain mapping for API metadata
# ---------------------------------------------------------------------------
$domainMap = @{
    'crm'                = 'CRM'
    'ecommerce'          = 'eCommerce'
    'inventory'          = 'Inventory'
    'logistics'          = 'Logistics'
    'product-management' = 'Product Management'
    'truth'              = 'Truth Layer'
    'search'             = 'Search'
}

function Get-ApiDomain {
    param([string]$ApiId)
    foreach ($prefix in $domainMap.Keys) {
        if ($ApiId -like "$prefix*" -or $ApiId -like "agent-$prefix*") {
            return $domainMap[$prefix]
        }
    }
    if ($ApiId -eq 'crud' -or $ApiId -eq 'crud-service') {
        return 'Platform'
    }
    if ($ApiId -eq 'aoai-gateway') {
        return 'AI Gateway'
    }
    return 'Other'
}

# ---------------------------------------------------------------------------
# Import APIs from APIM into API Center
# ---------------------------------------------------------------------------
$apimResourceId = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.ApiManagement/service/$ApimName"

Write-Host "Importing APIs from APIM '$ApimName' into API Center '$ApicName'..."
Write-Host "  APIM Resource ID: $apimResourceId"

if ($Preview) {
    Write-Host '[preview] Would import all APIs from APIM into API Center.'
    Write-Host "[preview] APIM: $ApimName -> APIC: $ApicName"
    exit 0
}

# Import all APIs from APIM (idempotent — updates existing, adds new)
$importResult = az apic import-from-apim `
    --resource-group $ResourceGroup `
    --service-name $ApicName `
    --source-resource-ids "$apimResourceId/apis/*" `
    --only-show-errors 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Warning "import-from-apim returned non-zero. Output: $importResult"
    Write-Warning 'Falling back to individual API registration...'

    $apimApis = az apim api list --resource-group $ResourceGroup --service-name $ApimName --query '[].{id:name, display:properties.displayName, path:properties.path}' -o json 2>$null | ConvertFrom-Json
    if (-not $apimApis) {
        Write-Error 'Failed to list APIM APIs for fallback registration.'
        exit 1
    }

    foreach ($api in $apimApis) {
        if ($api.id -eq 'echo-api') { continue }
        $domain = Get-ApiDomain -ApiId $api.id
        Write-Host "  Registering API: $($api.id) (domain: $domain)"

        az apic api register `
            --resource-group $ResourceGroup `
            --service-name $ApicName `
            --api-id $api.id `
            --title $api.display `
            --type rest `
            --only-show-errors 2>$null

        if ($LASTEXITCODE -ne 0) {
            Write-Warning "  Failed to register API: $($api.id)"
        }
    }
}
else {
    Write-Host 'API import from APIM completed successfully.'
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
$registeredApis = az apic api list --resource-group $ResourceGroup --service-name $ApicName --query 'length(@)' -o tsv 2>$null
Write-Host "API Center '$ApicName' now has $registeredApis registered APIs."
Write-Host 'API Center sync completed.'
