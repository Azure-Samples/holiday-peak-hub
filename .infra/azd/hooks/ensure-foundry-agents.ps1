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
    Kubernetes namespace. Defaults to K8S_AGENTS_NAMESPACE or K8S_NAMESPACE or 'holiday-peak-agents'.

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
    [string]$Namespace = $(if ($env:K8S_AGENTS_NAMESPACE) { $env:K8S_AGENTS_NAMESPACE } elseif ($env:K8S_NAMESPACE) { $env:K8S_NAMESPACE } else { 'holiday-peak-agents' }),
    [switch]$UsePortForward,
    [string]$BaseUrl,
    [string]$AzureYamlPath,
    [string]$ChangedServices = $env:CHANGED_SERVICES,
    [int]$MaxRetries = 3,
    [bool]$FailOnError = $false
)

$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path "$PSScriptRoot\..\..\.."
if (-not $AzureYamlPath) {
    $AzureYamlPath = Join-Path $repoRoot 'azure.yaml'
}

$validateRenderedFoundryContract = if ($env:VALIDATE_RENDERED_FOUNDRY_CONTRACT) {
    [string]$env:VALIDATE_RENDERED_FOUNDRY_CONTRACT
}
else {
    'false'
}
$validateReadyAfterEnsure = if ($env:VALIDATE_READY_AFTER_ENSURE) {
    [string]$env:VALIDATE_READY_AFTER_ENSURE
}
else {
    'false'
}
$expectedFoundryStrictEnforcement = if ($env:EXPECTED_FOUNDRY_STRICT_ENFORCEMENT) {
    [string]$env:EXPECTED_FOUNDRY_STRICT_ENFORCEMENT
}
elseif ($env:FOUNDRY_STRICT_ENFORCEMENT) {
    [string]$env:FOUNDRY_STRICT_ENFORCEMENT
}
else {
    ''
}
$expectedFoundryAutoEnsureOnStartup = if ($env:EXPECTED_FOUNDRY_AUTO_ENSURE_ON_STARTUP) {
    [string]$env:EXPECTED_FOUNDRY_AUTO_ENSURE_ON_STARTUP
}
elseif ($env:FOUNDRY_AUTO_ENSURE_ON_STARTUP) {
    [string]$env:FOUNDRY_AUTO_ENSURE_ON_STARTUP
}
else {
    ''
}
$renderedManifestRoot = if ($env:RENDERED_MANIFEST_ROOT) {
    $env:RENDERED_MANIFEST_ROOT
}
else {
    Join-Path $repoRoot '.kubernetes\rendered'
}
$contractChecksEnabled =
    ($validateRenderedFoundryContract.Trim().ToLowerInvariant() -eq 'true') -or
    (-not [string]::IsNullOrWhiteSpace($expectedFoundryStrictEnforcement)) -or
    (-not [string]::IsNullOrWhiteSpace($expectedFoundryAutoEnsureOnStartup))

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
            $response = Invoke-WebRequest -Uri $Url -Method POST -ContentType 'application/json' -TimeoutSec 120 -SkipHttpErrorCheck
            $statusCode = [int]$response.StatusCode
            $payload = $null
            if (-not [string]::IsNullOrWhiteSpace([string]$response.Content)) {
                $payload = $response.Content | ConvertFrom-Json -AsHashtable
            }

            if ($statusCode -ne 200) {
                throw "HTTP $statusCode"
            }

            $results = if ($payload) { $payload.results } else { $null }
            $requiredRoles = @('fast', 'rich')
            $validStatuses = @('exists', 'found_by_name', 'created')
            $missing = @()

            foreach ($role in $requiredRoles) {
                $details = $results.$role
                if (-not $details) {
                    $missing += "${role}:missing"
                    continue
                }

                $status = [string]$details.status
                $agentId = [string]$details.agent_id
                if (($validStatuses -notcontains $status) -or [string]::IsNullOrWhiteSpace($agentId)) {
                    $missing += "${role}:$status"
                }
            }

            if ($missing.Count -gt 0) {
                throw "Ensure response incomplete ($($missing -join ', '))"
            }

            Write-Host "  [$ServiceName] OK: fast+rich roles resolved."
            if ($payload) {
                Write-Host ($payload | ConvertTo-Json -Depth 6 -Compress)
            }
            return [pscustomobject]@{
                Ok = $true
                HttpCode = $statusCode
                Payload = $payload
            }
        }
        catch {
            $err = $_.Exception.Message
            Write-Warning "  [$ServiceName] Attempt $attempt failed: $err"
            if ($attempt -lt $Retries) {
                Start-Sleep -Seconds (5 * $attempt)
            }
        }
    }

    Write-Warning "  [$ServiceName] FAILED after $Retries attempts."
    return [pscustomobject]@{
        Ok = $false
        HttpCode = 0
        Payload = $null
    }
}

function Normalize-ContractValue {
    param([string]$Value)

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return ''
    }

    return $Value.Trim().ToLowerInvariant()
}

function Test-BoolLike {
    param([string]$Value)

    return (Normalize-ContractValue $Value) -in @('1', 'true', 'yes')
}

function Resolve-DeploymentName {
    param(
        [Parameter(Mandatory = $true)][string]$ServiceKey,
        [Parameter(Mandatory = $true)][string]$Ns
    )

    $deploymentName = kubectl get deployment -n $Ns -l "app=$ServiceKey" -o jsonpath="{.items[0].metadata.name}" 2>$null
    if (-not $deploymentName) {
        throw "Deployment '$ServiceKey' not found in namespace '$Ns' with label app=$ServiceKey."
    }

    return [string]$deploymentName
}

function Get-EnvFromDeployment {
    param(
        [Parameter(Mandatory = $true)][string]$Deployment,
        [Parameter(Mandatory = $true)][string]$Namespace,
        [Parameter(Mandatory = $true)][string]$Name
    )

    $value = kubectl get deployment $Deployment -n $Namespace -o jsonpath="{.spec.template.spec.containers[0].env[?(@.name=='$Name')].value}" 2>$null
    return [string]$value
}

function Get-RenderedEnvValue {
    param(
        [Parameter(Mandatory = $true)][string]$ManifestPath,
        [Parameter(Mandatory = $true)][string]$Name
    )

    if (-not (Test-Path $ManifestPath)) {
        return ''
    }

    $content = Get-Content -Path $ManifestPath -Raw
    $escapedName = [regex]::Escape($Name)
    $pattern = '-\s*name:\s*' + $escapedName + '\s*(?:\r?\n)+\s*value:\s*["'']?([^"''\r\n]+)["'']?'
    $match = [regex]::Match($content, $pattern)
    if ($match.Success) {
        return $match.Groups[1].Value.Trim()
    }

    return ''
}

function Test-FoundryContract {
    param(
        [Parameter(Mandatory = $true)][string]$ServiceName,
        [Parameter(Mandatory = $true)][string]$DeploymentName
    )

    $contractFailed = $false
    $manifestPath = Join-Path (Join-Path $renderedManifestRoot $ServiceName) 'all.yaml'
    $contractKeys = @(
        @{ Name = 'FOUNDRY_STRICT_ENFORCEMENT'; Expected = $expectedFoundryStrictEnforcement },
        @{ Name = 'FOUNDRY_AUTO_ENSURE_ON_STARTUP'; Expected = $expectedFoundryAutoEnsureOnStartup }
    )

    foreach ($contractKey in $contractKeys) {
        $keyName = [string]$contractKey.Name
        $expectedValue = Normalize-ContractValue ([string]$contractKey.Expected)
        $liveValue = Normalize-ContractValue (Get-EnvFromDeployment -Deployment $DeploymentName -Namespace $Namespace -Name $keyName)
        $renderedValue = ''

        if (Test-BoolLike $validateRenderedFoundryContract) {
            if (-not (Test-Path $manifestPath)) {
                Write-Warning "  [$ServiceName] Rendered manifest missing for contract validation: $manifestPath"
                $contractFailed = $true
            }
            else {
                $renderedValue = Normalize-ContractValue (Get-RenderedEnvValue -ManifestPath $manifestPath -Name $keyName)
            }
        }

        $expectedDisplay = if ($expectedValue) { $expectedValue } else { '<unspecified>' }
        $liveDisplay = if ($liveValue) { $liveValue } else { '<missing>' }
        $renderedDisplay = if (Test-BoolLike $validateRenderedFoundryContract) {
            if ($renderedValue) { $renderedValue } else { '<missing>' }
        }
        else {
            '<not-checked>'
        }

        Write-Host "  [$ServiceName] Foundry contract $keyName => expected=$expectedDisplay rendered=$renderedDisplay live=$liveDisplay"

        if ($expectedValue -and $liveValue -ne $expectedValue) {
            Write-Warning "  [$ServiceName] Live deployment drift for ${keyName}: expected '$expectedValue', got '$liveDisplay'"
            $contractFailed = $true
        }

        if (Test-BoolLike $validateRenderedFoundryContract) {
            if (-not $renderedValue) {
                Write-Warning "  [$ServiceName] Rendered manifest missing $keyName in $manifestPath"
                $contractFailed = $true
            }

            if ($expectedValue -and $renderedValue -ne $expectedValue) {
                Write-Warning "  [$ServiceName] Rendered manifest drift for ${keyName}: expected '$expectedValue', got '$renderedDisplay'"
                $contractFailed = $true
            }

            if ($renderedValue -and $liveValue -and $renderedValue -ne $liveValue) {
                Write-Warning "  [$ServiceName] Rendered/live drift for ${keyName}: rendered '$renderedValue', live '$liveValue'"
                $contractFailed = $true
            }
        }
    }

    return -not $contractFailed
}

function Invoke-ReadyEndpoint {
    param(
        [Parameter(Mandatory = $true)][string]$ServiceName,
        [Parameter(Mandatory = $true)][string]$Url
    )

    try {
        $response = Invoke-WebRequest -Uri $Url -Method GET -TimeoutSec 60 -SkipHttpErrorCheck
        $statusCode = [int]$response.StatusCode
        $payload = $null
        if (-not [string]::IsNullOrWhiteSpace([string]$response.Content)) {
            try {
                $payload = $response.Content | ConvertFrom-Json -AsHashtable
            }
            catch {
                $payload = $null
            }
        }

        Write-Host "  [$ServiceName] /ready returned HTTP $statusCode"
        return [pscustomobject]@{
            HttpCode = $statusCode
            Payload = $payload
        }
    }
    catch {
        Write-Warning "  [$ServiceName] /ready request failed: $($_.Exception.Message)"
        return [pscustomobject]@{
            HttpCode = 0
            Payload = $null
        }
    }
}

function Test-ReadyContract {
    param(
        [Parameter(Mandatory = $true)][string]$ServiceName,
        [Parameter(Mandatory = $true)]$ReadyResult,
        [Parameter(Mandatory = $true)][bool]$EnsureOk
    )

    if ([int]$ReadyResult.HttpCode -ne 200) {
        if ($EnsureOk) {
            Write-Warning "  [$ServiceName] Ready/ensure mismatch: ensure resolved Foundry roles but /ready returned HTTP $($ReadyResult.HttpCode)"
        }
        else {
            Write-Warning "  [$ServiceName] /ready returned HTTP $($ReadyResult.HttpCode)"
        }
        return $false
    }

    if (-not $ReadyResult.Payload) {
        Write-Warning "  [$ServiceName] Invalid /ready payload: empty or non-JSON content"
        return $false
    }

    $status = [string]$ReadyResult.Payload['status']
    $foundryReady = [bool]$ReadyResult.Payload['foundry_ready']
    $foundryRequired = [bool]$ReadyResult.Payload['foundry_required']
    $issues = @()

    if ($status -ne 'ready') {
        $issues += "status=$(if ($status) { $status } else { 'missing' })"
    }
    if ($EnsureOk -and -not $foundryReady) {
        $issues += 'foundry_ready=false after successful ensure'
    }
    if ($EnsureOk -and (Test-BoolLike $expectedFoundryStrictEnforcement) -and -not $foundryRequired) {
        $issues += 'foundry_required=false despite strict contract'
    }
    if (((Test-BoolLike $expectedFoundryStrictEnforcement) -or (Test-BoolLike $expectedFoundryAutoEnsureOnStartup)) -and -not $foundryReady) {
        $issues += 'foundry_ready=false despite strict/auto contract'
    }
    if (-not $EnsureOk) {
        $issues += '/ready returned HTTP 200 even though ensure failed'
    }

    if ($issues.Count -gt 0) {
        $uniqueIssues = [string[]]($issues | Select-Object -Unique)
        Write-Warning "  [$ServiceName] Ready/ensure mismatch: $([string]::Join(', ', $uniqueIssues))"
        Write-Warning ($ReadyResult.Payload | ConvertTo-Json -Depth 6 -Compress)
        return $false
    }

    Write-Host "  [$ServiceName] /ready validated: foundry_required=$foundryRequired foundry_ready=$foundryReady"
    return $true
}

function Resolve-K8sServiceEndpoint {
    param(
        [Parameter(Mandatory = $true)][string]$ServiceKey,
        [Parameter(Mandatory = $true)][string]$Ns
    )

    $resolvedName = kubectl get svc -n $Ns -l "app=$ServiceKey" -o jsonpath="{.items[0].metadata.name}" 2>$null
    if (-not $resolvedName) {
        throw "Service '$ServiceKey' not found in namespace '$Ns' with label app=$ServiceKey."
    }

    $resolvedPort = kubectl get svc $resolvedName -n $Ns -o jsonpath="{.spec.ports[0].port}" 2>$null
    if (-not $resolvedPort) {
        $resolvedPort = '80'
    }

    return @{
        Name = $resolvedName
        Port = [string]$resolvedPort
    }
}

# ---- Main ----
$services = Get-AgentServices -Path $AzureYamlPath

if ($ChangedServices) {
    $changedServiceSet = $ChangedServices.Split(',') | ForEach-Object { $_.Trim() } | Where-Object { $_ }
    $services = @($services | Where-Object { $changedServiceSet -contains $_ })
}

if (-not $services -or $services.Count -eq 0) {
    Write-Host 'No matching changed agent services to ensure.'
    exit 0
}

Write-Host "Found $($services.Count) agent services to ensure."

$failed = @()
$portForwardJobs = @()

foreach ($svc in $services) {
    $url = $null
    $readyUrl = $null
    $resolved = $null
    $job = $null
    $serviceFailed = $false

    try {
        $resolved = Resolve-K8sServiceEndpoint -ServiceKey $svc -Ns $Namespace
    }
    catch {
        Write-Warning "  [$svc] Service resolution failed: $($_.Exception.Message)"
        $failed += $svc
        continue
    }

    if ($contractChecksEnabled) {
        try {
            $deploymentName = Resolve-DeploymentName -ServiceKey $svc -Ns $Namespace
        }
        catch {
            Write-Warning "  [$svc] Deployment resolution failed: $($_.Exception.Message)"
            $serviceFailed = $true
            $deploymentName = $null
        }

        if ($deploymentName -and -not (Test-FoundryContract -ServiceName $svc -DeploymentName $deploymentName)) {
            $serviceFailed = $true
        }
    }

    if ($UsePortForward) {
        # Find a free local port
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
        $listener.Start()
        $localPort = $listener.LocalEndpoint.Port
        $listener.Stop()

        # Start port-forward in background
        $job = Start-Job -ScriptBlock {
            param($resolvedServiceName, $resolvedServicePort, $ns, $port)
            kubectl port-forward "svc/$resolvedServiceName" "${port}:$resolvedServicePort" -n $ns 2>&1
        } -ArgumentList $resolved.Name, $resolved.Port, $Namespace, $localPort
        $portForwardJobs += $job

        Start-Sleep -Seconds 3
        $url = "http://localhost:$localPort/foundry/agents/ensure"
        $readyUrl = "http://localhost:$localPort/ready"
    }
    elseif ($BaseUrl) {
        $url = "$BaseUrl/$svc/foundry/agents/ensure"
        $readyUrl = "$BaseUrl/$svc/ready"
    }
    else {
        # In-cluster direct call (assumes running from within cluster or with network access)
        $url = "http://$($resolved.Name).$Namespace.svc.cluster.local:$($resolved.Port)/foundry/agents/ensure"
        $readyUrl = "http://$($resolved.Name).$Namespace.svc.cluster.local:$($resolved.Port)/ready"
    }

    $ensureResult = Invoke-EnsureEndpoint -ServiceName $svc -Url $url -Retries $MaxRetries
    if (-not $ensureResult.Ok) {
        $serviceFailed = $true
    }

    if (Test-BoolLike $validateReadyAfterEnsure) {
        $readyResult = Invoke-ReadyEndpoint -ServiceName $svc -Url $readyUrl
        if (-not (Test-ReadyContract -ServiceName $svc -ReadyResult $readyResult -EnsureOk:$ensureResult.Ok)) {
            $serviceFailed = $true
        }
    }

    # Clean up port-forward
    if ($UsePortForward -and $portForwardJobs.Count -gt 0) {
        if ($serviceFailed) {
            Receive-Job -Job $portForwardJobs[-1] -Keep -ErrorAction SilentlyContinue | ForEach-Object {
                Write-Host "  [$svc] $_"
            }
        }
        $portForwardJobs[-1] | Stop-Job -PassThru | Remove-Job -Force
    }

    if ($serviceFailed) {
        $failed += $svc
    }
    else {
        Write-Host "  [$svc] Foundry runtime contract validated."
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
    if ($FailOnError) {
        exit 1
    }

    Write-Warning 'Foundry ensure completed with failures, but FailOnError=false so deployment can continue.'
    exit 0
}

Write-Host ""
Write-Host "All $($services.Count * 2) Foundry agents are provisioned."
