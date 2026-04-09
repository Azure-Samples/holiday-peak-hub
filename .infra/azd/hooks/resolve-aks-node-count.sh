#!/usr/bin/env sh
# resolve-aks-node-count.sh
#
# Queries Azure VM SKU availability-zone support for the AKS node VM size in
# the target region and sets aksNodeCount and aksAvailabilityZones azd parameters.
#
# For non-prod environments the count matches the number of available zones so
# the scheduler can spread pods evenly. Falls back to 1 when zone info is
# unavailable.
set -eu

ENVIRONMENT="${1:-${AZURE_ENV_NAME:-}}"
VM_SIZE="${2:-Standard_D8ds_v5}"

if [ -z "$ENVIRONMENT" ]; then
  echo "Environment must be provided as the first argument or AZURE_ENV_NAME." >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Resolve target location from the azd environment
# ---------------------------------------------------------------------------
AZD_VALUES="$(azd env get-values -e "$ENVIRONMENT" 2>/dev/null || true)"

get_env_value() {
  key="$1"
  value="$(printf '%s\n' "$AZD_VALUES" | grep -E "^${key}=" | tail -n 1 | cut -d '=' -f 2- || true)"
  case "$value" in
    \"*\") value="${value#\"}"; value="${value%\"}" ;;
    \'*\') value="${value#\'}"; value="${value%\'}" ;;
  esac
  printf '%s' "$value"
}

LOCATION="$(get_env_value AZURE_LOCATION)"
if [ -z "$LOCATION" ]; then
  LOCATION="westus2"
  echo "AZURE_LOCATION not found in azd env; defaulting to '$LOCATION'."
fi

# ---------------------------------------------------------------------------
# Skip for prod — Bicep uses hardcoded prod counts
# ---------------------------------------------------------------------------
ENV_TIER="$(get_env_value environment)"
if [ "$ENV_TIER" = "prod" ]; then
  echo "Production environment detected — skipping AKS node count override (Bicep uses prod defaults)."
  exit 0
fi

# ---------------------------------------------------------------------------
# Query VM SKU zone availability
# ---------------------------------------------------------------------------
echo "Querying availability zones for VM SKU '$VM_SIZE' in region '$LOCATION'..."

SKU_JSON="$(az vm list-skus -l "$LOCATION" --size "$VM_SIZE" --resource-type virtualMachines --output json 2>/dev/null || true)"
if [ -z "$SKU_JSON" ] || [ "$SKU_JSON" = "[]" ]; then
  echo "WARNING: Unable to query VM SKUs. Falling back to aksNodeCount=1, aksAvailabilityZones=[1,2,3]."
  azd env set aksNodeCount "1" -e "$ENVIRONMENT"
  azd env set aksAvailabilityZones "[1,2,3]" -e "$ENVIRONMENT"
  exit 0
fi

# Extract available zones using jq
if ! command -v jq >/dev/null 2>&1; then
  echo "WARNING: jq not available. Falling back to aksNodeCount=1, aksAvailabilityZones=[1,2,3]."
  azd env set aksNodeCount "1" -e "$ENVIRONMENT"
  azd env set aksAvailabilityZones "[1,2,3]" -e "$ENVIRONMENT"
  exit 0
fi

# Get all zones for the matched SKU
ALL_ZONES="$(printf '%s' "$SKU_JSON" | jq -r "[.[] | select(.name==\"$VM_SIZE\") | .locationInfo[]?.zones[]?] | unique | .[]" 2>/dev/null || true)"

# Get restricted zones
RESTRICTED_ZONES="$(printf '%s' "$SKU_JSON" | jq -r "[.[] | select(.name==\"$VM_SIZE\") | .restrictions[]? | select(.type==\"Zone\") | .restrictionInfo.zones[]?] | unique | .[]" 2>/dev/null || true)"

# Compute available zones by filtering out restricted ones
if [ -n "$ALL_ZONES" ]; then
  AVAILABLE_ZONES=""
  for zone in $ALL_ZONES; do
    restricted=false
    for rz in $RESTRICTED_ZONES; do
      if [ "$zone" = "$rz" ]; then
        restricted=true
        break
      fi
    done
    if [ "$restricted" = "false" ]; then
      AVAILABLE_ZONES="${AVAILABLE_ZONES} ${zone}"
    fi
  done

  ZONE_COUNT=0
  for _ in $AVAILABLE_ZONES; do
    ZONE_COUNT=$((ZONE_COUNT + 1))
  done
else
  ZONE_COUNT=0
fi

if [ "$ZONE_COUNT" -gt 0 ]; then
  NODE_COUNT="$ZONE_COUNT"
  # Build JSON array from available zones
  ZONES_JSON="["
  first=true
  for zone in $AVAILABLE_ZONES; do
    if [ "$first" = "true" ]; then
      ZONES_JSON="${ZONES_JSON}${zone}"
      first=false
    else
      ZONES_JSON="${ZONES_JSON},${zone}"
    fi
  done
  ZONES_JSON="${ZONES_JSON}]"
  echo "VM SKU '$VM_SIZE' available in $ZONE_COUNT zone(s) in '$LOCATION': $ZONES_JSON. Setting aksNodeCount=$NODE_COUNT."
else
  NODE_COUNT=1
  ZONES_JSON="[1,2,3]"
  echo "No availability zone info found for '$VM_SIZE' in '$LOCATION'. Setting aksNodeCount=1, aksAvailabilityZones=$ZONES_JSON."
fi

azd env set aksNodeCount "$NODE_COUNT" -e "$ENVIRONMENT"
azd env set aksAvailabilityZones "$ZONES_JSON" -e "$ENVIRONMENT"
echo "aksNodeCount=$NODE_COUNT, aksAvailabilityZones=$ZONES_JSON for environment '$ENVIRONMENT'."
