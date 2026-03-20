param(
    [Parameter(Mandatory = $true)]
    [string]$ServiceName
)

$namespace = if ($env:K8S_NAMESPACE) { $env:K8S_NAMESPACE } else { "holiday-peak" }
$imagePrefix = if ($env:IMAGE_PREFIX) { $env:IMAGE_PREFIX } else { "ghcr.io/azure-samples" }
$imageTag = if ($env:IMAGE_TAG) { $env:IMAGE_TAG } else { "latest" }
$kedaEnabled = if ($env:KEDA_ENABLED) { $env:KEDA_ENABLED } else { "false" }
$publicationMode = if ($env:PUBLICATION_MODE) { $env:PUBLICATION_MODE } else { "agc" }
$legacyIngressEnabled = "false"
$legacyIngressClassName = if ($env:LEGACY_INGRESS_CLASS_NAME) { $env:LEGACY_INGRESS_CLASS_NAME } elseif ($env:INGRESS_CLASS_NAME) { $env:INGRESS_CLASS_NAME } else { "" }
$agcEnabled = "false"
$agcGatewayClassName = if ($env:AGC_GATEWAY_CLASS) { $env:AGC_GATEWAY_CLASS } else { "azure-alb-external" }
$agcSubnetId = if ($env:AGC_SUBNET_ID) { $env:AGC_SUBNET_ID } else { "" }
$agcSharedNamespace = if ($env:AGC_SHARED_NAMESPACE) { $env:AGC_SHARED_NAMESPACE } else { $namespace }
$agcSharedGatewayName = if ($env:AGC_SHARED_GATEWAY_NAME) { $env:AGC_SHARED_GATEWAY_NAME } else { "holiday-peak-agc" }
$agcSharedAlbName = if ($env:AGC_SHARED_ALB_NAME) { $env:AGC_SHARED_ALB_NAME } else { $agcSharedGatewayName }
$agcSharedResourcesCreate = if ($env:AGC_SHARED_RESOURCES_CREATE) { $env:AGC_SHARED_RESOURCES_CREATE } else { "false" }
$agcHostname = if ($env:AGC_HOSTNAME) { $env:AGC_HOSTNAME } else { "" }
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

switch ($publicationMode.ToLowerInvariant()) {
  'legacy' {
    $legacyIngressEnabled = 'true'
  }
  'agc' {
    $agcEnabled = 'true'
  }
  'dual' {
    $legacyIngressEnabled = 'true'
    $agcEnabled = 'true'
  }
  'none' {
    $legacyIngressEnabled = 'false'
    $agcEnabled = 'false'
  }
  default {
    throw "Unsupported PUBLICATION_MODE '$publicationMode'. Expected one of legacy, agc, dual, none."
  }
}

if ($legacyIngressEnabled -eq 'true' -and -not $legacyIngressClassName) {
  throw "LEGACY_INGRESS_CLASS_NAME or INGRESS_CLASS_NAME must be set when PUBLICATION_MODE is legacy or dual."
}

if ($agcEnabled -eq 'true' -and -not $env:AGC_SHARED_RESOURCES_CREATE -and $ServiceName -eq 'crud-service') {
  $agcSharedResourcesCreate = 'true'
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
  "ingress.enabled=$legacyIngressEnabled",
  '--set-string',
  "ingress.className=$legacyIngressClassName",
  '--set',
  "agc.enabled=$agcEnabled",
  '--set-string',
  "agc.gatewayClassName=$agcGatewayClassName",
  '--set',
  "agc.sharedResources.create=$agcSharedResourcesCreate",
  '--set-string',
  "agc.sharedResources.namespace=$agcSharedNamespace",
  '--set-string',
  "agc.sharedResources.gatewayName=$agcSharedGatewayName",
  '--set-string',
  "agc.sharedResources.applicationLoadBalancerName=$agcSharedAlbName",
  '--set-string',
  "agc.sharedResources.subnetId=$agcSubnetId",
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

if ($ServiceName -eq "crud-service") {
  $helmArgs += @('--set', 'ingress.paths[0].path=/health')
  $helmArgs += @('--set', 'ingress.paths[0].pathType=Prefix')
  $helmArgs += @('--set', 'ingress.paths[1].path=/api')
  $helmArgs += @('--set', 'ingress.paths[1].pathType=Prefix')
  $helmArgs += @('--set', 'agc.paths[0].path=/health')
  $helmArgs += @('--set', 'agc.paths[0].pathType=PathPrefix')
  $helmArgs += @('--set', 'agc.paths[1].path=/api')
  $helmArgs += @('--set', 'agc.paths[1].pathType=PathPrefix')
} else {
  $helmArgs += @('--set', 'agc.paths[0].path=/health')
  $helmArgs += @('--set', 'agc.paths[0].pathType=PathPrefix')
  $helmArgs += @('--set', 'agc.paths[1].path=/invoke')
  $helmArgs += @('--set', 'agc.paths[1].pathType=PathPrefix')
  $helmArgs += @('--set', 'agc.paths[2].path=/mcp')
  $helmArgs += @('--set', 'agc.paths[2].pathType=PathPrefix')
}

if ($agcHostname) {
  $helmArgs += @('--set-string', "agc.hostnames[0]=$agcHostname")
  $helmArgs += @('--set-string', "agc.sharedResources.listeners[0].hostname=$agcHostname")
}

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

  # Azure AI Search
  AI_SEARCH_ENDPOINT = $env:AI_SEARCH_ENDPOINT
  AI_SEARCH_INDEX = $env:AI_SEARCH_INDEX
  AI_SEARCH_VECTOR_INDEX = $env:AI_SEARCH_VECTOR_INDEX
  AI_SEARCH_INDEXER_NAME = $env:AI_SEARCH_INDEXER_NAME
  AI_SEARCH_AUTH_MODE = $env:AI_SEARCH_AUTH_MODE
  AI_SEARCH_KEY = $env:AI_SEARCH_KEY
  EMBEDDING_DEPLOYMENT_NAME = $env:EMBEDDING_DEPLOYMENT_NAME

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

if ($ServiceName -eq "ecommerce-catalog-search") {
  $searchEnrichmentEventHubName = $env:SEARCH_ENRICHMENT_EVENT_HUB_NAME
  if ([string]::IsNullOrWhiteSpace($searchEnrichmentEventHubName)) {
    $searchEnrichmentEventHubName = "search-enrichment-jobs"
  }

  $searchEnrichmentConsumerGroup = $env:SEARCH_ENRICHMENT_EVENT_HUB_CONSUMER_GROUP
  if ([string]::IsNullOrWhiteSpace($searchEnrichmentConsumerGroup)) {
    $searchEnrichmentConsumerGroup = "search-enrichment-consumer"
  }

  $envMappings["SEARCH_ENRICHMENT_EVENT_HUB_NAME"] = $searchEnrichmentEventHubName
  $envMappings["SEARCH_ENRICHMENT_EVENT_HUB_CONSUMER_GROUP"] = $searchEnrichmentConsumerGroup
}

if ($ServiceName -eq "search-enrichment-agent") {
  $searchEnrichmentEventHubName = $env:SEARCH_ENRICHMENT_EVENT_HUB_NAME
  if ([string]::IsNullOrWhiteSpace($searchEnrichmentEventHubName)) {
    $searchEnrichmentEventHubName = "search-enrichment-jobs"
  }

  $searchEnrichmentConsumerGroup = $env:SEARCH_ENRICHMENT_EVENT_HUB_CONSUMER_GROUP
  if ([string]::IsNullOrWhiteSpace($searchEnrichmentConsumerGroup)) {
    $searchEnrichmentConsumerGroup = "search-enrichment-consumer"
  }

  $envMappings["SEARCH_ENRICHMENT_EVENT_HUB_NAME"] = $searchEnrichmentEventHubName
  $envMappings["SEARCH_ENRICHMENT_EVENT_HUB_CONSUMER_GROUP"] = $searchEnrichmentConsumerGroup
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
