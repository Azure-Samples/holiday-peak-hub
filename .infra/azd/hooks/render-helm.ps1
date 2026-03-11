param(
    [Parameter(Mandatory = $true)]
    [string]$ServiceName
)

$namespace = if ($env:K8S_NAMESPACE) { $env:K8S_NAMESPACE } else { "holiday-peak" }
$imagePrefix = if ($env:IMAGE_PREFIX) { $env:IMAGE_PREFIX } else { "ghcr.io/azure-samples" }
$imageTag = if ($env:IMAGE_TAG) { $env:IMAGE_TAG } else { "latest" }
$kedaEnabled = if ($env:KEDA_ENABLED) { $env:KEDA_ENABLED } else { "false" }
$ingressEnabled = if ($env:INGRESS_ENABLED) { $env:INGRESS_ENABLED } else { "true" }
$ingressClassName = if ($env:INGRESS_CLASS_NAME) { $env:INGRESS_CLASS_NAME } else { "webapprouting.kubernetes.azure.com" }
$canaryEnabled = if ($env:CANARY_ENABLED) { $env:CANARY_ENABLED } else { "false" }
$readinessPath = "/ready"
$replicaCount = ""
$deployEnv = if ($env:DEPLOY_ENV) { $env:DEPLOY_ENV } elseif ($env:AZURE_ENV_NAME) { $env:AZURE_ENV_NAME } else { "" }

$nodePool = "agents"
$workloadType = "agents"
$pdbEnabled = "false"
$pdbMinAvailable = ""
$maxUnavailable = ""
$maxSurge = ""

if ($ServiceName -eq "crud-service") {
  $nodePool = "crud"
  $workloadType = "crud"
  if ($deployEnv -in @("dev", "development", "local")) {
    # Dev profile prioritizes fast iteration over strict availability.
    $readinessPath = "/health"
    $replicaCount = "1"
    $pdbEnabled = "false"
    $pdbMinAvailable = ""
    $maxUnavailable = "100%"
    $maxSurge = "1"
  } else {
    $pdbEnabled = "true"
    $pdbMinAvailable = "1"
    $maxUnavailable = "0"
    $maxSurge = "1"
  }
}

$serviceImageVarName = "SERVICE_$($ServiceName.ToUpper().Replace('-', '_'))_IMAGE_NAME"
$serviceImage = [Environment]::GetEnvironmentVariable($serviceImageVarName)

if ($serviceImage) {
  $lastColon = $serviceImage.LastIndexOf(':')
  if ($lastColon -gt 0) {
    $imagePrefix = $serviceImage.Substring(0, $lastColon)
    $imageTag = $serviceImage.Substring($lastColon + 1)
  } else {
    $imagePrefix = $serviceImage
  }
} else {
  $imagePrefix = "$imagePrefix/$ServiceName"
}

$repoRoot = Resolve-Path "$PSScriptRoot\..\..\.."
$chartPath = Join-Path $repoRoot ".kubernetes\chart"
$outDir = Join-Path $repoRoot ".kubernetes\rendered\$ServiceName"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$rendered = Join-Path $outDir "all.yaml"

$helmArgs = @(
  'template',
  $ServiceName,
  $chartPath,
  '--namespace',
  $namespace,
  '--set',
  "serviceName=$ServiceName",
  '--set',
  "image.repository=$imagePrefix",
  '--set',
  "image.tag=$imageTag",
  '--set',
  "keda.enabled=$kedaEnabled",
  '--set',
  "ingress.enabled=$ingressEnabled",
  '--set-string',
  "ingress.className=$ingressClassName",
  '--set',
  "canary.enabled=$canaryEnabled",
  '--set',
  "probes.readiness.path=$readinessPath",
  '--set',
  "nodeSelector.agentpool=$nodePool",
  '--set',
  "tolerations[0].key=workload",
  '--set',
  "tolerations[0].operator=Equal",
  '--set',
  "tolerations[0].value=$workloadType",
  '--set',
  "tolerations[0].effect=NoSchedule"
)

if ($replicaCount) {
  $helmArgs += @('--set', "replicaCount=$replicaCount")
}

if ($maxUnavailable) {
  $helmArgs += @('--set-string', "availability.rollingUpdate.maxUnavailable=$maxUnavailable")
}

if ($maxSurge) {
  $helmArgs += @('--set-string', "availability.rollingUpdate.maxSurge=$maxSurge")
}

if ($pdbEnabled -eq "true") {
  $helmArgs += @('--set', "pdb.enabled=true")
  if ($pdbMinAvailable) {
    $helmArgs += @('--set-string', "pdb.minAvailable=$pdbMinAvailable")
  }
}

$envMappings = @{
  # Database
  POSTGRES_HOST = $env:POSTGRES_HOST
  POSTGRES_USER = $env:POSTGRES_USER
  POSTGRES_PASSWORD = $env:POSTGRES_PASSWORD
  POSTGRES_DATABASE = $env:POSTGRES_DATABASE
  POSTGRES_PORT = $env:POSTGRES_PORT
  POSTGRES_SSL = $env:POSTGRES_SSL

  # Messaging & Infrastructure
  EVENT_HUB_NAMESPACE = $env:EVENT_HUB_NAMESPACE
  KEY_VAULT_URI = $env:KEY_VAULT_URI
  REDIS_HOST = $env:REDIS_HOST
  AZURE_CLIENT_ID = $env:AZURE_CLIENT_ID
  AZURE_TENANT_ID = $env:AZURE_TENANT_ID

  # Azure AI Foundry
  PROJECT_ENDPOINT = $env:PROJECT_ENDPOINT
  PROJECT_NAME = $env:PROJECT_NAME
  FOUNDRY_AGENT_ID_FAST = $env:FOUNDRY_AGENT_ID_FAST
  FOUNDRY_AGENT_ID_RICH = $env:FOUNDRY_AGENT_ID_RICH
  MODEL_DEPLOYMENT_NAME_FAST = $env:MODEL_DEPLOYMENT_NAME_FAST
  MODEL_DEPLOYMENT_NAME_RICH = $env:MODEL_DEPLOYMENT_NAME_RICH
  FOUNDRY_STREAM = $env:FOUNDRY_STREAM
  FOUNDRY_STRICT_ENFORCEMENT = $env:FOUNDRY_STRICT_ENFORCEMENT
  FOUNDRY_AUTO_ENSURE_ON_STARTUP = $env:FOUNDRY_AUTO_ENSURE_ON_STARTUP

  # Memory tiers
  REDIS_URL = $env:REDIS_URL
  COSMOS_ACCOUNT_URI = $env:COSMOS_ACCOUNT_URI
  COSMOS_DATABASE = $env:COSMOS_DATABASE
  COSMOS_CONTAINER = $env:COSMOS_CONTAINER
  BLOB_ACCOUNT_URL = $env:BLOB_ACCOUNT_URL
  BLOB_CONTAINER = $env:BLOB_CONTAINER

  # Observability
  APPLICATIONINSIGHTS_CONNECTION_STRING = $env:APPLICATIONINSIGHTS_CONNECTION_STRING
}

$truthServiceEventHubMappings = @{
  "truth-ingestion" = @{ TRUTH_EVENT_HUB_NAME = "ingest-jobs"; TRUTH_EVENT_HUB_CONSUMER_GROUP = "ingestion-group" }
  "truth-enrichment" = @{ TRUTH_EVENT_HUB_NAME = "enrichment-jobs"; TRUTH_EVENT_HUB_CONSUMER_GROUP = "enrichment-engine" }
  "truth-export" = @{ TRUTH_EVENT_HUB_NAME = "export-jobs"; TRUTH_EVENT_HUB_CONSUMER_GROUP = "export-engine" }
  "truth-hitl" = @{ TRUTH_EVENT_HUB_NAME = "hitl-jobs"; TRUTH_EVENT_HUB_CONSUMER_GROUP = "hitl-service" }
}

$isTruthService = $truthServiceEventHubMappings.ContainsKey($ServiceName)
if ($isTruthService) {
  $truthServiceVars = $truthServiceEventHubMappings[$ServiceName]
  foreach ($truthKey in $truthServiceVars.Keys) {
    $envMappings[$truthKey] = $truthServiceVars[$truthKey]
  }

  $requiredTruthEnv = @("EVENT_HUB_NAMESPACE", "PROJECT_ENDPOINT", "COSMOS_ACCOUNT_URI", "COSMOS_DATABASE")
  $missingTruthEnv = @()
  foreach ($requiredKey in $requiredTruthEnv) {
    $requiredValue = $envMappings[$requiredKey]
    if ([string]::IsNullOrWhiteSpace($requiredValue)) {
      $missingTruthEnv += $requiredKey
    }
  }
  if ($missingTruthEnv.Count -gt 0) {
    throw "Missing required environment variables for ${ServiceName}: $($missingTruthEnv -join ', ')"
  }
}

foreach ($key in $envMappings.Keys) {
  $value = $envMappings[$key]
  if ($value) {
    $helmArgs += @('--set-string', "env.$key=$value")
  }
}

& helm @helmArgs | Out-File -FilePath $rendered -Encoding utf8

if ($isTruthService) {
  $requiredRenderedKeys = @(
    "EVENT_HUB_NAMESPACE",
    "PROJECT_ENDPOINT",
    "COSMOS_ACCOUNT_URI",
    "COSMOS_DATABASE",
    "TRUTH_EVENT_HUB_NAME",
    "TRUTH_EVENT_HUB_CONSUMER_GROUP"
  )
  foreach ($renderedKey in $requiredRenderedKeys) {
    $present = Select-String -Path $rendered -SimpleMatch "name: $renderedKey" -Quiet
    if (-not $present) {
      throw "Rendered manifest missing env key '$renderedKey' for $ServiceName"
    }
  }
}

Write-Host "Rendered Helm manifests to $rendered"
