#!/usr/bin/env sh
set -eu

ENVIRONMENT="${1:-${AZURE_ENV_NAME:-}}"
CANONICAL_PROJECT_NAME="holidaypeakhub405"

if [ -z "$ENVIRONMENT" ]; then
  echo "Environment must be provided as the first argument or AZURE_ENV_NAME." >&2
  exit 1
fi

if ! command -v azd >/dev/null 2>&1; then
  echo "Required command 'azd' is not available on PATH." >&2
  exit 1
fi

EXPECTED_RESOURCE_GROUP="${CANONICAL_PROJECT_NAME}-${ENVIRONMENT}-rg"

if ! AZD_VALUES="$(azd env get-values -e "$ENVIRONMENT")"; then
  echo "Failed to resolve azd environment values for '$ENVIRONMENT'." >&2
  exit 1
fi

get_required_env_value() {
  key="$1"
  value="$(printf '%s\n' "$AZD_VALUES" | grep -E "^${key}=" | tail -n 1 | cut -d '=' -f 2- || true)"

  if [ -z "$value" ]; then
    echo "Required azd environment value '$key' is missing for '$ENVIRONMENT'." >&2
    exit 1
  fi

  case "$value" in
    \"*\")
      value="${value#\"}"
      value="${value%\"}"
      ;;
    \'*\')
      value="${value#\'}"
      value="${value%\'}"
      ;;
  esac

  printf '%s' "$value"
}

RESOLVED_PROJECT_NAME="$(get_required_env_value projectName)"
RESOLVED_RESOURCE_GROUP_NAME="$(get_required_env_value resourceGroupName)"
RESOLVED_AZURE_RESOURCE_GROUP="$(get_required_env_value AZURE_RESOURCE_GROUP)"

if [ "$RESOLVED_PROJECT_NAME" != "$CANONICAL_PROJECT_NAME" ]; then
  echo "Invalid projectName '$RESOLVED_PROJECT_NAME'. Expected '$CANONICAL_PROJECT_NAME'." >&2
  exit 1
fi

if [ "$RESOLVED_RESOURCE_GROUP_NAME" != "$EXPECTED_RESOURCE_GROUP" ]; then
  echo "Invalid resourceGroupName '$RESOLVED_RESOURCE_GROUP_NAME'. Expected '$EXPECTED_RESOURCE_GROUP'." >&2
  exit 1
fi

if [ "$RESOLVED_AZURE_RESOURCE_GROUP" != "$EXPECTED_RESOURCE_GROUP" ]; then
  echo "Invalid AZURE_RESOURCE_GROUP '$RESOLVED_AZURE_RESOURCE_GROUP'. Expected '$EXPECTED_RESOURCE_GROUP'." >&2
  exit 1
fi

echo "Canonical azd naming guard passed for environment '$ENVIRONMENT'."