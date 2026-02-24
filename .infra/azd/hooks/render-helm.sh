#!/usr/bin/env sh
set -eu

SERVICE_NAME="$1"

NAMESPACE="${K8S_NAMESPACE:-holiday-peak}"
IMAGE_PREFIX="${IMAGE_PREFIX:-ghcr.io/azure-samples}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
KEDA_ENABLED="${KEDA_ENABLED:-false}"

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

HELM_ARGS="--namespace $NAMESPACE --set serviceName=$SERVICE_NAME --set image.repository=$IMAGE_PREFIX --set image.tag=$IMAGE_TAG --set keda.enabled=$KEDA_ENABLED"

add_env_arg() {
  key="$1"
  value="${2:-}"
  if [ -n "$value" ]; then
    HELM_ARGS="$HELM_ARGS --set-string env.$key=$value"
  fi
}

add_env_arg "POSTGRES_HOST" "${POSTGRES_HOST:-}"
add_env_arg "POSTGRES_USER" "${POSTGRES_USER:-}"
add_env_arg "POSTGRES_PASSWORD" "${POSTGRES_PASSWORD:-}"
add_env_arg "POSTGRES_DATABASE" "${POSTGRES_DATABASE:-}"
add_env_arg "POSTGRES_PORT" "${POSTGRES_PORT:-}"
add_env_arg "POSTGRES_SSL" "${POSTGRES_SSL:-}"
add_env_arg "EVENT_HUB_NAMESPACE" "${EVENT_HUB_NAMESPACE:-}"
add_env_arg "KEY_VAULT_URI" "${KEY_VAULT_URI:-}"
add_env_arg "REDIS_HOST" "${REDIS_HOST:-}"

# shellcheck disable=SC2086
helm template "$SERVICE_NAME" "$CHART_PATH" $HELM_ARGS > "$OUT_DIR/all.yaml"

echo "Rendered Helm manifests to $OUT_DIR/all.yaml"
