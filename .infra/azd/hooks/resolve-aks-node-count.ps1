#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Queries Azure VM SKU availability-zone support for the AKS node VM size in the
    target region and sets aksNodeCount and aksAvailabilityZones azd parameters.

.DESCRIPTION
    For non-prod environments the AKS node pool initial count should match the
    number of availability zones the chosen VM SKU supports so the scheduler can
    spread pods evenly.  If the SKU has zone restrictions (or none at all) the
    count falls back to 1.

    The hook writes both aksNodeCount (int) and aksAvailabilityZones (JSON array)
    into the azd environment so Bicep receives them during provisioning.
#>
param(
    [string]$Environment = $(if ($env:AZURE_ENV_NAME) { $env:AZURE_ENV_NAME } else { '' }),
    [string]$VmSize = 'Standard_D8ds_v5'
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($Environment)) {
    throw "Environment must be provided via -Environment or AZURE_ENV_NAME."
}

# ---------------------------------------------------------------------------
# Resolve target location from the azd environment
# ---------------------------------------------------------------------------
$location = ''
$rawValues = azd env get-values -e "$Environment" 2>$null
foreach ($line in $rawValues) {
    if ($line -match '^AZURE_LOCATION=(.*)$') {
        $location = $Matches[1].Trim('"').Trim("'")
    }
}
if ([string]::IsNullOrWhiteSpace($location)) {
    $location = 'westus2'
    Write-Host "AZURE_LOCATION not found in azd env; defaulting to '$location'."
}

# ---------------------------------------------------------------------------
# Resolve environment tier — skip for prod (Bicep uses hardcoded counts)
# ---------------------------------------------------------------------------
$envTier = ''
foreach ($line in $rawValues) {
    if ($line -match '^environment=(.*)$') {
        $envTier = $Matches[1].Trim('"').Trim("'")
    }
}
if ($envTier -eq 'prod') {
    Write-Host "Production environment detected — skipping AKS node count override (Bicep uses prod defaults)."
    exit 0
}

# ---------------------------------------------------------------------------
# Query VM SKU zone availability
# ---------------------------------------------------------------------------
Write-Host "Querying availability zones for VM SKU '$VmSize' in region '$location'..."

$skuJson = az vm list-skus -l $location --size $VmSize --resource-type virtualMachines --output json 2>$null
if (-not $skuJson) {
    Write-Host "WARNING: Unable to query VM SKUs. Falling back to aksNodeCount=1, aksAvailabilityZones=[1,2,3]."
    azd env set aksNodeCount '1' -e "$Environment"
    azd env set aksAvailabilityZones '[1,2,3]' -e "$Environment"
    exit 0
}

$skus = $skuJson | ConvertFrom-Json
$matchedSku = $skus | Where-Object { $_.name -eq $VmSize } | Select-Object -First 1

if (-not $matchedSku) {
    Write-Host "WARNING: VM SKU '$VmSize' not found in region '$location'. Falling back to aksNodeCount=1, aksAvailabilityZones=[1,2,3]."
    azd env set aksNodeCount '1' -e "$Environment"
    azd env set aksAvailabilityZones '[1,2,3]' -e "$Environment"
    exit 0
}

# Check for zone restrictions
$zoneRestrictions = $matchedSku.restrictions | Where-Object { $_.type -eq 'Zone' }
$allZones = @()
if ($matchedSku.locationInfo) {
    foreach ($locInfo in $matchedSku.locationInfo) {
        if ($locInfo.zones) {
            $allZones += $locInfo.zones
        }
    }
}

if ($zoneRestrictions) {
    # Remove restricted zones from available zones
    $restrictedZones = @()
    foreach ($restriction in $zoneRestrictions) {
        if ($restriction.restrictionInfo -and $restriction.restrictionInfo.zones) {
            $restrictedZones += $restriction.restrictionInfo.zones
        }
    }
    $availableZones = $allZones | Where-Object { $_ -notin $restrictedZones }
} else {
    $availableZones = $allZones
}

$zoneCount = ($availableZones | Sort-Object -Unique).Count

if ($zoneCount -gt 0) {
    $nodeCount = $zoneCount
    $sortedZones = $availableZones | Sort-Object -Unique
    $zonesJson = '[' + (($sortedZones | ForEach-Object { $_.ToString() }) -join ',') + ']'
    Write-Host "VM SKU '$VmSize' available in $zoneCount zone(s) in '$location': $zonesJson. Setting aksNodeCount=$nodeCount."
} else {
    $nodeCount = 1
    $zonesJson = '[1,2,3]'
    Write-Host "No availability zone info found for '$VmSize' in '$location'. Setting aksNodeCount=1, aksAvailabilityZones=$zonesJson."
}

azd env set aksNodeCount "$nodeCount" -e "$Environment"
azd env set aksAvailabilityZones "$zonesJson" -e "$Environment"
Write-Host "aksNodeCount=$nodeCount, aksAvailabilityZones=$zonesJson for environment '$Environment'."
