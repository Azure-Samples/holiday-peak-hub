#!/usr/bin/env sh
set -eu

if [ "${GITHUB_ACTIONS:-}" != "true" ]; then
  exit 0
fi

if [ -z "${AZURE_CLIENT_ID:-}" ] || [ -z "${AZURE_TENANT_ID:-}" ]; then
  exit 0
fi

if [ -z "${ACTIONS_ID_TOKEN_REQUEST_URL:-}" ] || [ -z "${ACTIONS_ID_TOKEN_REQUEST_TOKEN:-}" ]; then
  echo "GitHub OIDC token request context is unavailable." >&2
  exit 1
fi

for command_name in az curl python3; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Required command '$command_name' is not available on PATH." >&2
    exit 1
  fi
done

OIDC_URL="$(
  python3 - <<'PY'
import os
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

parts = list(urlparse(os.environ['ACTIONS_ID_TOKEN_REQUEST_URL']))
query = dict(parse_qsl(parts[4], keep_blank_values=True))
query['audience'] = 'api://AzureADTokenExchange'
parts[4] = urlencode(query)
print(urlunparse(parts))
PY
)"

OIDC_RESPONSE_FILE="$(mktemp)"
cleanup() {
  rm -f "$OIDC_RESPONSE_FILE"
}
trap cleanup EXIT INT TERM

OIDC_TOKEN=""
for attempt in 1 2 3; do
  if ! curl -fsSL \
    -H "Authorization: bearer ${ACTIONS_ID_TOKEN_REQUEST_TOKEN}" \
    "$OIDC_URL" \
    -o "$OIDC_RESPONSE_FILE"; then
    echo "Failed to request GitHub OIDC token on attempt ${attempt}." >&2
    sleep 2
    continue
  fi

  if [ ! -s "$OIDC_RESPONSE_FILE" ]; then
    echo "GitHub OIDC token response was empty on attempt ${attempt}." >&2
    sleep 2
    continue
  fi

  if OIDC_TOKEN="$(python3 - "$OIDC_RESPONSE_FILE" <<'PY'
import json
import sys
from pathlib import Path

payload_path = Path(sys.argv[1])
raw_payload = payload_path.read_text(encoding='utf-8').strip()
if not raw_payload:
    raise SystemExit('GitHub OIDC token response was empty.')

payload = json.loads(raw_payload)
token = payload.get('value')
if not isinstance(token, str) or not token:
    raise SystemExit('GitHub OIDC token response did not include a token value.')

print(token)
PY
  )"; then
    break
  fi

  echo "Failed to parse GitHub OIDC token response on attempt ${attempt}." >&2
  OIDC_TOKEN=""
  sleep 2
done

if [ -z "$OIDC_TOKEN" ]; then
  echo "Unable to refresh Azure CLI login from GitHub OIDC after multiple attempts." >&2
  exit 1
fi

az login \
  --service-principal \
  --username "$AZURE_CLIENT_ID" \
  --tenant "$AZURE_TENANT_ID" \
  --federated-token "$OIDC_TOKEN" \
  --allow-no-subscriptions \
  --output none

if [ -n "${AZURE_SUBSCRIPTION_ID:-}" ]; then
  az account set --subscription "$AZURE_SUBSCRIPTION_ID"
fi