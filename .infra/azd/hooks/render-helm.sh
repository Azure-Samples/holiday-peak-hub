#!/usr/bin/env sh
set -eu

SERVICE_NAME="$1"

# Namespace routing: CRUD goes to holiday-peak-crud, agents to holiday-peak-agents.
# ADR-034: Namespace Isolation Strategy
if [ "$SERVICE_NAME" = "crud-service" ]; then
  NAMESPACE="${K8S_CRUD_NAMESPACE:-${K8S_NAMESPACE:-holiday-peak-crud}}"
else
  NAMESPACE="${K8S_AGENTS_NAMESPACE:-${K8S_NAMESPACE:-holiday-peak-agents}}"
fi
IMAGE_PREFIX="${IMAGE_PREFIX:-ghcr.io/azure-samples}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
IMAGE_DIGEST="${IMAGE_DIGEST:-}"
KEDA_ENABLED="${KEDA_ENABLED:-false}"
PUBLICATION_MODE="${PUBLICATION_MODE:-agc}"
LEGACY_INGRESS_ENABLED="false"
LEGACY_INGRESS_CLASS_NAME="${LEGACY_INGRESS_CLASS_NAME:-${INGRESS_CLASS_NAME:-}}"
AGC_ENABLED="false"
AGC_GATEWAY_CLASS_NAME="${AGC_GATEWAY_CLASS:-azure-alb-external}"
AGC_SUBNET_ID="${AGC_SUBNET_ID:-}"
AGC_SHARED_NAMESPACE="${AGC_SHARED_NAMESPACE:-$NAMESPACE}"
AGC_SHARED_GATEWAY_NAME="${AGC_SHARED_GATEWAY_NAME:-holiday-peak-agc}"
AGC_SHARED_ALB_NAME="${AGC_SHARED_ALB_NAME:-$AGC_SHARED_GATEWAY_NAME}"
AGC_SHARED_RESOURCES_CREATE="${AGC_SHARED_RESOURCES_CREATE:-false}"
AGC_HOSTNAME="${AGC_HOSTNAME:-}"
CANARY_ENABLED="${CANARY_ENABLED:-false}"
READINESS_PATH="/ready"
REPLICA_COUNT=""
DEPLOY_ENV="${DEPLOY_ENV:-${AZURE_ENV_NAME:-}}"
SELECTOR_INCLUDE_CANARY="false"

case "$PUBLICATION_MODE" in
  legacy)
    LEGACY_INGRESS_ENABLED="true"
    ;;
  agc)
    AGC_ENABLED="true"
    ;;
  dual)
    LEGACY_INGRESS_ENABLED="true"
    AGC_ENABLED="true"
    ;;
  none)
    LEGACY_INGRESS_ENABLED="false"
    AGC_ENABLED="false"
    ;;
  *)
    echo "Unsupported PUBLICATION_MODE '$PUBLICATION_MODE'. Expected one of legacy, agc, dual, none." >&2
    exit 1
    ;;
esac

if [ "$LEGACY_INGRESS_ENABLED" = "true" ] && [ -z "$LEGACY_INGRESS_CLASS_NAME" ]; then
  echo "LEGACY_INGRESS_CLASS_NAME or INGRESS_CLASS_NAME must be set when PUBLICATION_MODE is legacy or dual." >&2
  exit 1
fi

# Determine workload type (crud-service goes to crud pool, others to agents pool)
if [ "$SERVICE_NAME" = "crud-service" ]; then
  NODE_POOL="crud"
  WORKLOAD_TYPE="crud"
  case "$DEPLOY_ENV" in
    dev|development|local)
      # Dev profile prioritizes fast iteration while preserving dependency-aware readiness.
      REPLICA_COUNT="1"
      PDB_ENABLED="false"
      PDB_MIN_AVAILABLE=""
      ROLLING_MAX_UNAVAILABLE="100%"
      ROLLING_MAX_SURGE="1"
      ;;
    *)
      PDB_ENABLED="true"
      PDB_MIN_AVAILABLE="1"
      ROLLING_MAX_UNAVAILABLE="0"
      ROLLING_MAX_SURGE="1"
      ;;
  esac
else
  NODE_POOL="agents"
  WORKLOAD_TYPE="agents"
  PDB_ENABLED="false"
  PDB_MIN_AVAILABLE=""
  ROLLING_MAX_UNAVAILABLE=""
  ROLLING_MAX_SURGE=""
fi

if [ "$AGC_ENABLED" = "true" ] && [ -z "${AGC_SHARED_RESOURCES_CREATE:-}" ] && [ "$SERVICE_NAME" = "crud-service" ]; then
  AGC_SHARED_RESOURCES_CREATE="true"
fi

case "$SERVICE_NAME" in
  truth-ingestion)
    # Preserve legacy selector shape for existing truth-ingestion deployment.
    SELECTOR_INCLUDE_CANARY="true"
    ;;
esac

SERVICE_IMAGE_VAR_NAME="SERVICE_$(printf '%s' "$SERVICE_NAME" | tr '[:lower:]-' '[:upper:]_')_IMAGE_NAME"
SERVICE_IMAGE="$(printenv "$SERVICE_IMAGE_VAR_NAME" || true)"

if [ -n "$SERVICE_IMAGE" ]; then
  case "$SERVICE_IMAGE" in
    *@*)
      IMAGE_PREFIX="${SERVICE_IMAGE%@*}"
      IMAGE_DIGEST="${SERVICE_IMAGE#*@}"
      IMAGE_TAG="latest"
      ;;
    *)
      IMAGE_PREFIX="${SERVICE_IMAGE%:*}"
      if [ "$IMAGE_PREFIX" = "$SERVICE_IMAGE" ]; then
        IMAGE_TAG="latest"
      else
        IMAGE_TAG="${SERVICE_IMAGE##*:}"
      fi
      IMAGE_DIGEST=""
      ;;
  esac
else
  IMAGE_PREFIX="$IMAGE_PREFIX/$SERVICE_NAME"
fi

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
CHART_PATH="$REPO_ROOT/.kubernetes/chart"
OUT_DIR="$REPO_ROOT/.kubernetes/rendered/$SERVICE_NAME"

mkdir -p "$OUT_DIR"

# Base Helm arguments
HELM_ARGS="--namespace $NAMESPACE"
HELM_ARGS="$HELM_ARGS --set serviceName=$SERVICE_NAME"
HELM_ARGS="$HELM_ARGS --set image.repository=$IMAGE_PREFIX"
if [ -n "$IMAGE_DIGEST" ]; then
  HELM_ARGS="$HELM_ARGS --set-string image.digest=$IMAGE_DIGEST"
else
  HELM_ARGS="$HELM_ARGS --set image.tag=$IMAGE_TAG"
fi
HELM_ARGS="$HELM_ARGS --set keda.enabled=$KEDA_ENABLED"
HELM_ARGS="$HELM_ARGS --set ingress.enabled=$LEGACY_INGRESS_ENABLED"
HELM_ARGS="$HELM_ARGS --set-string ingress.className=$LEGACY_INGRESS_CLASS_NAME"
HELM_ARGS="$HELM_ARGS --set agc.enabled=$AGC_ENABLED"
HELM_ARGS="$HELM_ARGS --set-string agc.gatewayClassName=$AGC_GATEWAY_CLASS_NAME"
HELM_ARGS="$HELM_ARGS --set agc.sharedResources.create=$AGC_SHARED_RESOURCES_CREATE"
HELM_ARGS="$HELM_ARGS --set-string agc.sharedResources.namespace=$AGC_SHARED_NAMESPACE"
HELM_ARGS="$HELM_ARGS --set-string agc.sharedResources.gatewayName=$AGC_SHARED_GATEWAY_NAME"
HELM_ARGS="$HELM_ARGS --set-string agc.sharedResources.applicationLoadBalancerName=$AGC_SHARED_ALB_NAME"
HELM_ARGS="$HELM_ARGS --set-string agc.sharedResources.subnetId=$AGC_SUBNET_ID"
HELM_ARGS="$HELM_ARGS --set-string agc.sharedResources.listeners[0].name=http"
HELM_ARGS="$HELM_ARGS --set-string agc.sharedResources.listeners[0].protocol=HTTP"
HELM_ARGS="$HELM_ARGS --set agc.sharedResources.listeners[0].port=80"
if [ "$SERVICE_NAME" = "crud-service" ]; then
  HELM_ARGS="$HELM_ARGS --set ingress.paths[0].path=/health"
  HELM_ARGS="$HELM_ARGS --set ingress.paths[0].pathType=Prefix"
  HELM_ARGS="$HELM_ARGS --set ingress.paths[1].path=/api"
  HELM_ARGS="$HELM_ARGS --set ingress.paths[1].pathType=Prefix"
  HELM_ARGS="$HELM_ARGS --set agc.paths[0].path=/health"
  HELM_ARGS="$HELM_ARGS --set agc.paths[0].pathType=PathPrefix"
  HELM_ARGS="$HELM_ARGS --set agc.paths[1].path=/api"
  HELM_ARGS="$HELM_ARGS --set agc.paths[1].pathType=PathPrefix"
else
  HELM_ARGS="$HELM_ARGS --set agc.paths[0].path=/$SERVICE_NAME"
  HELM_ARGS="$HELM_ARGS --set agc.paths[0].pathType=PathPrefix"
  HELM_ARGS="$HELM_ARGS --set agc.paths[0].rewritePrefixMatch=/"
fi

if [ "$SERVICE_NAME" = "truth-export" ]; then
  # Override legacy in-cluster startup script with deterministic image entrypoint.
  HELM_ARGS="$HELM_ARGS --set-string container.command[0]=uvicorn"
  HELM_ARGS="$HELM_ARGS --set-string container.args[0]=truth_export.main:app"
  HELM_ARGS="$HELM_ARGS --set-string container.args[1]=--host"
  HELM_ARGS="$HELM_ARGS --set-string container.args[2]=0.0.0.0"
  HELM_ARGS="$HELM_ARGS --set-string container.args[3]=--port"
  HELM_ARGS="$HELM_ARGS --set-string container.args[4]=8000"
fi

if [ -n "$AGC_HOSTNAME" ]; then
  HELM_ARGS="$HELM_ARGS --set-string agc.hostnames[0]=$AGC_HOSTNAME"
  HELM_ARGS="$HELM_ARGS --set-string agc.sharedResources.listeners[0].hostname=$AGC_HOSTNAME"
fi
HELM_ARGS="$HELM_ARGS --set canary.enabled=$CANARY_ENABLED"
HELM_ARGS="$HELM_ARGS --set deployment.selectorIncludeCanary=$SELECTOR_INCLUDE_CANARY"
HELM_ARGS="$HELM_ARGS --set probes.readiness.path=$READINESS_PATH"
if [ -n "$REPLICA_COUNT" ]; then
  HELM_ARGS="$HELM_ARGS --set replicaCount=$REPLICA_COUNT"
fi

# Node pool targeting
HELM_ARGS="$HELM_ARGS --set nodeSelector.agentpool=$NODE_POOL"
HELM_ARGS="$HELM_ARGS --set tolerations[0].key=workload"
HELM_ARGS="$HELM_ARGS --set tolerations[0].operator=Equal"
HELM_ARGS="$HELM_ARGS --set tolerations[0].value=$WORKLOAD_TYPE"
HELM_ARGS="$HELM_ARGS --set tolerations[0].effect=NoSchedule"

if [ -n "$ROLLING_MAX_UNAVAILABLE" ]; then
  HELM_ARGS="$HELM_ARGS --set-string availability.rollingUpdate.maxUnavailable=$ROLLING_MAX_UNAVAILABLE"
fi

if [ -n "$ROLLING_MAX_SURGE" ]; then
  HELM_ARGS="$HELM_ARGS --set-string availability.rollingUpdate.maxSurge=$ROLLING_MAX_SURGE"
fi

if [ "$PDB_ENABLED" = "true" ]; then
  HELM_ARGS="$HELM_ARGS --set pdb.enabled=true"
  HELM_ARGS="$HELM_ARGS --set-string pdb.minAvailable=$PDB_MIN_AVAILABLE"
fi

# Workload Identity — bind pods to the correct UAMI via ServiceAccount
# Batch 1 agents (first 20) use AGENTS_WORKLOAD_CLIENT_ID; batch 2 (overflow) use AGENTS2_WORKLOAD_CLIENT_ID.
HELM_ARGS="$HELM_ARGS --set serviceAccount.create=true"
if [ "$SERVICE_NAME" = "crud-service" ]; then
  WORKLOAD_CLIENT_ID="${CRUD_WORKLOAD_CLIENT_ID:-}"
else
  case "$SERVICE_NAME" in
    product-management-normalization-classification|search-enrichment-agent|truth-enrichment|truth-export|truth-hitl|truth-ingestion)
      WORKLOAD_CLIENT_ID="${AGENTS2_WORKLOAD_CLIENT_ID:-${AGENTS_WORKLOAD_CLIENT_ID:-}}"
      ;;
    *)
      WORKLOAD_CLIENT_ID="${AGENTS_WORKLOAD_CLIENT_ID:-}"
      ;;
  esac
fi
if [ -n "$WORKLOAD_CLIENT_ID" ]; then
  HELM_ARGS="$HELM_ARGS --set-string serviceAccount.clientId=$WORKLOAD_CLIENT_ID"
fi

add_env_arg() {
  key="$1"
  value="${2:-}"
  if [ -n "$value" ]; then
    HELM_ARGS="$HELM_ARGS --set-string env.$key=$value"
  fi
}

is_truth_service() {
  case "$SERVICE_NAME" in
    truth-ingestion|truth-enrichment|truth-export|truth-hitl)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

is_platform_jobs_service() {
  case "$SERVICE_NAME" in
    truth-ingestion|truth-enrichment|truth-export|truth-hitl|search-enrichment-agent|product-management-consistency-validation)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

is_agent_service() {
  [ "$SERVICE_NAME" != "crud-service" ]
}

require_env_keys() {
  MISSING_REQUIRED=""
  for required in "$@"; do
    eval "value=\${$required:-}"
    if [ -z "$value" ]; then
      MISSING_REQUIRED="$MISSING_REQUIRED $required"
    fi
  done

  if [ -n "$MISSING_REQUIRED" ]; then
    TARGET_ENV="${DEPLOY_ENV:-${AZURE_ENV_NAME:-<environment>}}"
    echo "::warning::Missing environment variables for $SERVICE_NAME:$MISSING_REQUIRED — rendering with empty values. Run 'azd provision -e $TARGET_ENV' with deployShared=true to populate them." >&2
  fi
}

if is_agent_service; then
  FOUNDRY_AGENT_NAME_FAST="${FOUNDRY_AGENT_NAME_FAST:-$SERVICE_NAME-fast}"
  FOUNDRY_AGENT_NAME_RICH="${FOUNDRY_AGENT_NAME_RICH:-$SERVICE_NAME-rich}"
  MODEL_DEPLOYMENT_NAME_FAST="${MODEL_DEPLOYMENT_NAME_FAST:-gpt-5-nano}"
  MODEL_DEPLOYMENT_NAME_RICH="${MODEL_DEPLOYMENT_NAME_RICH:-gpt-5}"

  case "${FOUNDRY_AGENT_ID_FAST:-}" in
    *-pending)
      echo "Invalid FOUNDRY_AGENT_ID_FAST for $SERVICE_NAME: placeholder ids are not deployable." >&2
      exit 1
      ;;
  esac
  case "${FOUNDRY_AGENT_ID_RICH:-}" in
    *-pending)
      echo "Invalid FOUNDRY_AGENT_ID_RICH for $SERVICE_NAME: placeholder ids are not deployable." >&2
      exit 1
      ;;
  esac

  if [ -z "${FOUNDRY_AGENT_ID_FAST:-}" ] && [ -z "${FOUNDRY_AGENT_NAME_FAST:-}" ]; then
    echo "Missing Foundry fast-role definition for $SERVICE_NAME (set FOUNDRY_AGENT_ID_FAST or FOUNDRY_AGENT_NAME_FAST)." >&2
    exit 1
  fi
  if [ -z "${FOUNDRY_AGENT_ID_RICH:-}" ] && [ -z "${FOUNDRY_AGENT_NAME_RICH:-}" ]; then
    echo "Missing Foundry rich-role definition for $SERVICE_NAME (set FOUNDRY_AGENT_ID_RICH or FOUNDRY_AGENT_NAME_RICH)." >&2
    exit 1
  fi
fi

RESOLVED_POSTGRES_AUTH_MODE="${POSTGRES_AUTH_MODE:-password}"
RESOLVED_POSTGRES_USER="${POSTGRES_USER:-}"
POSTGRES_ADMIN_USER_VALUE="${POSTGRES_ADMIN_USER:-}"

if [ "$SERVICE_NAME" = "crud-service" ]; then
  if [ "$RESOLVED_POSTGRES_AUTH_MODE" = "password" ] && [ -n "$POSTGRES_ADMIN_USER_VALUE" ]; then
    RESOLVED_POSTGRES_USER="$POSTGRES_ADMIN_USER_VALUE"
  fi

  if [ "$RESOLVED_POSTGRES_AUTH_MODE" = "entra" ]; then
    if [ -z "$RESOLVED_POSTGRES_USER" ] || [ "$RESOLVED_POSTGRES_USER" = "crud_workload" ] || [ "$RESOLVED_POSTGRES_USER" = "crud_admin" ] || [ "$RESOLVED_POSTGRES_USER" = "$POSTGRES_ADMIN_USER_VALUE" ]; then
      AKS_CLUSTER_NAME_VALUE="${AZURE_AKS_CLUSTER_NAME:-${AKS_CLUSTER_NAME:-}}"
      if [ -n "$AKS_CLUSTER_NAME_VALUE" ]; then
        RESOLVED_POSTGRES_USER="${AKS_CLUSTER_NAME_VALUE}-agentpool"
      fi
    fi
  fi
fi

RESOLVED_REDIS_HOST="${REDIS_HOST:-}"
if [ -n "$RESOLVED_REDIS_HOST" ] && ! printf '%s' "$RESOLVED_REDIS_HOST" | grep -q '\.'; then
  RESOLVED_REDIS_HOST="${RESOLVED_REDIS_HOST}.redis.cache.windows.net"
fi
RESOLVED_REDIS_PASSWORD_SECRET_NAME="${REDIS_PASSWORD_SECRET_NAME:-redis-primary-key}"
RESOLVED_REDIS_URL=""
if [ -n "${REDIS_URL:-}" ]; then
  case "$REDIS_URL" in
    *://*:*@*)
      RESOLVED_REDIS_URL="$REDIS_URL"
      ;;
    *)
      if [ -z "$RESOLVED_REDIS_HOST" ]; then
        RESOLVED_REDIS_URL="$REDIS_URL"
      fi
      ;;
  esac
fi
RESOLVED_AI_SEARCH_AUTH_MODE="${AI_SEARCH_AUTH_MODE:-}"
case "$(printf '%s' "$RESOLVED_AI_SEARCH_AUTH_MODE" | tr '[:upper:]' '[:lower:]')" in
  api_key)
    RESOLVED_AI_SEARCH_KEY="${AI_SEARCH_KEY:-}"
    ;;
  *)
    RESOLVED_AI_SEARCH_KEY=""
    ;;
esac

# Database
add_env_arg "POSTGRES_HOST" "${POSTGRES_HOST:-}"
add_env_arg "POSTGRES_AUTH_MODE" "$RESOLVED_POSTGRES_AUTH_MODE"
add_env_arg "POSTGRES_USER" "$RESOLVED_POSTGRES_USER"
add_env_arg "POSTGRES_PASSWORD" "${POSTGRES_PASSWORD:-}"
add_env_arg "POSTGRES_DATABASE" "${POSTGRES_DATABASE:-}"
add_env_arg "POSTGRES_PORT" "${POSTGRES_PORT:-}"
add_env_arg "POSTGRES_SSL" "${POSTGRES_SSL:-}"

# Messaging & Infrastructure
if is_platform_jobs_service; then
  add_env_arg "PLATFORM_JOBS_EVENT_HUB_NAMESPACE" "${PLATFORM_JOBS_EVENT_HUB_NAMESPACE:-}"
  add_env_arg "PLATFORM_JOBS_EVENT_HUB_CONNECTION_STRING" "${PLATFORM_JOBS_EVENT_HUB_CONNECTION_STRING:-}"
else
  add_env_arg "EVENT_HUB_NAMESPACE" "${EVENT_HUB_NAMESPACE:-}"
  add_env_arg "EVENT_HUB_CONNECTION_STRING" "${EVENT_HUB_CONNECTION_STRING:-}"
fi
add_env_arg "KEY_VAULT_URI" "${KEY_VAULT_URI:-}"
add_env_arg "REDIS_HOST" "$RESOLVED_REDIS_HOST"
add_env_arg "REDIS_PASSWORD" "${REDIS_PASSWORD:-}"
add_env_arg "REDIS_PASSWORD_SECRET_NAME" "$RESOLVED_REDIS_PASSWORD_SECRET_NAME"
add_env_arg "AZURE_CLIENT_ID" "${WORKLOAD_CLIENT_ID:-${AZURE_CLIENT_ID:-}}"
add_env_arg "AZURE_TENANT_ID" "${AZURE_TENANT_ID:-}"

# Azure AI Foundry
add_env_arg "PROJECT_ENDPOINT" "${PROJECT_ENDPOINT:-}"
add_env_arg "PROJECT_NAME" "${PROJECT_NAME:-}"
add_env_arg "FOUNDRY_AGENT_ID_FAST" "${FOUNDRY_AGENT_ID_FAST:-}"
add_env_arg "FOUNDRY_AGENT_ID_RICH" "${FOUNDRY_AGENT_ID_RICH:-}"
add_env_arg "FOUNDRY_AGENT_NAME_FAST" "${FOUNDRY_AGENT_NAME_FAST:-}"
add_env_arg "FOUNDRY_AGENT_NAME_RICH" "${FOUNDRY_AGENT_NAME_RICH:-}"
add_env_arg "MODEL_DEPLOYMENT_NAME_FAST" "${MODEL_DEPLOYMENT_NAME_FAST:-}"
add_env_arg "MODEL_DEPLOYMENT_NAME_RICH" "${MODEL_DEPLOYMENT_NAME_RICH:-}"
add_env_arg "FOUNDRY_STREAM" "${FOUNDRY_STREAM:-}"
add_env_arg "FOUNDRY_STRICT_ENFORCEMENT" "${FOUNDRY_STRICT_ENFORCEMENT:-}"
add_env_arg "FOUNDRY_AUTO_ENSURE_ON_STARTUP" "${FOUNDRY_AUTO_ENSURE_ON_STARTUP:-}"

# Azure AI Search
add_env_arg "AI_SEARCH_ENDPOINT" "${AI_SEARCH_ENDPOINT:-}"
add_env_arg "AI_SEARCH_INDEX" "${AI_SEARCH_INDEX:-}"
add_env_arg "AI_SEARCH_VECTOR_INDEX" "${AI_SEARCH_VECTOR_INDEX:-}"
add_env_arg "AI_SEARCH_INDEXER_NAME" "${AI_SEARCH_INDEXER_NAME:-}"
add_env_arg "AI_SEARCH_AUTH_MODE" "$RESOLVED_AI_SEARCH_AUTH_MODE"
add_env_arg "CATALOG_SEARCH_REQUIRE_AI_SEARCH" "${CATALOG_SEARCH_REQUIRE_AI_SEARCH:-}"
add_env_arg "AI_SEARCH_KEY" "$RESOLVED_AI_SEARCH_KEY"
add_env_arg "EMBEDDING_DEPLOYMENT_NAME" "${EMBEDDING_DEPLOYMENT_NAME:-}"

# Memory tiers
add_env_arg "REDIS_URL" "$RESOLVED_REDIS_URL"
add_env_arg "COSMOS_ACCOUNT_URI" "${COSMOS_ACCOUNT_URI:-}"
add_env_arg "COSMOS_DATABASE" "${COSMOS_DATABASE:-}"
COSMOS_CONTAINER_VALUE="${COSMOS_CONTAINER:-}"
COSMOS_AUDIT_CONTAINER_VALUE="${COSMOS_AUDIT_CONTAINER:-}"
if [ "$SERVICE_NAME" = "truth-ingestion" ]; then
  COSMOS_CONTAINER_VALUE="${TRUTH_INGESTION_COSMOS_CONTAINER:-products}"
  COSMOS_AUDIT_CONTAINER_VALUE="${TRUTH_INGESTION_COSMOS_AUDIT_CONTAINER:-audit}"
fi
add_env_arg "COSMOS_CONTAINER" "$COSMOS_CONTAINER_VALUE"
add_env_arg "COSMOS_AUDIT_CONTAINER" "$COSMOS_AUDIT_CONTAINER_VALUE"
add_env_arg "BLOB_ACCOUNT_URL" "${BLOB_ACCOUNT_URL:-}"
add_env_arg "BLOB_CONTAINER" "${BLOB_CONTAINER:-}"

# Observability
add_env_arg "APPLICATIONINSIGHTS_CONNECTION_STRING" "${APPLICATIONINSIGHTS_CONNECTION_STRING:-}"

# Cross-namespace CRUD service URL for agent→CRUD communication (ADR-034)
if is_agent_service; then
  CRUD_NS="${K8S_CRUD_NAMESPACE:-${K8S_NAMESPACE:-holiday-peak-crud}}"
  add_env_arg "CRUD_SERVICE_URL" "${CRUD_SERVICE_URL:-http://crud-service-crud-service.${CRUD_NS}.svc.cluster.local:80}"
fi

if [ "$SERVICE_NAME" = "ecommerce-catalog-search" ]; then
  add_env_arg "SEARCH_ENRICHMENT_EVENT_HUB_NAME" "${SEARCH_ENRICHMENT_EVENT_HUB_NAME:-search-enrichment-jobs}"
  add_env_arg "SEARCH_ENRICHMENT_EVENT_HUB_CONSUMER_GROUP" "${SEARCH_ENRICHMENT_EVENT_HUB_CONSUMER_GROUP:-search-enrichment-consumer}"
fi

if [ "$SERVICE_NAME" = "search-enrichment-agent" ]; then
  add_env_arg "SEARCH_ENRICHMENT_EVENT_HUB_NAME" "${SEARCH_ENRICHMENT_EVENT_HUB_NAME:-search-enrichment-jobs}"
  add_env_arg "SEARCH_ENRICHMENT_EVENT_HUB_CONSUMER_GROUP" "${SEARCH_ENRICHMENT_EVENT_HUB_CONSUMER_GROUP:-search-enrichment-consumer}"
fi

if is_truth_service; then
  case "$SERVICE_NAME" in
    truth-ingestion)
      add_env_arg "TRUTH_EVENT_HUB_NAME" "${TRUTH_EVENT_HUB_NAME:-ingest-jobs}"
      add_env_arg "TRUTH_EVENT_HUB_CONSUMER_GROUP" "${TRUTH_EVENT_HUB_CONSUMER_GROUP:-ingestion-group}"
      ;;
    truth-enrichment)
      add_env_arg "TRUTH_EVENT_HUB_NAME" "${TRUTH_EVENT_HUB_NAME:-enrichment-jobs}"
      add_env_arg "TRUTH_EVENT_HUB_CONSUMER_GROUP" "${TRUTH_EVENT_HUB_CONSUMER_GROUP:-enrichment-engine}"
      ;;
    truth-export)
      add_env_arg "TRUTH_EVENT_HUB_NAME" "${TRUTH_EVENT_HUB_NAME:-export-jobs}"
      add_env_arg "TRUTH_EVENT_HUB_CONSUMER_GROUP" "${TRUTH_EVENT_HUB_CONSUMER_GROUP:-export-engine}"
      ;;
    truth-hitl)
      add_env_arg "TRUTH_EVENT_HUB_NAME" "${TRUTH_EVENT_HUB_NAME:-hitl-jobs}"
      add_env_arg "TRUTH_EVENT_HUB_CONSUMER_GROUP" "${TRUTH_EVENT_HUB_CONSUMER_GROUP:-hitl-service}"
      ;;
  esac
fi

if is_agent_service; then
  if is_platform_jobs_service; then
    require_env_keys \
      PLATFORM_JOBS_EVENT_HUB_NAMESPACE \
      PROJECT_ENDPOINT \
      PROJECT_NAME \
      MODEL_DEPLOYMENT_NAME_FAST \
      MODEL_DEPLOYMENT_NAME_RICH \
      COSMOS_ACCOUNT_URI \
      COSMOS_DATABASE \
      REDIS_HOST \
      BLOB_ACCOUNT_URL \
      KEY_VAULT_URI
  else
    require_env_keys \
      EVENT_HUB_NAMESPACE \
      PROJECT_ENDPOINT \
      PROJECT_NAME \
      MODEL_DEPLOYMENT_NAME_FAST \
      MODEL_DEPLOYMENT_NAME_RICH \
      COSMOS_ACCOUNT_URI \
      COSMOS_DATABASE \
      REDIS_HOST \
      BLOB_ACCOUNT_URL \
      KEY_VAULT_URI
  fi
fi

if [ "$SERVICE_NAME" = "ecommerce-catalog-search" ] || [ "$SERVICE_NAME" = "search-enrichment-agent" ]; then
  require_env_keys \
    AI_SEARCH_ENDPOINT \
    AI_SEARCH_INDEX \
    AI_SEARCH_VECTOR_INDEX \
    AI_SEARCH_INDEXER_NAME \
    EMBEDDING_DEPLOYMENT_NAME
fi

# shellcheck disable=SC2086
helm template "$SERVICE_NAME" "$CHART_PATH" $HELM_ARGS > "$OUT_DIR/all.yaml"

if is_agent_service; then
  for key in PROJECT_ENDPOINT PROJECT_NAME MODEL_DEPLOYMENT_NAME_FAST MODEL_DEPLOYMENT_NAME_RICH FOUNDRY_AGENT_NAME_FAST FOUNDRY_AGENT_NAME_RICH FOUNDRY_STRICT_ENFORCEMENT FOUNDRY_AUTO_ENSURE_ON_STARTUP; do
    if ! grep -q "name: $key" "$OUT_DIR/all.yaml"; then
      echo "Rendered manifest missing Foundry env key '$key' for $SERVICE_NAME" >&2
      exit 1
    fi
  done

  if [ -n "${FOUNDRY_AGENT_ID_FAST:-}" ] && ! grep -q "name: FOUNDRY_AGENT_ID_FAST" "$OUT_DIR/all.yaml"; then
    echo "Rendered manifest missing Foundry env key 'FOUNDRY_AGENT_ID_FAST' for $SERVICE_NAME" >&2
    exit 1
  fi
  if [ -n "${FOUNDRY_AGENT_ID_RICH:-}" ] && ! grep -q "name: FOUNDRY_AGENT_ID_RICH" "$OUT_DIR/all.yaml"; then
    echo "Rendered manifest missing Foundry env key 'FOUNDRY_AGENT_ID_RICH' for $SERVICE_NAME" >&2
    exit 1
  fi
fi

if is_truth_service; then
  for key in PLATFORM_JOBS_EVENT_HUB_NAMESPACE PROJECT_ENDPOINT COSMOS_ACCOUNT_URI COSMOS_DATABASE TRUTH_EVENT_HUB_NAME TRUTH_EVENT_HUB_CONSUMER_GROUP; do
    if ! grep -q "name: $key" "$OUT_DIR/all.yaml"; then
      echo "Rendered manifest missing env key '$key' for $SERVICE_NAME" >&2
      exit 1
    fi
  done

  if [ "$SERVICE_NAME" = "truth-ingestion" ]; then
    for key in COSMOS_CONTAINER COSMOS_AUDIT_CONTAINER; do
      if ! grep -q "name: $key" "$OUT_DIR/all.yaml"; then
        echo "Rendered manifest missing env key '$key' for $SERVICE_NAME" >&2
        exit 1
      fi
    done
  fi
fi

if is_platform_jobs_service; then
  if ! grep -q "name: PLATFORM_JOBS_EVENT_HUB_NAMESPACE" "$OUT_DIR/all.yaml"; then
    echo "Rendered manifest missing env key 'PLATFORM_JOBS_EVENT_HUB_NAMESPACE' for $SERVICE_NAME" >&2
    exit 1
  fi

  if [ -n "${PLATFORM_JOBS_EVENT_HUB_CONNECTION_STRING:-}" ] && ! grep -q "name: PLATFORM_JOBS_EVENT_HUB_CONNECTION_STRING" "$OUT_DIR/all.yaml"; then
    echo "Rendered manifest missing env key 'PLATFORM_JOBS_EVENT_HUB_CONNECTION_STRING' for $SERVICE_NAME" >&2
    exit 1
  fi
fi

if [ "$SERVICE_NAME" = "ecommerce-catalog-search" ] || [ "$SERVICE_NAME" = "search-enrichment-agent" ]; then
  for key in AI_SEARCH_ENDPOINT AI_SEARCH_INDEX AI_SEARCH_VECTOR_INDEX AI_SEARCH_INDEXER_NAME EMBEDDING_DEPLOYMENT_NAME SEARCH_ENRICHMENT_EVENT_HUB_NAME SEARCH_ENRICHMENT_EVENT_HUB_CONSUMER_GROUP; do
    if ! grep -q "name: $key" "$OUT_DIR/all.yaml"; then
      echo "Rendered manifest missing env key '$key' for $SERVICE_NAME" >&2
      exit 1
    fi
  done
fi

echo "Rendered Helm manifests to $OUT_DIR/all.yaml"
