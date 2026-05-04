#!/usr/bin/env bash
# agc-bisect.sh — AGC (Application Gateway for Containers) edge-path bisection.
#
# Runs a fixed sequence of hops (pod-local, in-cluster Service DNS, AGC direct,
# APIM fronting) and writes a structured JSON evidence artifact under docs/ops.
# Completes under 60 seconds. Read-only: no destructive az/kubectl commands.
#
# Usage:
#   ./agc-bisect.sh [--cluster NAME] [--namespace NS] [--service NAME]
#                   [--pod-selector LBL=VAL] [--agc-fqdn FQDN] [--agc-path /PATH]
#                   [--apim-fqdn FQDN] [--apim-path /PATH] [--output-dir DIR]
#                   [--fail-on-hop-gt N] [--skip-in-cluster]
#
# Exit codes:
#   0   success (or first failing hop < --fail-on-hop-gt)
#   1   first failing hop >= --fail-on-hop-gt
#   2   prerequisite missing (kubectl, curl, jq)

set -euo pipefail

CLUSTER="holidaypeakhub405-dev-aks"
NAMESPACE="holiday-peak-agents"
SERVICE="ecommerce-catalog-search-ecommerce-catalog-search"
POD_SELECTOR="app=ecommerce-catalog-search"
AGC_FQDN="esbcc8bcfyazbbdg.fz03.alb.azure.com"
AGC_PATH="/ecommerce-catalog-search"
APIM_FQDN="holidaypeakhub405-dev-apim.azure-api.net"
APIM_PATH="/agents/ecommerce-catalog-search"
OUTPUT_DIR="docs/ops"
FAIL_ON_HOP_GT=0
SKIP_IN_CLUSTER=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --cluster)          CLUSTER="$2"; shift 2;;
    --namespace)        NAMESPACE="$2"; shift 2;;
    --service)          SERVICE="$2"; shift 2;;
    --pod-selector)     POD_SELECTOR="$2"; shift 2;;
    --agc-fqdn)         AGC_FQDN="$2"; shift 2;;
    --agc-path)         AGC_PATH="$2"; shift 2;;
    --apim-fqdn)        APIM_FQDN="$2"; shift 2;;
    --apim-path)        APIM_PATH="$2"; shift 2;;
    --output-dir)       OUTPUT_DIR="$2"; shift 2;;
    --fail-on-hop-gt)   FAIL_ON_HOP_GT="$2"; shift 2;;
    --skip-in-cluster)  SKIP_IN_CLUSTER=1; shift;;
    -h|--help) sed -n '1,25p' "$0"; exit 0;;
    *) echo "unknown flag: $1" >&2; exit 2;;
  esac
done

for tool in curl jq; do
  command -v "$tool" >/dev/null 2>&1 || { echo "missing: $tool" >&2; exit 2; }
done
if [[ $SKIP_IN_CLUSTER -eq 0 ]]; then
  command -v kubectl >/dev/null 2>&1 || { echo "missing: kubectl (or use --skip-in-cluster)" >&2; exit 2; }
fi

mkdir -p "$OUTPUT_DIR"
ARTIFACT="$OUTPUT_DIR/agc-bisection-$(date -u +%Y-%m-%d-%H%M%S).json"
START_EPOCH_MS=$(date +%s%3N 2>/dev/null || python -c 'import time; print(int(time.time()*1000))')

hops_json="[]"

# --- probe via curl; emits a JSON object per hop ---
probe() {
  local id="$1" label="$2" method="$3" url="$4" timeout="$5"
  local tmp="$(mktemp)"
  local metrics
  if ! metrics=$(curl -sS -o "$tmp" -m "$timeout" -X "$method" \
        -w 'code=%{http_code};time=%{time_total};ct=%{content_type}\n' "$url" 2>&1); then
    jq -cn \
      --argjson id "$id" --arg label "$label" --arg method "$method" --arg url "$url" \
      --arg err "$metrics" \
      '{id:$id,label:$label,method:$method,url:$url,statusCode:null,elapsedMs:null,error:$err,result:"fail"}'
    rm -f "$tmp"
    return
  fi
  local code elapsed_s elapsed_ms ct preview
  code=$(echo "$metrics" | sed -n 's/.*code=\([0-9]*\).*/\1/p')
  elapsed_s=$(echo "$metrics" | sed -n 's/.*time=\([0-9.]*\).*/\1/p')
  ct=$(echo "$metrics" | sed -n 's/.*ct=\([^;]*\).*/\1/p' || true)
  elapsed_ms=$(awk -v t="$elapsed_s" 'BEGIN{printf "%d", t*1000}')
  preview=$(head -c 240 "$tmp" | tr '\n' ' ' | tr '\r' ' ')
  rm -f "$tmp"
  local result="pass"
  [[ -z "$code" || "$code" == "000" || "$code" -ge 500 ]] && result="fail"
  jq -cn \
    --argjson id "$id" --arg label "$label" --arg method "$method" --arg url "$url" \
    --argjson code "${code:-0}" --argjson ems "$elapsed_ms" \
    --arg ct "$ct" --arg preview "$preview" --arg result "$result" \
    '{id:$id,label:$label,method:$method,url:$url,statusCode:$code,elapsedMs:$ems,contentType:$ct,bodyPreview:$preview,result:$result}'
}

if [[ $SKIP_IN_CLUSTER -eq 0 ]]; then
  echo "[Hop 2] In-cluster Service DNS..."
  POD="agc-bisect-$RANDOM"
  SVC_URL="http://${SERVICE}.${NAMESPACE}.svc.cluster.local/health"
  hop2_start=$(date +%s%3N 2>/dev/null || python -c 'import time; print(int(time.time()*1000))')
  if kubectl run "$POD" -n "$NAMESPACE" --rm -i --restart=Never --quiet \
        --image=curlimages/curl:8.10.1 --command -- \
        sh -c "curl -sS -m 5 -o /dev/null -w 'code=%{http_code}\n' $SVC_URL" > /tmp/agcbisect_hop2 2>&1; then
    code=$(sed -n 's/.*code=\([0-9]*\).*/\1/p' /tmp/agcbisect_hop2 | tail -n1)
    hop2_end=$(date +%s%3N 2>/dev/null || python -c 'import time; print(int(time.time()*1000))')
    elapsed=$((hop2_end - hop2_start))
    result="pass"; [[ "$code" != "200" ]] && result="fail"
    hop=$(jq -cn --arg url "$SVC_URL" --argjson code "${code:-0}" --argjson ems "$elapsed" --arg result "$result" \
          '{id:2,label:"In-cluster Service DNS",method:"GET",url:$url,statusCode:$code,elapsedMs:$ems,result:$result}')
  else
    hop=$(jq -cn --arg url "$SVC_URL" --arg err "$(cat /tmp/agcbisect_hop2)" \
          '{id:2,label:"In-cluster Service DNS",url:$url,result:"fail",error:$err}')
  fi
  hops_json=$(echo "$hops_json" | jq ". + [$hop]")

  echo "[Hop 3] Gateway + HTTPRoute status..."
  gw_ok=true; rt_ok=true
  kubectl get gateway -A -o json   | jq -e '.items[].status.conditions[] | select(.type=="Programmed" and .status!="True")' >/dev/null 2>&1 && gw_ok=false
  kubectl get httproute -A -o json | jq -e '.items[].status.parents[].conditions[] | select(.type=="Programmed" and .status!="True")' >/dev/null 2>&1 && rt_ok=false
  result="pass"; { [[ "$gw_ok" == "false" ]] || [[ "$rt_ok" == "false" ]]; } && result="fail"
  hop=$(jq -cn --argjson gw "$gw_ok" --argjson rt "$rt_ok" --arg result "$result" \
        '{id:3,label:"Gateway + HTTPRoute status",gatewayOk:$gw,routeOk:$rt,result:$result}')
  hops_json=$(echo "$hops_json" | jq ". + [$hop]")
fi

echo "[Hop 4] AGC direct HTTP..."
hop=$(probe 4 "AGC direct HTTP" GET "http://${AGC_FQDN}${AGC_PATH}/health" 10)
hops_json=$(echo "$hops_json" | jq ". + [$hop]")

echo "[Hop 5] AGC direct HTTPS..."
hop=$(probe 5 "AGC direct HTTPS" GET "https://${AGC_FQDN}${AGC_PATH}/health" 10)
hops_json=$(echo "$hops_json" | jq ". + [$hop]")

echo "[Hop 6] APIM fronting..."
hop=$(probe 6 "APIM fronting" GET "https://${APIM_FQDN}${APIM_PATH}/health" 10)
hops_json=$(echo "$hops_json" | jq ". + [$hop]")

END_EPOCH_MS=$(date +%s%3N 2>/dev/null || python -c 'import time; print(int(time.time()*1000))')
TOTAL_MS=$((END_EPOCH_MS - START_EPOCH_MS))
FIRST_FAIL=$(echo "$hops_json" | jq -r 'map(select(.result=="fail")) | (first // {}) | .id // empty')

jq -n \
  --arg schema "holiday-peak-hub/agc-bisection/v1" \
  --arg generatedAt "$(date -u +%FT%TZ)" \
  --arg cluster "$CLUSTER" --arg namespace "$NAMESPACE" --arg service "$SERVICE" \
  --arg agcFqdn "$AGC_FQDN" --arg apimFqdn "$APIM_FQDN" \
  --argjson totalMs "$TOTAL_MS" \
  --argjson hops "$hops_json" \
  --arg firstFail "${FIRST_FAIL:-}" \
  '{schema:$schema,generatedAt:$generatedAt,cluster:$cluster,namespace:$namespace,serviceName:$service,
    agcFqdn:$agcFqdn,apimFqdn:$apimFqdn,totalElapsedMs:$totalMs,
    firstFailingHop:(if $firstFail=="" then null else ($firstFail|tonumber) end),
    hops:$hops}' > "$ARTIFACT"

echo
echo "Wrote: $ARTIFACT"
echo "Total elapsed: ${TOTAL_MS} ms"
echo "First failing hop: ${FIRST_FAIL:-none}"

if [[ "$FAIL_ON_HOP_GT" -gt 0 && -n "${FIRST_FAIL:-}" && "$FIRST_FAIL" -ge "$FAIL_ON_HOP_GT" ]]; then
  echo "FAIL: first failing hop ($FIRST_FAIL) >= threshold ($FAIL_ON_HOP_GT)" >&2
  exit 1
fi
exit 0
