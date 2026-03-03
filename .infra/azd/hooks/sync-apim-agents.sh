#!/usr/bin/env sh

set -eu

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
AZURE_YAML_PATH="${AZURE_YAML_PATH:-$REPO_ROOT/azure.yaml}"
NAMESPACE="${K8S_NAMESPACE:-holiday-peak}"
API_PATH_PREFIX="${API_PATH_PREFIX:-agents}"
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-${RESOURCE_GROUP:-}}"
APIM_NAME="${APIM_NAME:-}"
AKS_CLUSTER_NAME="${AKS_CLUSTER_NAME:-}"
APP_GW_NAME="${APP_GW_NAME:-}"
USE_INGRESS="${USE_INGRESS:-false}"
REQUIRE_LOAD_BALANCER=true
BACKEND_RESOLVE_RETRIES="${BACKEND_RESOLVE_RETRIES:-24}"
BACKEND_RESOLVE_DELAY_SECONDS="${BACKEND_RESOLVE_DELAY_SECONDS:-5}"
PREVIEW=false

while [ "$#" -gt 0 ]; do
  case "$1" in
    --preview)
      PREVIEW=true
      ;;
    --require-load-balancer)
      REQUIRE_LOAD_BALANCER=true
      USE_INGRESS=false
      ;;
    --allow-non-lb)
      REQUIRE_LOAD_BALANCER=false
      ;;
    --use-ingress)
      USE_INGRESS=true
      REQUIRE_LOAD_BALANCER=false
      ;;
    --namespace)
      shift
      NAMESPACE="$1"
      ;;
    --resource-group)
      shift
      RESOURCE_GROUP="$1"
      ;;
    --apim-name)
      shift
      APIM_NAME="$1"
      ;;
    --aks-cluster-name)
      shift
      AKS_CLUSTER_NAME="$1"
      ;;
    --app-gw-name)
      shift
      APP_GW_NAME="$1"
      ;;
    --azure-yaml)
      shift
      AZURE_YAML_PATH="$1"
      ;;
    --api-path-prefix)
      shift
      API_PATH_PREFIX="$1"
      ;;
    *)
      echo "Unknown argument: $1"
      exit 1
      ;;
  esac
  shift
done

# Initialize App Gateway IP cache
APP_GW_IP=""

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

if [ -z "$AKS_CLUSTER_NAME" ] && [ -n "${AZURE_ENV_NAME:-}" ]; then
  ENV_FILE="$REPO_ROOT/.azure/$AZURE_ENV_NAME/.env"
  if [ -f "$ENV_FILE" ]; then
    AKS_CLUSTER_NAME="$(grep -E '^(AKS_CLUSTER_NAME|aksClusterName)=' "$ENV_FILE" | head -n 1 | cut -d '=' -f2- | tr -d '"' || true)"
  fi
fi

if [ -z "$AKS_CLUSTER_NAME" ]; then
  AKS_CLUSTER_NAME="$(az aks list --resource-group "$RESOURCE_GROUP" --query '[0].name' -o tsv 2>/dev/null || true)"
fi

if [ "$PREVIEW" = false ]; then
  if ! command -v kubectl >/dev/null 2>&1; then
    echo "kubectl is required to resolve APIM backends."
    exit 1
  fi
  if [ -z "$AKS_CLUSTER_NAME" ]; then
    echo "AKS cluster name could not be resolved. Set AKS_CLUSTER_NAME."
    exit 1
  fi
  az aks get-credentials --resource-group "$RESOURCE_GROUP" --name "$AKS_CLUSTER_NAME" --overwrite-existing --only-show-errors >/dev/null
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
        if current_service and current_host == "aks":
            services.append(current_service)
        current_service = service_match.group(1)
        current_host = None
        continue

    host_match = re.match(r"^    host:\s*([^\s]+)\s*$", line)
    if host_match:
        current_host = host_match.group(1)

if current_service and current_host == "aks":
    services.append(current_service)

print("\n".join(services))
PY
)"

if [ -z "$SERVICES" ]; then
  echo "No AKS agent services were found in azure.yaml. Nothing to sync."
  exit 0
fi

echo "Syncing APIM APIs for AKS agent services into $APIM_NAME (RG: $RESOURCE_GROUP)..."

resolve_backend_url() {
  svc="$1"
  resolved_name=""
  resolved_port="80"
  lb_host=""
  attempt=1

  # If using Ingress (AGIC), resolve via App Gateway public IP
  if [ "$USE_INGRESS" = true ]; then
    if [ -z "$APP_GW_IP" ]; then
      if [ -n "$APP_GW_NAME" ]; then
        APP_GW_IP="$(az network public-ip show \
          --resource-group "$RESOURCE_GROUP" \
          --name "${APP_GW_NAME}-pip" \
          --query ipAddress -o tsv 2>/dev/null || true)"
      fi
      if [ -z "$APP_GW_IP" ]; then
        # Try to find App Gateway public IP from VNet
        APP_GW_IP="$(az network application-gateway list \
          --resource-group "$RESOURCE_GROUP" \
          --query "[0].frontendIPConfigurations[0].publicIPAddress.id" -o tsv 2>/dev/null | \
          xargs -I{} az network public-ip show --ids {} --query ipAddress -o tsv 2>/dev/null || true)"
      fi
    fi
    if [ -n "$APP_GW_IP" ]; then
      # Route through App Gateway with path-based routing
      printf 'http://%s/%s' "$APP_GW_IP" "$svc"
      return
    fi
    echo "App Gateway IP could not be resolved. Falling back to cluster DNS." >&2
  fi

  if command -v kubectl >/dev/null 2>&1; then
    resolved_name="$(kubectl get svc -n "$NAMESPACE" -l "app=$svc" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)"
    if [ -n "$resolved_name" ]; then
      resolved_port="$(kubectl get svc "$resolved_name" -n "$NAMESPACE" -o jsonpath='{.spec.ports[0].port}' 2>/dev/null || true)"
      [ -z "$resolved_port" ] && resolved_port="80"

      while [ "$attempt" -le "$BACKEND_RESOLVE_RETRIES" ]; do
        lb_host="$(kubectl get svc "$resolved_name" -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || true)"
        if [ -n "$lb_host" ]; then
          printf 'http://%s:%s' "$lb_host" "$resolved_port"
          return
        fi

        lb_host="$(kubectl get svc "$resolved_name" -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || true)"
        if [ -n "$lb_host" ]; then
          printf 'http://%s:%s' "$lb_host" "$resolved_port"
          return
        fi

        if [ "$attempt" -lt "$BACKEND_RESOLVE_RETRIES" ]; then
          sleep "$BACKEND_RESOLVE_DELAY_SECONDS"
        fi
        attempt=$((attempt + 1))
      done

      if [ "$REQUIRE_LOAD_BALANCER" = false ]; then
        cluster_ip="$(kubectl get svc "$resolved_name" -n "$NAMESPACE" -o jsonpath='{.spec.clusterIP}' 2>/dev/null || true)"
        if [ -n "$cluster_ip" ]; then
          printf 'http://%s:%s' "$cluster_ip" "$resolved_port"
          return
        fi

        printf 'http://%s.%s.svc.cluster.local:%s' "$resolved_name" "$NAMESPACE" "$resolved_port"
        return
      fi

      echo "Service '$svc' has no load balancer address in namespace '$NAMESPACE'." >&2
      return 1
    fi
  fi

  if [ "$REQUIRE_LOAD_BALANCER" = true ]; then
    echo "Service '$svc' could not be resolved from Kubernetes in namespace '$NAMESPACE'." >&2
    return 1
  fi

  printf 'http://%s-%s.%s.svc.cluster.local:80' "$svc" "$svc" "$NAMESPACE"
}

ensure_crud_api() {
  API_ID="crud"
  DISPLAY_NAME="CRUD Service"
  API_PATH="api"

  if [ "$PREVIEW" = true ]; then
    echo "[preview] api-id=$API_ID path=$API_PATH"
    return
  fi

  BACKEND_URL="$(resolve_backend_url crud-service)"

  if az apim api show --resource-group "$RESOURCE_GROUP" --service-name "$APIM_NAME" --api-id "crud-service" >/dev/null 2>&1; then
    API_ID="crud-service"
  elif az apim api show --resource-group "$RESOURCE_GROUP" --service-name "$APIM_NAME" --api-id "crud" >/dev/null 2>&1; then
    API_ID="crud"
  fi

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

  for OP_ID in \
    health \
    api-root-get api-root-post \
    api-get api-post api-put api-patch api-delete api-options \
    acp-get acp-post acp-put acp-patch acp-delete; do
    az apim api operation delete \
      --resource-group "$RESOURCE_GROUP" \
      --service-name "$APIM_NAME" \
      --api-id "$API_ID" \
      --operation-id "$OP_ID" \
      --if-match '*' \
      >/dev/null 2>&1 || true
  done

  az apim api operation create --resource-group "$RESOURCE_GROUP" --service-name "$APIM_NAME" --api-id "$API_ID" --operation-id health --display-name "Health" --method GET --url-template "/health" >/dev/null
  az apim api operation create --resource-group "$RESOURCE_GROUP" --service-name "$APIM_NAME" --api-id "$API_ID" --operation-id api-root-get --display-name "API Root GET" --method GET --url-template "/" >/dev/null
  az apim api operation create --resource-group "$RESOURCE_GROUP" --service-name "$APIM_NAME" --api-id "$API_ID" --operation-id api-root-post --display-name "API Root POST" --method POST --url-template "/" >/dev/null

  for METHOD in GET POST PUT PATCH DELETE OPTIONS; do
    op="api-$(printf '%s' "$METHOD" | tr '[:upper:]' '[:lower:]')"
    az apim api operation create \
      --resource-group "$RESOURCE_GROUP" \
      --service-name "$APIM_NAME" \
      --api-id "$API_ID" \
      --operation-id "$op" \
      --display-name "API $METHOD" \
      --method "$METHOD" \
      --url-template "/{*path}" \
      --template-parameters name=path description="Wildcard route path" type=string required=false \
      >/dev/null
  done

  for METHOD in GET POST PUT PATCH DELETE; do
    op="acp-$(printf '%s' "$METHOD" | tr '[:upper:]' '[:lower:]')"
    az apim api operation create \
      --resource-group "$RESOURCE_GROUP" \
      --service-name "$APIM_NAME" \
      --api-id "$API_ID" \
      --operation-id "$op" \
      --display-name "ACP $METHOD" \
      --method "$METHOD" \
      --url-template "/acp/{*path}" \
      --template-parameters name=path description="Wildcard ACP path" type=string required=false \
      >/dev/null
  done

  SUBSCRIPTION_ID="$(az account show --query id -o tsv 2>/dev/null || true)"
  if [ -z "$SUBSCRIPTION_ID" ]; then
    echo "Failed to resolve Azure subscription id for CRUD APIM policy update."
    return 1
  fi

  POLICY_FILE="$(mktemp)"
  cat > "$POLICY_FILE" <<'JSON'
{
  "properties": {
    "format": "rawxml",
    "value": "<policies><inbound><base /><choose><when condition=\"@(context.Request.OriginalUrl.Path == &quot;/api/health&quot;)\"><rewrite-uri template=\"/health\" copy-unmatched-params=\"true\" /></when><otherwise><rewrite-uri template=\"@(string.Concat(&quot;/api&quot;, context.Request.OriginalUrl.Path.Substring(4)))\" copy-unmatched-params=\"true\" /></otherwise></choose></inbound><backend><base /></backend><outbound><base /></outbound><on-error><base /></on-error></policies>"
  }
}
JSON

  POLICY_URL="https://management.azure.com/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.ApiManagement/service/$APIM_NAME/apis/$API_ID/policies/policy?api-version=2022-08-01"
  az rest --method put --url "$POLICY_URL" --headers "Content-Type=application/json" --body "@$POLICY_FILE" --only-show-errors >/dev/null
  rm -f "$POLICY_FILE"
}

echo "$SERVICES" | while IFS= read -r SERVICE; do
  [ -z "$SERVICE" ] && continue

  if [ "$SERVICE" = "crud-service" ]; then
    ensure_crud_api
    continue
  fi

  API_ID="agent-$SERVICE"
  DISPLAY_NAME="Agent - $SERVICE"
  API_PATH="$API_PATH_PREFIX/$SERVICE"

  if [ "$PREVIEW" = true ]; then
    echo "[preview] api-id=$API_ID path=$API_PATH"
    continue
  fi

  BACKEND_URL="$(resolve_backend_url "$SERVICE")"

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
