<#
.SYNOPSIS
    Bisects the AGC (Application Gateway for Containers) edge path to quickly
    locate where a request stops flowing between a Kubernetes pod and the
    public APIM endpoint.

.DESCRIPTION
    Runs a fixed sequence of hops (pod-local, in-cluster Service DNS, AGC
    direct, APIM fronting) and writes a structured JSON evidence artifact.

    Designed to complete under 60 seconds. Read-only: no destructive az/kubectl
    commands. Prints a short human summary to stdout.

.PARAMETER Cluster
    AKS cluster name. Default: holidaypeakhub405-dev-aks.

.PARAMETER Namespace
    Namespace hosting the target service. Default: holiday-peak-agents.

.PARAMETER ServiceName
    Kubernetes Service name (ClusterIP). Default:
    ecommerce-catalog-search-ecommerce-catalog-search.

.PARAMETER PodSelector
    Label selector to pick a pod for pod-local probe. Default:
    app=ecommerce-catalog-search.

.PARAMETER AgcFqdn
    AGC frontend FQDN. Default: esbcc8bcfyazbbdg.fz03.alb.azure.com.

.PARAMETER AgcPath
    Path prefix routed by the HTTPRoute. Default: /ecommerce-catalog-search.

.PARAMETER ApimFqdn
    APIM gateway FQDN. Default: holidaypeakhub405-dev-apim.azure-api.net.

.PARAMETER ApimPath
    APIM path for the service. Default: /agents/ecommerce-catalog-search.

.PARAMETER OutputDir
    Directory for the JSON artifact. Default: docs/ops.

.PARAMETER FailOnHopGt
    Exit non-zero if the first failing hop is >= this value. Useful for CI
    smoke checks. 0 disables. Default: 0.

.PARAMETER SkipInCluster
    Skip hops requiring kubectl/cluster access.

.EXAMPLE
    ./agc-bisect.ps1
    Run full bisection and write JSON artifact under docs/ops.

.EXAMPLE
    ./agc-bisect.ps1 -FailOnHopGt 4
    CI mode: exit 1 if the first failure is at hop 4 (AGC edge) or later.
#>
[CmdletBinding()]
param(
    [string]$Cluster     = 'holidaypeakhub405-dev-aks',
    [string]$Namespace   = 'holiday-peak-agents',
    [string]$ServiceName = 'ecommerce-catalog-search-ecommerce-catalog-search',
    [string]$PodSelector = 'app=ecommerce-catalog-search',
    [string]$AgcFqdn     = 'esbcc8bcfyazbbdg.fz03.alb.azure.com',
    [string]$AgcPath     = '/ecommerce-catalog-search',
    [string]$ApimFqdn    = 'holidaypeakhub405-dev-apim.azure-api.net',
    [string]$ApimPath    = '/agents/ecommerce-catalog-search',
    [string]$OutputDir   = (Join-Path $PSScriptRoot '..\..\docs\ops'),
    [int]   $FailOnHopGt = 0,
    [switch]$SkipInCluster
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Net.Http

$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
$http = [System.Net.Http.HttpClient]::new()
$http.Timeout = [TimeSpan]::FromSeconds(10)

function Invoke-HttpProbe {
    param([string]$Method, [string]$Url, [hashtable]$Headers = @{}, [int]$TimeoutSec = 10)
    $req = [System.Net.Http.HttpRequestMessage]::new([System.Net.Http.HttpMethod]::$Method, $Url)
    foreach ($k in $Headers.Keys) { $null = $req.Headers.TryAddWithoutValidation($k, $Headers[$k]) }
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        $cts = [System.Threading.CancellationTokenSource]::new([TimeSpan]::FromSeconds($TimeoutSec))
        $resp = $http.SendAsync($req, [System.Net.Http.HttpCompletionOption]::ResponseHeadersRead, $cts.Token).GetAwaiter().GetResult()
        $sw.Stop()
        $body = $resp.Content.ReadAsStringAsync().GetAwaiter().GetResult()
        return [ordered]@{
            method      = $Method
            url         = $Url
            statusCode  = [int]$resp.StatusCode
            elapsedMs   = [int]$sw.Elapsed.TotalMilliseconds
            contentType = $resp.Content.Headers.ContentType.MediaType
            bodyPreview = if ($body.Length -gt 240) { $body.Substring(0, 240) } else { $body }
            result      = if ([int]$resp.StatusCode -lt 500) { 'pass' } else { 'fail' }
        }
    } catch {
        $sw.Stop()
        return [ordered]@{
            method     = $Method
            url        = $Url
            statusCode = $null
            elapsedMs  = [int]$sw.Elapsed.TotalMilliseconds
            error      = $_.Exception.Message
            result     = 'fail'
        }
    }
}

function Invoke-KubectlJson {
    param([Parameter(Mandatory)][string[]]$Args, [int]$TimeoutSec = 15)
    $p = Start-Process -FilePath kubectl -ArgumentList $Args -NoNewWindow -PassThru -RedirectStandardOutput ([IO.Path]::GetTempFileName()) -RedirectStandardError ([IO.Path]::GetTempFileName())
    if (-not $p.WaitForExit($TimeoutSec * 1000)) { $p.Kill(); throw "kubectl timeout: $($Args -join ' ')" }
    $stdout = Get-Content $p.StartInfo.RedirectStandardOutput -Raw
    if ($p.ExitCode -ne 0) { throw "kubectl failed: $stdout" }
    return ($stdout | ConvertFrom-Json)
}

$hops = @()

# Hop 2 (we don't run pod-local from PowerShell directly; skipped for speed —
# pod-local is covered by the readiness probe on the pod itself. In-cluster
# Service DNS is our first in-cluster probe.)
if (-not $SkipInCluster) {
    Write-Host '[Hop 2] In-cluster Service DNS via ephemeral curl pod...' -ForegroundColor Cyan
    $podName = "agc-bisect-$(Get-Random -Maximum 999999)"
    $svcUrl  = "http://$ServiceName.$Namespace.svc.cluster.local/health"
    try {
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        $out = & kubectl run $podName -n $Namespace --rm -i --restart=Never --quiet `
                --image=curlimages/curl:8.10.1 --command -- `
                sh -c "curl -sS -m 5 -o /dev/null -w 'code=%{http_code} time=%{time_total}' $svcUrl" 2>&1
        $sw.Stop()
        $code = 0; if ($out -match 'code=(\d+)') { $code = [int]$Matches[1] }
        $hops += [ordered]@{
            id = 2; label = 'In-cluster Service DNS'; method = 'GET'; url = $svcUrl
            statusCode = $code; elapsedMs = [int]$sw.Elapsed.TotalMilliseconds
            raw = ($out -join ' ')
            result = if ($code -eq 200) { 'pass' } else { 'fail' }
        }
    } catch {
        $hops += [ordered]@{ id = 2; label = 'In-cluster Service DNS'; url = $svcUrl; result = 'fail'; error = $_.Exception.Message }
    }

    # Hop 3: Gateway / HTTPRoute status
    Write-Host '[Hop 3] Gateway + HTTPRoute status...' -ForegroundColor Cyan
    try {
        $gw = Invoke-KubectlJson @('get','gateway','-A','-o','json')
        $rt = Invoke-KubectlJson @('get','httproute','-A','-o','json')
        $gwOk = $true; foreach ($g in $gw.items) {
            foreach ($c in $g.status.conditions) { if ($c.type -eq 'Programmed' -and $c.status -ne 'True') { $gwOk = $false } }
        }
        $rtOk = $true; foreach ($r in $rt.items) {
            foreach ($p in $r.status.parents) {
                foreach ($c in $p.conditions) {
                    if ($c.type -in @('Accepted','ResolvedRefs','Programmed') -and $c.status -ne 'True') { $rtOk = $false }
                }
            }
        }
        $hops += [ordered]@{
            id = 3; label = 'Gateway + HTTPRoute status'
            gatewayOk = $gwOk; routeOk = $rtOk
            gatewayCount = $gw.items.Count; routeCount = $rt.items.Count
            result = if ($gwOk -and $rtOk) { 'pass' } else { 'fail' }
        }
    } catch {
        $hops += [ordered]@{ id = 3; label = 'Gateway + HTTPRoute status'; result = 'fail'; error = $_.Exception.Message }
    }
}

# Hop 4: AGC direct
Write-Host '[Hop 4] AGC direct HTTP...' -ForegroundColor Cyan
$hops += ((Invoke-HttpProbe -Method Get -Url "http://$AgcFqdn$AgcPath/health" -TimeoutSec 10) + @{ id = 4; label = 'AGC direct HTTP' } | ForEach-Object { $_ })

# Hop 5: AGC HTTPS
Write-Host '[Hop 5] AGC direct HTTPS...' -ForegroundColor Cyan
$hops += ((Invoke-HttpProbe -Method Get -Url "https://$AgcFqdn$AgcPath/health" -TimeoutSec 10) + @{ id = 5; label = 'AGC direct HTTPS' } | ForEach-Object { $_ })

# Hop 6: APIM fronting
Write-Host '[Hop 6] APIM fronting...' -ForegroundColor Cyan
$hops += ((Invoke-HttpProbe -Method Get -Url "https://$ApimFqdn$ApimPath/health" -TimeoutSec 10) + @{ id = 6; label = 'APIM fronting' } | ForEach-Object { $_ })

$stopwatch.Stop()

$firstFail = ($hops | Where-Object { $_.result -eq 'fail' } | Select-Object -First 1)
$firstFailHop = if ($firstFail) { $firstFail.id } else { $null }

$artifact = [ordered]@{
    schema          = 'holiday-peak-hub/agc-bisection/v1'
    generatedAt     = (Get-Date).ToUniversalTime().ToString('o')
    cluster         = $Cluster
    namespace       = $Namespace
    serviceName     = $ServiceName
    agcFqdn         = $AgcFqdn
    apimFqdn        = $ApimFqdn
    totalElapsedMs  = [int]$stopwatch.Elapsed.TotalMilliseconds
    firstFailingHop = $firstFailHop
    hops            = $hops
}

if (-not (Test-Path $OutputDir)) { New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null }
$outPath = Join-Path $OutputDir ("agc-bisection-{0}.json" -f (Get-Date -Format 'yyyy-MM-dd-HHmmss'))
$artifact | ConvertTo-Json -Depth 10 | Set-Content -Path $outPath -Encoding utf8

Write-Host ""
Write-Host "Wrote: $outPath" -ForegroundColor Green
Write-Host ("Total elapsed: {0} ms" -f $artifact.totalElapsedMs)
Write-Host ("First failing hop: {0}" -f ($(if ($firstFailHop) { $firstFailHop } else { 'none' })))

if ($FailOnHopGt -gt 0 -and $firstFailHop -ge $FailOnHopGt) {
    Write-Host "FAIL: first failing hop ($firstFailHop) >= threshold ($FailOnHopGt)" -ForegroundColor Red
    exit 1
}
exit 0
