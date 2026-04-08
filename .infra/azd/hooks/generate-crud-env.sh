#!/usr/bin/env sh

set -eu

ENV_NAME="${1:-${AZURE_ENV_NAME:-dev}}"
OUTPUT_PATH="${2:-apps/crud-service/.env}"
FORCE="${FORCE:-false}"

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
OUTPUT_FILE="$REPO_ROOT/$OUTPUT_PATH"

if [ -f "$OUTPUT_FILE" ] && [ "$FORCE" != "true" ]; then
  echo "Output file already exists: $OUTPUT_FILE"
  echo "Set FORCE=true to overwrite."
  exit 1
fi

AZD_VALUES="$(azd env get-values -e "$ENV_NAME" 2>/dev/null || true)"
if [ -z "$AZD_VALUES" ]; then
  echo "Failed to read azd env values for environment '$ENV_NAME'."
  exit 1
fi

get_val() {
  key="$1"
  printf '%s\n' "$AZD_VALUES" | grep -E "^${key}=" | head -n 1 | cut -d '=' -f2- | tr -d '"' || true
}

ensure_suffix() {
  value="$1"
  suffix="$2"
  if [ -z "$value" ]; then
    echo ""
    return
  fi
  case "$value" in
    *.*) echo "$value" ;;
    *) echo "${value}${suffix}" ;;
  esac
}

RESOURCE_GROUP="$(get_val AZURE_RESOURCE_GROUP)"
[ -z "$RESOURCE_GROUP" ] && RESOURCE_GROUP="$(get_val resourceGroupName)"

ENVIRONMENT_VALUE="$(get_val ENVIRONMENT)"
[ -z "$ENVIRONMENT_VALUE" ] && ENVIRONMENT_VALUE="$(get_val environment)"
[ -z "$ENVIRONMENT_VALUE" ] && ENVIRONMENT_VALUE="$ENV_NAME"

POSTGRES_HOST="$(get_val POSTGRES_HOST)"
[ -z "$POSTGRES_HOST" ] && POSTGRES_HOST="$(get_val postgresFqdn)"
[ -z "$POSTGRES_HOST" ] && POSTGRES_HOST="$(get_val POSTGRES_FQDN)"

POSTGRES_DATABASE="$(get_val POSTGRES_DATABASE)"
[ -z "$POSTGRES_DATABASE" ] && POSTGRES_DATABASE="$(get_val postgresDatabaseName)"
[ -z "$POSTGRES_DATABASE" ] && POSTGRES_DATABASE="holiday_peak_crud"

POSTGRES_AUTH_MODE="$(get_val POSTGRES_AUTH_MODE)"
[ -z "$POSTGRES_AUTH_MODE" ] && POSTGRES_AUTH_MODE="$(get_val postgresAuthMode)"
[ -z "$POSTGRES_AUTH_MODE" ] && POSTGRES_AUTH_MODE="password"

POSTGRES_ADMIN_USER="$(get_val POSTGRES_ADMIN_USER)"
[ -z "$POSTGRES_ADMIN_USER" ] && POSTGRES_ADMIN_USER="$(get_val postgresAdminUser)"
[ -z "$POSTGRES_ADMIN_USER" ] && POSTGRES_ADMIN_USER="crud_admin"

POSTGRES_USER="$(get_val POSTGRES_USER)"
if [ "$POSTGRES_AUTH_MODE" = "password" ]; then
  POSTGRES_USER="$POSTGRES_ADMIN_USER"
elif [ -z "$POSTGRES_USER" ] || [ "$POSTGRES_USER" = "$POSTGRES_ADMIN_USER" ] || [ "$POSTGRES_USER" = "crud_admin" ]; then
  AKS_CLUSTER_NAME="$(get_val AZURE_AKS_CLUSTER_NAME)"
  [ -z "$AKS_CLUSTER_NAME" ] && AKS_CLUSTER_NAME="$(get_val AKS_CLUSTER_NAME)"
  [ -z "$AKS_CLUSTER_NAME" ] && AKS_CLUSTER_NAME="$(get_val aksClusterName)"

  if [ -n "$AKS_CLUSTER_NAME" ]; then
    POSTGRES_USER="${AKS_CLUSTER_NAME}-agentpool"
  else
    PROJECT_NAME="$(get_val projectName)"
    [ -z "$PROJECT_NAME" ] && PROJECT_NAME="$(get_val PROJECT_NAME)"

    if [ -n "$PROJECT_NAME" ]; then
      if [ "$ENVIRONMENT_VALUE" = "prod" ]; then
        POSTGRES_USER="${PROJECT_NAME}-aks-agentpool"
      else
        POSTGRES_USER="${PROJECT_NAME}-${ENVIRONMENT_VALUE}-aks-agentpool"
      fi
    else
      POSTGRES_USER="crud-${ENVIRONMENT_VALUE}-aks-agentpool"
    fi
  fi
fi

EVENT_HUB_NAMESPACE="$(get_val EVENT_HUB_NAMESPACE)"
[ -z "$EVENT_HUB_NAMESPACE" ] && EVENT_HUB_NAMESPACE="$(get_val eventHubsNamespaceName)"
EVENT_HUB_NAMESPACE="$(ensure_suffix "$EVENT_HUB_NAMESPACE" '.servicebus.windows.net')"

KEY_VAULT_URI="$(get_val KEY_VAULT_URI)"
[ -z "$KEY_VAULT_URI" ] && KEY_VAULT_URI="$(get_val keyVaultUri)"

REDIS_HOST="$(get_val REDIS_HOST)"
[ -z "$REDIS_HOST" ] && REDIS_HOST="$(get_val redisName)"
REDIS_HOST="$(ensure_suffix "$REDIS_HOST" '.redis.cache.windows.net')"
REDIS_PASSWORD="$(get_val REDIS_PASSWORD)"
REDIS_PASSWORD_SECRET_NAME="$(get_val REDIS_PASSWORD_SECRET_NAME)"
[ -z "$REDIS_PASSWORD_SECRET_NAME" ] && REDIS_PASSWORD_SECRET_NAME="$(get_val redisPasswordSecretName)"
[ -z "$REDIS_PASSWORD_SECRET_NAME" ] && REDIS_PASSWORD_SECRET_NAME="redis-primary-key"

ENTRA_TENANT_ID="$(get_val ENTRA_TENANT_ID)"
[ -z "$ENTRA_TENANT_ID" ] && ENTRA_TENANT_ID="$(get_val NEXT_PUBLIC_ENTRA_TENANT_ID)"

ENTRA_CLIENT_ID="$(get_val ENTRA_CLIENT_ID)"
[ -z "$ENTRA_CLIENT_ID" ] && ENTRA_CLIENT_ID="$(get_val NEXT_PUBLIC_ENTRA_CLIENT_ID)"

APIM_GATEWAY_URL="$(get_val AGENT_APIM_BASE_URL)"
[ -z "$APIM_GATEWAY_URL" ] && APIM_GATEWAY_URL="$(get_val APIM_GATEWAY_URL)"
[ -z "$APIM_GATEWAY_URL" ] && APIM_GATEWAY_URL="$(get_val apimGatewayUrl)"

if [ -z "$APIM_GATEWAY_URL" ]; then
  APIM_NAME="$(get_val APIM_NAME)"
  [ -z "$APIM_NAME" ] && APIM_NAME="$(get_val apimName)"
  if [ -z "$APIM_NAME" ] && [ -n "$RESOURCE_GROUP" ]; then
    APIM_NAME="$(az apim list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv 2>/dev/null || true)"
  fi
  if [ -n "$APIM_NAME" ]; then
    APIM_GATEWAY_URL="https://${APIM_NAME}.azure-api.net"
  fi
fi

mkdir -p "$(dirname "$OUTPUT_FILE")"

cat > "$OUTPUT_FILE" <<EOF
# Auto-generated from azd env '$ENV_NAME'
# Source: azd env get-values -e $ENV_NAME

ENVIRONMENT=$ENVIRONMENT_VALUE
SERVICE_NAME=crud-service
LOG_LEVEL=INFO

POSTGRES_HOST=$POSTGRES_HOST
POSTGRES_PORT=5432
POSTGRES_DATABASE=$POSTGRES_DATABASE
POSTGRES_AUTH_MODE=$POSTGRES_AUTH_MODE
POSTGRES_USER=$POSTGRES_USER
POSTGRES_PASSWORD=
POSTGRES_PASSWORD_SECRET_NAME=postgres-admin-password
POSTGRES_ENTRA_SCOPE=https://ossrdbms-aad.database.windows.net/.default
POSTGRES_SSL=true

EVENT_HUB_NAMESPACE=$EVENT_HUB_NAMESPACE
KEY_VAULT_URI=$KEY_VAULT_URI
REDIS_HOST=$REDIS_HOST
REDIS_PASSWORD=$REDIS_PASSWORD
REDIS_PASSWORD_SECRET_NAME=$REDIS_PASSWORD_SECRET_NAME
REDIS_PORT=6380
REDIS_DB=0
REDIS_SSL=true

ENTRA_TENANT_ID=$ENTRA_TENANT_ID
ENTRA_CLIENT_ID=$ENTRA_CLIENT_ID
ENTRA_CLIENT_SECRET=
ENTRA_ISSUER=

ENABLE_AGENT_FALLBACK=true
AGENT_TIMEOUT_SECONDS=0.5
AGENT_RETRY_ATTEMPTS=2
AGENT_CIRCUIT_FAILURE_THRESHOLD=5
AGENT_CIRCUIT_RECOVERY_SECONDS=60

AGENT_APIM_BASE_URL=$APIM_GATEWAY_URL

PRODUCT_ENRICHMENT_AGENT_URL=
CART_INTELLIGENCE_AGENT_URL=
INVENTORY_HEALTH_AGENT_URL=
CHECKOUT_SUPPORT_AGENT_URL=

APP_INSIGHTS_CONNECTION_STRING=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
SENDGRID_API_KEY=
EOF

echo "Generated CRUD env file at: $OUTPUT_FILE"
