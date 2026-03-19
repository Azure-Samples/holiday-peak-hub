#!/usr/bin/env pwsh
param()

$ErrorActionPreference = 'Stop'

if ($env:GITHUB_ACTIONS -ne 'true') {
    exit 0
}

if ([string]::IsNullOrWhiteSpace($env:AZURE_CLIENT_ID) -or [string]::IsNullOrWhiteSpace($env:AZURE_TENANT_ID)) {
    exit 0
}

if ([string]::IsNullOrWhiteSpace($env:ACTIONS_ID_TOKEN_REQUEST_URL) -or [string]::IsNullOrWhiteSpace($env:ACTIONS_ID_TOKEN_REQUEST_TOKEN)) {
    Write-Error 'GitHub OIDC token request context is unavailable.'
    exit 1
}

$requiredCommands = @('az', 'curl', 'python')
foreach ($command in $requiredCommands) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
        Write-Error "Required command '$command' is not available on PATH."
        exit 1
    }
}

$oidcUrl = & python -c @"
import os
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

parts = list(urlparse(os.environ['ACTIONS_ID_TOKEN_REQUEST_URL']))
query = dict(parse_qsl(parts[4], keep_blank_values=True))
query['audience'] = 'api://AzureADTokenExchange'
parts[4] = urlencode(query)
print(urlunparse(parts))
"@

$oidcToken = ''
for ($attempt = 1; $attempt -le 3; $attempt++) {
    try {
        $response = & curl -fsSL -H "Authorization: bearer $($env:ACTIONS_ID_TOKEN_REQUEST_TOKEN)" "$oidcUrl"
        $payload = $response | ConvertFrom-Json
        if ($payload.value) {
            $oidcToken = $payload.value
            break
        }
    }
    catch {
        Write-Host "Failed to request or parse GitHub OIDC token on attempt $attempt."
    }

    Start-Sleep -Seconds 2
}

if (-not $oidcToken) {
    Write-Error 'Unable to refresh Azure CLI login from GitHub OIDC after multiple attempts.'
    exit 1
}

az login `
    --service-principal `
    --username "$($env:AZURE_CLIENT_ID)" `
    --tenant "$($env:AZURE_TENANT_ID)" `
    --federated-token "$oidcToken" `
    --allow-no-subscriptions `
    --output none | Out-Null

if (-not [string]::IsNullOrWhiteSpace($env:AZURE_SUBSCRIPTION_ID)) {
    az account set --subscription "$($env:AZURE_SUBSCRIPTION_ID)"
}
