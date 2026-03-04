param(
    [string]$ResourceGroup = $env:AZURE_RESOURCE_GROUP,
    [string]$ApimName = $env:APIM_NAME,
    [string]$Namespace = $(if ($env:K8S_NAMESPACE) { $env:K8S_NAMESPACE } else { 'holiday-peak' }),
    [string]$AzureYamlPath,
    [string]$ApiPathPrefix = 'agents',
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

    if ($RequireLb) {
        throw "Service '$Service' has no resolvable load balancer backend in namespace '$Namespace'."
    }

    return "http://$Service-$Service.$Namespace.svc.cluster.local:$servicePort"
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

    $backend = Resolve-ServiceBackendUrl -Service $service -Namespace $Ns -RequireLb:$true -Retries $BackendResolveRetries -DelaySeconds $BackendResolveDelaySeconds

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

        $crudPolicyXml = @'
<policies>
    <inbound>
        <base />
        <choose>
            <when condition="@(context.Request.OriginalUrl.Path == &quot;/api/health&quot;)">
                <rewrite-uri template="/health" copy-unmatched-params="true" />
            </when>
            <otherwise>
                <rewrite-uri template="@(string.Concat(&quot;/api&quot;, context.Request.OriginalUrl.Path.Substring(4)))" copy-unmatched-params="true" />
            </otherwise>
        </choose>
    </inbound>
    <backend>
        <base />
    </backend>
    <outbound>
        <base />
    </outbound>
    <on-error>
        <base />
    </on-error>
</policies>
'@

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
if (-not $agentServices -or $agentServices.Count -eq 0) {
    Write-Host 'No AKS agent services were found in azure.yaml. Nothing to sync.'
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
