param(
    [string]$ResourceGroup = $env:AZURE_RESOURCE_GROUP,
    [string]$ApimName = $env:APIM_NAME,
    [string]$ApimCorsAllowedOrigins = $(if ($env:APIM_CORS_ALLOWED_ORIGINS) { $env:APIM_CORS_ALLOWED_ORIGINS } else { 'http://localhost:3000' }),
    [string]$Namespace = $(if ($env:K8S_NAMESPACE) { $env:K8S_NAMESPACE } else { 'holiday-peak' }),
    [string]$AzureYamlPath,
    [string]$ChangedServices = $env:CHANGED_SERVICES,
    [string]$ApiPathPrefix = 'agents',
    [switch]$UseIngress,
    [string]$IngressHost,
    [string]$AppGatewayName,
    [string]$AppGatewayIp,
    [bool]$IncludeCrudService = $true,
    [bool]$RequireLoadBalancer = $true,
    [int]$BackendResolveRetries = 24,
    [int]$BackendResolveDelaySeconds = 5,
    [switch]$Preview
)

$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path "$PSScriptRoot\..\..\.."
if (-not $AzureYamlPath) {
    $AzureYamlPath = Join-Path $repoRoot 'azure.yaml'
}

$script:resolvedIngressGatewayHost = ''
$script:useIngressMode = $UseIngress.IsPresent -or $env:USE_INGRESS -eq 'true'
$script:resolvedAppGatewayName = if ($AppGatewayName) { $AppGatewayName } elseif ($env:APP_GW_NAME) { $env:APP_GW_NAME } else { '' }
$script:resolvedAppGatewayIp = if ($AppGatewayIp) { $AppGatewayIp } elseif ($env:APP_GW_IP) { $env:APP_GW_IP } else { '' }
$script:resolvedIngressHostOverride = if ($IngressHost) { $IngressHost } elseif ($env:INGRESS_HOST) { $env:INGRESS_HOST } else { '' }
$script:ingressValidated = $false

if ($script:useIngressMode) {
    $RequireLoadBalancer = $false
}

function Get-EnvValueFromFile {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string]$Key
    )

    if (-not (Test-Path $FilePath)) {
        return ''
    }

    foreach ($line in Get-Content $FilePath) {
        if ($line -match "^$Key=(.*)$") {
            return $Matches[1].Trim('"')
        }
    }

    return ''
}

function Convert-ToXmlEscapedValue {
    param([Parameter(Mandatory = $true)][string]$Value)

    return $Value.Replace('&', '&amp;').Replace('<', '&lt;').Replace('>', '&gt;').Replace('"', '&quot;').Replace("'", '&apos;')
}

function Get-CorsOriginXml {
    param([string]$OriginsCsv)

    $origins = @($OriginsCsv.Split(',') | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    if (-not $origins -or $origins.Count -eq 0) {
        $origins = @('http://localhost:3000')
    }

    return ($origins | ForEach-Object { "<origin>$(Convert-ToXmlEscapedValue -Value $_)</origin>" }) -join "`n            "
}

function Get-ResourceGroup {
    param([string]$RepoRoot)

    if ($ResourceGroup) {
        return $ResourceGroup
    }

    if ($env:AZURE_ENV_NAME) {
        $envFile = Join-Path $RepoRoot ".azure\$($env:AZURE_ENV_NAME)\.env"
        $value = Get-EnvValueFromFile -FilePath $envFile -Key 'AZURE_RESOURCE_GROUP'
        if ($value) {
            return $value
        }
        $value = Get-EnvValueFromFile -FilePath $envFile -Key 'resourceGroupName'
        if ($value) {
            return $value
        }
    }

    return ''
}

function Get-ApimName {
    param(
        [string]$Rg,
        [string]$RepoRoot
    )

    if ($ApimName) {
        return $ApimName
    }

    if ($env:AZURE_ENV_NAME) {
        $envFile = Join-Path $RepoRoot ".azure\$($env:AZURE_ENV_NAME)\.env"
        $value = Get-EnvValueFromFile -FilePath $envFile -Key 'APIM_NAME'
        if ($value) {
            return $value
        }
        $value = Get-EnvValueFromFile -FilePath $envFile -Key 'apimName'
        if ($value) {
            return $value
        }
    }

    $derived = az apim list --resource-group $Rg --query "[0].name" -o tsv 2>$null
    if ($LASTEXITCODE -eq 0 -and $derived) {
        return $derived
    }

    return ''
}

function Get-AksClusterName {
    param(
        [string]$Rg,
        [string]$RepoRoot
    )

    if ($env:AKS_CLUSTER_NAME) {
        return $env:AKS_CLUSTER_NAME
    }

    if ($env:AZURE_ENV_NAME) {
        $envFile = Join-Path $RepoRoot ".azure\$($env:AZURE_ENV_NAME)\.env"
        $value = Get-EnvValueFromFile -FilePath $envFile -Key 'AKS_CLUSTER_NAME'
        if ($value) {
            return $value
        }
        $value = Get-EnvValueFromFile -FilePath $envFile -Key 'aksClusterName'
        if ($value) {
            return $value
        }
    }

    $derived = az aks list --resource-group $Rg --query "[0].name" -o tsv 2>$null
    if ($LASTEXITCODE -eq 0 -and $derived) {
        return $derived
    }

    return ''
}

function Ensure-AksCredentials {
    param(
        [string]$Rg,
        [string]$RepoRoot,
        [switch]$SkipForPreview
    )

    if ($SkipForPreview) {
        return
    }

    if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
        throw 'kubectl is required to resolve APIM backends. Install kubectl or run with -RequireLoadBalancer:$false.'
    }

    if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
        throw 'Azure CLI is required to resolve AKS cluster credentials for APIM backend sync.'
    }

    $clusterName = Get-AksClusterName -Rg $Rg -RepoRoot $RepoRoot
    if (-not $clusterName) {
        throw 'AKS cluster name could not be resolved. Set AKS_CLUSTER_NAME in env/.azure/<env>/.env.'
    }

    az aks get-credentials --resource-group $Rg --name $clusterName --overwrite-existing --only-show-errors *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to fetch AKS credentials for cluster '$clusterName'."
    }
}

function Invoke-AksKubectlJsonPath {
    param(
        [Parameter(Mandatory = $true)][string]$Rg,
        [Parameter(Mandatory = $true)][string]$ClusterName,
        [Parameter(Mandatory = $true)][string]$KubectlArgs
    )

    $command = "kubectl $KubectlArgs"
    $logs = az aks command invoke --resource-group $Rg --name $ClusterName --command $command --query logs -o tsv 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $logs) {
        return ''
    }

    return ($logs.Trim() -split "`r?`n")[-1].Trim()
}

function Get-AksServicesFromAzureYaml {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [switch]$IncludeCrud
    )

    if (-not (Test-Path $Path)) {
        throw "azure.yaml not found at: $Path"
    }

    $services = @()
    $inServices = $false
    $currentService = ''
    $currentHost = ''

    foreach ($line in Get-Content $Path) {
        if (-not $inServices) {
            if ($line -match '^services:\s*$') {
                $inServices = $true
            }
            continue
        }

        if ($line -match '^[^\s]') {
            break
        }

        if ($line -match '^  ([a-z0-9\-]+):\s*$') {
            if ($currentService -and $currentHost -eq 'aks') {
                $services += $currentService
            }
            $currentService = $Matches[1]
            $currentHost = ''
            continue
        }

        if ($line -match '^    host:\s*([^\s]+)\s*$') {
            $currentHost = $Matches[1]
        }
    }

    if ($currentService -and $currentHost -eq 'aks') {
        $services += $currentService
    }

    if (-not $IncludeCrud) {
        return $services | Where-Object { $_ -ne 'crud-service' }
    }

    return $services
}

function Resolve-IngressGatewayHost {
    param(
        [Parameter(Mandatory = $true)][string]$Rg,
        [string]$GatewayName
    )

    if ($script:resolvedIngressGatewayHost) {
        return $script:resolvedIngressGatewayHost
    }

    if ($script:resolvedIngressHostOverride) {
        $script:resolvedIngressGatewayHost = $script:resolvedIngressHostOverride
        return $script:resolvedIngressGatewayHost
    }

    if ($script:resolvedAppGatewayIp) {
        $script:resolvedIngressGatewayHost = $script:resolvedAppGatewayIp
        return $script:resolvedIngressGatewayHost
    }

    function Resolve-PublicHostFromGateway {
        param([Parameter(Mandatory = $true)][string]$Gateway)

        $pipId = az network application-gateway show --resource-group $Rg --name $Gateway --query 'frontendIPConfigurations[0].publicIPAddress.id' -o tsv 2>$null
        if (-not $pipId) {
            return ''
        }

        $publicHost = az network public-ip show --ids $pipId --query ipAddress -o tsv 2>$null
        if ($publicHost) {
            return $publicHost
        }

        $publicHost = az network public-ip show --ids $pipId --query dnsSettings.fqdn -o tsv 2>$null
        if ($publicHost) {
            return $publicHost
        }

        return ''
    }

    function Add-UniqueHostCandidate {
        param(
            [System.Collections.Generic.List[string]]$Collection,
            [string]$Candidate
        )

        if (-not $Candidate) {
            return
        }

        $trimmed = $Candidate.Trim()
        if (-not $trimmed) {
            return
        }

        if (-not $Collection.Contains($trimmed)) {
            $Collection.Add($trimmed)
        }
    }

    $resolvedHost = ''

    $effectiveGatewayName = if ($GatewayName) { $GatewayName } else { $script:resolvedAppGatewayName }
    if ($effectiveGatewayName) {
        $resolvedHost = Resolve-PublicHostFromGateway -Gateway $effectiveGatewayName
        if (-not $resolvedHost) {
            throw "Failed to resolve ingress host from explicit application gateway '$effectiveGatewayName'."
        }

        $script:resolvedIngressGatewayHost = $resolvedHost
        return $script:resolvedIngressGatewayHost
    }

    $autoGateways = @(az network application-gateway list --resource-group $Rg --query '[].name' -o tsv 2>$null | Where-Object { $_.Trim() })
    if ($autoGateways.Count -gt 1) {
        $appGatewayCandidates = @($autoGateways | Where-Object { $_ -match 'appgw' })
        if ($appGatewayCandidates.Count -eq 1) {
            $autoGateways = $appGatewayCandidates
        }
        else {
            throw "Multiple application gateways detected in '$Rg'. Provide -AppGatewayName, -AppGatewayIp, or -IngressHost."
        }
    }

    if ($autoGateways.Count -eq 1) {
        $resolvedHost = Resolve-PublicHostFromGateway -Gateway $autoGateways[0]
        if (-not $resolvedHost) {
            throw "Failed to resolve ingress host from detected application gateway '$($autoGateways[0])'."
        }
    }

    if (-not $resolvedHost) {
        $ingressCandidates = [System.Collections.Generic.List[string]]::new()
        Add-UniqueHostCandidate -Collection $ingressCandidates -Candidate (kubectl get svc -A -l 'app.kubernetes.io/name=nginx' -o jsonpath="{.items[0].status.loadBalancer.ingress[0].ip}" 2>$null)
        Add-UniqueHostCandidate -Collection $ingressCandidates -Candidate (kubectl get svc -A -l 'app.kubernetes.io/name=nginx' -o jsonpath="{.items[0].status.loadBalancer.ingress[0].hostname}" 2>$null)
        Add-UniqueHostCandidate -Collection $ingressCandidates -Candidate (kubectl get svc nginx -n app-routing-system -o jsonpath="{.status.loadBalancer.ingress[0].ip}" 2>$null)
        Add-UniqueHostCandidate -Collection $ingressCandidates -Candidate (kubectl get svc nginx -n app-routing-system -o jsonpath="{.status.loadBalancer.ingress[0].hostname}" 2>$null)
        Add-UniqueHostCandidate -Collection $ingressCandidates -Candidate (kubectl get svc ingress-nginx-controller -n ingress-nginx -o jsonpath="{.status.loadBalancer.ingress[0].ip}" 2>$null)
        Add-UniqueHostCandidate -Collection $ingressCandidates -Candidate (kubectl get svc ingress-nginx-controller -n ingress-nginx -o jsonpath="{.status.loadBalancer.ingress[0].hostname}" 2>$null)

        if ($ingressCandidates.Count -gt 1) {
            throw 'Ambiguous ingress host candidates detected. Provide -AppGatewayName, -AppGatewayIp, or -IngressHost.'
        }

        if ($ingressCandidates.Count -eq 1) {
            $resolvedHost = $ingressCandidates[0]
        }
    }

    if ($resolvedHost) {
        $script:resolvedIngressGatewayHost = $resolvedHost
    }

    return $script:resolvedIngressGatewayHost
}

function Test-IngressCrudHealth {
    param(
        [Parameter(Mandatory = $true)][string]$GatewayHost
    )

    $probeUrl = "http://$GatewayHost/health"
    $lastStatus = ''
    $lastBody = ''

    for ($attempt = 1; $attempt -le 8; $attempt++) {
        try {
            $response = Invoke-WebRequest -Uri $probeUrl -Method GET -TimeoutSec 10 -UseBasicParsing
            if ($response.StatusCode -eq 200) {
                Write-Host "Validated ingress host '$GatewayHost' via $probeUrl"
                return
            }

            $lastStatus = [string]$response.StatusCode
            $lastBody = [string]$response.Content
        }
        catch {
            $statusCode = $_.Exception.Response.StatusCode.value__
            if ($statusCode) {
                $lastStatus = [string]$statusCode
                if ($statusCode -eq 404) {
                    Write-Host "Validated ingress host '$GatewayHost' via $probeUrl (404 indicates reachable ingress path without rewrite)"
                    return
                }
            }
            $lastBody = $_.Exception.Message
        }

        Start-Sleep -Seconds 5
    }

    throw "Ingress validation failed for '$GatewayHost' (last status: $lastStatus) using $probeUrl. Last response: $lastBody"
}

function Ensure-IngressReady {
    if ($script:ingressValidated) {
        return
    }

    $resolvedHost = Resolve-IngressGatewayHost -Rg $script:resolvedResourceGroup -GatewayName $script:resolvedAppGatewayName
    if (-not $resolvedHost) {
        throw 'Ingress endpoint could not be resolved for APIM backend sync. Refusing to fall back to cluster-local addresses that APIM cannot reach.'
    }

    if (-not $Preview) {
        Test-IngressCrudHealth -GatewayHost $resolvedHost
    }

    $script:ingressValidated = $true
}

function Resolve-ServiceBackendUrl {
    param(
        [Parameter(Mandatory = $true)][string]$Service,
        [Parameter(Mandatory = $true)][string]$Namespace,
        [bool]$RequireLb = $true,
        [int]$Retries = 24,
        [int]$DelaySeconds = 5
    )

    $serviceName = ''
    $servicePort = '80'
    $lbHost = ''

    if ($script:useIngressMode) {
        Ensure-IngressReady
        if ($Service -eq 'crud-service') {
            return "http://$($script:resolvedIngressGatewayHost)"
        }
        return "http://$($script:resolvedIngressGatewayHost)/$Service"
    }

    if (Get-Command kubectl -ErrorAction SilentlyContinue) {
        $serviceName = kubectl get svc -n $Namespace -l "app=$Service" -o jsonpath="{.items[0].metadata.name}" 2>$null
        if ($LASTEXITCODE -eq 0 -and $serviceName) {
            $servicePortCandidate = kubectl get svc $serviceName -n $Namespace -o jsonpath="{.spec.ports[0].port}" 2>$null
            if ($LASTEXITCODE -eq 0 -and $servicePortCandidate) {
                $servicePort = $servicePortCandidate
            }

            for ($attempt = 1; $attempt -le $Retries; $attempt++) {
                $lbIp = kubectl get svc $serviceName -n $Namespace -o jsonpath="{.status.loadBalancer.ingress[0].ip}" 2>$null
                if ($LASTEXITCODE -eq 0 -and $lbIp) {
                    $lbHost = $lbIp
                    break
                }

                $lbDns = kubectl get svc $serviceName -n $Namespace -o jsonpath="{.status.loadBalancer.ingress[0].hostname}" 2>$null
                if ($LASTEXITCODE -eq 0 -and $lbDns) {
                    $lbHost = $lbDns
                    break
                }

                if ($attempt -lt $Retries) {
                    Start-Sleep -Seconds $DelaySeconds
                }
            }

            if ($lbHost) {
                return "http://${lbHost}:$servicePort"
            }

            if (-not $RequireLb) {
                $clusterIp = kubectl get svc $serviceName -n $Namespace -o jsonpath="{.spec.clusterIP}" 2>$null
                if ($LASTEXITCODE -eq 0 -and $clusterIp) {
                    return "http://${clusterIp}:$servicePort"
                }
                return "http://$serviceName.$Namespace.svc.cluster.local:$servicePort"
            }
        }
    }

    if ($script:resolvedAksClusterName -and $script:resolvedResourceGroup) {
        $serviceName = Invoke-AksKubectlJsonPath -Rg $script:resolvedResourceGroup -ClusterName $script:resolvedAksClusterName -KubectlArgs "get svc -n $Namespace -l app=$Service -o jsonpath='{.items[0].metadata.name}'"
        if ($serviceName) {
            $servicePortCandidate = Invoke-AksKubectlJsonPath -Rg $script:resolvedResourceGroup -ClusterName $script:resolvedAksClusterName -KubectlArgs "get svc $serviceName -n $Namespace -o jsonpath='{.spec.ports[0].port}'"
            if ($servicePortCandidate) {
                $servicePort = $servicePortCandidate
            }

            for ($attempt = 1; $attempt -le $Retries; $attempt++) {
                $lbIp = Invoke-AksKubectlJsonPath -Rg $script:resolvedResourceGroup -ClusterName $script:resolvedAksClusterName -KubectlArgs "get svc $serviceName -n $Namespace -o jsonpath='{.status.loadBalancer.ingress[0].ip}'"
                if ($lbIp) {
                    $lbHost = $lbIp
                    break
                }

                $lbDns = Invoke-AksKubectlJsonPath -Rg $script:resolvedResourceGroup -ClusterName $script:resolvedAksClusterName -KubectlArgs "get svc $serviceName -n $Namespace -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'"
                if ($lbDns) {
                    $lbHost = $lbDns
                    break
                }

                if ($attempt -lt $Retries) {
                    Start-Sleep -Seconds $DelaySeconds
                }
            }

            if ($lbHost) {
                return "http://${lbHost}:$servicePort"
            }

            if (-not $RequireLb) {
                $clusterIp = Invoke-AksKubectlJsonPath -Rg $script:resolvedResourceGroup -ClusterName $script:resolvedAksClusterName -KubectlArgs "get svc $serviceName -n $Namespace -o jsonpath='{.spec.clusterIP}'"
                if ($clusterIp) {
                    return "http://${clusterIp}:$servicePort"
                }
            }
        }
    }

    if ($RequireLb -and $Service -eq 'crud-service') {
        try {
            $fallbackHost = Resolve-IngressGatewayHost -Rg $script:resolvedResourceGroup -GatewayName $script:resolvedAppGatewayName
            if (-not $Preview) {
                Test-IngressCrudHealth -GatewayHost $fallbackHost
            }
            Write-Host "Using ingress fallback host '$fallbackHost' for CRUD APIM backend because no load balancer endpoint was resolved."
            return "http://$fallbackHost"
        }
        catch {
            throw "Service '$Service' has no resolvable load balancer backend and ingress fallback failed in namespace '$Namespace'. $($_.Exception.Message)"
        }
    }

    if ($RequireLb) {
        throw "Service '$Service' has no resolvable load balancer backend in namespace '$Namespace'."
    }

    return "http://$Service-$Service.$Namespace.svc.cluster.local:$servicePort"
}

function Get-ServiceEndpointIps {
    param(
        [Parameter(Mandatory = $true)][string]$Service,
        [Parameter(Mandatory = $true)][string]$Namespace
    )

    $endpointIps = @()

    if (Get-Command kubectl -ErrorAction SilentlyContinue) {
        $ipsFromKubectl = kubectl get endpoints $Service -n $Namespace -o jsonpath="{.subsets[*].addresses[*].ip}" 2>$null
        if ($LASTEXITCODE -eq 0 -and $ipsFromKubectl) {
            $endpointIps += @($ipsFromKubectl -split '\s+' | Where-Object { $_ })
        }
    }

    if (($endpointIps.Count -eq 0) -and $script:resolvedAksClusterName -and $script:resolvedResourceGroup) {
        $ipsFromAksCommand = Invoke-AksKubectlJsonPath -Rg $script:resolvedResourceGroup -ClusterName $script:resolvedAksClusterName -KubectlArgs "get endpoints $Service -n $Namespace -o jsonpath='{.subsets[*].addresses[*].ip}'"
        if ($ipsFromAksCommand) {
            $endpointIps += @($ipsFromAksCommand -split '\s+' | Where-Object { $_ })
        }
    }

    return @($endpointIps | Sort-Object -Unique)
}

function Get-UrlHost {
    param([Parameter(Mandatory = $true)][string]$Url)

    try {
        return ([uri]$Url).Host
    }
    catch {
        return ''
    }
}

function Assert-StableCrudBackendTarget {
    param(
        [Parameter(Mandatory = $true)][string]$BackendUrl,
        [Parameter(Mandatory = $true)][string]$Namespace
    )

    $backendHost = Get-UrlHost -Url $BackendUrl
    if (-not $backendHost) {
        throw "Unable to parse host from CRUD APIM backend URL '$BackendUrl'."
    }

    $endpointIps = Get-ServiceEndpointIps -Service 'crud-service' -Namespace $Namespace
    if ($endpointIps -contains $backendHost) {
        $joinedIps = $endpointIps -join ', '
        throw "Refusing to set unstable CRUD APIM backend '$BackendUrl': host '$backendHost' matches current crud-service endpoint IP(s): $joinedIps"
    }

    Write-Host "Validated stable CRUD APIM backend host '$backendHost'."
}

function Ensure-AgentApi {
    param(
        [Parameter(Mandatory = $true)][string]$Rg,
        [Parameter(Mandatory = $true)][string]$Service,
        [Parameter(Mandatory = $true)][string]$Apim,
        [Parameter(Mandatory = $true)][string]$Ns,
        [Parameter(Mandatory = $true)][string]$Prefix,
        [switch]$DryRun
    )

    $apiId = "agent-$Service"
    $displayName = "Agent - $Service"
    $path = "$Prefix/$Service"

    if ($DryRun) {
        Write-Host "[preview] api-id=$apiId path=$path"
        return
    }

    $backend = Resolve-ServiceBackendUrl -Service $Service -Namespace $Ns -RequireLb:$RequireLoadBalancer -Retries $BackendResolveRetries -DelaySeconds $BackendResolveDelaySeconds

    az apim api show --resource-group $Rg --service-name $Apim --api-id $apiId --only-show-errors *> $null
    if ($LASTEXITCODE -eq 0) {
        az apim api update --resource-group $Rg --service-name $Apim --api-id $apiId --display-name $displayName --path $path --protocols https http --service-url $backend --subscription-required false --only-show-errors *> $null
        Write-Host "Updated API: $apiId"
    }
    else {
        az apim api create --resource-group $Rg --service-name $Apim --api-id $apiId --display-name $displayName --path $path --protocols https http --service-url $backend --subscription-required false --only-show-errors *> $null
        Write-Host "Created API: $apiId"
    }

    $operations = @(
        @{ id = 'health'; method = 'GET'; template = '/health'; name = 'Health' },
        @{ id = 'invoke'; method = 'POST'; template = '/invoke'; name = 'Invoke' },
        @{ id = 'mcp-tool'; method = 'POST'; template = '/mcp/{tool}'; name = 'MCP Tool' }
    )

    foreach ($op in $operations) {
        az apim api operation delete --resource-group $Rg --service-name $Apim --api-id $apiId --operation-id $op.id --if-match '*' --only-show-errors *> $null
        $createArgs = @(
            'apim', 'api', 'operation', 'create',
            '--resource-group', $Rg,
            '--service-name', $Apim,
            '--api-id', $apiId,
            '--operation-id', $op.id,
            '--display-name', $op.name,
            '--method', $op.method,
            '--url-template', $op.template,
            '--only-show-errors'
        )

        if ($op.id -eq 'mcp-tool') {
            $createArgs += @(
                '--template-parameters',
                'name=tool',
                'description=MCP tool name',
                'type=string',
                'required=true'
            )
        }

        az @createArgs *> $null
    }
}

function Update-CrudApi {
    param(
        [Parameter(Mandatory = $true)][string]$Rg,
        [Parameter(Mandatory = $true)][string]$Apim,
        [Parameter(Mandatory = $true)][string]$Ns,
        [switch]$DryRun
    )

    $service = 'crud-service'
    $apiId = 'crud'
    $displayName = 'CRUD Service'
    $path = 'api'

    if ($DryRun) {
        Write-Host "[preview] api-id=$apiId path=$path"
        return
    }

    $backend = Resolve-ServiceBackendUrl -Service $service -Namespace $Ns -RequireLb:$RequireLoadBalancer -Retries $BackendResolveRetries -DelaySeconds $BackendResolveDelaySeconds
    Assert-StableCrudBackendTarget -BackendUrl $backend -Namespace $Ns

    $apiExists = $false
    az apim api show --resource-group $Rg --service-name $Apim --api-id 'crud-service' --only-show-errors *> $null
    if ($LASTEXITCODE -eq 0) {
        $apiId = 'crud-service'
        $apiExists = $true
    }
    else {
        az apim api show --resource-group $Rg --service-name $Apim --api-id 'crud' --only-show-errors *> $null
        if ($LASTEXITCODE -eq 0) {
            $apiId = 'crud'
            $apiExists = $true
        }
    }

    if ($apiExists) {
        az apim api update --resource-group $Rg --service-name $Apim --api-id $apiId --display-name $displayName --path $path --protocols https http --service-url $backend --subscription-required false --only-show-errors *> $null
        Write-Host "Updated API: $apiId"
    }
    else {
        az apim api create --resource-group $Rg --service-name $Apim --api-id $apiId --display-name $displayName --path $path --protocols https http --service-url $backend --subscription-required false --only-show-errors *> $null
        Write-Host "Created API: $apiId"
    }

    $operations = @(
        @{ id = 'health'; method = 'GET'; template = '/health'; name = 'Health' },
        @{ id = 'api-root-get'; method = 'GET'; template = '/'; name = 'API Root GET' },
        @{ id = 'api-root-post'; method = 'POST'; template = '/'; name = 'API Root POST' },
        @{ id = 'api-get'; method = 'GET'; template = '/{*path}'; name = 'API GET' },
        @{ id = 'api-post'; method = 'POST'; template = '/{*path}'; name = 'API POST' },
        @{ id = 'api-put'; method = 'PUT'; template = '/{*path}'; name = 'API PUT' },
        @{ id = 'api-patch'; method = 'PATCH'; template = '/{*path}'; name = 'API PATCH' },
        @{ id = 'api-delete'; method = 'DELETE'; template = '/{*path}'; name = 'API DELETE' },
        @{ id = 'api-options'; method = 'OPTIONS'; template = '/{*path}'; name = 'API OPTIONS' },
        @{ id = 'acp-get'; method = 'GET'; template = '/acp/{*path}'; name = 'ACP GET' },
        @{ id = 'acp-post'; method = 'POST'; template = '/acp/{*path}'; name = 'ACP POST' },
        @{ id = 'acp-put'; method = 'PUT'; template = '/acp/{*path}'; name = 'ACP PUT' },
        @{ id = 'acp-patch'; method = 'PATCH'; template = '/acp/{*path}'; name = 'ACP PATCH' },
        @{ id = 'acp-delete'; method = 'DELETE'; template = '/acp/{*path}'; name = 'ACP DELETE' }
    )

    foreach ($op in $operations) {
        az apim api operation delete --resource-group $Rg --service-name $Apim --api-id $apiId --operation-id $op.id --if-match '*' --only-show-errors *> $null
        $createArgs = @(
            'apim', 'api', 'operation', 'create',
            '--resource-group', $Rg,
            '--service-name', $Apim,
            '--api-id', $apiId,
            '--operation-id', $op.id,
            '--display-name', $op.name,
            '--method', $op.method,
            '--url-template', $op.template,
            '--only-show-errors'
        )

        if ($op.template -like '*{*path}*') {
            $createArgs += @(
                '--template-parameters',
                'name=path',
                'description=Wildcard route path',
                'type=string',
                'required=false'
            )
        }

        az @createArgs *> $null
    }

        $subscriptionId = az account show --query id -o tsv 2>$null
        if (-not $subscriptionId) {
                throw 'Failed to resolve Azure subscription id for CRUD APIM policy update.'
        }

        $corsOriginXml = Get-CorsOriginXml -OriginsCsv $ApimCorsAllowedOrigins

        $crudPolicyXml = @"
<policies>
    <inbound>
        <base />
        <cors allow-credentials="false">
            <allowed-origins>
            $corsOriginXml
            </allowed-origins>
            <allowed-methods preflight-result-max-age="300">
                <method>*</method>
            </allowed-methods>
            <allowed-headers>
                <header>*</header>
            </allowed-headers>
            <expose-headers>
                <header>*</header>
            </expose-headers>
        </cors>
        <choose>
            <when condition="@(context.Request.OriginalUrl.Path.Equals(&quot;/api/health&quot;, System.StringComparison.OrdinalIgnoreCase))">
                <rewrite-uri template="/health" copy-unmatched-params="true" />
            </when>
            <when condition="@(context.Request.OriginalUrl.Path.Equals(&quot;/api&quot;, System.StringComparison.OrdinalIgnoreCase) || context.Request.OriginalUrl.Path.StartsWith(&quot;/api/&quot;, System.StringComparison.OrdinalIgnoreCase))">
                <set-variable name="crudBackendPath" value="@(context.Request.OriginalUrl.Path.Length > 4 ? context.Request.OriginalUrl.Path.Substring(4) : string.Empty)" />
                <rewrite-uri template="@(string.Concat(&quot;/api&quot;, (string)context.Variables[&quot;crudBackendPath&quot;]))" copy-unmatched-params="true" />
            </when>
            <otherwise>
                <return-response>
                    <set-status code="400" reason="Bad Request" />
                    <set-header name="Content-Type" exists-action="override">
                        <value>application/json</value>
                    </set-header>
                    <set-body>{"detail":"Invalid CRUD API path."}</set-body>
                </return-response>
            </otherwise>
        </choose>
    </inbound>
    <backend>
        <base />
        <forward-request timeout="60" />
    </backend>
    <outbound>
        <base />
        <set-header name="Access-Control-Allow-Origin" exists-action="override">
            <value>@(context.Request.Headers.GetValueOrDefault(&quot;Origin&quot;, &quot;http://localhost:3000&quot;))</value>
        </set-header>
        <set-header name="Access-Control-Allow-Methods" exists-action="override">
            <value>GET,POST,PUT,PATCH,DELETE,OPTIONS</value>
        </set-header>
        <set-header name="Access-Control-Allow-Headers" exists-action="override">
            <value>*</value>
        </set-header>
    </outbound>
    <on-error>
        <base />
        <return-response>
            <set-status code="502" reason="Bad Gateway" />
            <set-header name="Access-Control-Allow-Origin" exists-action="override">
                <value>@(context.Request.Headers.GetValueOrDefault(&quot;Origin&quot;, &quot;http://localhost:3000&quot;))</value>
            </set-header>
            <set-header name="Access-Control-Allow-Methods" exists-action="override">
                <value>GET,POST,PUT,PATCH,DELETE,OPTIONS</value>
            </set-header>
            <set-header name="Access-Control-Allow-Headers" exists-action="override">
                <value>*</value>
            </set-header>
            <set-header name="Content-Type" exists-action="override">
                <value>application/json</value>
            </set-header>
            <set-body>{"detail":"APIM upstream error while routing to CRUD backend."}</set-body>
        </return-response>
    </on-error>
</policies>
"@

        $policyPayload = @{ properties = @{ format = 'rawxml'; value = $crudPolicyXml } } | ConvertTo-Json -Depth 8
        $policyTempPath = Join-Path ([System.IO.Path]::GetTempPath()) 'apim-crud-policy.json'
        Set-Content -Path $policyTempPath -Value $policyPayload -Encoding UTF8

        $policyUrl = "https://management.azure.com/subscriptions/$subscriptionId/resourceGroups/$Rg/providers/Microsoft.ApiManagement/service/$Apim/apis/$apiId/policies/policy?api-version=2022-08-01"
        az rest --method put --url $policyUrl --headers 'Content-Type=application/json' --body "@$policyTempPath" --only-show-errors *> $null
}

$resolvedResourceGroup = Get-ResourceGroup -RepoRoot $repoRoot
if (-not $resolvedResourceGroup) {
    throw 'Resource group could not be resolved. Set AZURE_RESOURCE_GROUP, pass -ResourceGroup, or run within an azd environment.'
}

$resolvedApimName = Get-ApimName -Rg $resolvedResourceGroup -RepoRoot $repoRoot
if (-not $resolvedApimName) {
    throw 'APIM name could not be resolved. Set APIM_NAME or pass -ApimName.'
}

$script:resolvedResourceGroup = $resolvedResourceGroup
$script:resolvedAksClusterName = Get-AksClusterName -Rg $resolvedResourceGroup -RepoRoot $repoRoot

Ensure-AksCredentials -Rg $resolvedResourceGroup -RepoRoot $repoRoot -SkipForPreview:$Preview

$agentServices = Get-AksServicesFromAzureYaml -Path $AzureYamlPath -IncludeCrud:$IncludeCrudService

if ($ChangedServices) {
    $changedServiceSet = $ChangedServices.Split(',') | ForEach-Object { $_.Trim() } | Where-Object { $_ }
    $agentServices = @($agentServices | Where-Object { $changedServiceSet -contains $_ })

    if ($IncludeCrudService -and -not ($agentServices -contains 'crud-service')) {
        $agentServices += 'crud-service'
    }
}

if (-not $agentServices -or $agentServices.Count -eq 0) {
    Write-Host 'No matching changed AKS services to sync.'
    exit 0
}

Write-Host "Syncing $($agentServices.Count) AKS services into APIM '$resolvedApimName' (RG: $resolvedResourceGroup)..."

foreach ($service in $agentServices) {
    if ($service -eq 'crud-service') {
        Update-CrudApi -Rg $resolvedResourceGroup -Apim $resolvedApimName -Ns $Namespace -DryRun:$Preview
        continue
    }

    Ensure-AgentApi -Rg $resolvedResourceGroup -Service $service -Apim $resolvedApimName -Ns $Namespace -Prefix $ApiPathPrefix -DryRun:$Preview
}

Write-Host 'APIM agent sync completed.'
