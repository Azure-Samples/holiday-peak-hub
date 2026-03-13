#!/usr/bin/env sh
set -eu

SERVICE_NAME="$1"

NAMESPACE="${K8S_NAMESPACE:-holiday-peak}"
IMAGE_PREFIX="${IMAGE_PREFIX:-ghcr.io/azure-samples}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
KEDA_ENABLED="${KEDA_ENABLED:-false}"
INGRESS_ENABLED="${INGRESS_ENABLED:-true}"
INGRESS_CLASS_NAME="${INGRESS_CLASS_NAME:-webapprouting.kubernetes.azure.com}"
CANARY_ENABLED="${CANARY_ENABLED:-false}"
READINESS_PATH="/ready"
REPLICA_COUNT=""
DEPLOY_ENV="${DEPLOY_ENV:-${AZURE_ENV_NAME:-}}"

# Determine workload type (crud-service goes to crud pool, others to agents pool)
if [ "$SERVICE_NAME" = "crud-service" ]; then
  NODE_POOL="crud"
  WORKLOAD_TYPE="crud"
  case "$DEPLOY_ENV" in
    dev|development|local)
      # Dev profile prioritizes fast iteration over strict availability.
      READINESS_PATH="/health"
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

SERVICE_IMAGE_VAR_NAME="SERVICE_$(printf '%s' "$SERVICE_NAME" | tr '[:lower:]-' '[:upper:]_')_IMAGE_NAME"
SERVICE_IMAGE="$(printenv "$SERVICE_IMAGE_VAR_NAME" || true)"

if [ -n "$SERVICE_IMAGE" ]; then
  IMAGE_PREFIX="${SERVICE_IMAGE%:*}"
  if [ "$IMAGE_PREFIX" = "$SERVICE_IMAGE" ]; then
    IMAGE_TAG="latest"
  else
    IMAGE_TAG="${SERVICE_IMAGE##*:}"
  fi
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
HELM_ARGS="$HELM_ARGS --set image.tag=$IMAGE_TAG"
HELM_ARGS="$HELM_ARGS --set keda.enabled=$KEDA_ENABLED"
HELM_ARGS="$HELM_ARGS --set ingress.enabled=$INGRESS_ENABLED"
HELM_ARGS="$HELM_ARGS --set-string ingress.className=$INGRESS_CLASS_NAME"
if [ "$SERVICE_NAME" = "crud-service" ]; then
  HELM_ARGS="$HELM_ARGS --set ingress.paths[0].path=/health"
  HELM_ARGS="$HELM_ARGS --set ingress.paths[0].pathType=Prefix"
  HELM_ARGS="$HELM_ARGS --set ingress.paths[1].path=/api"
  HELM_ARGS="$HELM_ARGS --set ingress.paths[1].pathType=Prefix"
fi
HELM_ARGS="$HELM_ARGS --set canary.enabled=$CANARY_ENABLED"
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

# Database
add_env_arg "POSTGRES_HOST" "${POSTGRES_HOST:-}"
add_env_arg "POSTGRES_USER" "${POSTGRES_USER:-}"
add_env_arg "POSTGRES_PASSWORD" "${POSTGRES_PASSWORD:-}"
add_env_arg "POSTGRES_DATABASE" "${POSTGRES_DATABASE:-}"
add_env_arg "POSTGRES_PORT" "${POSTGRES_PORT:-}"
add_env_arg "POSTGRES_SSL" "${POSTGRES_SSL:-}"

# Messaging & Infrastructure
add_env_arg "EVENT_HUB_NAMESPACE" "${EVENT_HUB_NAMESPACE:-}"
add_env_arg "KEY_VAULT_URI" "${KEY_VAULT_URI:-}"
add_env_arg "REDIS_HOST" "${REDIS_HOST:-}"
add_env_arg "AZURE_CLIENT_ID" "${AZURE_CLIENT_ID:-}"
add_env_arg "AZURE_TENANT_ID" "${AZURE_TENANT_ID:-}"

# Azure AI Foundry
add_env_arg "PROJECT_ENDPOINT" "${PROJECT_ENDPOINT:-}"
add_env_arg "PROJECT_NAME" "${PROJECT_NAME:-}"
add_env_arg "FOUNDRY_AGENT_ID_FAST" "${FOUNDRY_AGENT_ID_FAST:-}"
add_env_arg "FOUNDRY_AGENT_ID_RICH" "${FOUNDRY_AGENT_ID_RICH:-}"
add_env_arg "MODEL_DEPLOYMENT_NAME_FAST" "${MODEL_DEPLOYMENT_NAME_FAST:-}"
add_env_arg "MODEL_DEPLOYMENT_NAME_RICH" "${MODEL_DEPLOYMENT_NAME_RICH:-}"
add_env_arg "FOUNDRY_STREAM" "${FOUNDRY_STREAM:-}"
add_env_arg "FOUNDRY_STRICT_ENFORCEMENT" "${FOUNDRY_STRICT_ENFORCEMENT:-}"
add_env_arg "FOUNDRY_AUTO_ENSURE_ON_STARTUP" "${FOUNDRY_AUTO_ENSURE_ON_STARTUP:-}"

# Azure AI Search
add_env_arg "AI_SEARCH_ENDPOINT" "${AI_SEARCH_ENDPOINT:-}"
add_env_arg "AI_SEARCH_INDEX" "${AI_SEARCH_INDEX:-}"
add_env_arg "AI_SEARCH_AUTH_MODE" "${AI_SEARCH_AUTH_MODE:-}"
add_env_arg "AI_SEARCH_KEY" "${AI_SEARCH_KEY:-}"

# Memory tiers
add_env_arg "REDIS_URL" "${REDIS_URL:-}"
add_env_arg "COSMOS_ACCOUNT_URI" "${COSMOS_ACCOUNT_URI:-}"
add_env_arg "COSMOS_DATABASE" "${COSMOS_DATABASE:-}"
add_env_arg "COSMOS_CONTAINER" "${COSMOS_CONTAINER:-}"
add_env_arg "BLOB_ACCOUNT_URL" "${BLOB_ACCOUNT_URL:-}"
add_env_arg "BLOB_CONTAINER" "${BLOB_CONTAINER:-}"

# Observability
add_env_arg "APPLICATIONINSIGHTS_CONNECTION_STRING" "${APPLICATIONINSIGHTS_CONNECTION_STRING:-}"

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

  MISSING_REQUIRED=""
  for required in EVENT_HUB_NAMESPACE PROJECT_ENDPOINT COSMOS_ACCOUNT_URI COSMOS_DATABASE; do
    eval "value=\${$required:-}"
    if [ -z "$value" ]; then
      MISSING_REQUIRED="$MISSING_REQUIRED $required"
    fi
  done

  if [ -n "$MISSING_REQUIRED" ]; then
    echo "Missing required environment variables for $SERVICE_NAME:$MISSING_REQUIRED" >&2
    exit 1
  fi
fi

# shellcheck disable=SC2086
helm template "$SERVICE_NAME" "$CHART_PATH" $HELM_ARGS > "$OUT_DIR/all.yaml"

if is_truth_service; then
  for key in EVENT_HUB_NAMESPACE PROJECT_ENDPOINT COSMOS_ACCOUNT_URI COSMOS_DATABASE TRUTH_EVENT_HUB_NAME TRUTH_EVENT_HUB_CONSUMER_GROUP; do
    if ! grep -q "name: $key" "$OUT_DIR/all.yaml"; then
      echo "Rendered manifest missing env key '$key' for $SERVICE_NAME" >&2
      exit 1
    fi
  done
fi

echo "Rendered Helm manifests to $OUT_DIR/all.yaml"
