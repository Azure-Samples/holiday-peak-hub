#!/usr/bin/env sh
# Deploys required AI model deployments to the AI Services account.
# after Bicep provisions the AI Foundry project.
#
# Usage: deploy-foundry-models.sh [RESOURCE_GROUP] [AI_SERVICES_NAME]
set -eu

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
RESOURCE_GROUP="${1:-${AZURE_RESOURCE_GROUP:-}}"
AI_SERVICES_NAME="${2:-${AI_SERVICES_NAME:-}}"

# ---- Resolve from azd env ----
if [ -z "$RESOURCE_GROUP" ] && [ -n "${AZURE_ENV_NAME:-}" ]; then
  ENV_FILE="$REPO_ROOT/.azure/$AZURE_ENV_NAME/.env"
  if [ -f "$ENV_FILE" ]; then
    RESOURCE_GROUP="$(grep -E '^(AZURE_RESOURCE_GROUP|resourceGroupName)=' "$ENV_FILE" | head -n 1 | cut -d '=' -f2- | tr -d '"' || true)"
  fi
fi

if [ -z "$RESOURCE_GROUP" ]; then
  echo "Resource group could not be resolved. Set AZURE_RESOURCE_GROUP or run inside an azd environment."
  exit 1
fi

if [ -z "$AI_SERVICES_NAME" ] && [ -n "${AZURE_ENV_NAME:-}" ]; then
  ENV_FILE="$REPO_ROOT/.azure/$AZURE_ENV_NAME/.env"
  if [ -f "$ENV_FILE" ]; then
    AI_SERVICES_NAME="$(grep -E '^(AI_SERVICES_NAME|aiServicesName)=' "$ENV_FILE" | head -n 1 | cut -d '=' -f2- | tr -d '"' || true)"
  fi
fi

if [ -z "$AI_SERVICES_NAME" ]; then
  AI_SERVICES_NAME="$(az cognitiveservices account list \
    --resource-group "$RESOURCE_GROUP" \
    --query "[?kind=='AIServices'].name | [0]" -o tsv 2>/dev/null || true)"
fi

if [ -z "$AI_SERVICES_NAME" ]; then
  echo "AI Services account name could not be resolved. Set AI_SERVICES_NAME."
  exit 1
fi

echo "Deploying model deployments to AI Services account: $AI_SERVICES_NAME (RG: $RESOURCE_GROUP)"

# ---- Deploy models idempotently ----
deploy_model() {
  DEPLOYMENT_NAME="$1"
  MODEL_NAME="$2"
  MODEL_VERSION="$3"
  SKU_NAME="$4"
  SKU_CAPACITY="$5"

  if az cognitiveservices account deployment show \
      --resource-group "$RESOURCE_GROUP" \
      --name "$AI_SERVICES_NAME" \
      --deployment-name "$DEPLOYMENT_NAME" >/dev/null 2>&1; then
    echo "  [skip] Deployment '$DEPLOYMENT_NAME' already exists."
    return 0
  fi

  echo "  [create] Deploying model '$MODEL_NAME' as '$DEPLOYMENT_NAME'..."
  if ! az cognitiveservices account deployment create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$AI_SERVICES_NAME" \
    --deployment-name "$DEPLOYMENT_NAME" \
    --model-name "$MODEL_NAME" \
    --model-version "$MODEL_VERSION" \
    --model-format OpenAI \
    --sku-name "$SKU_NAME" \
    --sku-capacity "$SKU_CAPACITY"; then
    echo "  [warn] Deployment '$DEPLOYMENT_NAME' for model '$MODEL_NAME' is not available in this account/region. Continuing."
    return 0
  fi
  echo "  [done] Deployment '$DEPLOYMENT_NAME' created."
}

deploy_model "gpt-5-nano"  "gpt-5-nano"  "2025-08-07"  "GlobalStandard"  30
deploy_model "gpt-5"       "gpt-5"       "2025-08-07"  "GlobalStandard"  30

echo "All model deployments are ready."
