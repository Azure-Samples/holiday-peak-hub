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
APP_GW_NAME="${APP_GW_NAME:-}"
APP_GW_IP="${APP_GW_IP:-}"
INGRESS_HOST="${INGRESS_HOST:-}"
USE_INGRESS="${USE_INGRESS:-false}"
REQUIRE_LOAD_BALANCER=true
BACKEND_RESOLVE_RETRIES="${BACKEND_RESOLVE_RETRIES:-24}"
BACKEND_RESOLVE_DELAY_SECONDS="${BACKEND_RESOLVE_DELAY_SECONDS:-5}"
PREVIEW=false
RESOLVED_INGRESS_HOST=""
INGRESS_VALIDATED=false

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
    --app-gw-ip)
      shift
      APP_GW_IP="$1"
      ;;
    --ingress-host)
      shift
      INGRESS_HOST="$1"
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

resolve_ingress_gateway_ip() {
  if [ -n "$RESOLVED_INGRESS_HOST" ]; then
    printf '%s' "$RESOLVED_INGRESS_HOST"
    return 0
  fi

  resolve_app_gw_public_host() {
    gateway_name="$1"
    pip_id=""
    host=""

    pip_id="$(az network application-gateway show \
      --resource-group "$RESOURCE_GROUP" \
      --name "$gateway_name" \
      --query 'frontendIPConfigurations[0].publicIPAddress.id' -o tsv 2>/dev/null || true)"

    if [ -n "$pip_id" ]; then
      host="$(az network public-ip show --ids "$pip_id" --query ipAddress -o tsv 2>/dev/null || true)"
      if [ -z "$host" ]; then
        host="$(az network public-ip show --ids "$pip_id" --query dnsSettings.fqdn -o tsv 2>/dev/null || true)"
      fi
      if [ -n "$host" ]; then
        printf '%s' "$host"
        return 0
      fi
    fi

    return 1
  }

  append_unique_candidate() {
    candidate="$1"
    candidate="$(printf '%s' "$candidate" | xargs)"
    [ -z "$candidate" ] && return 0

    if [ -z "$INGRESS_CANDIDATES" ]; then
      INGRESS_CANDIDATES="$candidate"
      return 0
    fi

    if ! printf '%s\n' "$INGRESS_CANDIDATES" | grep -Fxq "$candidate"; then
      INGRESS_CANDIDATES="$INGRESS_CANDIDATES
$candidate"
    fi
  }

  count_candidates() {
    if [ -z "$1" ]; then
      printf '0'
      return
    fi
    printf '%s\n' "$1" | sed '/^[[:space:]]*$/d' | wc -l | tr -d '[:space:]'
  }

  if [ -n "$INGRESS_HOST" ]; then
    RESOLVED_INGRESS_HOST="$INGRESS_HOST"
    printf '%s' "$RESOLVED_INGRESS_HOST"
    return 0
  fi

  if [ -n "$APP_GW_IP" ]; then
    RESOLVED_INGRESS_HOST="$APP_GW_IP"
    printf '%s' "$RESOLVED_INGRESS_HOST"
    return 0
  fi

  if [ -n "$APP_GW_NAME" ]; then
    RESOLVED_INGRESS_HOST="$(resolve_app_gw_public_host "$APP_GW_NAME" || true)"
    if [ -z "$RESOLVED_INGRESS_HOST" ]; then
      echo "Failed to resolve ingress host from explicit application gateway '$APP_GW_NAME'." >&2
      return 1
    fi
    printf '%s' "$RESOLVED_INGRESS_HOST"
    return 0
  fi

  INGRESS_CANDIDATES=""
  append_unique_candidate "$(kubectl get svc -A -l app.kubernetes.io/name=nginx -o jsonpath='{.items[0].status.loadBalancer.ingress[0].ip}' 2>/dev/null || true)"
  append_unique_candidate "$(kubectl get svc -A -l app.kubernetes.io/name=nginx -o jsonpath='{.items[0].status.loadBalancer.ingress[0].hostname}' 2>/dev/null || true)"
  append_unique_candidate "$(kubectl get svc nginx -n app-routing-system -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || true)"
  append_unique_candidate "$(kubectl get svc nginx -n app-routing-system -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || true)"
  append_unique_candidate "$(kubectl get svc ingress-nginx-controller -n ingress-nginx -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || true)"
  append_unique_candidate "$(kubectl get svc ingress-nginx-controller -n ingress-nginx -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || true)"

  INGRESS_CANDIDATE_COUNT="$(count_candidates "$INGRESS_CANDIDATES")"
  if [ "$INGRESS_CANDIDATE_COUNT" -gt 1 ]; then
    echo "Ambiguous ingress host candidates detected. Provide --app-gw-name, --app-gw-ip, or --ingress-host." >&2
    return 1
  fi

  if [ "$INGRESS_CANDIDATE_COUNT" -eq 1 ]; then
    RESOLVED_INGRESS_HOST="$(printf '%s\n' "$INGRESS_CANDIDATES" | sed '/^[[:space:]]*$/d' | head -n 1)"
    printf '%s' "$RESOLVED_INGRESS_HOST"
    return 0
  fi

  APP_GW_NAMES="$(az network application-gateway list --resource-group "$RESOURCE_GROUP" --query '[].name' -o tsv 2>/dev/null || true)"
  APP_GW_COUNT="$(count_candidates "$APP_GW_NAMES")"

  if [ "$APP_GW_COUNT" -gt 1 ]; then
    echo "Multiple application gateways detected in '$RESOURCE_GROUP'. Provide --app-gw-name, --app-gw-ip, or --ingress-host." >&2
    return 1
  fi

  if [ "$APP_GW_COUNT" -eq 1 ]; then
    AUTO_GW_NAME="$(printf '%s\n' "$APP_GW_NAMES" | sed '/^[[:space:]]*$/d' | head -n 1)"
    RESOLVED_INGRESS_HOST="$(resolve_app_gw_public_host "$AUTO_GW_NAME" || true)"
    if [ -n "$RESOLVED_INGRESS_HOST" ]; then
      printf '%s' "$RESOLVED_INGRESS_HOST"
      return 0
    fi
    echo "Failed to resolve ingress host from detected application gateway '$AUTO_GW_NAME'." >&2
    return 1
  fi

  return 1
}

validate_ingress_health() {
  host="$1"
  probe_url="http://$host/health"
  probe_body="/tmp/apim-ingress-health.json"
  status_code=""

  for attempt in $(seq 1 8); do
    status_code="$(curl -sS -o "$probe_body" -w '%{http_code}' --max-time 10 "$probe_url" || true)"
    if [ "$status_code" = "200" ] || [ "$status_code" = "404" ]; then
      echo "Validated ingress host '$host' via $probe_url"
      return 0
    fi
    sleep 5
  done

  echo "Ingress validation failed for '$host' (last status: ${status_code:-n/a}) using $probe_url" >&2
  cat "$probe_body" 2>/dev/null >&2 || true
  return 1
}

ensure_ingress_ready() {
  if [ "$INGRESS_VALIDATED" = true ]; then
    return 0
  fi

  RESOLVED_INGRESS_HOST="$(resolve_ingress_gateway_ip || true)"
  if [ -z "$RESOLVED_INGRESS_HOST" ]; then
    echo "Ingress endpoint could not be resolved for APIM backend sync. Refusing to fall back to cluster-local addresses that APIM cannot reach." >&2
    return 1
  fi

  if [ "$PREVIEW" = false ]; then
    validate_ingress_health "$RESOLVED_INGRESS_HOST"
  fi

  INGRESS_VALIDATED=true
  return 0
}

resolve_backend_url() {
  svc="$1"
  resolved_name=""
  resolved_port="80"
  lb_host=""
  attempt=1

  # If using Ingress (AGIC), resolve via App Gateway public IP
  if [ "$USE_INGRESS" = true ]; then
    ensure_ingress_ready
    # CRUD uses app-native ingress paths (/health, /api) at gateway root.
    if [ "$svc" = "crud-service" ]; then
      printf 'http://%s' "$RESOLVED_INGRESS_HOST"
    else
      printf 'http://%s/%s' "$RESOLVED_INGRESS_HOST" "$svc"
    fi
    return
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

assert_stable_crud_backend_target() {
  backend_url="$1"
  backend_host="$(get_url_host "$backend_url")"

  if [ -z "$backend_host" ]; then
    echo "Unable to parse host from CRUD APIM backend URL '$backend_url'." >&2
    return 1
  fi

  endpoint_ips="$(get_service_endpoint_ips crud-service "$NAMESPACE")"
  if [ -n "$endpoint_ips" ] && printf '%s\n' "$endpoint_ips" | tr ' ' '\n' | sed '/^[[:space:]]*$/d' | grep -Fxq "$backend_host"; then
    endpoint_list="$(printf '%s\n' "$endpoint_ips" | tr ' ' '\n' | sed '/^[[:space:]]*$/d' | paste -sd ',' -)"
    echo "Refusing to set unstable CRUD APIM backend '$backend_url': host '$backend_host' matches current crud-service endpoint IP(s): $endpoint_list" >&2
    return 1
  fi

  echo "Validated stable CRUD APIM backend host '$backend_host'."
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
  assert_stable_crud_backend_target "$BACKEND_URL"

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
