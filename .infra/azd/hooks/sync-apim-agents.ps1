param(
    [string]$ResourceGroup = $env:AZURE_RESOURCE_GROUP,
    [string]$ApimName = $env:APIM_NAME,
    [string]$Namespace = $(if ($env:K8S_NAMESPACE) { $env:K8S_NAMESPACE } else { 'holiday-peak' }),
    [string]$AzureYamlPath,
    [string]$ApiPathPrefix = 'agents',
    [switch]$IncludeCrudService,
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
                if ($IncludeCrud -or $currentService -ne 'crud-service') {
                    $services += $currentService
                }
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
        if ($IncludeCrud -or $currentService -ne 'crud-service') {
            $services += $currentService
        }
    }

    return $services
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
    $backend = "http://$Service-$Service.$Ns.svc.cluster.local"

    if ($DryRun) {
        Write-Host "[preview] api-id=$apiId path=$path backend=$backend"
        return
    }

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

$resolvedResourceGroup = Get-ResourceGroup -RepoRoot $repoRoot
if (-not $resolvedResourceGroup) {
    throw 'Resource group could not be resolved. Set AZURE_RESOURCE_GROUP, pass -ResourceGroup, or run within an azd environment.'
}

$resolvedApimName = Get-ApimName -Rg $resolvedResourceGroup -RepoRoot $repoRoot
if (-not $resolvedApimName) {
    throw 'APIM name could not be resolved. Set APIM_NAME or pass -ApimName.'
}

$agentServices = Get-AksServicesFromAzureYaml -Path $AzureYamlPath -IncludeCrud:$IncludeCrudService
if (-not $agentServices -or $agentServices.Count -eq 0) {
    Write-Host 'No AKS agent services were found in azure.yaml. Nothing to sync.'
    exit 0
}

Write-Host "Syncing $($agentServices.Count) AKS services into APIM '$resolvedApimName' (RG: $resolvedResourceGroup)..."

foreach ($service in $agentServices) {
    Ensure-AgentApi -Rg $resolvedResourceGroup -Service $service -Apim $resolvedApimName -Ns $Namespace -Prefix $ApiPathPrefix -DryRun:$Preview
}

Write-Host 'APIM agent sync completed.'
