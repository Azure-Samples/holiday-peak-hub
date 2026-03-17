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

OIDC_TOKEN="$(
  curl -fsSL \
    -H "Authorization: bearer ${ACTIONS_ID_TOKEN_REQUEST_TOKEN}" \
    "$OIDC_URL" |
    python3 - <<'PY'
import json
import sys

payload = json.load(sys.stdin)
print(payload['value'])
PY
)"

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