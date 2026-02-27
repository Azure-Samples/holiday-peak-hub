#!/usr/bin/env sh

set -eu

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
AZURE_YAML_PATH="${AZURE_YAML_PATH:-$REPO_ROOT/azure.yaml}"
NAMESPACE="${K8S_NAMESPACE:-holiday-peak}"
API_PATH_PREFIX="${API_PATH_PREFIX:-agents}"
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-${RESOURCE_GROUP:-}}"
APIM_NAME="${APIM_NAME:-}"

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

if [ -z "$APIM_NAME" ] && [ -n "${AZURE_ENV_NAME:-}" ]; then
  ENV_FILE="$REPO_ROOT/.azure/$AZURE_ENV_NAME/.env"
  if [ -f "$ENV_FILE" ]; then
    APIM_NAME="$(grep -E '^(APIM_NAME|apimName)=' "$ENV_FILE" | head -n 1 | cut -d '=' -f2- | tr -d '"' || true)"
  fi
fi

if [ -z "$APIM_NAME" ]; then
  APIM_NAME="$(az apim list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv 2>/dev/null || true)"
fi

if [ -z "$APIM_NAME" ]; then
  echo "APIM name could not be resolved. Set APIM_NAME."
  exit 1
fi

SERVICES="$(python - "$AZURE_YAML_PATH" << 'PY'
import re
import sys

path = sys.argv[1]
with open(path, encoding="utf-8") as f:
    lines = f.readlines()

in_services = False
current_service = None
current_host = None
services = []

for raw in lines:
    line = raw.rstrip("\n")
    if not in_services:
        if re.match(r"^services:\s*$", line):
            in_services = True
        continue

    if re.match(r"^[^\s]", line):
        break

    service_match = re.match(r"^  ([a-z0-9\-]+):\s*$", line)
    if service_match:
        if current_service and current_host == "aks" and current_service != "crud-service":
            services.append(current_service)
        current_service = service_match.group(1)
        current_host = None
        continue

    host_match = re.match(r"^    host:\s*([^\s]+)\s*$", line)
    if host_match:
        current_host = host_match.group(1)

if current_service and current_host == "aks" and current_service != "crud-service":
    services.append(current_service)

print("\n".join(services))
PY
)"

if [ -z "$SERVICES" ]; then
  echo "No AKS agent services were found in azure.yaml. Nothing to sync."
  exit 0
fi

echo "Syncing APIM APIs for AKS agent services into $APIM_NAME (RG: $RESOURCE_GROUP)..."

echo "$SERVICES" | while IFS= read -r SERVICE; do
  [ -z "$SERVICE" ] && continue

  API_ID="agent-$SERVICE"
  DISPLAY_NAME="Agent - $SERVICE"
  API_PATH="$API_PATH_PREFIX/$SERVICE"
  BACKEND_URL="http://$SERVICE-$SERVICE.$NAMESPACE.svc.cluster.local"

  if az apim api show --resource-group "$RESOURCE_GROUP" --service-name "$APIM_NAME" --api-id "$API_ID" >/dev/null 2>&1; then
    az apim api update \
      --resource-group "$RESOURCE_GROUP" \
      --service-name "$APIM_NAME" \
      --api-id "$API_ID" \
      --display-name "$DISPLAY_NAME" \
      --path "$API_PATH" \
      --protocols https http \
      --service-url "$BACKEND_URL" \
      --subscription-required false \
      >/dev/null
    echo "Updated API: $API_ID"
  else
    az apim api create \
      --resource-group "$RESOURCE_GROUP" \
      --service-name "$APIM_NAME" \
      --api-id "$API_ID" \
      --display-name "$DISPLAY_NAME" \
      --path "$API_PATH" \
      --protocols https http \
      --service-url "$BACKEND_URL" \
      --subscription-required false \
      >/dev/null
    echo "Created API: $API_ID"
  fi

  for OP_ID in health invoke mcp-tool; do
    az apim api operation delete \
      --resource-group "$RESOURCE_GROUP" \
      --service-name "$APIM_NAME" \
      --api-id "$API_ID" \
      --operation-id "$OP_ID" \
      --if-match '*' \
      >/dev/null 2>&1 || true
  done

  az apim api operation create --resource-group "$RESOURCE_GROUP" --service-name "$APIM_NAME" --api-id "$API_ID" --operation-id health --display-name "Health" --method GET --url-template "/health" >/dev/null
  az apim api operation create --resource-group "$RESOURCE_GROUP" --service-name "$APIM_NAME" --api-id "$API_ID" --operation-id invoke --display-name "Invoke" --method POST --url-template "/invoke" >/dev/null
  az apim api operation create --resource-group "$RESOURCE_GROUP" --service-name "$APIM_NAME" --api-id "$API_ID" --operation-id mcp-tool --display-name "MCP Tool" --method POST --url-template "/mcp/{tool}" --template-parameters name=tool description="MCP tool name" type=string required=true >/dev/null
done

echo "APIM agent sync completed."
