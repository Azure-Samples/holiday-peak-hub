param(
    [string]$Environment = $(if ($env:AZURE_ENV_NAME) { $env:AZURE_ENV_NAME } else { '' }),
    [string]$ProjectName = "holidaypeakhub405",
    [string]$Namespace = "holiday-peak",
    [int]$StartupTimeoutMinutes = 20,
    [int]$HttpRetryCount = 24,
    [int]$HttpRetryDelaySeconds = 10,
    [switch]$SkipAksCredentials
)

$ErrorActionPreference = "Stop"

function Resolve-HostIPv4 {
    param([Parameter(Mandatory = $true)][string]$HostName)

    try {
        return [System.Net.Dns]::GetHostAddresses($HostName) |
            Where-Object { $_.AddressFamily -eq [System.Net.Sockets.AddressFamily]::InterNetwork } |
            ForEach-Object { $_.IPAddressToString } |
            Select-Object -Unique
    }
    catch {
        return @()
    }
}

function Start-AksIfStopped {
    param(
        [string]$ResourceGroup,
        [string]$ClusterName,
        [int]$TimeoutMinutes
    )

    $powerState = az aks show -g $ResourceGroup -n $ClusterName --query "powerState.code" -o tsv
    if ($powerState -eq "Stopped") {
        Write-Host "AKS '$ClusterName' is stopped. Starting..."
        az aks start -g $ResourceGroup -n $ClusterName | Out-Null
    }

    $deadline = (Get-Date).AddMinutes($TimeoutMinutes)
    do {
        $current = az aks show -g $ResourceGroup -n $ClusterName --query "powerState.code" -o tsv
        if ($current -eq "Running") {
            Write-Host "AKS '$ClusterName' is running."
            return
        }
        Start-Sleep -Seconds 15
    } while ((Get-Date) -lt $deadline)

    throw "AKS '$ClusterName' did not reach Running state in time."
}

function Start-ApplicationGatewayIfStopped {
    param(
        [string]$ResourceGroup,
        [string]$GatewayName,
        [int]$TimeoutMinutes
    )

    $operationalState = az network application-gateway show -g $ResourceGroup -n $GatewayName --query "operationalState" -o tsv
    if ($operationalState -ne "Running") {
        Write-Host "Application Gateway '$GatewayName' is '$operationalState'. Starting..."
        az network application-gateway start -g $ResourceGroup -n $GatewayName | Out-Null
    }

    $deadline = (Get-Date).AddMinutes($TimeoutMinutes)
    do {
        $current = az network application-gateway show -g $ResourceGroup -n $GatewayName --query "operationalState" -o tsv
        if ($current -eq "Running") {
            Write-Host "Application Gateway '$GatewayName' is running."
            return
        }
        Start-Sleep -Seconds 15
    } while ((Get-Date) -lt $deadline)

    throw "Application Gateway '$GatewayName' did not reach Running state in time."
}

function Start-PostgresIfStopped {
    param(
        [string]$ResourceGroup,
        [string]$ServerName,
        [int]$TimeoutMinutes
    )

    $state = az postgres flexible-server show -g $ResourceGroup -n $ServerName --query "state" -o tsv
    if ($state -eq "Stopped") {
        Write-Host "PostgreSQL '$ServerName' is stopped. Starting..."
        az postgres flexible-server start -g $ResourceGroup -n $ServerName | Out-Null
    }

    $deadline = (Get-Date).AddMinutes($TimeoutMinutes)
    do {
        $current = az postgres flexible-server show -g $ResourceGroup -n $ServerName --query "state" -o tsv
        if ($current -eq "Ready") {
            Write-Host "PostgreSQL '$ServerName' is ready."
            return
        }
        Start-Sleep -Seconds 15
    } while ((Get-Date) -lt $deadline)

    throw "PostgreSQL '$ServerName' did not reach Ready state in time."
}

function Test-Http200WithRetry {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [int]$RetryCount = 18,
        [int]$RetryDelaySeconds = 10
    )

    for ($attempt = 1; $attempt -le $RetryCount; $attempt++) {
        az rest --method get --url $Url --output none --only-show-errors 2>$null
        if ($LASTEXITCODE -eq 0) {
            return $true
        }
        Start-Sleep -Seconds $RetryDelaySeconds
    }

    return $false
}

function Assert-Overlap {
    param(
        [string]$Name,
        [string[]]$Left,
        [string[]]$Right
    )

    if (-not $Left -or -not $Right) {
        throw "$Name failed: one side has no IP data. left='$($Left -join ',')' right='$($Right -join ',')'"
    }

    $intersect = @($Left | Where-Object { $Right -contains $_ } | Select-Object -Unique)
    if (-not $intersect) {
        throw "$Name failed: no IP overlap. left='$($Left -join ',')' right='$($Right -join ',')'"
    }
}

if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    throw "Required command not found: az"
}

if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
    throw "Required command not found: kubectl"
}

if ([string]::IsNullOrWhiteSpace($Environment)) {
    throw "Environment must be provided via -Environment or AZURE_ENV_NAME."
}

az account show --query "id" -o tsv | Out-Null

$resourceGroup = "$ProjectName-$Environment-rg"
$aksName = "$ProjectName-$Environment-aks"
$appGwName = "$ProjectName-$Environment-appgw"
$postgresName = "$ProjectName-$Environment-postgres"
$apimName = "$ProjectName-$Environment-apim"
$apimBase = (az apim show -g $resourceGroup -n $apimName --query "gatewayUrl" -o tsv).TrimEnd('/')

Write-Host "Starting demo dependencies for '$resourceGroup'..."
Start-AksIfStopped -ResourceGroup $resourceGroup -ClusterName $aksName -TimeoutMinutes $StartupTimeoutMinutes
Start-ApplicationGatewayIfStopped -ResourceGroup $resourceGroup -GatewayName $appGwName -TimeoutMinutes $StartupTimeoutMinutes
Start-PostgresIfStopped -ResourceGroup $resourceGroup -ServerName $postgresName -TimeoutMinutes $StartupTimeoutMinutes

if (-not $SkipAksCredentials) {
    Write-Host "Fetching AKS credentials..."
    az aks get-credentials -g $resourceGroup -n $aksName --overwrite-existing | Out-Null
}

Write-Host "Collecting AKS/App Gateway ingress IP signals..."
$appGwPublicIpId = az network application-gateway show -g $resourceGroup -n $appGwName --query "frontendIPConfigurations[?publicIPAddress!=null][0].publicIPAddress.id" -o tsv
$appGwPublicIp = ""
if (-not [string]::IsNullOrWhiteSpace($appGwPublicIpId)) {
    $appGwPublicIp = az network public-ip show --ids $appGwPublicIpId --query "ipAddress" -o tsv
}
if ([string]::IsNullOrWhiteSpace($appGwPublicIp)) {
    throw "Could not resolve Application Gateway public IP for '$appGwName'."
}

$agcHostname = ""
if (Get-Command azd -ErrorAction SilentlyContinue) {
    try {
        $agcHostname = (azd env get-value AGC_FRONTEND_HOSTNAME -e $Environment 2>$null).Trim()
    }
    catch {
        $agcHostname = ""
    }
}

$agcResolvedIps = @()
if (-not [string]::IsNullOrWhiteSpace($agcHostname)) {
    $agcResolvedIps = Resolve-HostIPv4 -HostName $agcHostname
    if (-not $agcResolvedIps) {
        throw "AGC frontend hostname '$agcHostname' did not resolve to IPv4 addresses."
    }
    Assert-Overlap -Name "AGC hostname to AppGW public IP" -Left $agcResolvedIps -Right @($appGwPublicIp)
}

$lbServiceIps = @()
try {
    $services = kubectl get svc -A -o json | ConvertFrom-Json
    foreach ($svc in $services.items) {
        if ($svc.spec.type -eq "LoadBalancer" -and $svc.status.loadBalancer.ingress) {
            foreach ($ing in $svc.status.loadBalancer.ingress) {
                if ($ing.ip) {
                    $lbServiceIps += $ing.ip
                }
            }
        }
    }
}
catch {
    $lbServiceIps = @()
}
$lbServiceIps = @($lbServiceIps | Select-Object -Unique)

Write-Host "Validating APIM backend hosts and IP overlap with AKS ingress..."
$apis = az apim api list -g $resourceGroup --service-name $apimName --query "[].{name:name,path:path,serviceUrl:serviceUrl}" -o json | ConvertFrom-Json
$clusterApiCandidates = @($apis | Where-Object { $_.path -eq 'api' -or $_.path -like 'agents/*' })
if (-not $clusterApiCandidates) {
    throw "No APIM APIs with path 'api' or 'agents/*' were found."
}

$expectedIngressIps = @($appGwPublicIp)
if ($agcResolvedIps) { $expectedIngressIps += $agcResolvedIps }
if ($lbServiceIps) { $expectedIngressIps += $lbServiceIps }
$expectedIngressIps = @($expectedIngressIps | Select-Object -Unique)

$backendChecks = @()
foreach ($api in $clusterApiCandidates) {
    if ([string]::IsNullOrWhiteSpace($api.serviceUrl)) {
        throw "APIM API '$($api.name)' has empty serviceUrl."
    }

    $uri = [System.Uri]$api.serviceUrl
    $backendHost = $uri.Host
    $backendIps = Resolve-HostIPv4 -HostName $backendHost

    if (-not $backendIps) {
        throw "APIM API '$($api.name)' backend host '$backendHost' has no IPv4 resolution."
    }

    Assert-Overlap -Name "APIM backend '$($api.name)'" -Left $backendIps -Right $expectedIngressIps

    $backendChecks += [pscustomobject]@{
        apiName = $api.name
        path = $api.path
        serviceUrl = $api.serviceUrl
        backendHost = $backendHost
        backendIps = $backendIps
    }
}

Write-Host "Running APIM smoke checks..."
$smokeUrls = @(
    "$apimBase/api/health",
    "$apimBase/api/products?limit=1",
    "$apimBase/api/categories"
)

foreach ($url in $smokeUrls) {
    if (-not (Test-Http200WithRetry -Url $url -RetryCount $HttpRetryCount -RetryDelaySeconds $HttpRetryDelaySeconds)) {
        throw "APIM smoke check failed with non-200 after retries: $url"
    }
}

$reportDir = Join-Path (Get-Location) ".tmp"
if (-not (Test-Path $reportDir)) {
    New-Item -Path $reportDir -ItemType Directory | Out-Null
}

$reportPath = Join-Path $reportDir ("demo-preflight-report-{0}.json" -f (Get-Date -Format "yyyyMMdd-HHmmss"))
$report = [pscustomobject]@{
    environment = $Environment
    resourceGroup = $resourceGroup
    generatedAtUtc = (Get-Date).ToUniversalTime().ToString("o")
    apimGateway = $apimBase
    appGatewayPublicIp = $appGwPublicIp
    agcFrontendHostname = $agcHostname
    agcResolvedIps = $agcResolvedIps
    kubernetesLoadBalancerServiceIps = $lbServiceIps
    expectedIngressIps = $expectedIngressIps
    apimBackendChecks = $backendChecks
    smokeChecks = $smokeUrls
    status = "PASS"
}
$report | ConvertTo-Json -Depth 8 | Out-File -FilePath $reportPath -Encoding utf8

Write-Host "Pre-demo validation PASSED."
Write-Host "Report saved to: $reportPath"