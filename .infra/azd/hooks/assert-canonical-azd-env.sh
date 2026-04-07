#!/usr/bin/env sh
set -eu

ENVIRONMENT="${1:-${AZURE_ENV_NAME:-}}"

if [ -z "$ENVIRONMENT" ]; then
  echo "Environment must be provided as the first argument or AZURE_ENV_NAME." >&2
  exit 1
fi

if ! command -v azd >/dev/null 2>&1; then
  echo "Required command 'azd' is not available on PATH." >&2
  exit 1
fi

if ! AZD_VALUES="$(azd env get-values -e "$ENVIRONMENT" 2>/dev/null)"; then
  AZD_VALUES=""
fi

get_env_value() {
  key="$1"
  value="$(printf '%s\n' "$AZD_VALUES" | grep -E "^${key}=" | tail -n 1 | cut -d '=' -f 2- || true)"
  case "$value" in
    \"*\") value="${value#\"}"; value="${value%\"}" ;;
    \'*\') value="${value#\'}"; value="${value%\'}" ;;
  esac
  printf '%s' "$value"
}

# AZURE_LOCATION defaults to 'eastus2'.
AZURE_LOC="$(get_env_value AZURE_LOCATION)"
if [ -z "$AZURE_LOC" ]; then
  echo "AZURE_LOCATION not set - defaulting to 'eastus2'."
  azd env set AZURE_LOCATION "eastus2" -e "$ENVIRONMENT"
fi

# projectName defaults to the azd environment name.
PROJECT_NAME="$(get_env_value projectName)"
if [ -z "$PROJECT_NAME" ]; then
  echo "projectName not set - defaulting to AZURE_ENV_NAME '$ENVIRONMENT'."
  azd env set projectName "$ENVIRONMENT" -e "$ENVIRONMENT"
  PROJECT_NAME="$ENVIRONMENT"
fi

# environment (dev/staging/prod) defaults to 'dev'.
ENV_VALUE="$(get_env_value environment)"
if [ -z "$ENV_VALUE" ]; then
  echo "environment not set - defaulting to 'dev'."
  azd env set environment "dev" -e "$ENVIRONMENT"
  ENV_VALUE="dev"
fi

EXPECTED_RESOURCE_GROUP="${PROJECT_NAME}-${ENV_VALUE}-rg"

# resourceGroupName defaults to <projectName>-<environment>-rg.
RG_NAME="$(get_env_value resourceGroupName)"
if [ -z "$RG_NAME" ]; then
  echo "resourceGroupName not set - defaulting to '$EXPECTED_RESOURCE_GROUP'."
  azd env set resourceGroupName "$EXPECTED_RESOURCE_GROUP" -e "$ENVIRONMENT"
fi

# AZURE_RESOURCE_GROUP defaults to the same value.
AZURE_RG="$(get_env_value AZURE_RESOURCE_GROUP)"
if [ -z "$AZURE_RG" ]; then
  echo "AZURE_RESOURCE_GROUP not set - defaulting to '$EXPECTED_RESOURCE_GROUP'."
  azd env set AZURE_RESOURCE_GROUP "$EXPECTED_RESOURCE_GROUP" -e "$ENVIRONMENT"
fi

echo "Azd environment defaults resolved for '$ENVIRONMENT': projectName=$PROJECT_NAME, environment=$ENV_VALUE, resourceGroup=$EXPECTED_RESOURCE_GROUP"