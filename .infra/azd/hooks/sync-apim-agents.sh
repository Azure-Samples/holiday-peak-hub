#!/usr/bin/env sh

set -eu

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
AZURE_YAML_PATH="${AZURE_YAML_PATH:-$REPO_ROOT/azure.yaml}"
NAMESPACE="${K8S_NAMESPACE:-holiday-peak}"
API_PATH_PREFIX="${API_PATH_PREFIX:-agents}"
CHANGED_SERVICES="${CHANGED_SERVICES:-}"
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-${RESOURCE_GROUP:-}}"
APIM_NAME="${APIM_NAME:-}"
APIM_CORS_ALLOWED_ORIGINS="${APIM_CORS_ALLOWED_ORIGINS:-http://localhost:3000}"
AKS_CLUSTER_NAME="${AKS_CLUSTER_NAME:-}"
APIM_APPROVED_BACKEND_HOSTNAMES="${APIM_APPROVED_BACKEND_HOSTNAMES:-${AGC_FRONTEND_HOSTNAME:-}}"
APIM_APPROVED_BACKEND_SCHEME="${APIM_APPROVED_BACKEND_SCHEME:-${AGC_FRONTEND_SCHEME:-http}}"
PREVIEW=false
RESOLVED_APPROVED_BACKEND_HOST=""
APPROVED_BACKEND_VALIDATED=false
APPROVED_BACKEND_REFERENCE="${AGC_FRONTEND_REFERENCE:-}"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --preview)
      PREVIEW=true
      ;;
    --require-load-balancer)
      ;;
    --allow-non-lb)
      ;;
    --use-ingress)
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
    --approved-backend-hostnames)
      shift
      APIM_APPROVED_BACKEND_HOSTNAMES="$1"
      ;;
    --approved-backend-scheme)
      shift
      APIM_APPROVED_BACKEND_SCHEME="$1"
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

if [ -z "$APIM_APPROVED_BACKEND_HOSTNAMES" ] && [ -n "${AZURE_ENV_NAME:-}" ]; then
  ENV_FILE="$REPO_ROOT/.azure/$AZURE_ENV_NAME/.env"
  if [ -f "$ENV_FILE" ]; then
    APIM_APPROVED_BACKEND_HOSTNAMES="$(grep -E '^(APIM_APPROVED_BACKEND_HOSTNAMES|AGC_FRONTEND_HOSTNAME)=' "$ENV_FILE" | head -n 1 | cut -d '=' -f2- | tr -d '"' || true)"
    if [ -z "$APPROVED_BACKEND_REFERENCE" ]; then
      APPROVED_BACKEND_REFERENCE="$(grep -E '^(AGC_FRONTEND_REFERENCE)=' "$ENV_FILE" | head -n 1 | cut -d '=' -f2- | tr -d '"' || true)"
    fi
  fi
fi

if [ -z "$APIM_APPROVED_BACKEND_SCHEME" ] && [ -n "${AZURE_ENV_NAME:-}" ]; then
  ENV_FILE="$REPO_ROOT/.azure/$AZURE_ENV_NAME/.env"
  if [ -f "$ENV_FILE" ]; then
    APIM_APPROVED_BACKEND_SCHEME="$(grep -E '^(APIM_APPROVED_BACKEND_SCHEME|AGC_FRONTEND_SCHEME)=' "$ENV_FILE" | head -n 1 | cut -d '=' -f2- | tr -d '"' || true)"
  fi
fi

[ -z "$APIM_APPROVED_BACKEND_SCHEME" ] && APIM_APPROVED_BACKEND_SCHEME="http"

case "$APIM_APPROVED_BACKEND_SCHEME" in
  http|https)
    ;;
  *)
    echo "Unsupported APIM approved backend scheme '$APIM_APPROVED_BACKEND_SCHEME'. Supported values are 'http' and 'https'." >&2
    exit 1
    ;;
esac

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
    echo "kubectl is required to validate APIM backend targets."
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

if [ -n "$CHANGED_SERVICES" ]; then
  FILTER_FILE="$(mktemp)"
  printf '%s' "$CHANGED_SERVICES" | tr ',' '\n' | sed '/^[[:space:]]*$/d' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' > "$FILTER_FILE"
  if printf '%s\n' "$SERVICES" | grep -Fxq 'crud-service' && ! grep -Fxq 'crud-service' "$FILTER_FILE"; then
    printf '%s\n' 'crud-service' >> "$FILTER_FILE"
  fi
  SERVICES="$(printf '%s\n' "$SERVICES" | while IFS= read -r SERVICE; do
    [ -z "$SERVICE" ] && continue
    if grep -Fxq "$SERVICE" "$FILTER_FILE"; then
      printf '%s\n' "$SERVICE"
    fi
  done)"
  rm -f "$FILTER_FILE"
fi

if [ -z "$SERVICES" ]; then
  echo "No matching changed AKS services to sync."
  exit 0
fi

echo "Syncing APIM APIs for AKS agent services into $APIM_NAME (RG: $RESOURCE_GROUP)..."

split_hostname_list() {
  printf '%s' "$1" | tr ',' '\n' | tr -s '[:space:]' '\n' | sed '/^[[:space:]]*$/d' | awk '!seen[$0]++'
}

resolve_approved_backend_host() {
  if [ -n "$RESOLVED_APPROVED_BACKEND_HOST" ]; then
    printf '%s' "$RESOLVED_APPROVED_BACKEND_HOST"
    return 0
  fi

  RESOLVED_APPROVED_BACKEND_HOST="$(split_hostname_list "$APIM_APPROVED_BACKEND_HOSTNAMES" | head -n 1)"
  if [ -z "$RESOLVED_APPROVED_BACKEND_HOST" ]; then
    if [ -n "$APPROVED_BACKEND_REFERENCE" ]; then
      echo "No approved AGC backend hostname was provided. Set APIM_APPROVED_BACKEND_HOSTNAMES or AGC_FRONTEND_HOSTNAME before APIM sync. AGC frontend reference: $APPROVED_BACKEND_REFERENCE" >&2
    else
      echo "No approved AGC backend hostname was provided. Set APIM_APPROVED_BACKEND_HOSTNAMES or AGC_FRONTEND_HOSTNAME before APIM sync." >&2
    fi
    return 1
  fi

  printf '%s' "$RESOLVED_APPROVED_BACKEND_HOST"
}

validate_approved_backend_health() {
  host="$1"
  probe_url="$APIM_APPROVED_BACKEND_SCHEME://$host/health"
  probe_body="/tmp/apim-agc-health.json"
  status_code=""

  for attempt in $(seq 1 8); do
    status_code="$(curl -sS -o "$probe_body" -w '%{http_code}' --max-time 10 "$probe_url" || true)"
    if [ "$status_code" = "200" ] || [ "$status_code" = "404" ]; then
      echo "Validated approved AGC backend host '$host' via $probe_url"
      return 0
    fi
    sleep 5
  done

  echo "AGC backend validation failed for '$host' (last status: ${status_code:-n/a}) using $probe_url" >&2
  cat "$probe_body" 2>/dev/null >&2 || true
  return 1
}

ensure_approved_backend_ready() {
  if [ "$APPROVED_BACKEND_VALIDATED" = true ]; then
    return 0
  fi

  RESOLVED_APPROVED_BACKEND_HOST="$(resolve_approved_backend_host || true)"
  [ -z "$RESOLVED_APPROVED_BACKEND_HOST" ] && return 1

  if [ "$PREVIEW" = false ]; then
    validate_approved_backend_health "$RESOLVED_APPROVED_BACKEND_HOST"
  fi

  APPROVED_BACKEND_VALIDATED=true
  return 0
}

resolve_backend_url() {
  svc="$1"
  ensure_approved_backend_ready
  if [ "$svc" = "crud-service" ]; then
    printf '%s://%s' "$APIM_APPROVED_BACKEND_SCHEME" "$RESOLVED_APPROVED_BACKEND_HOST"
    return
  fi

  printf '%s://%s/%s' "$APIM_APPROVED_BACKEND_SCHEME" "$RESOLVED_APPROVED_BACKEND_HOST" "$svc"
}

get_service_name() {
  svc="$1"
  resolved_name="$svc"

  if command -v kubectl >/dev/null 2>&1; then
    resolved_name="$(kubectl get svc -n "$NAMESPACE" -l "app=$svc" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)"
    [ -n "$resolved_name" ] && printf '%s' "$resolved_name" && return
  fi

  if [ -n "$AKS_CLUSTER_NAME" ] && [ -n "$RESOURCE_GROUP" ]; then
    aks_logs="$(az aks command invoke \
      --resource-group "$RESOURCE_GROUP" \
      --name "$AKS_CLUSTER_NAME" \
      --command "kubectl get svc -n $NAMESPACE -l app=$svc -o jsonpath='{.items[0].metadata.name}'" \
      --query logs -o tsv 2>/dev/null || true)"
    resolved_name="$(printf '%s' "$aks_logs" | awk 'NF{line=$0} END{print line}')"
    [ -n "$resolved_name" ] && printf '%s' "$resolved_name" && return
  fi

  printf '%s' "$svc"
}

get_service_cluster_ip() {
  svc="$1"
  resolved_name="$(get_service_name "$svc")"
  cluster_ip=""

  if command -v kubectl >/dev/null 2>&1; then
    cluster_ip="$(kubectl get svc "$resolved_name" -n "$NAMESPACE" -o jsonpath='{.spec.clusterIP}' 2>/dev/null || true)"
    [ -n "$cluster_ip" ] && printf '%s' "$cluster_ip" && return
  fi

  if [ -n "$AKS_CLUSTER_NAME" ] && [ -n "$RESOURCE_GROUP" ]; then
    aks_logs="$(az aks command invoke \
      --resource-group "$RESOURCE_GROUP" \
      --name "$AKS_CLUSTER_NAME" \
      --command "kubectl get svc $resolved_name -n $NAMESPACE -o jsonpath='{.spec.clusterIP}'" \
      --query logs -o tsv 2>/dev/null || true)"
    cluster_ip="$(printf '%s' "$aks_logs" | awk 'NF{line=$0} END{print line}')"
    [ -n "$cluster_ip" ] && printf '%s' "$cluster_ip" && return
  fi
}

get_service_endpoint_ips() {
  svc="$1"
  ns="$2"
  endpoint_ips=""

  if command -v kubectl >/dev/null 2>&1; then
    endpoint_ips="$(kubectl get endpoints "$svc" -n "$ns" -o jsonpath='{.subsets[*].addresses[*].ip}' 2>/dev/null || true)"
  fi

  if [ -z "$endpoint_ips" ] && [ -n "$AKS_CLUSTER_NAME" ] && [ -n "$RESOURCE_GROUP" ]; then
    aks_logs="$(az aks command invoke \
      --resource-group "$RESOURCE_GROUP" \
      --name "$AKS_CLUSTER_NAME" \
      --command "kubectl get endpoints $svc -n $ns -o jsonpath='{.subsets[*].addresses[*].ip}'" \
      --query logs -o tsv 2>/dev/null || true)"

    endpoint_ips="$(printf '%s' "$aks_logs" | awk 'NF{line=$0} END{print line}')"
  fi

  printf '%s' "$endpoint_ips"
}

get_url_host() {
  url="$1"

  python3 - "$url" <<'PY'
import sys
from urllib.parse import urlparse

value = sys.argv[1]
parsed = urlparse(value)
print(parsed.hostname or "")
PY
}

is_ip_literal() {
  python - "$1" <<'PY'
import ipaddress
import sys

value = sys.argv[1]
try:
    ipaddress.ip_address(value)
except ValueError:
    print("false")
else:
    print("true")
PY
}

get_node_ips() {
  node_ips=""

  if command -v kubectl >/dev/null 2>&1; then
    node_ips="$(kubectl get nodes -o jsonpath='{.items[*].status.addresses[?(@.type=="InternalIP")].address} {.items[*].status.addresses[?(@.type=="ExternalIP")].address}' 2>/dev/null || true)"
  fi

  if [ -z "$node_ips" ] && [ -n "$AKS_CLUSTER_NAME" ] && [ -n "$RESOURCE_GROUP" ]; then
    aks_logs="$(az aks command invoke \
      --resource-group "$RESOURCE_GROUP" \
      --name "$AKS_CLUSTER_NAME" \
      --command "kubectl get nodes -o jsonpath='{.items[*].status.addresses[?(@.type==\"InternalIP\")].address} {.items[*].status.addresses[?(@.type==\"ExternalIP\")].address}'" \
      --query logs -o tsv 2>/dev/null || true)"
    node_ips="$(printf '%s' "$aks_logs" | awk 'NF{line=$0} END{print line}')"
  fi

  printf '%s' "$node_ips"
}

assert_approved_backend_target() {
  backend_url="$1"
  service_name="$2"
  backend_host="$(get_url_host "$backend_url")"

  if [ -z "$backend_host" ]; then
    echo "Unable to parse host from APIM backend URL '$backend_url'." >&2
    return 1
  fi

  if ! split_hostname_list "$APIM_APPROVED_BACKEND_HOSTNAMES" | grep -Fxq "$backend_host"; then
    allowed_hosts="$(split_hostname_list "$APIM_APPROVED_BACKEND_HOSTNAMES" | paste -sd ',' -)"
    echo "Refusing to set APIM backend '$backend_url': host '$backend_host' is not in the approved AGC hostname list: $allowed_hosts" >&2
    return 1
  fi

  if [ "$(is_ip_literal "$backend_host")" = "true" ]; then
    echo "Refusing to set APIM backend '$backend_url': approved target '$backend_host' is an IP literal. APIM backends must target AGC hostnames only." >&2
    return 1
  fi

  case "$backend_host" in
    *.svc.cluster.local|*.svc)
      echo "Refusing to set APIM backend '$backend_url': host '$backend_host' is cluster-local." >&2
      return 1
      ;;
  esac

  cluster_ip="$(get_service_cluster_ip "$service_name")"
  if [ -n "$cluster_ip" ] && [ "$backend_host" = "$cluster_ip" ]; then
    echo "Refusing to set APIM backend '$backend_url': host '$backend_host' matches the '$service_name' ClusterIP." >&2
    return 1
  fi

  endpoint_ips="$(get_service_endpoint_ips "$service_name" "$NAMESPACE")"
  if [ -n "$endpoint_ips" ] && printf '%s\n' "$endpoint_ips" | tr ' ' '\n' | sed '/^[[:space:]]*$/d' | grep -Fxq "$backend_host"; then
    endpoint_list="$(printf '%s\n' "$endpoint_ips" | tr ' ' '\n' | sed '/^[[:space:]]*$/d' | paste -sd ',' -)"
    echo "Refusing to set APIM backend '$backend_url': host '$backend_host' matches current '$service_name' endpoint IP(s): $endpoint_list" >&2
    return 1
  fi

  node_ips="$(get_node_ips)"
  if [ -n "$node_ips" ] && printf '%s\n' "$node_ips" | tr ' ' '\n' | sed '/^[[:space:]]*$/d' | grep -Fxq "$backend_host"; then
    node_list="$(printf '%s\n' "$node_ips" | tr ' ' '\n' | sed '/^[[:space:]]*$/d' | paste -sd ',' -)"
    echo "Refusing to set APIM backend '$backend_url': host '$backend_host' matches AKS node IP(s): $node_list" >&2
    return 1
  fi

  echo "Validated approved APIM backend host '$backend_host' for service '$service_name'."
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
  assert_approved_backend_target "$BACKEND_URL" crud-service

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

  CORS_ORIGINS_XML="$(python - "$APIM_CORS_ALLOWED_ORIGINS" <<'PY'
import html
import sys

raw = sys.argv[1]
origins = [origin.strip() for origin in raw.split(',') if origin.strip()]
if not origins:
    origins = ["http://localhost:3000"]

print("".join(f"<origin>{html.escape(origin, quote=True)}</origin>" for origin in origins))
PY
)"

  POLICY_XML_FILE="$(mktemp)"
  cat > "$POLICY_XML_FILE" <<EOF
<policies>
  <inbound>
    <base />
    <cors allow-credentials="false">
      <allowed-origins>$CORS_ORIGINS_XML</allowed-origins>
      <allowed-methods preflight-result-max-age="300"><method>*</method></allowed-methods>
      <allowed-headers><header>*</header></allowed-headers>
      <expose-headers><header>*</header></expose-headers>
    </cors>
    <choose>
      <when condition="@(context.Request.OriginalUrl.Path.Equals(&quot;/api/health&quot;, System.StringComparison.OrdinalIgnoreCase))">
        <rewrite-uri template="/health" copy-unmatched-params="true" />
      </when>
      <when condition="@(context.Request.OriginalUrl.Path.Equals(&quot;/api&quot;, System.StringComparison.OrdinalIgnoreCase) || context.Request.OriginalUrl.Path.StartsWith(&quot;/api/&quot;, System.StringComparison.OrdinalIgnoreCase))">
        <set-variable name="crudBackendPath" value="@(context.Request.OriginalUrl.Path.Length > 4 ? context.Request.OriginalUrl.Path.Substring(4) : string.Empty)" />
        <rewrite-uri template="@(string.Concat(&quot;/api&quot;, (string)context.Variables[&quot;crudBackendPath&quot;]))" copy-unmatched-params="true" />
      </when>
      <otherwise>
        <return-response>
          <set-status code="400" reason="Bad Request" />
          <set-header name="Content-Type" exists-action="override"><value>application/json</value></set-header>
          <set-body>{"detail":"Invalid CRUD API path."}</set-body>
        </return-response>
      </otherwise>
    </choose>
  </inbound>
  <backend>
    <base />
    <forward-request timeout="60" />
  </backend>
  <outbound>
    <base />
    <set-header name="Access-Control-Allow-Origin" exists-action="override"><value>@(context.Request.Headers.GetValueOrDefault(&quot;Origin&quot;, &quot;http://localhost:3000&quot;))</value></set-header>
    <set-header name="Access-Control-Allow-Methods" exists-action="override"><value>GET,POST,PUT,PATCH,DELETE,OPTIONS</value></set-header>
    <set-header name="Access-Control-Allow-Headers" exists-action="override"><value>*</value></set-header>
  </outbound>
  <on-error>
    <base />
    <return-response>
      <set-status code="502" reason="Bad Gateway" />
      <set-header name="Access-Control-Allow-Origin" exists-action="override"><value>@(context.Request.Headers.GetValueOrDefault(&quot;Origin&quot;, &quot;http://localhost:3000&quot;))</value></set-header>
      <set-header name="Access-Control-Allow-Methods" exists-action="override"><value>GET,POST,PUT,PATCH,DELETE,OPTIONS</value></set-header>
      <set-header name="Access-Control-Allow-Headers" exists-action="override"><value>*</value></set-header>
      <set-header name="Content-Type" exists-action="override"><value>application/json</value></set-header>
      <set-body>{"detail":"APIM upstream error while routing to CRUD backend."}</set-body>
    </return-response>
  </on-error>
</policies>
EOF

  POLICY_FILE="$(mktemp)"
  python - "$POLICY_XML_FILE" "$POLICY_FILE" <<'PY'
import json
import sys

xml_path = sys.argv[1]
json_path = sys.argv[2]

with open(xml_path, encoding="utf-8") as f:
    xml = f.read()

payload = {
    "properties": {
        "format": "rawxml",
        "value": xml,
    }
}

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(payload, f)
PY

  POLICY_URL="https://management.azure.com/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.ApiManagement/service/$APIM_NAME/apis/$API_ID/policies/policy?api-version=2022-08-01"
  az rest --method put --url "$POLICY_URL" --headers "Content-Type=application/json" --body "@$POLICY_FILE" --only-show-errors >/dev/null
  rm -f "$POLICY_XML_FILE"
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
  assert_approved_backend_target "$BACKEND_URL" "$SERVICE"

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

  for OP_ID in health ready invoke mcp-tool agent-traces agent-metrics agent-evaluation-latest; do
    az apim api operation delete \
      --resource-group "$RESOURCE_GROUP" \
      --service-name "$APIM_NAME" \
      --api-id "$API_ID" \
      --operation-id "$OP_ID" \
      --if-match '*' \
      >/dev/null 2>&1 || true
  done

  az apim api operation create --resource-group "$RESOURCE_GROUP" --service-name "$APIM_NAME" --api-id "$API_ID" --operation-id health --display-name "Health" --method GET --url-template "/health" >/dev/null
  az apim api operation create --resource-group "$RESOURCE_GROUP" --service-name "$APIM_NAME" --api-id "$API_ID" --operation-id ready --display-name "Ready" --method GET --url-template "/ready" >/dev/null
  az apim api operation create --resource-group "$RESOURCE_GROUP" --service-name "$APIM_NAME" --api-id "$API_ID" --operation-id invoke --display-name "Invoke" --method POST --url-template "/invoke" >/dev/null
  az apim api operation create --resource-group "$RESOURCE_GROUP" --service-name "$APIM_NAME" --api-id "$API_ID" --operation-id mcp-tool --display-name "MCP Tool" --method POST --url-template "/mcp/{tool}" --template-parameters name=tool description="MCP tool name" type=string required=true >/dev/null
  az apim api operation create --resource-group "$RESOURCE_GROUP" --service-name "$APIM_NAME" --api-id "$API_ID" --operation-id agent-traces --display-name "Agent Traces" --method GET --url-template "/agent/traces" >/dev/null
  az apim api operation create --resource-group "$RESOURCE_GROUP" --service-name "$APIM_NAME" --api-id "$API_ID" --operation-id agent-metrics --display-name "Agent Metrics" --method GET --url-template "/agent/metrics" >/dev/null
  az apim api operation create --resource-group "$RESOURCE_GROUP" --service-name "$APIM_NAME" --api-id "$API_ID" --operation-id agent-evaluation-latest --display-name "Agent Evaluation Latest" --method GET --url-template "/agent/evaluation/latest" >/dev/null
done

echo "APIM agent sync completed."
