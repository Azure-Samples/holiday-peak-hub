#!/usr/bin/env pwsh
param(
    [string]$ResourceGroup = $env:AZURE_RESOURCE_GROUP,
    [string]$AksClusterName = $env:AKS_CLUSTER_NAME,
    [string]$AgcSupportEnabled = $env:AGC_SUPPORT_ENABLED,
    [string]$ControllerIdentityClientId = $env:AGC_CONTROLLER_IDENTITY_CLIENT_ID,
    [string]$ControllerIdentityPrincipalId = $env:AGC_CONTROLLER_IDENTITY_PRINCIPAL_ID,
    [string]$AgcSubnetId = $env:AGC_SUBNET_ID,
    [string]$AksNodeResourceGroup = $env:AKS_NODE_RESOURCE_GROUP
)

$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path "$PSScriptRoot\..\..\.."

function Get-EnvValueFromFile {
    param([string]$FilePath, [string]$Key)
    if (-not (Test-Path $FilePath)) { return '' }
    foreach ($line in Get-Content $FilePath) {
        if ($line -match "^$Key=(.*)$") { return $Matches[1].Trim('"') }
    }
    return ''
}

function Resolve-EnvValue {
    param([string[]]$Keys, [string]$CurrentValue)
    if ($CurrentValue) { return $CurrentValue }
    if (-not $env:AZURE_ENV_NAME) { return '' }

    $envFile = Join-Path $repoRoot ".azure\$($env:AZURE_ENV_NAME)\.env"
    foreach ($key in $Keys) {
        $value = Get-EnvValueFromFile -FilePath $envFile -Key $key
        if ($value) { return $value }
    }

    return ''
}

function Ensure-RoleAssignment {
    param(
        [string]$PrincipalId,
        [string]$Scope,
        [string]$RoleDefinitionId
    )

    $existing = az role assignment list --assignee-object-id $PrincipalId --scope $Scope --query "[?roleDefinitionId=='$RoleDefinitionId'] | length(@)" -o tsv 2>$null
    if ($existing -and $existing -ne '0') {
        return
    }

    az role assignment create --assignee-object-id $PrincipalId --assignee-principal-type ServicePrincipal --scope $Scope --role $RoleDefinitionId --only-show-errors | Out-Null
}

$AgcSupportEnabled = Resolve-EnvValue -Keys @('AGC_SUPPORT_ENABLED') -CurrentValue $AgcSupportEnabled
if (($AgcSupportEnabled ?? '').ToLowerInvariant() -ne 'true') {
    Write-Host 'AGC support is disabled for this environment. Skipping ALB controller installation.'
    exit 0
}

$ResourceGroup = Resolve-EnvValue -Keys @('AZURE_RESOURCE_GROUP', 'resourceGroupName') -CurrentValue $ResourceGroup
$AksClusterName = Resolve-EnvValue -Keys @('AKS_CLUSTER_NAME', 'aksClusterName') -CurrentValue $AksClusterName
$ControllerIdentityClientId = Resolve-EnvValue -Keys @('AGC_CONTROLLER_IDENTITY_CLIENT_ID') -CurrentValue $ControllerIdentityClientId
$ControllerIdentityPrincipalId = Resolve-EnvValue -Keys @('AGC_CONTROLLER_IDENTITY_PRINCIPAL_ID') -CurrentValue $ControllerIdentityPrincipalId
$AgcSubnetId = Resolve-EnvValue -Keys @('AGC_SUBNET_ID') -CurrentValue $AgcSubnetId
$AksNodeResourceGroup = Resolve-EnvValue -Keys @('AKS_NODE_RESOURCE_GROUP') -CurrentValue $AksNodeResourceGroup

if (-not $ResourceGroup) {
    throw 'Resource group could not be resolved. Set AZURE_RESOURCE_GROUP or run within an azd environment.'
}

if (-not $AksClusterName) {
    throw 'AKS cluster name could not be resolved. Set AKS_CLUSTER_NAME or run within an azd environment.'
}

if (-not $ControllerIdentityClientId) {
    throw 'AGC controller identity client ID could not be resolved. Provision shared infrastructure before running this hook.'
}

if (-not $ControllerIdentityPrincipalId) {
    throw 'AGC controller identity principal ID could not be resolved. Provision shared infrastructure before running this hook.'
}

if (-not $AgcSubnetId) {
    throw 'AGC subnet ID could not be resolved. Provision shared infrastructure before running this hook.'
}

if (-not $AksNodeResourceGroup) {
    throw 'AKS node resource group could not be resolved. Provision shared infrastructure before running this hook.'
}

foreach ($commandName in @('az', 'kubectl', 'helm')) {
    if (-not (Get-Command $commandName -ErrorAction SilentlyContinue)) {
        throw "Required command '$commandName' is not available on PATH."
    }
}

Write-Host "Installing AGC ALB controller support for cluster '$AksClusterName' in resource group '$ResourceGroup'."

$subscriptionId = az account show --query id -o tsv
$aksNodeResourceGroupId = "/subscriptions/$subscriptionId/resourceGroups/$AksNodeResourceGroup"

Ensure-RoleAssignment -PrincipalId $ControllerIdentityPrincipalId -Scope $aksNodeResourceGroupId -RoleDefinitionId 'acdd72a7-3385-48ef-bd42-f606fba81ae7'
Ensure-RoleAssignment -PrincipalId $ControllerIdentityPrincipalId -Scope $aksNodeResourceGroupId -RoleDefinitionId 'fbc52c3f-28ad-4303-a892-8a056630b8f1'
Ensure-RoleAssignment -PrincipalId $ControllerIdentityPrincipalId -Scope $AgcSubnetId -RoleDefinitionId '4d97b98b-1d4f-4787-a291-c67834d212e7'

az aks get-credentials --resource-group $ResourceGroup --name $AksClusterName --overwrite-existing --only-show-errors | Out-Null

$releaseStatus = $null
try {
    $releaseStatus = helm status alb-controller --namespace azure-alb-system 2>$null
} catch {
    $releaseStatus = $null
}

$helmArgs = @(
    'upgrade'
    '--install'
    'alb-controller'
    'oci://mcr.microsoft.com/application-lb/charts/alb-controller'
    '--namespace'
    'azure-alb-system'
    '--create-namespace'
    '--version'
    '1.9.13'
    '--set'
    'albController.namespace=azure-alb-system'
    '--set'
    "albController.podIdentity.clientID=$ControllerIdentityClientId"
)

helm @helmArgs | Out-Null

kubectl rollout status deployment/alb-controller -n azure-alb-system --timeout=300s | Out-Null
kubectl get gatewayclass azure-alb-external -o name | Out-Null

if ($releaseStatus) {
    Write-Host 'AGC ALB controller is up to date.'
} else {
    Write-Host 'AGC ALB controller installed successfully.'
}