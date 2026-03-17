#!/usr/bin/env sh
set -eu

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
RESOURCE_GROUP="${1:-${AZURE_RESOURCE_GROUP:-}}"
SEARCH_SERVICE_NAME="${2:-${AI_SEARCH_NAME:-}}"
INDEX_NAME="${3:-${AI_SEARCH_INDEX:-}}"

resolve_from_azd_env() {
  KEY_PATTERN="$1"
  if [ -z "${AZURE_ENV_NAME:-}" ]; then
    return 0
  fi

  ENV_FILE="$REPO_ROOT/.azure/$AZURE_ENV_NAME/.env"
  if [ ! -f "$ENV_FILE" ]; then
    return 0
  fi

  grep -E "^(${KEY_PATTERN})=" "$ENV_FILE" | head -n 1 | cut -d '=' -f2- | tr -d '"' || true
}

if [ -z "$RESOURCE_GROUP" ]; then
  RESOURCE_GROUP="$(resolve_from_azd_env 'AZURE_RESOURCE_GROUP|resourceGroupName')"
fi

if [ -z "$SEARCH_SERVICE_NAME" ]; then
  SEARCH_SERVICE_NAME="$(resolve_from_azd_env 'AI_SEARCH_NAME|aiSearchName')"
fi

if [ -z "$INDEX_NAME" ]; then
  INDEX_NAME="$(resolve_from_azd_env 'AI_SEARCH_INDEX|aiSearchIndexName')"
fi

if [ -z "$RESOURCE_GROUP" ]; then
  echo 'Resource group could not be resolved. Set AZURE_RESOURCE_GROUP or run inside an azd environment.'
  exit 1
fi

if [ -z "$SEARCH_SERVICE_NAME" ]; then
  SEARCH_SERVICE_NAME="$(az resource list --resource-group "$RESOURCE_GROUP" --resource-type Microsoft.Search/searchServices --query '[0].name' -o tsv 2>/dev/null || true)"
fi

if [ -z "$SEARCH_SERVICE_NAME" ]; then
  echo 'Azure AI Search service name could not be resolved. Set AI_SEARCH_NAME.'
  exit 1
fi

if [ -z "$INDEX_NAME" ]; then
  INDEX_NAME='catalog-products'
fi

echo "Ensuring Azure AI Search index '${INDEX_NAME}' on service '${SEARCH_SERVICE_NAME}' (RG: ${RESOURCE_GROUP})"

attempt=1
SERVICE_ID=""
while [ "$attempt" -le 18 ]; do
  SERVICE_ID="$(az resource show --resource-group "$RESOURCE_GROUP" --resource-type Microsoft.Search/searchServices --name "$SEARCH_SERVICE_NAME" --query id -o tsv 2>/dev/null || true)"
  if [ -n "$SERVICE_ID" ]; then
    break
  fi

  if [ "$attempt" -eq 18 ]; then
    echo "Azure AI Search service '${SEARCH_SERVICE_NAME}' was not reachable after waiting for postprovision readiness."
    exit 1
  fi

  attempt=$((attempt + 1))
  sleep 10
done

SEARCH_ENDPOINT="$(az resource show --ids "$SERVICE_ID" --query properties.endpoint -o tsv)"
ADMIN_KEY="$(az rest --only-show-errors --method post --uri "https://management.azure.com${SERVICE_ID}/listAdminKeys?api-version=2022-09-01" --query primaryKey -o tsv)"
INDEX_URI="${SEARCH_ENDPOINT}/indexes('${INDEX_NAME}')?api-version=2024-07-01"

INDEX_DEFINITION=$(cat <<EOF
{"name":"${INDEX_NAME}","fields":[{"name":"id","type":"Edm.String","key":true,"filterable":true,"searchable":false},{"name":"sku","type":"Edm.String","searchable":true,"filterable":true},{"name":"title","type":"Edm.String","searchable":true},{"name":"description","type":"Edm.String","searchable":true},{"name":"content","type":"Edm.String","searchable":true},{"name":"category","type":"Edm.String","searchable":true,"filterable":true},{"name":"brand","type":"Edm.String","searchable":true,"filterable":true},{"name":"availability","type":"Edm.String","filterable":true},{"name":"price","type":"Edm.Double","filterable":true,"sortable":true}]}
EOF
)

attempt=1
while [ "$attempt" -le 12 ]; do
  if curl -fsS -X PUT -H "api-key: ${ADMIN_KEY}" -H 'Content-Type: application/json' --data "$INDEX_DEFINITION" "$INDEX_URI" >/dev/null; then
    echo "Azure AI Search index '${INDEX_NAME}' is ready."
    exit 0
  fi

  if [ "$attempt" -eq 12 ]; then
    echo "Failed to create or update Azure AI Search index '${INDEX_NAME}' on service '${SEARCH_SERVICE_NAME}'."
    exit 1
  fi

  attempt=$((attempt + 1))
  sleep 10
done