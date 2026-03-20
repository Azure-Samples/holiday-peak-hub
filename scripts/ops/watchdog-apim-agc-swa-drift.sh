#!/usr/bin/env bash

set -euo pipefail

PROJECT_NAME="${PROJECT_NAME:-holidaypeakhub405}"
ENVIRONMENT="${ENVIRONMENT:-dev}"
RESOURCE_GROUP="${RESOURCE_GROUP:-${PROJECT_NAME}-${ENVIRONMENT}-rg}"
APIM_NAME="${APIM_NAME:-${PROJECT_NAME}-${ENVIRONMENT}-apim}"
AKS_NAME="${AKS_NAME:-${PROJECT_NAME}-${ENVIRONMENT}-aks}"
SWA_NAME="${SWA_NAME:-${PROJECT_NAME}-ui-${ENVIRONMENT}}"
APIM_GATEWAY_URL_INPUT="${APIM_GATEWAY_URL:-}"
AGC_FRONTEND_HOSTNAME_INPUT="${AGC_FRONTEND_HOSTNAME:-}"
AGC_SUPPORT_ENABLED_INPUT="${AGC_SUPPORT_ENABLED:-}"
REPORT_DIR="${REPORT_DIR:-$PWD/.tmp/watchdog-drift}"

mkdir -p "$REPORT_DIR"

RESULTS_TSV="$REPORT_DIR/checks.tsv"
RESULTS_JSON="$REPORT_DIR/watchdog-results.json"
SUMMARY_MD="$REPORT_DIR/watchdog-summary.md"

: > "$RESULTS_TSV"

record_result() {
  local name="$1"
  local status="$2"
  local detail="$3"
  printf '%s\t%s\t%s\n' "$name" "$status" "$detail" >> "$RESULTS_TSV"
}

normalize_url() {
  local value="$1"
  value="$(echo "$value" | xargs)"
  value="${value%/}"
  echo "$value"
}

resolve_apim_gateway_url() {
  local resolved="$APIM_GATEWAY_URL_INPUT"
  if [ -z "$resolved" ]; then
    resolved="$(az apim show \
      --name "$APIM_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --query gatewayUrl -o tsv 2>/dev/null || true)"
  fi
  normalize_url "$resolved"
}

resolve_agc_support_enabled() {
  local resolved="$AGC_SUPPORT_ENABLED_INPUT"
  if [ -z "$resolved" ] && command -v azd >/dev/null 2>&1; then
    resolved="$(azd env get-value AGC_SUPPORT_ENABLED -e "$ENVIRONMENT" 2>/dev/null || true)"
  fi
  echo "$(echo "$resolved" | xargs)"
}

resolve_agc_frontend_hostname() {
  local resolved="$AGC_FRONTEND_HOSTNAME_INPUT"
  if [ -z "$resolved" ] && command -v azd >/dev/null 2>&1; then
    resolved="$(azd env get-value AGC_FRONTEND_HOSTNAME -e "$ENVIRONMENT" 2>/dev/null || true)"
  fi
  echo "$(echo "$resolved" | xargs)"
}

resolve_aks_web_routing_enabled() {
  local value

  value="$(az aks show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$AKS_NAME" \
    --query "ingressProfile.webAppRouting.enabled" -o tsv 2>/dev/null || true)"
  value="$(echo "$value" | xargs)"
  if [ -n "$value" ] && [ "$value" != "null" ]; then
    echo "$value"
    return
  fi

  value="$(az aks show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$AKS_NAME" \
    --query "webApplicationRouting.enabled" -o tsv 2>/dev/null || true)"
  value="$(echo "$value" | xargs)"
  if [ -n "$value" ] && [ "$value" != "null" ]; then
    echo "$value"
    return
  fi

  value="$(az aks show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$AKS_NAME" \
    --query "addonProfiles.web_application_routing.enabled" -o tsv 2>/dev/null || true)"
  value="$(echo "$value" | xargs)"
  if [ -n "$value" ] && [ "$value" != "null" ]; then
    echo "$value"
    return
  fi

  echo "unknown"
}

resolve_crud_api_id() {
  if az apim api show --resource-group "$RESOURCE_GROUP" --service-name "$APIM_NAME" --api-id "crud-service" --only-show-errors >/dev/null 2>&1; then
    echo "crud-service"
    return
  fi
  if az apim api show --resource-group "$RESOURCE_GROUP" --service-name "$APIM_NAME" --api-id "crud" --only-show-errors >/dev/null 2>&1; then
    echo "crud"
    return
  fi
  echo ""
}

extract_hostname() {
  local url="$1"
  python3 -c "from urllib.parse import urlparse; import sys; print(urlparse(sys.argv[1]).hostname or '')" "$url"
}

http_check_with_retry() {
  local check_name="$1"
  local url="$2"
  local attempts="${3:-12}"
  local wait_seconds="${4:-5}"

  if [ -z "$url" ]; then
    record_result "$check_name" "FAIL" "URL was empty"
    return
  fi

  for attempt in $(seq 1 "$attempts"); do
    local status
    if ! status=$(curl -sS -o /tmp/watchdog-http-body.txt -w "%{http_code}" "$url"); then
      status="000"
    fi

    if [ "$status" = "200" ]; then
      record_result "$check_name" "PASS" "HTTP 200 at $url"
      return
    fi

    if [ "$attempt" -lt "$attempts" ]; then
      sleep "$wait_seconds"
    fi
  done

  record_result "$check_name" "FAIL" "Did not return HTTP 200 at $url"
}

AGC_SUPPORT_ENABLED_VALUE="$(resolve_agc_support_enabled)"
if [ "$ENVIRONMENT" = "dev" ]; then
  if [ "$AGC_SUPPORT_ENABLED_VALUE" = "true" ]; then
    record_result "agc_support_enabled" "PASS" "AGC_SUPPORT_ENABLED=true"
  else
    record_result "agc_support_enabled" "FAIL" "Expected AGC_SUPPORT_ENABLED=true for dev; got '${AGC_SUPPORT_ENABLED_VALUE:-<empty>}'"
  fi
else
  record_result "agc_support_enabled" "PASS" "Environment '$ENVIRONMENT' is not dev; AGC_SUPPORT_ENABLED check skipped"
fi

AKS_WEB_ROUTING_ENABLED="$(resolve_aks_web_routing_enabled)"
if [ "$AKS_WEB_ROUTING_ENABLED" = "false" ]; then
  record_result "legacy_web_application_routing_disabled" "PASS" "AKS web application routing is disabled"
elif [ "$AKS_WEB_ROUTING_ENABLED" = "unknown" ]; then
  record_result "legacy_web_application_routing_disabled" "FAIL" "Could not resolve AKS web routing status for $AKS_NAME"
else
  record_result "legacy_web_application_routing_disabled" "FAIL" "Expected disabled web routing; got '$AKS_WEB_ROUTING_ENABLED'"
fi

AGC_FRONTEND_HOSTNAME_VALUE="$(resolve_agc_frontend_hostname)"
CRUD_API_ID="$(resolve_crud_api_id)"
if [ -z "$CRUD_API_ID" ]; then
  record_result "apim_backend_hostname_matches_agc_frontend" "FAIL" "Could not find APIM API id 'crud-service' or 'crud'"
else
  CRUD_SERVICE_URL="$(az apim api show --resource-group "$RESOURCE_GROUP" --service-name "$APIM_NAME" --api-id "$CRUD_API_ID" --query serviceUrl -o tsv --only-show-errors 2>/dev/null || true)"
  CRUD_SERVICE_URL="$(echo "$CRUD_SERVICE_URL" | xargs)"
  CRUD_SERVICE_HOST=""
  if [ -n "$CRUD_SERVICE_URL" ]; then
    CRUD_SERVICE_HOST="$(extract_hostname "$CRUD_SERVICE_URL")"
  fi

  if [ -z "$AGC_FRONTEND_HOSTNAME_VALUE" ]; then
    record_result "apim_backend_hostname_matches_agc_frontend" "FAIL" "AGC_FRONTEND_HOSTNAME is empty"
  elif [ -z "$CRUD_SERVICE_HOST" ]; then
    record_result "apim_backend_hostname_matches_agc_frontend" "FAIL" "Could not parse APIM CRUD backend host from '$CRUD_SERVICE_URL'"
  elif [ "$CRUD_SERVICE_HOST" = "$AGC_FRONTEND_HOSTNAME_VALUE" ]; then
    record_result "apim_backend_hostname_matches_agc_frontend" "PASS" "APIM CRUD backend host matches AGC frontend host '$AGC_FRONTEND_HOSTNAME_VALUE'"
  else
    record_result "apim_backend_hostname_matches_agc_frontend" "FAIL" "APIM CRUD backend host '$CRUD_SERVICE_HOST' does not match AGC frontend '$AGC_FRONTEND_HOSTNAME_VALUE'"
  fi
fi

APIM_GATEWAY_URL_VALUE="$(resolve_apim_gateway_url)"
SWA_SETTINGS_JSON="$(az staticwebapp appsettings list --name "$SWA_NAME" --resource-group "$RESOURCE_GROUP" --query properties -o json 2>/dev/null || echo '{}')"

mapfile -t SWA_URLS < <(python3 -c "import json,sys
settings=json.loads(sys.argv[1])
def normalize(v):
    if not isinstance(v, str):
        return ''
    v=v.strip().rstrip('/')
    return v
api=normalize(settings.get('NEXT_PUBLIC_API_URL',''))
crud=normalize(settings.get('NEXT_PUBLIC_CRUD_API_URL',''))
print(api)
print(crud)
" "$SWA_SETTINGS_JSON")

SWA_NEXT_PUBLIC_API_URL="${SWA_URLS[0]:-}"
SWA_NEXT_PUBLIC_CRUD_API_URL="${SWA_URLS[1]:-}"

if [ -z "$SWA_NEXT_PUBLIC_API_URL" ] || [ -z "$SWA_NEXT_PUBLIC_CRUD_API_URL" ]; then
  record_result "swa_next_public_urls_aligned" "FAIL" "Missing NEXT_PUBLIC_API_URL or NEXT_PUBLIC_CRUD_API_URL in SWA app settings"
elif [ "$SWA_NEXT_PUBLIC_API_URL" != "$SWA_NEXT_PUBLIC_CRUD_API_URL" ]; then
  record_result "swa_next_public_urls_aligned" "FAIL" "SWA NEXT_PUBLIC URL mismatch: API='$SWA_NEXT_PUBLIC_API_URL' CRUD='$SWA_NEXT_PUBLIC_CRUD_API_URL'"
elif [ -n "$APIM_GATEWAY_URL_VALUE" ] && [ "$SWA_NEXT_PUBLIC_API_URL" != "$APIM_GATEWAY_URL_VALUE" ]; then
  record_result "swa_next_public_urls_aligned" "FAIL" "SWA NEXT_PUBLIC URLs ('$SWA_NEXT_PUBLIC_API_URL') drift from APIM gateway ('$APIM_GATEWAY_URL_VALUE')"
else
  record_result "swa_next_public_urls_aligned" "PASS" "SWA NEXT_PUBLIC_API_URL and NEXT_PUBLIC_CRUD_API_URL are aligned"
fi

http_check_with_retry "smoke_apim_api_ready" "${APIM_GATEWAY_URL_VALUE%/}/api/ready"
http_check_with_retry "smoke_apim_api_health" "${APIM_GATEWAY_URL_VALUE%/}/api/health"

python3 - "$RESULTS_TSV" "$RESULTS_JSON" "$SUMMARY_MD" "$ENVIRONMENT" <<'PY'
import json
import pathlib
import sys
from datetime import datetime, timezone

tsv_path = pathlib.Path(sys.argv[1])
json_path = pathlib.Path(sys.argv[2])
md_path = pathlib.Path(sys.argv[3])
env_name = sys.argv[4]

rows = []
for line in tsv_path.read_text(encoding="utf-8").splitlines():
  if not line.strip():
    continue
  parts = line.split("\t", 2)
  if len(parts) != 3:
    continue
  check, status, detail = parts
  rows.append({"check": check, "status": status, "detail": detail})

failed = [row for row in rows if row["status"] != "PASS"]
summary = {
  "environment": env_name,
  "generated_at_utc": datetime.now(timezone.utc).isoformat(),
  "drift_detected": len(failed) > 0,
  "failed_checks": [row["check"] for row in failed],
  "checks": rows,
}
json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

lines = [
  f"# Drift watchdog summary ({env_name})",
  "",
  f"Drift detected: {'YES' if summary['drift_detected'] else 'NO'}",
  "",
  "| Check | Status | Detail |",
  "|---|---|---|",
]
for row in rows:
  status_icon = "✅" if row["status"] == "PASS" else "❌"
  detail = (row["detail"] or "").replace("|", "\\|")
  lines.append(f"| {row['check']} | {status_icon} {row['status']} | {detail} |")

md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

if [ -n "${GITHUB_OUTPUT:-}" ]; then
  DRIFT_DETECTED="$(python3 -c "import json,sys; print('true' if json.load(open(sys.argv[1], encoding='utf-8')).get('drift_detected') else 'false')" "$RESULTS_JSON")"
  FAILED_CHECKS="$(python3 -c "import json,sys; print(','.join(json.load(open(sys.argv[1], encoding='utf-8')).get('failed_checks', [])))" "$RESULTS_JSON")"
  echo "drift_detected=$DRIFT_DETECTED" >> "$GITHUB_OUTPUT"
  echo "failed_checks=$FAILED_CHECKS" >> "$GITHUB_OUTPUT"
  echo "summary_file=$SUMMARY_MD" >> "$GITHUB_OUTPUT"
  echo "results_file=$RESULTS_JSON" >> "$GITHUB_OUTPUT"
fi

echo "Watchdog report written to $REPORT_DIR"