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

call_ensure() {
  SVC="$1"
  URL="$2"
  attempt=1

  while [ "$attempt" -le "$MAX_RETRIES" ]; do
    echo "  [$SVC] Calling $URL (attempt $attempt/$MAX_RETRIES)..."
    HTTP_CODE="$(curl -s -o /tmp/ensure_response.json -w "%{http_code}" \
      -X POST "$URL" \
      -H "Content-Type: application/json" \
      --connect-timeout 10 \
      --max-time 120 2>/dev/null || echo "000")"

    if [ "$HTTP_CODE" = "200" ]; then
      if python3 - "$SVC" <<'PY'
import json
import sys

service = sys.argv[1]

try:
    with open('/tmp/ensure_response.json', encoding='utf-8') as handle:
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
        cat /tmp/ensure_response.json 2>/dev/null || true
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

while IFS= read -r SVC; do
  [ -z "$SVC" ] && continue

  RESOLVED="$(resolve_service_endpoint "$SVC" || true)"
  if [ -z "$RESOLVED" ]; then
    echo "  [$SVC] Service resolution failed (label app=$SVC not found in namespace $NAMESPACE)"
    FAILED="$FAILED $SVC"
    FAIL_COUNT=$((FAIL_COUNT + 1))
    continue
  fi

  RESOLVED_NAME="${RESOLVED%%|*}"
  RESOLVED_PORT="${RESOLVED##*|}"

  if [ -n "$BASE_URL" ]; then
    URL="$BASE_URL/$SVC/foundry/agents/ensure"
  elif [ "$USE_PORT_FORWARD" = "true" ]; then
    # Find free port and start port-forward
    LOCAL_PORT="$(python3 -c 'import socket; s=socket.socket(); s.bind(("",0)); print(s.getsockname()[1]); s.close()')"
    kubectl port-forward "svc/$RESOLVED_NAME" "$LOCAL_PORT:$RESOLVED_PORT" -n "$NAMESPACE" >/tmp/ensure_port_forward.log 2>&1 &
    PF_PID=$!
    sleep 3
    URL="http://localhost:$LOCAL_PORT/foundry/agents/ensure"

    if call_ensure "$SVC" "$URL"; then
      kill "$PF_PID" 2>/dev/null || true
    else
      kill "$PF_PID" 2>/dev/null || true
      FAILED="$FAILED $SVC"
      FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
    continue
  else
    URL="http://$RESOLVED_NAME.$NAMESPACE.svc.cluster.local:$RESOLVED_PORT/foundry/agents/ensure"
  fi

  if ! call_ensure "$SVC" "$URL"; then
    FAILED="$FAILED $SVC"
    FAIL_COUNT=$((FAIL_COUNT + 1))
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
