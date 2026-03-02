#!/usr/bin/env pwsh
<#!
.SYNOPSIS
    Ensures a Microsoft Entra app registration exists for the UI and writes
    its identifiers into the azd environment.

.DESCRIPTION
    This script is intended to run as an azd postprovision hook. It creates
    or updates a single-tenant app registration with SPA redirect URIs, then
    writes the following values into azd env:
      - NEXT_PUBLIC_ENTRA_CLIENT_ID
      - NEXT_PUBLIC_ENTRA_TENANT_ID
      - ENTRA_CLIENT_ID
      - ENTRA_TENANT_ID

    The script is idempotent and safe to rerun.
#>
param(
    [string]$EnvironmentName = $(if ($env:AZURE_ENV_NAME) { $env:AZURE_ENV_NAME } else { 'dev' }),
    [string]$DisplayName,
    [switch]$FailOnError = $false
)

$ErrorActionPreference = 'Stop'

function Get-AzdValues {
    param([string]$EnvName)

    $content = azd env get-values -e $EnvName 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $content) {
        throw "Failed to read azd env values for environment '$EnvName'."
    }

    $map = @{}
    foreach ($line in $content) {
        if ($line -match '^\s*([^=\s]+)=(.*)$') {
            $key = $Matches[1].Trim()
            $value = $Matches[2].Trim().Trim('"')
            $map[$key] = $value
        }
    }
    return $map
}

function First-Value {
    param(
        [hashtable]$Map,
        [string[]]$Keys,
        [string]$DefaultValue = ''
    )

    foreach ($key in $Keys) {
        if ($Map.ContainsKey($key) -and $Map[$key]) {
            return "$($Map[$key])"
        }
    }
    return $DefaultValue
}

function Save-AzdValue {
    param(
        [string]$EnvName,
        [string]$Key,
        [string]$Value
    )

    azd env set $Key $Value -e $EnvName | Out-Null
}

function Set-SpaRedirectUris {
    param(
        [string]$AppId,
        [string[]]$RedirectUris
    )

    $objectId = az ad app show --id $AppId --query id -o tsv 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $objectId) {
        throw "Failed resolving object id for Entra app registration '$AppId'."
    }

    $payload = @{ spa = @{ redirectUris = $RedirectUris } } | ConvertTo-Json -Compress -Depth 6
    $payloadPath = Join-Path $env:TEMP ("entra-spa-redirects-{0}.json" -f [System.Guid]::NewGuid())
    Set-Content -Path $payloadPath -Value $payload -Encoding utf8

    try {
        az rest `
            --method PATCH `
            --uri "https://graph.microsoft.com/v1.0/applications/$objectId" `
            --headers "Content-Type=application/json" `
            --body "@$payloadPath" 1>$null 2>$null

        if ($LASTEXITCODE -ne 0) {
            throw "Failed updating SPA redirect URIs for Entra app registration '$AppId'."
        }
    }
    finally {
        Remove-Item -Path $payloadPath -Force -ErrorAction SilentlyContinue
    }
}

function Invoke-Maybe {
    param([scriptblock]$Action)

    try {
        & $Action
    }
    catch {
        if ($FailOnError) {
            throw
        }
        Write-Warning $_
    }
}

Invoke-Maybe {
    $values = Get-AzdValues -EnvName $EnvironmentName

    $projectName = First-Value -Map $values -Keys @('projectName', 'PROJECT_NAME') -DefaultValue 'holidaypeakhub'
    $environment = First-Value -Map $values -Keys @('environment', 'ENVIRONMENT') -DefaultValue $EnvironmentName
    $swaHost = First-Value -Map $values -Keys @('staticWebAppDefaultHostname', 'STATIC_WEB_APP_DEFAULT_HOSTNAME', 'NEXT_PUBLIC_APP_URL')

    if (-not $DisplayName) {
        $DisplayName = "$projectName-$environment-ui"
    }

    $tenantId = az account show --query tenantId -o tsv 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $tenantId) {
        throw 'Unable to determine Azure tenant id from current az login.'
    }

    $redirectUris = @(
        'http://localhost:3000/auth/callback'
        'http://localhost:3000'
    )

    if ($swaHost -and -not $swaHost.StartsWith('http')) {
        $swaHost = "https://$swaHost"
    }
    if ($swaHost) {
        $swaHostTrimmed = $swaHost.TrimEnd('/')
        $redirectUris += @(
            "$swaHostTrimmed/auth/callback"
            $swaHostTrimmed
        )
    }

    $redirectUris = $redirectUris | Select-Object -Unique

    Write-Host "Ensuring Entra UI app registration '$DisplayName'..."

    $existingAppId = az ad app list --display-name $DisplayName --query '[0].appId' -o tsv 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw 'Failed querying Entra applications. Ensure directory read/write permissions for this principal.'
    }

    if (-not $existingAppId) {
        $createdAppId = az ad app create `
            --display-name $DisplayName `
            --sign-in-audience AzureADMyOrg `
            --query appId -o tsv 2>$null

        if ($LASTEXITCODE -ne 0 -or -not $createdAppId) {
            throw "Failed creating Entra app registration '$DisplayName'."
        }
        $appId = $createdAppId
        Set-SpaRedirectUris -AppId $appId -RedirectUris $redirectUris
        Write-Host "  [create] Created Entra app with client id: $appId"
    }
    else {
        Set-SpaRedirectUris -AppId $existingAppId -RedirectUris $redirectUris
        $appId = $existingAppId
        Write-Host "  [update] Updated Entra app redirect URIs for client id: $appId"
    }

    Save-AzdValue -EnvName $EnvironmentName -Key 'NEXT_PUBLIC_ENTRA_CLIENT_ID' -Value $appId
    Save-AzdValue -EnvName $EnvironmentName -Key 'NEXT_PUBLIC_ENTRA_TENANT_ID' -Value $tenantId
    Save-AzdValue -EnvName $EnvironmentName -Key 'ENTRA_CLIENT_ID' -Value $appId
    Save-AzdValue -EnvName $EnvironmentName -Key 'ENTRA_TENANT_ID' -Value $tenantId

    Write-Host 'Entra UI app registration is ready and azd env values were updated.'
}