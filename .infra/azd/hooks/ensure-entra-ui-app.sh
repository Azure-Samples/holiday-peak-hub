#!/usr/bin/env sh
# Ensures a Microsoft Entra app registration exists for the UI and writes
# its identifiers into the azd environment.

set -eu

ENV_NAME="${1:-${AZURE_ENV_NAME:-dev}}"
DISPLAY_NAME="${2:-}"
FAIL_ON_ERROR="${FAIL_ON_ERROR:-false}"

run_safe() {
  if "$@"; then
    return 0
  fi

  if [ "$FAIL_ON_ERROR" = "true" ]; then
    return 1
  fi

  echo "Warning: command failed but continuing: $*"
  return 0
}

AZD_VALUES="$(azd env get-values -e "$ENV_NAME" 2>/dev/null || true)"
if [ -z "$AZD_VALUES" ]; then
  if [ "$FAIL_ON_ERROR" = "true" ]; then
    echo "Failed to read azd env values for environment '$ENV_NAME'."
    exit 1
  fi
  echo "Warning: Failed to read azd env values for environment '$ENV_NAME'."
  exit 0
fi

get_val() {
  key="$1"
  printf '%s\n' "$AZD_VALUES" | grep -E "^${key}=" | head -n 1 | cut -d '=' -f2- | tr -d '"' || true
}

PROJECT_NAME="$(get_val projectName)"
[ -z "$PROJECT_NAME" ] && PROJECT_NAME="$(get_val PROJECT_NAME)"
[ -z "$PROJECT_NAME" ] && PROJECT_NAME="holidaypeakhub"

ENVIRONMENT_VALUE="$(get_val environment)"
[ -z "$ENVIRONMENT_VALUE" ] && ENVIRONMENT_VALUE="$(get_val ENVIRONMENT)"
[ -z "$ENVIRONMENT_VALUE" ] && ENVIRONMENT_VALUE="$ENV_NAME"

SWA_HOST="$(get_val staticWebAppDefaultHostname)"
[ -z "$SWA_HOST" ] && SWA_HOST="$(get_val STATIC_WEB_APP_DEFAULT_HOSTNAME)"
[ -z "$SWA_HOST" ] && SWA_HOST="$(get_val NEXT_PUBLIC_APP_URL)"

[ -z "$DISPLAY_NAME" ] && DISPLAY_NAME="${PROJECT_NAME}-${ENVIRONMENT_VALUE}-ui"

TENANT_ID="$(az account show --query tenantId -o tsv 2>/dev/null || true)"
if [ -z "$TENANT_ID" ]; then
  if [ "$FAIL_ON_ERROR" = "true" ]; then
    echo "Unable to determine tenant id from current az login."
    exit 1
  fi
  echo "Warning: Unable to determine tenant id from current az login."
  exit 0
fi

REDIRECT_URIS="http://localhost:3000/auth/callback http://localhost:3000"

if [ -n "$SWA_HOST" ]; then
  case "$SWA_HOST" in
    http://*|https://*) SWA_URL="${SWA_HOST%/}" ;;
    *) SWA_URL="https://${SWA_HOST%/}" ;;
  esac
  REDIRECT_URIS="$REDIRECT_URIS ${SWA_URL}/auth/callback ${SWA_URL}"
fi

echo "Ensuring Entra UI app registration '$DISPLAY_NAME'..."

EXISTING_APP_ID="$(az ad app list --display-name "$DISPLAY_NAME" --query '[0].appId' -o tsv 2>/dev/null || true)"

if [ -z "$EXISTING_APP_ID" ]; then
  APP_ID="$(az ad app create \
    --display-name "$DISPLAY_NAME" \
    --sign-in-audience AzureADMyOrg \
    --query appId -o tsv 2>/dev/null || true)"

  if [ -z "$APP_ID" ]; then
    if [ "$FAIL_ON_ERROR" = "true" ]; then
      echo "Failed creating Entra app registration '$DISPLAY_NAME'."
      exit 1
    fi
    echo "Warning: Failed creating Entra app registration '$DISPLAY_NAME'."
    exit 0
  fi

  echo "  [create] Created Entra app with client id: $APP_ID"
else
  APP_ID="$EXISTING_APP_ID"
fi

REDIRECT_JSON="$(python -c "import json; print(json.dumps('''$REDIRECT_URIS'''.split()))")"
OBJECT_ID="$(az ad app show --id "$APP_ID" --query id -o tsv 2>/dev/null || true)"
if [ -z "$OBJECT_ID" ]; then
  if [ "$FAIL_ON_ERROR" = "true" ]; then
    echo "Failed resolving object id for Entra app '$DISPLAY_NAME'."
    exit 1
  fi
  echo "Warning: Failed resolving object id for Entra app '$DISPLAY_NAME'."
  exit 0
fi

PAYLOAD_FILE="$(mktemp)"
printf '{"spa":{"redirectUris":%s}}' "$REDIRECT_JSON" > "$PAYLOAD_FILE"

if ! az rest --method PATCH --uri "https://graph.microsoft.com/v1.0/applications/$OBJECT_ID" --headers "Content-Type=application/json" --body "@$PAYLOAD_FILE" >/dev/null 2>&1; then
  rm -f "$PAYLOAD_FILE"
    if [ "$FAIL_ON_ERROR" = "true" ]; then
      echo "Failed updating SPA redirect URIs for Entra app '$DISPLAY_NAME'."
      exit 1
    fi
    echo "Warning: Failed updating SPA redirect URIs for Entra app '$DISPLAY_NAME'."
    exit 0
fi
rm -f "$PAYLOAD_FILE"

if [ -z "$EXISTING_APP_ID" ]; then
  echo "  [update] Set SPA redirect URIs for client id: $APP_ID"
else
  echo "  [update] Updated Entra app redirect URIs for client id: $APP_ID"
fi

run_safe azd env set NEXT_PUBLIC_ENTRA_CLIENT_ID "$APP_ID" -e "$ENV_NAME" >/dev/null
run_safe azd env set NEXT_PUBLIC_ENTRA_TENANT_ID "$TENANT_ID" -e "$ENV_NAME" >/dev/null
run_safe azd env set ENTRA_CLIENT_ID "$APP_ID" -e "$ENV_NAME" >/dev/null
run_safe azd env set ENTRA_TENANT_ID "$TENANT_ID" -e "$ENV_NAME" >/dev/null

echo "Entra UI app registration is ready and azd env values were updated."