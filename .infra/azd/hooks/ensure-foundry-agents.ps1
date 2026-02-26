#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Ensures all 42 V2 Foundry agents (21 services × 2 roles) are provisioned
    by calling each service's POST /foundry/agents/ensure endpoint.

.DESCRIPTION
    Iterates over all AKS-hosted agent services, resolves their in-cluster URL,
    and calls the /foundry/agents/ensure endpoint. Supports both in-cluster
    (kubectl port-forward) and direct URL modes.

    The script is idempotent — it creates agents only if they don't already exist.

.PARAMETER Namespace
    Kubernetes namespace. Defaults to K8S_NAMESPACE or 'holiday-peak'.

.PARAMETER UsePortForward
    If set, uses kubectl port-forward to reach services. Otherwise expects
    services to be reachable via direct URLs (e.g., via Ingress or APIM).

.PARAMETER BaseUrl
    Direct base URL for services (e.g., https://api.example.com/agents).
    Each service is called at $BaseUrl/$ServiceName/foundry/agents/ensure.

.PARAMETER AzureYamlPath
    Path to azure.yaml. Used to discover service names.

.PARAMETER MaxRetries
    Number of retries per service if the ensure call fails. Default 3.
#>
param(
    [string]$Namespace = $(if ($env:K8S_NAMESPACE) { $env:K8S_NAMESPACE } else { 'holiday-peak' }),
    [switch]$UsePortForward,
    [string]$BaseUrl,
    [string]$AzureYamlPath,
    [int]$MaxRetries = 3
)

$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path "$PSScriptRoot\..\..\.."
if (-not $AzureYamlPath) {
    $AzureYamlPath = Join-Path $repoRoot 'azure.yaml'
}

# ---- Parse agent services from azure.yaml ----
function Get-AgentServices {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        throw "azure.yaml not found at: $Path"
    }

    $services = @()
    $inServices = $false
    $currentService = $null
    $currentHost = $null

    foreach ($line in Get-Content $Path) {
        if (-not $inServices) {
            if ($line -match '^services:\s*$') {
                $inServices = $true
            }
            continue
        }

        if ($line -match '^[^\s]') { break }

        if ($line -match '^\s{2}([a-z0-9\-]+):\s*$') {
            if ($currentService -and $currentHost -eq 'aks' -and $currentService -ne 'crud-service') {
                $services += $currentService
            }
            $currentService = $Matches[1]
            $currentHost = $null
            continue
        }

        if ($line -match '^\s{4}host:\s*(\S+)') {
            $currentHost = $Matches[1]
        }
    }

    if ($currentService -and $currentHost -eq 'aks' -and $currentService -ne 'crud-service') {
        $services += $currentService
    }

    return $services
}

# ---- Call ensure endpoint ----
function Invoke-EnsureEndpoint {
    param(
        [string]$ServiceName,
        [string]$Url,
        [int]$Retries
    )

    for ($attempt = 1; $attempt -le $Retries; $attempt++) {
        try {
            Write-Host "  [$ServiceName] Calling $Url (attempt $attempt/$Retries)..."
            $response = Invoke-RestMethod -Uri $Url -Method POST -ContentType 'application/json' -TimeoutSec 120
            Write-Host "  [$ServiceName] OK: fast=$($response.fast_agent_id), rich=$($response.rich_agent_id)"
            return $true
        }
        catch {
            $err = $_.Exception.Message
            Write-Warning "  [$ServiceName] Attempt $attempt failed: $err"
            if ($attempt -lt $Retries) {
                Start-Sleep -Seconds (5 * $attempt)
            }
        }
    }

    Write-Error "  [$ServiceName] FAILED after $Retries attempts."
    return $false
}

# ---- Main ----
$services = Get-AgentServices -Path $AzureYamlPath
Write-Host "Found $($services.Count) agent services to ensure."

$failed = @()
$portForwardJobs = @()

foreach ($svc in $services) {
    $url = $null

    if ($UsePortForward) {
        # Find a free local port
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
        $listener.Start()
        $localPort = $listener.LocalEndpoint.Port
        $listener.Stop()

        # Start port-forward in background
        $job = Start-Job -ScriptBlock {
            param($svc, $ns, $port)
            kubectl port-forward "svc/$svc" "${port}:8000" -n $ns 2>&1
        } -ArgumentList $svc, $Namespace, $localPort
        $portForwardJobs += $job

        Start-Sleep -Seconds 2
        $url = "http://localhost:$localPort/foundry/agents/ensure"
    }
    elseif ($BaseUrl) {
        $url = "$BaseUrl/$svc/foundry/agents/ensure"
    }
    else {
        # In-cluster direct call (assumes running from within cluster or with network access)
        $url = "http://$svc.$Namespace.svc.cluster.local:8000/foundry/agents/ensure"
    }

    $ok = Invoke-EnsureEndpoint -ServiceName $svc -Url $url -Retries $MaxRetries
    if (-not $ok) {
        $failed += $svc
    }

    # Clean up port-forward
    if ($UsePortForward -and $portForwardJobs.Count -gt 0) {
        $portForwardJobs[-1] | Stop-Job -PassThru | Remove-Job -Force
    }
}

Write-Host ""
Write-Host "=== Ensure Summary ==="
Write-Host "Total services: $($services.Count)"
Write-Host "Succeeded:      $($services.Count - $failed.Count)"
Write-Host "Failed:         $($failed.Count)"

if ($failed.Count -gt 0) {
    Write-Host ""
    Write-Host "Failed services:"
    $failed | ForEach-Object { Write-Host "  - $_" }
    exit 1
}

Write-Host ""
Write-Host "All $($services.Count * 2) Foundry agents are provisioned."
