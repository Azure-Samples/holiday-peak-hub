#!/usr/bin/env sh
# Ensures all V2 Foundry agents are provisioned by calling each service's
# POST /foundry/agents/ensure endpoint.
#
# Usage:
#   ensure-foundry-agents.sh                              # in-cluster direct
#   ensure-foundry-agents.sh --port-forward               # via kubectl port-forward
#   ensure-foundry-agents.sh --base-url https://api/agents # via Ingress/APIM
set -eu

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
AZURE_YAML_PATH="${AZURE_YAML_PATH:-$REPO_ROOT/azure.yaml}"
NAMESPACE="${K8S_NAMESPACE:-holiday-peak}"
MAX_RETRIES="${MAX_RETRIES:-3}"
USE_PORT_FORWARD=false
BASE_URL=""
FAIL_ON_ERROR="${FAIL_ON_ERROR:-false}"
CHANGED_SERVICES="${CHANGED_SERVICES:-}"
VALIDATE_RENDERED_FOUNDRY_CONTRACT="${VALIDATE_RENDERED_FOUNDRY_CONTRACT:-false}"
VALIDATE_READY_AFTER_ENSURE="${VALIDATE_READY_AFTER_ENSURE:-false}"
EXPECTED_FOUNDRY_STRICT_ENFORCEMENT="${EXPECTED_FOUNDRY_STRICT_ENFORCEMENT:-${FOUNDRY_STRICT_ENFORCEMENT:-}}"
EXPECTED_FOUNDRY_AUTO_ENSURE_ON_STARTUP="${EXPECTED_FOUNDRY_AUTO_ENSURE_ON_STARTUP:-${FOUNDRY_AUTO_ENSURE_ON_STARTUP:-}}"
RENDERED_MANIFEST_ROOT="${RENDERED_MANIFEST_ROOT:-$REPO_ROOT/.kubernetes/rendered}"
CONTRACT_CHECKS_ENABLED=false

if [ "$VALIDATE_RENDERED_FOUNDRY_CONTRACT" = "true" ] || [ -n "$EXPECTED_FOUNDRY_STRICT_ENFORCEMENT" ] || [ -n "$EXPECTED_FOUNDRY_AUTO_ENSURE_ON_STARTUP" ]; then
  CONTRACT_CHECKS_ENABLED=true
fi

# ---- Parse arguments ----
while [ $# -gt 0 ]; do
  case "$1" in
    --port-forward) USE_PORT_FORWARD=true; shift ;;
    --base-url)     BASE_URL="$2"; shift 2 ;;
    --namespace)    NAMESPACE="$2"; shift 2 ;;
    --retries)      MAX_RETRIES="$2"; shift 2 ;;
    --fail-on-error) FAIL_ON_ERROR=true; shift ;;
    --non-blocking) FAIL_ON_ERROR=false; shift ;;
    *)              shift ;;
  esac
done

# ---- Discover agent services from azure.yaml ----
SERVICES="$(python3 - "$AZURE_YAML_PATH" << 'PY'
import re, sys
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
    m = re.match(r"^  ([a-z0-9\-]+):\s*$", line)
    if m:
        if current_service and current_host == "aks" and current_service != "crud-service":
            services.append(current_service)
        current_service = m.group(1)
        current_host = None
        continue
    h = re.match(r"^    host:\s*([^\s]+)\s*$", line)
    if h:
        current_host = h.group(1)
if current_service and current_host == "aks" and current_service != "crud-service":
    services.append(current_service)
print("\n".join(services))
PY
)"

if [ -z "$SERVICES" ]; then
  echo "No agent services found in azure.yaml."
  exit 0
fi

if [ -n "$CHANGED_SERVICES" ]; then
  FILTER_FILE="$(mktemp)"
  printf '%s' "$CHANGED_SERVICES" | tr ',' '\n' | sed '/^[[:space:]]*$/d' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' > "$FILTER_FILE"
  SERVICES="$(printf '%s\n' "$SERVICES" | while IFS= read -r SVC; do
    [ -z "$SVC" ] && continue
    if grep -Fxq "$SVC" "$FILTER_FILE"; then
      printf '%s\n' "$SVC"
    fi
  done)"
  rm -f "$FILTER_FILE"
fi

if [ -z "$SERVICES" ]; then
  echo "No matching changed agent services to ensure."
  exit 0
fi

SERVICE_COUNT="$(echo "$SERVICES" | wc -l | tr -d ' ')"
echo "Found $SERVICE_COUNT agent services to ensure."

FAILED=""
FAIL_COUNT=0

resolve_service_endpoint() {
  SVC_KEY="$1"
  RESOLVED_NAME="$(kubectl get svc -n "$NAMESPACE" -l "app=$SVC_KEY" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)"
  if [ -z "$RESOLVED_NAME" ]; then
    return 1
  fi

  RESOLVED_PORT="$(kubectl get svc "$RESOLVED_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.ports[0].port}' 2>/dev/null || true)"
  [ -z "$RESOLVED_PORT" ] && RESOLVED_PORT="80"

  echo "$RESOLVED_NAME|$RESOLVED_PORT"
  return 0
}

resolve_deployment_name() {
  SVC_KEY="$1"
  DEPLOYMENT_NAME="$(kubectl get deployment -n "$NAMESPACE" -l "app=$SVC_KEY" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)"
  if [ -z "$DEPLOYMENT_NAME" ]; then
    return 1
  fi

  echo "$DEPLOYMENT_NAME"
  return 0
}

get_live_env_from_deployment() {
  DEPLOYMENT_NAME="$1"
  ENV_NAME="$2"
  kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE" -o jsonpath="{.spec.template.spec.containers[0].env[?(@.name=='$ENV_NAME')].value}" 2>/dev/null || true
}

get_rendered_env_value() {
  MANIFEST_PATH="$1"
  ENV_NAME="$2"

  python3 - "$MANIFEST_PATH" "$ENV_NAME" <<'PY'
import re
import sys

manifest_path, env_name = sys.argv[1], sys.argv[2]

try:
    content = open(manifest_path, encoding="utf-8").read()
except OSError:
    sys.exit(0)

pattern = rf"-\s*name:\s*{re.escape(env_name)}\s*(?:\r?\n)+\s*value:\s*[\"']?([^\"'\r\n]+)[\"']?"
match = re.search(pattern, content)
if match:
    print(match.group(1).strip())
PY
}

normalize_contract_value() {
  printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
}

validate_service_contract() {
  SVC="$1"
  DEPLOYMENT_NAME="$2"
  MANIFEST_PATH="$RENDERED_MANIFEST_ROOT/$SVC/all.yaml"
  CONTRACT_FAILED=0

  for KEY in FOUNDRY_STRICT_ENFORCEMENT FOUNDRY_AUTO_ENSURE_ON_STARTUP; do
    case "$KEY" in
      FOUNDRY_STRICT_ENFORCEMENT)
        EXPECTED_RAW="$EXPECTED_FOUNDRY_STRICT_ENFORCEMENT"
        ;;
      FOUNDRY_AUTO_ENSURE_ON_STARTUP)
        EXPECTED_RAW="$EXPECTED_FOUNDRY_AUTO_ENSURE_ON_STARTUP"
        ;;
    esac

    EXPECTED_VALUE="$(normalize_contract_value "$EXPECTED_RAW")"
    LIVE_VALUE="$(normalize_contract_value "$(get_live_env_from_deployment "$DEPLOYMENT_NAME" "$KEY")")"
    RENDERED_VALUE=""

    if [ "$VALIDATE_RENDERED_FOUNDRY_CONTRACT" = "true" ]; then
      if [ ! -f "$MANIFEST_PATH" ]; then
        echo "  [$SVC] Rendered manifest missing for contract validation: $MANIFEST_PATH" >&2
        CONTRACT_FAILED=1
      else
        RENDERED_VALUE="$(normalize_contract_value "$(get_rendered_env_value "$MANIFEST_PATH" "$KEY")")"
      fi
    fi

    EXPECTED_DISPLAY="${EXPECTED_VALUE:-<unspecified>}"
    LIVE_DISPLAY="${LIVE_VALUE:-<missing>}"
    RENDERED_DISPLAY="<not-checked>"
    if [ "$VALIDATE_RENDERED_FOUNDRY_CONTRACT" = "true" ]; then
      RENDERED_DISPLAY="${RENDERED_VALUE:-<missing>}"
    fi

    echo "  [$SVC] Foundry contract $KEY => expected=$EXPECTED_DISPLAY rendered=$RENDERED_DISPLAY live=$LIVE_DISPLAY"

    if [ -n "$EXPECTED_VALUE" ] && [ "$LIVE_VALUE" != "$EXPECTED_VALUE" ]; then
      echo "  [$SVC] Live deployment drift for $KEY: expected '$EXPECTED_VALUE', got '${LIVE_VALUE:-<missing>}'" >&2
      CONTRACT_FAILED=1
    fi

    if [ "$VALIDATE_RENDERED_FOUNDRY_CONTRACT" = "true" ]; then
      if [ -z "$RENDERED_VALUE" ]; then
        echo "  [$SVC] Rendered manifest missing $KEY in $MANIFEST_PATH" >&2
        CONTRACT_FAILED=1
      fi

      if [ -n "$EXPECTED_VALUE" ] && [ "$RENDERED_VALUE" != "$EXPECTED_VALUE" ]; then
        echo "  [$SVC] Rendered manifest drift for $KEY: expected '$EXPECTED_VALUE', got '${RENDERED_VALUE:-<missing>}'" >&2
        CONTRACT_FAILED=1
      fi

      if [ -n "$RENDERED_VALUE" ] && [ -n "$LIVE_VALUE" ] && [ "$RENDERED_VALUE" != "$LIVE_VALUE" ]; then
        echo "  [$SVC] Rendered/live drift for $KEY: rendered '$RENDERED_VALUE', live '$LIVE_VALUE'" >&2
        CONTRACT_FAILED=1
      fi
    fi
  done

  if [ "$CONTRACT_FAILED" -ne 0 ]; then
    return 1
  fi

  return 0
}

call_ensure() {
  SVC="$1"
  URL="$2"
  RESPONSE_FILE="$3"
  attempt=1

  while [ "$attempt" -le "$MAX_RETRIES" ]; do
    echo "  [$SVC] Calling $URL (attempt $attempt/$MAX_RETRIES)..."
    HTTP_CODE="$(curl -s -o "$RESPONSE_FILE" -w "%{http_code}" \
      -X POST "$URL" \
      -H "Content-Type: application/json" \
      --connect-timeout 10 \
      --max-time 120 2>/dev/null || echo "000")"

    if [ "$HTTP_CODE" = "200" ]; then
      if python3 - "$SVC" "$RESPONSE_FILE" <<'PY'
import json
import sys

service = sys.argv[1]
response_path = sys.argv[2]

try:
    with open(response_path, encoding='utf-8') as handle:
        payload = json.load(handle)
except Exception as exc:  # pragma: no cover - shell integration guard
    print(f"  [{service}] Invalid ensure response payload: {exc}")
    sys.exit(1)

results = payload.get('results') or {}
required_roles = ('fast', 'rich')
valid_statuses = {'exists', 'found_by_name', 'created'}
missing = []

for role in required_roles:
    details = results.get(role)
    if not isinstance(details, dict):
        missing.append(f"{role}:missing")
        continue
    status = str(details.get('status') or '')
    agent_id = str(details.get('agent_id') or '')
    if status not in valid_statuses or not agent_id:
        missing.append(f"{role}:{status or 'unknown'}")

if missing:
    print(f"  [{service}] Ensure response incomplete: {', '.join(missing)}")
    sys.exit(1)

print(f"  [{service}] Ensure response validated: fast+rich roles resolved.")
PY
      then
        echo "  [$SVC] OK (HTTP $HTTP_CODE)"
        cat "$RESPONSE_FILE" 2>/dev/null || true
        echo ""
        return 0
      fi
    fi

    echo "  [$SVC] Attempt $attempt failed (HTTP $HTTP_CODE)"
    attempt=$((attempt + 1))
    [ "$attempt" -le "$MAX_RETRIES" ] && sleep $((5 * (attempt - 1)))
  done

  return 1
}

call_ready() {
  SVC="$1"
  URL="$2"
  RESPONSE_FILE="$3"

  READY_HTTP_CODE="$(curl -s -o "$RESPONSE_FILE" -w "%{http_code}" \
    --connect-timeout 10 \
    --max-time 60 "$URL" 2>/dev/null || echo "000")"

  echo "  [$SVC] /ready returned HTTP $READY_HTTP_CODE"
}

validate_ready_response() {
  SVC="$1"
  RESPONSE_FILE="$2"
  HTTP_CODE="$3"
  ENSURE_OK="$4"

  python3 - "$SVC" "$RESPONSE_FILE" "$HTTP_CODE" "$ENSURE_OK" "$EXPECTED_FOUNDRY_STRICT_ENFORCEMENT" "$EXPECTED_FOUNDRY_AUTO_ENSURE_ON_STARTUP" <<'PY'
import json
import sys

service, response_path, http_code, ensure_ok_raw, expected_strict_raw, expected_auto_raw = sys.argv[1:]

bool_like = {"1", "true", "yes"}
ensure_ok = ensure_ok_raw.lower() == "true"
expected_strict = expected_strict_raw.strip().lower() in bool_like
expected_auto = expected_auto_raw.strip().lower() in bool_like

if http_code != "200":
    if ensure_ok:
        print(
            f"  [{service}] Ready/ensure mismatch: ensure resolved Foundry roles but /ready returned HTTP {http_code}",
            file=sys.stderr,
        )
    else:
        print(f"  [{service}] /ready returned HTTP {http_code}", file=sys.stderr)
    sys.exit(1)

try:
    with open(response_path, encoding="utf-8") as handle:
        payload = json.load(handle)
except Exception as exc:
    print(f"  [{service}] Invalid /ready payload: {exc}", file=sys.stderr)
    sys.exit(1)

status = str(payload.get("status") or "")
foundry_ready = bool(payload.get("foundry_ready"))
foundry_required = bool(payload.get("foundry_required"))
issues = []

if status != "ready":
    issues.append(f"status={status or 'missing'}")
if ensure_ok and not foundry_ready:
    issues.append("foundry_ready=false after successful ensure")
if ensure_ok and expected_strict and not foundry_required:
    issues.append("foundry_required=false despite strict contract")
if (expected_strict or expected_auto) and not foundry_ready:
    issues.append("foundry_ready=false despite strict/auto contract")
if not ensure_ok:
    issues.append("/ready returned HTTP 200 even though ensure failed")

if issues:
    print(f"  [{service}] Ready/ensure mismatch: {', '.join(dict.fromkeys(issues))}", file=sys.stderr)
    print(json.dumps(payload, sort_keys=True), file=sys.stderr)
    sys.exit(1)

print(
    f"  [{service}] /ready validated: foundry_required={foundry_required} foundry_ready={foundry_ready}"
)
PY
}

while IFS= read -r SVC; do
  [ -z "$SVC" ] && continue
  SERVICE_FAILED=0

  RESOLVED="$(resolve_service_endpoint "$SVC" || true)"
  if [ -z "$RESOLVED" ]; then
    echo "  [$SVC] Service resolution failed (label app=$SVC not found in namespace $NAMESPACE)"
    FAILED="$FAILED $SVC"
    FAIL_COUNT=$((FAIL_COUNT + 1))
    continue
  fi

  RESOLVED_NAME="${RESOLVED%%|*}"
  RESOLVED_PORT="${RESOLVED##*|}"

  if [ "$CONTRACT_CHECKS_ENABLED" = "true" ]; then
    DEPLOYMENT_NAME="$(resolve_deployment_name "$SVC" || true)"
    if [ -z "$DEPLOYMENT_NAME" ]; then
      echo "  [$SVC] Deployment resolution failed (label app=$SVC not found in namespace $NAMESPACE)" >&2
      SERVICE_FAILED=1
    elif ! validate_service_contract "$SVC" "$DEPLOYMENT_NAME"; then
      SERVICE_FAILED=1
    fi
  fi

  ENSURE_RESPONSE_FILE="$(mktemp)"
  READY_RESPONSE_FILE="$(mktemp)"
  PORT_FORWARD_LOG="$(mktemp)"
  PF_PID=""

  if [ -n "$BASE_URL" ]; then
    ENSURE_URL="$BASE_URL/$SVC/foundry/agents/ensure"
    READY_URL="$BASE_URL/$SVC/ready"
  elif [ "$USE_PORT_FORWARD" = "true" ]; then
    LOCAL_PORT="$(python3 -c 'import socket; s=socket.socket(); s.bind(("",0)); print(s.getsockname()[1]); s.close()')"
    kubectl port-forward "svc/$RESOLVED_NAME" "$LOCAL_PORT:$RESOLVED_PORT" -n "$NAMESPACE" >"$PORT_FORWARD_LOG" 2>&1 &
    PF_PID=$!
    sleep 3
    ENSURE_URL="http://localhost:$LOCAL_PORT/foundry/agents/ensure"
    READY_URL="http://localhost:$LOCAL_PORT/ready"
  else
    ENSURE_URL="http://$RESOLVED_NAME.$NAMESPACE.svc.cluster.local:$RESOLVED_PORT/foundry/agents/ensure"
    READY_URL="http://$RESOLVED_NAME.$NAMESPACE.svc.cluster.local:$RESOLVED_PORT/ready"
  fi

  ENSURE_OK=false
  if call_ensure "$SVC" "$ENSURE_URL" "$ENSURE_RESPONSE_FILE"; then
    ENSURE_OK=true
  else
    SERVICE_FAILED=1
  fi

  if [ "$VALIDATE_READY_AFTER_ENSURE" = "true" ]; then
    call_ready "$SVC" "$READY_URL" "$READY_RESPONSE_FILE"
    if ! validate_ready_response "$SVC" "$READY_RESPONSE_FILE" "$READY_HTTP_CODE" "$ENSURE_OK"; then
      SERVICE_FAILED=1
    fi
  fi

  if [ -n "$PF_PID" ]; then
    kill "$PF_PID" 2>/dev/null || true
  fi

  if [ "$SERVICE_FAILED" -ne 0 ] && [ -s "$PORT_FORWARD_LOG" ]; then
    echo "  [$SVC] Port-forward log:"
    cat "$PORT_FORWARD_LOG" 2>/dev/null || true
  fi

  rm -f "$ENSURE_RESPONSE_FILE" "$READY_RESPONSE_FILE" "$PORT_FORWARD_LOG"

  if [ "$SERVICE_FAILED" -ne 0 ]; then
    FAILED="$FAILED $SVC"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  else
    echo "  [$SVC] Foundry runtime contract validated."
  fi
done <<EOF
$SERVICES
EOF

echo ""
echo "=== Ensure Summary ==="
echo "Total services: $SERVICE_COUNT"

if [ -n "$FAILED" ]; then
  echo "Failed:$FAILED"
  if [ "$FAIL_ON_ERROR" = "true" ]; then
    exit 1
  fi
  echo "WARNING: Foundry ensure completed with failures, but FAIL_ON_ERROR=false so deployment can continue."
  exit 0
fi

echo "All agents provisioned successfully."
