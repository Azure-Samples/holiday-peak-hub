param(
    [Parameter(Mandatory = $true)]
    [string]$ServiceName
)

$namespace = if ($ServiceName -eq "crud-service") {
    if ($env:K8S_CRUD_NAMESPACE) { $env:K8S_CRUD_NAMESPACE }
    elseif ($env:K8S_NAMESPACE) { $env:K8S_NAMESPACE }
    else { "holiday-peak-crud" }
} else {
    if ($env:K8S_AGENTS_NAMESPACE) { $env:K8S_AGENTS_NAMESPACE }
    elseif ($env:K8S_NAMESPACE) { $env:K8S_NAMESPACE }
    else { "holiday-peak-agents" }
}
$imagePrefix = if ($env:IMAGE_PREFIX) { $env:IMAGE_PREFIX } else { "ghcr.io/azure-samples" }
$imageTag = if ($env:IMAGE_TAG) { $env:IMAGE_TAG } else { "latest" }
$imageDigest = if ($env:IMAGE_DIGEST) { $env:IMAGE_DIGEST } else { "" }
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
$selectorIncludeCanary = "false"

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
    # Dev profile prioritizes fast iteration while preserving dependency-aware readiness.
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

if ($ServiceName -eq "truth-ingestion") {
  # Preserve legacy selector shape for existing truth-ingestion deployment.
  $selectorIncludeCanary = "true"
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
  if ($serviceImage.Contains('@')) {
    $parts = $serviceImage.Split('@', 2)
    $imagePrefix = $parts[0]
    $imageDigest = $parts[1]
    $imageTag = 'latest'
  } else {
    $lastColon = $serviceImage.LastIndexOf(':')
    if ($lastColon -gt 0) {
      $imagePrefix = $serviceImage.Substring(0, $lastColon)
      $imageTag = $serviceImage.Substring($lastColon + 1)
    } else {
      $imagePrefix = $serviceImage
    }
    $imageDigest = ''
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
  '--set-string',
  'agc.sharedResources.listeners[0].name=http',
  '--set-string',
  'agc.sharedResources.listeners[0].protocol=HTTP',
  '--set',
  'agc.sharedResources.listeners[0].port=80',
  '--set',
  "canary.enabled=$canaryEnabled",
  '--set',
  "deployment.selectorIncludeCanary=$selectorIncludeCanary",
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

if ($imageDigest) {
  $helmArgs += @('--set-string', "image.digest=$imageDigest")
} else {
  $helmArgs += @('--set', "image.tag=$imageTag")
}

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
  $helmArgs += @('--set', "agc.paths[0].path=/$ServiceName")
  $helmArgs += @('--set', 'agc.paths[0].pathType=PathPrefix')
  $helmArgs += @('--set', 'agc.paths[0].rewritePrefixMatch=/')
}

if ($ServiceName -eq 'truth-export') {
  # Override legacy in-cluster startup script with deterministic image entrypoint.
  $helmArgs += @('--set-string', 'container.command[0]=uvicorn')
  $helmArgs += @('--set-string', 'container.args[0]=truth_export.main:app')
  $helmArgs += @('--set-string', 'container.args[1]=--host')
  $helmArgs += @('--set-string', 'container.args[2]=0.0.0.0')
  $helmArgs += @('--set-string', 'container.args[3]=--port')
  $helmArgs += @('--set-string', 'container.args[4]=8000')
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

# Workload Identity — bind pods to the correct UAMI via ServiceAccount
# Batch 1 agents (first 20) use AGENTS_WORKLOAD_CLIENT_ID; batch 2 (overflow) use AGENTS2_WORKLOAD_CLIENT_ID.
$helmArgs += @('--set', 'serviceAccount.create=true')
if ($ServiceName -eq 'crud-service') {
  $workloadClientId = $env:CRUD_WORKLOAD_CLIENT_ID
} else {
  $batch2Services = @(
    'product-management-normalization-classification',
    'search-enrichment-agent',
    'truth-enrichment',
    'truth-export',
    'truth-hitl',
    'truth-ingestion'
  )
  if ($batch2Services -contains $ServiceName) {
    $workloadClientId = if ($env:AGENTS2_WORKLOAD_CLIENT_ID) { $env:AGENTS2_WORKLOAD_CLIENT_ID } else { $env:AGENTS_WORKLOAD_CLIENT_ID }
  } else {
    $workloadClientId = $env:AGENTS_WORKLOAD_CLIENT_ID
  }
}
if ($workloadClientId) {
  $helmArgs += @('--set-string', "serviceAccount.clientId=$workloadClientId")
}

$isAgentService = $ServiceName -ne "crud-service"
$resolvedFoundryAgentNameFast = $env:FOUNDRY_AGENT_NAME_FAST
$resolvedFoundryAgentNameRich = $env:FOUNDRY_AGENT_NAME_RICH
$resolvedModelDeploymentFast = $env:MODEL_DEPLOYMENT_NAME_FAST
$resolvedModelDeploymentRich = $env:MODEL_DEPLOYMENT_NAME_RICH

if ($isAgentService) {
  if ([string]::IsNullOrWhiteSpace($resolvedFoundryAgentNameFast)) {
    $resolvedFoundryAgentNameFast = "$ServiceName-fast"
  }
  if ([string]::IsNullOrWhiteSpace($resolvedFoundryAgentNameRich)) {
    $resolvedFoundryAgentNameRich = "$ServiceName-rich"
  }
  if ([string]::IsNullOrWhiteSpace($resolvedModelDeploymentFast)) {
    $resolvedModelDeploymentFast = "gpt-5-nano"
  }
  if ([string]::IsNullOrWhiteSpace($resolvedModelDeploymentRich)) {
    $resolvedModelDeploymentRich = "gpt-5"
  }

  if (-not [string]::IsNullOrWhiteSpace($env:FOUNDRY_AGENT_ID_FAST) -and $env:FOUNDRY_AGENT_ID_FAST.EndsWith("-pending")) {
    throw "Invalid FOUNDRY_AGENT_ID_FAST for ${ServiceName}: placeholder ids are not deployable."
  }
  if (-not [string]::IsNullOrWhiteSpace($env:FOUNDRY_AGENT_ID_RICH) -and $env:FOUNDRY_AGENT_ID_RICH.EndsWith("-pending")) {
    throw "Invalid FOUNDRY_AGENT_ID_RICH for ${ServiceName}: placeholder ids are not deployable."
  }

  if ([string]::IsNullOrWhiteSpace($env:FOUNDRY_AGENT_ID_FAST) -and [string]::IsNullOrWhiteSpace($resolvedFoundryAgentNameFast)) {
    throw "Missing Foundry fast-role definition for $ServiceName (set FOUNDRY_AGENT_ID_FAST or FOUNDRY_AGENT_NAME_FAST)."
  }
  if ([string]::IsNullOrWhiteSpace($env:FOUNDRY_AGENT_ID_RICH) -and [string]::IsNullOrWhiteSpace($resolvedFoundryAgentNameRich)) {
    throw "Missing Foundry rich-role definition for $ServiceName (set FOUNDRY_AGENT_ID_RICH or FOUNDRY_AGENT_NAME_RICH)."
  }
}

$resolvedPostgresAuthMode = if ($env:POSTGRES_AUTH_MODE) { $env:POSTGRES_AUTH_MODE } else { 'password' }
$resolvedPostgresUser = $env:POSTGRES_USER
$postgresAdminUser = $env:POSTGRES_ADMIN_USER

if ($ServiceName -eq 'crud-service') {
  if ($resolvedPostgresAuthMode -eq 'password' -and -not [string]::IsNullOrWhiteSpace($postgresAdminUser)) {
    $resolvedPostgresUser = $postgresAdminUser
  }

  if (
    $resolvedPostgresAuthMode -eq 'entra' -and
    (
      [string]::IsNullOrWhiteSpace($resolvedPostgresUser) -or
      $resolvedPostgresUser -eq 'crud_workload' -or
      $resolvedPostgresUser -eq 'crud_admin' -or
      $resolvedPostgresUser -eq $postgresAdminUser
    )
  ) {
    $aksClusterName = if ($env:AZURE_AKS_CLUSTER_NAME) {
      $env:AZURE_AKS_CLUSTER_NAME
    } elseif ($env:AKS_CLUSTER_NAME) {
      $env:AKS_CLUSTER_NAME
    } else {
      ''
    }

    if (-not [string]::IsNullOrWhiteSpace($aksClusterName)) {
      $resolvedPostgresUser = "$aksClusterName-agentpool"
    }
  }
}

$resolvedRedisHost = $env:REDIS_HOST
if (-not [string]::IsNullOrWhiteSpace($resolvedRedisHost) -and -not $resolvedRedisHost.Contains('.')) {
  $resolvedRedisHost = "$resolvedRedisHost.redis.cache.windows.net"
}
$resolvedRedisPasswordSecretName = if ($env:REDIS_PASSWORD_SECRET_NAME) { $env:REDIS_PASSWORD_SECRET_NAME } else { 'redis-primary-key' }
$resolvedRedisUrl = $null
if (-not [string]::IsNullOrWhiteSpace($env:REDIS_URL)) {
  $candidateRedisUrl = $env:REDIS_URL.Trim()
  $hasEmbeddedRedisCredentials = $candidateRedisUrl -match '^[^:]+://[^/@\s]+@'
  if ($hasEmbeddedRedisCredentials -or [string]::IsNullOrWhiteSpace($resolvedRedisHost)) {
    $resolvedRedisUrl = $candidateRedisUrl
  }
}
$resolvedAiSearchAuthMode = if ($env:AI_SEARCH_AUTH_MODE) { $env:AI_SEARCH_AUTH_MODE } else { '' }
$shouldInjectAiSearchKey = -not [string]::IsNullOrWhiteSpace($resolvedAiSearchAuthMode) -and $resolvedAiSearchAuthMode.Trim().Equals('api_key', [System.StringComparison]::OrdinalIgnoreCase)
$resolvedAiSearchKey = if ($shouldInjectAiSearchKey) { $env:AI_SEARCH_KEY } else { $null }

$envMappings = @{
  # Database
  POSTGRES_HOST = $env:POSTGRES_HOST
  POSTGRES_AUTH_MODE = $resolvedPostgresAuthMode
  POSTGRES_USER = $resolvedPostgresUser
  POSTGRES_PASSWORD = $env:POSTGRES_PASSWORD
  POSTGRES_DATABASE = $env:POSTGRES_DATABASE
  POSTGRES_PORT = $env:POSTGRES_PORT
  POSTGRES_SSL = $env:POSTGRES_SSL

  # Messaging & Infrastructure
  KEY_VAULT_URI = $env:KEY_VAULT_URI
  REDIS_HOST = $resolvedRedisHost
  REDIS_PASSWORD = $env:REDIS_PASSWORD
  REDIS_PASSWORD_SECRET_NAME = $resolvedRedisPasswordSecretName
  AZURE_CLIENT_ID = if ($workloadClientId) { $workloadClientId } else { $env:AZURE_CLIENT_ID }
  AZURE_TENANT_ID = $env:AZURE_TENANT_ID

  # Azure AI Foundry
  PROJECT_ENDPOINT = $env:PROJECT_ENDPOINT
  PROJECT_NAME = $env:PROJECT_NAME
  FOUNDRY_AGENT_ID_FAST = $env:FOUNDRY_AGENT_ID_FAST
  FOUNDRY_AGENT_ID_RICH = $env:FOUNDRY_AGENT_ID_RICH
  FOUNDRY_AGENT_NAME_FAST = $resolvedFoundryAgentNameFast
  FOUNDRY_AGENT_NAME_RICH = $resolvedFoundryAgentNameRich
  MODEL_DEPLOYMENT_NAME_FAST = $resolvedModelDeploymentFast
  MODEL_DEPLOYMENT_NAME_RICH = $resolvedModelDeploymentRich
  FOUNDRY_STREAM = $env:FOUNDRY_STREAM
  FOUNDRY_STRICT_ENFORCEMENT = $env:FOUNDRY_STRICT_ENFORCEMENT
  FOUNDRY_AUTO_ENSURE_ON_STARTUP = $env:FOUNDRY_AUTO_ENSURE_ON_STARTUP

  # Azure AI Search
  AI_SEARCH_ENDPOINT = $env:AI_SEARCH_ENDPOINT
  AI_SEARCH_INDEX = $env:AI_SEARCH_INDEX
  AI_SEARCH_VECTOR_INDEX = $env:AI_SEARCH_VECTOR_INDEX
  AI_SEARCH_INDEXER_NAME = $env:AI_SEARCH_INDEXER_NAME
  AI_SEARCH_AUTH_MODE = $resolvedAiSearchAuthMode
  CATALOG_SEARCH_REQUIRE_AI_SEARCH = $env:CATALOG_SEARCH_REQUIRE_AI_SEARCH
  AI_SEARCH_KEY = $resolvedAiSearchKey
  EMBEDDING_DEPLOYMENT_NAME = $env:EMBEDDING_DEPLOYMENT_NAME

  # Memory tiers
  REDIS_URL = $resolvedRedisUrl
  COSMOS_ACCOUNT_URI = $env:COSMOS_ACCOUNT_URI
  COSMOS_DATABASE = $env:COSMOS_DATABASE
  COSMOS_CONTAINER = $env:COSMOS_CONTAINER
  COSMOS_AUDIT_CONTAINER = $env:COSMOS_AUDIT_CONTAINER
  BLOB_ACCOUNT_URL = $env:BLOB_ACCOUNT_URL
  BLOB_CONTAINER = $env:BLOB_CONTAINER

  # Observability
  APPLICATIONINSIGHTS_CONNECTION_STRING = $env:APPLICATIONINSIGHTS_CONNECTION_STRING
}

# Cross-namespace CRUD service URL for agent->CRUD communication (ADR-034)
if ($ServiceName -ne "crud-service") {
  $crudNs = if ($env:K8S_CRUD_NAMESPACE) { $env:K8S_CRUD_NAMESPACE }
            elseif ($env:K8S_NAMESPACE) { $env:K8S_NAMESPACE }
            else { "holiday-peak-crud" }
  $defaultCrudUrl = "http://crud-service-crud-service.${crudNs}.svc.cluster.local:80"
  $envMappings["CRUD_SERVICE_URL"] = if ($env:CRUD_SERVICE_URL) { $env:CRUD_SERVICE_URL } else { $defaultCrudUrl }
}

$truthServiceEventHubMappings = @{
  "truth-ingestion" = @{ TRUTH_EVENT_HUB_NAME = "ingest-jobs"; TRUTH_EVENT_HUB_CONSUMER_GROUP = "ingestion-group" }
  "truth-enrichment" = @{ TRUTH_EVENT_HUB_NAME = "enrichment-jobs"; TRUTH_EVENT_HUB_CONSUMER_GROUP = "enrichment-engine" }
  "truth-export" = @{ TRUTH_EVENT_HUB_NAME = "export-jobs"; TRUTH_EVENT_HUB_CONSUMER_GROUP = "export-engine" }
  "truth-hitl" = @{ TRUTH_EVENT_HUB_NAME = "hitl-jobs"; TRUTH_EVENT_HUB_CONSUMER_GROUP = "hitl-service" }
}

$platformJobsServiceNames = @(
  "product-management-consistency-validation",
  "search-enrichment-agent"
) + $truthServiceEventHubMappings.Keys

function Assert-RequiredEnvKeys {
  param(
    [string]$TargetService,
    [hashtable]$Mappings,
    [string[]]$RequiredKeys,
    [string]$TargetEnvironment
  )

  $missing = @()
  foreach ($required in $RequiredKeys) {
    $value = $null
    if ($Mappings.ContainsKey($required)) {
      $value = $Mappings[$required]
    }
    if ([string]::IsNullOrWhiteSpace($value)) {
      $missing += $required
    }
  }

  if ($missing.Count -gt 0) {
    $envHint = if ([string]::IsNullOrWhiteSpace($TargetEnvironment)) { "<environment>" } else { $TargetEnvironment }
    throw "Missing required environment variables for ${TargetService}: $($missing -join ', '). Run 'azd provision -e $envHint' with deployShared=true so shared dependencies are exported."
  }
}

$isTruthService = $truthServiceEventHubMappings.ContainsKey($ServiceName)
$isPlatformJobsService = $platformJobsServiceNames -contains $ServiceName
if ($isTruthService) {
  $truthServiceVars = $truthServiceEventHubMappings[$ServiceName]
  foreach ($truthKey in $truthServiceVars.Keys) {
    $envMappings[$truthKey] = $truthServiceVars[$truthKey]
  }

  if ($ServiceName -eq 'truth-ingestion') {
    $ingestionContainer = if ($env:TRUTH_INGESTION_COSMOS_CONTAINER) {
      $env:TRUTH_INGESTION_COSMOS_CONTAINER
    } else {
      'products'
    }
    $ingestionAuditContainer = if ($env:TRUTH_INGESTION_COSMOS_AUDIT_CONTAINER) {
      $env:TRUTH_INGESTION_COSMOS_AUDIT_CONTAINER
    } else {
      'audit'
    }

    $envMappings['COSMOS_CONTAINER'] = $ingestionContainer
    $envMappings['COSMOS_AUDIT_CONTAINER'] = $ingestionAuditContainer
  }
}

if ($isPlatformJobsService) {
  $envMappings['PLATFORM_JOBS_EVENT_HUB_NAMESPACE'] = $env:PLATFORM_JOBS_EVENT_HUB_NAMESPACE
  $envMappings['PLATFORM_JOBS_EVENT_HUB_CONNECTION_STRING'] = $env:PLATFORM_JOBS_EVENT_HUB_CONNECTION_STRING
} else {
  $envMappings['EVENT_HUB_NAMESPACE'] = $env:EVENT_HUB_NAMESPACE
  $envMappings['EVENT_HUB_CONNECTION_STRING'] = $env:EVENT_HUB_CONNECTION_STRING
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

if ($isAgentService) {
  $requiredAgentEnvKeys = @(
    "PROJECT_ENDPOINT",
    "PROJECT_NAME",
    "MODEL_DEPLOYMENT_NAME_FAST",
    "MODEL_DEPLOYMENT_NAME_RICH",
    "COSMOS_ACCOUNT_URI",
    "COSMOS_DATABASE",
    "REDIS_HOST",
    "BLOB_ACCOUNT_URL",
    "KEY_VAULT_URI"
  )

  if ($isPlatformJobsService) {
    $requiredAgentEnvKeys = @("PLATFORM_JOBS_EVENT_HUB_NAMESPACE") + $requiredAgentEnvKeys
  } else {
    $requiredAgentEnvKeys = @("EVENT_HUB_NAMESPACE") + $requiredAgentEnvKeys
  }

  Assert-RequiredEnvKeys -TargetService $ServiceName -Mappings $envMappings -RequiredKeys $requiredAgentEnvKeys -TargetEnvironment $deployEnv
}

if ($ServiceName -in @("ecommerce-catalog-search", "search-enrichment-agent")) {
  Assert-RequiredEnvKeys -TargetService $ServiceName -Mappings $envMappings -RequiredKeys @(
    "AI_SEARCH_ENDPOINT",
    "AI_SEARCH_INDEX",
    "AI_SEARCH_VECTOR_INDEX",
    "AI_SEARCH_INDEXER_NAME",
    "EMBEDDING_DEPLOYMENT_NAME"
  ) -TargetEnvironment $deployEnv
}

foreach ($key in $envMappings.Keys) {
  $value = $envMappings[$key]
  if ($value) {
    $helmArgs += @('--set-string', "env.$key=$value")
  }
}

& helm @helmArgs | Out-File -FilePath $rendered -Encoding utf8

if ($isAgentService) {
  $requiredFoundryRenderedKeys = @(
    "PROJECT_ENDPOINT",
    "PROJECT_NAME",
    "MODEL_DEPLOYMENT_NAME_FAST",
    "MODEL_DEPLOYMENT_NAME_RICH",
    "FOUNDRY_AGENT_NAME_FAST",
    "FOUNDRY_AGENT_NAME_RICH",
    "FOUNDRY_STRICT_ENFORCEMENT",
    "FOUNDRY_AUTO_ENSURE_ON_STARTUP"
  )

  foreach ($foundryKey in $requiredFoundryRenderedKeys) {
    $present = Select-String -Path $rendered -SimpleMatch "name: $foundryKey" -Quiet
    if (-not $present) {
      throw "Rendered manifest missing Foundry env key '$foundryKey' for $ServiceName"
    }
  }

  if (-not [string]::IsNullOrWhiteSpace($env:FOUNDRY_AGENT_ID_FAST)) {
    $presentFastId = Select-String -Path $rendered -SimpleMatch "name: FOUNDRY_AGENT_ID_FAST" -Quiet
    if (-not $presentFastId) {
      throw "Rendered manifest missing Foundry env key 'FOUNDRY_AGENT_ID_FAST' for $ServiceName"
    }
  }

  if (-not [string]::IsNullOrWhiteSpace($env:FOUNDRY_AGENT_ID_RICH)) {
    $presentRichId = Select-String -Path $rendered -SimpleMatch "name: FOUNDRY_AGENT_ID_RICH" -Quiet
    if (-not $presentRichId) {
      throw "Rendered manifest missing Foundry env key 'FOUNDRY_AGENT_ID_RICH' for $ServiceName"
    }
  }
}

if ($isTruthService) {
  $requiredRenderedKeys = @(
    "PLATFORM_JOBS_EVENT_HUB_NAMESPACE",
    "PROJECT_ENDPOINT",
    "COSMOS_ACCOUNT_URI",
    "COSMOS_DATABASE",
    "TRUTH_EVENT_HUB_NAME",
    "TRUTH_EVENT_HUB_CONSUMER_GROUP"
  )
  if ($ServiceName -eq 'truth-ingestion') {
    $requiredRenderedKeys += @(
      'COSMOS_CONTAINER',
      'COSMOS_AUDIT_CONTAINER'
    )
  }
  foreach ($renderedKey in $requiredRenderedKeys) {
    $present = Select-String -Path $rendered -SimpleMatch "name: $renderedKey" -Quiet
    if (-not $present) {
      throw "Rendered manifest missing env key '$renderedKey' for $ServiceName"
    }
  }
}

if ($isPlatformJobsService) {
  foreach ($platformKey in @('PLATFORM_JOBS_EVENT_HUB_NAMESPACE')) {
    $present = Select-String -Path $rendered -SimpleMatch "name: $platformKey" -Quiet
    if (-not $present) {
      throw "Rendered manifest missing env key '$platformKey' for $ServiceName"
    }
  }

  if (-not [string]::IsNullOrWhiteSpace($env:PLATFORM_JOBS_EVENT_HUB_CONNECTION_STRING)) {
    $presentConnectionString = Select-String -Path $rendered -SimpleMatch 'name: PLATFORM_JOBS_EVENT_HUB_CONNECTION_STRING' -Quiet
    if (-not $presentConnectionString) {
      throw "Rendered manifest missing env key 'PLATFORM_JOBS_EVENT_HUB_CONNECTION_STRING' for $ServiceName"
    }
  }
}

if ($ServiceName -in @("ecommerce-catalog-search", "search-enrichment-agent")) {
  $requiredSearchRenderedKeys = @(
    "AI_SEARCH_ENDPOINT",
    "AI_SEARCH_INDEX",
    "AI_SEARCH_VECTOR_INDEX",
    "AI_SEARCH_INDEXER_NAME",
    "EMBEDDING_DEPLOYMENT_NAME",
    "SEARCH_ENRICHMENT_EVENT_HUB_NAME",
    "SEARCH_ENRICHMENT_EVENT_HUB_CONSUMER_GROUP"
  )
  foreach ($searchKey in $requiredSearchRenderedKeys) {
    $present = Select-String -Path $rendered -SimpleMatch "name: $searchKey" -Quiet
    if (-not $present) {
      throw "Rendered manifest missing env key '$searchKey' for $ServiceName"
    }
  }
}

Write-Host "Rendered Helm manifests to $rendered"
