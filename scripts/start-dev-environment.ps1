#!/usr/bin/env pwsh
# Start dev environment resources stopped by MCAPSGov nightly automation.
# Run this when you begin your work session.

param(
    [string]$ResourceGroup  = "holidaypeakhub405-dev-rg",
    [string]$AksCluster     = "holidaypeakhub405-dev-aks",
    [string]$PostgresServer = "holidaypeakhub405-dev-postgres",
    [string]$CrudIdentity   = "holidaypeakhub405-dev-crud-identity"
)

$ErrorActionPreference = "Continue"

# Start PostgreSQL FIRST — AKS pods (CRUD) depend on it being ready.
# If AKS starts before PostgreSQL, the CRUD pod fails its readiness probe
# and requires a manual rollout restart.

Write-Host "Checking PostgreSQL server state..." -ForegroundColor Cyan
$pgState = az postgres flexible-server show -g $ResourceGroup -n $PostgresServer --query "state" -o tsv 2>&1
if ($pgState -eq "Stopped") {
    Write-Host "PostgreSQL server is stopped. Starting..." -ForegroundColor Yellow
    az postgres flexible-server start -g $ResourceGroup -n $PostgresServer
    Write-Host "PostgreSQL server start issued. Waiting for Ready state..." -ForegroundColor Yellow
}

# Poll until PostgreSQL reports Ready before proceeding to AKS.
$maxAttempts = 30
$attempt = 0
do {
    $attempt++
    $pgState = az postgres flexible-server show -g $ResourceGroup -n $PostgresServer --query "state" -o tsv 2>&1
    if ($pgState -eq "Ready") {
        Write-Host "PostgreSQL server is Ready." -ForegroundColor Green
        break
    }
    Write-Host "  PostgreSQL state: $pgState (attempt $attempt/$maxAttempts)..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
} while ($attempt -lt $maxAttempts)

if ($pgState -ne "Ready") {
    Write-Host "PostgreSQL did not reach Ready state after $maxAttempts attempts. Aborting." -ForegroundColor Red
    exit 1
}

# MCAPSGov nightly automation can disable Entra AD authentication on PostgreSQL.
# The CRUD service uses workload identity (Entra token) to connect, so if AD auth
# is disabled the readiness probe returns 503 and the entire CRUD namespace is down.
Write-Host "Checking PostgreSQL Entra AD authentication..." -ForegroundColor Cyan
$authConfig = az postgres flexible-server show -g $ResourceGroup -n $PostgresServer --query "authConfig" -o json 2>&1 | ConvertFrom-Json
if ($authConfig.activeDirectoryAuth -ne "Enabled") {
    Write-Host "Entra AD auth is Disabled — re-enabling..." -ForegroundColor Yellow
    az postgres flexible-server update -g $ResourceGroup -n $PostgresServer --microsoft-entra-auth Enabled 2>&1 | Out-Null
    Write-Host "Entra AD auth re-enabled." -ForegroundColor Green

    # Verify the CRUD identity is registered as an AD admin (may have been dropped).
    $identityOid = az identity show -g $ResourceGroup -n $CrudIdentity --query "principalId" -o tsv 2>&1
    $admins = az postgres flexible-server microsoft-entra-admin list -g $ResourceGroup -s $PostgresServer -o json 2>&1 | ConvertFrom-Json
    $hasAdmin = $admins | Where-Object { $_.objectId -eq $identityOid }
    if (-not $hasAdmin) {
        Write-Host "CRUD identity not found in AD admins — registering..." -ForegroundColor Yellow
        az postgres flexible-server microsoft-entra-admin create `
            -g $ResourceGroup -s $PostgresServer `
            --display-name $CrudIdentity `
            --object-id $identityOid `
            --type ServicePrincipal 2>&1 | Out-Null
        Write-Host "CRUD identity registered as PostgreSQL Entra admin." -ForegroundColor Green
    } else {
        Write-Host "CRUD identity is registered as PostgreSQL Entra admin." -ForegroundColor Green
    }
} else {
    Write-Host "PostgreSQL Entra AD auth is Enabled." -ForegroundColor Green
}

Write-Host "Checking AKS cluster power state..." -ForegroundColor Cyan
$aksState = az aks show -g $ResourceGroup -n $AksCluster --query "powerState.code" -o tsv 2>&1
if ($aksState -eq "Stopped") {
    Write-Host "AKS cluster is stopped. Starting..." -ForegroundColor Yellow
    az aks start -g $ResourceGroup -n $AksCluster
    Write-Host "AKS cluster started." -ForegroundColor Green
} else {
    Write-Host "AKS cluster is already running." -ForegroundColor Green
}

# After AKS start (or if Entra auth was just re-enabled), CRUD pods may be stuck
# in 0/1 Ready because the readiness probe failed before Postgres auth was fixed.
# A rollout restart forces fresh pods that acquire new Entra tokens.
Write-Host "Checking CRUD namespace pod readiness..." -ForegroundColor Cyan
$unreadyPods = kubectl get pods -n holiday-peak-crud --no-headers 2>&1 | Select-String "0/1"
if ($unreadyPods) {
    Write-Host "Unready CRUD pods detected — rolling restart..." -ForegroundColor Yellow
    kubectl rollout restart deployment crud-service-crud-service -n holiday-peak-crud 2>&1 | Out-Null
    kubectl rollout status deployment crud-service-crud-service -n holiday-peak-crud --timeout=120s 2>&1 | Out-Null
    kubectl rollout restart deployment apim-proxy -n holiday-peak-crud 2>&1 | Out-Null
    kubectl rollout status deployment apim-proxy -n holiday-peak-crud --timeout=90s 2>&1 | Out-Null
    Write-Host "CRUD namespace pods restarted." -ForegroundColor Green
} else {
    Write-Host "All CRUD pods are ready." -ForegroundColor Green
}

Write-Host "Dev environment ready." -ForegroundColor Cyan
