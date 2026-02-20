param(
    [Parameter(Mandatory = $true)]
    [string]$ServiceName
)

$namespace = if ($env:K8S_NAMESPACE) { $env:K8S_NAMESPACE } else { "holiday-peak" }
$imagePrefix = if ($env:IMAGE_PREFIX) { $env:IMAGE_PREFIX } else { "ghcr.io/azure-samples" }
$imageTag = if ($env:IMAGE_TAG) { $env:IMAGE_TAG } else { "latest" }
$kedaEnabled = if ($env:KEDA_ENABLED) { $env:KEDA_ENABLED } else { "false" }

$repoRoot = Resolve-Path "$PSScriptRoot\..\..\.."
$chartPath = Join-Path $repoRoot ".kubernetes\chart"
$outDir = Join-Path $repoRoot ".kubernetes\rendered\$ServiceName"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$rendered = Join-Path $outDir "all.yaml"

& helm template $ServiceName $chartPath `
  --namespace $namespace `
  --set "serviceName=$ServiceName" `
  --set "image.repository=$imagePrefix/$ServiceName" `
  --set "image.tag=$imageTag" `
  --set "keda.enabled=$kedaEnabled" | Out-File -FilePath $rendered -Encoding utf8

Write-Host "Rendered Helm manifests to $rendered"
