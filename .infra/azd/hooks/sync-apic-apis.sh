#!/usr/bin/env sh
# Shell wrapper for sync-apic-apis.ps1 — imports APIM APIs into API Center.

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-${RESOURCE_GROUP:-}}"
APIC_NAME="${APIC_NAME:-}"
APIM_NAME="${APIM_NAME:-}"
SUBSCRIPTION_ID="${AZURE_SUBSCRIPTION_ID:-}"

PREVIEW=false
while [ "$#" -gt 0 ]; do
  case "$1" in
    --preview) PREVIEW=true ;;
    --resource-group) shift; RESOURCE_GROUP="$1" ;;
    --apic-name) shift; APIC_NAME="$1" ;;
    --apim-name) shift; APIM_NAME="$1" ;;
    *) echo "Unknown flag: $1" >&2; exit 1 ;;
  esac
  shift
done

PREVIEW_FLAG=""
if [ "$PREVIEW" = true ]; then
  PREVIEW_FLAG="-Preview"
fi

exec pwsh -NoProfile -NonInteractive -File "$SCRIPT_DIR/sync-apic-apis.ps1" \
  -ResourceGroup "$RESOURCE_GROUP" \
  -ApicName "$APIC_NAME" \
  -ApimName "$APIM_NAME" \
  -SubscriptionId "$SUBSCRIPTION_ID" \
  $PREVIEW_FLAG
