#!/usr/bin/env pwsh
# Start dev environment resources stopped by MCAPSGov nightly automation.
# Run this when you begin your work session.

param(
    [string]$ResourceGroup = "holidaypeakhub405-dev-rg",
    [string]$AksCluster    = "holidaypeakhub405-dev-aks",
    [string]$PostgresServer = "holidaypeakhub405-dev-postgres"
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

Write-Host "Checking AKS cluster power state..." -ForegroundColor Cyan
$aksState = az aks show -g $ResourceGroup -n $AksCluster --query "powerState.code" -o tsv 2>&1
if ($aksState -eq "Stopped") {
    Write-Host "AKS cluster is stopped. Starting..." -ForegroundColor Yellow
    az aks start -g $ResourceGroup -n $AksCluster
    Write-Host "AKS cluster started." -ForegroundColor Green
} else {
    Write-Host "AKS cluster is already running." -ForegroundColor Green
}

Write-Host "Dev environment ready." -ForegroundColor Cyan
