#!/usr/bin/env sh
set -eu

SERVICE_NAME="$1"

NAMESPACE="${K8S_NAMESPACE:-holiday-peak}"
IMAGE_PREFIX="${IMAGE_PREFIX:-ghcr.io/azure-samples}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
KEDA_ENABLED="${KEDA_ENABLED:-false}"

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
CHART_PATH="$REPO_ROOT/.kubernetes/chart"
OUT_DIR="$REPO_ROOT/.kubernetes/rendered/$SERVICE_NAME"

mkdir -p "$OUT_DIR"

helm template "$SERVICE_NAME" "$CHART_PATH" \
  --namespace "$NAMESPACE" \
  --set "serviceName=$SERVICE_NAME" \
  --set "image.repository=$IMAGE_PREFIX/$SERVICE_NAME" \
  --set "image.tag=$IMAGE_TAG" \
  --set "keda.enabled=$KEDA_ENABLED" \
  > "$OUT_DIR/all.yaml"

echo "Rendered Helm manifests to $OUT_DIR/all.yaml"
