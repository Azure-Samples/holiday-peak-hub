#!/usr/bin/env bash
# reconcile-postgres-password.sh
# Probe or reconcile the Azure Key Vault secret and the PostgreSQL Flexible Server admin password.
#
# Modes:
#   probe                 (default, read-only)
#   rotate-from-keyvault  (reset DB password FROM the current Key Vault secret)
#   rotate-new            (generate new random, update BOTH Key Vault AND DB)
#
# All non-fatal progress is emitted as JSON lines to stdout with fields:
#   step, mode, status, detail
#
# Exit codes:
#   0 — success / already in sync
#   1 — configuration error or rotation failure
#   2 — probe failed with invalid password (auth error)
#   3 — probe failed because the server is unreachable / network error
set -euo pipefail

SCRIPT_NAME="$(basename "$0")"

MODE="probe"
DRY_RUN=0
SUBSCRIPTION_ID=""
RESOURCE_GROUP=""
SERVER_NAME=""
ADMIN_USER="crud_admin"
KEY_VAULT_NAME=""
SECRET_NAME="postgres-admin-password"

log_json() {
  local step="$1" status="$2" detail="${3:-}"
  # Compact JSON line, no newlines in detail
  printf '{"step":"%s","mode":"%s","status":"%s","detail":"%s","ts":"%s"}\n' \
    "$step" "$MODE" "$status" "$(printf '%s' "$detail" | sed 's/"/\\"/g' | tr -d '\n')" \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}

usage() {
  cat >&2 <<EOF
Usage: $SCRIPT_NAME [options]

  --subscription-id <id>        Azure subscription ID (optional; falls back to az default)
  --resource-group <rg>         Resource group of the PostgreSQL Flexible Server (required)
  --server-name <name>          PostgreSQL Flexible Server name (required)
  --admin-user <user>           Admin username (default: crud_admin)
  --key-vault-name <name>       Key Vault name that stores the admin password (required)
  --secret-name <name>          Key Vault secret name (default: postgres-admin-password)
  --mode <probe|rotate-from-keyvault|rotate-new>
                                Execution mode (default: probe)
  --dry-run                     Print planned actions; do not execute write operations
  -h, --help                    Show this message
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --subscription-id) SUBSCRIPTION_ID="$2"; shift 2 ;;
    --resource-group)  RESOURCE_GROUP="$2"; shift 2 ;;
    --server-name)     SERVER_NAME="$2"; shift 2 ;;
    --admin-user)      ADMIN_USER="$2"; shift 2 ;;
    --key-vault-name)  KEY_VAULT_NAME="$2"; shift 2 ;;
    --secret-name)     SECRET_NAME="$2"; shift 2 ;;
    --mode)            MODE="$2"; shift 2 ;;
    --dry-run)         DRY_RUN=1; shift ;;
    -h|--help)         usage; exit 0 ;;
    *)                 echo "Unknown argument: $1" >&2; usage; exit 1 ;;
  esac
done

case "$MODE" in
  probe|rotate-from-keyvault|rotate-new) ;;
  *)
    log_json "validate-args" "error" "Unsupported --mode '$MODE'"
    exit 1
    ;;
esac

for required in RESOURCE_GROUP SERVER_NAME KEY_VAULT_NAME; do
  if [[ -z "${!required}" ]]; then
    log_json "validate-args" "error" "Missing required parameter: $required"
    exit 1
  fi
done

require_bin() {
  local bin="$1" hint="$2"
  if ! command -v "$bin" >/dev/null 2>&1; then
    if [[ $DRY_RUN -eq 1 ]]; then
      log_json "check-tools" "warning" "$bin not found on PATH (dry-run; continuing). Hint: $hint"
      return 0
    fi
    log_json "check-tools" "error" "$bin not found on PATH. Hint: $hint"
    exit 1
  fi
}

require_bin az "install Azure CLI (https://aka.ms/InstallAzureCLI)"
require_bin psql "install PostgreSQL client (apt install postgresql-client / brew install libpq)"
if [[ "$MODE" == "rotate-new" ]]; then
  require_bin openssl "install openssl"
fi
log_json "check-tools" "ok" "az, psql, openssl available as required"

if [[ -n "$SUBSCRIPTION_ID" ]]; then
  if [[ $DRY_RUN -eq 1 ]]; then
    log_json "set-subscription" "dry-run" "az account set --subscription $SUBSCRIPTION_ID"
  else
    az account set --subscription "$SUBSCRIPTION_ID" >/dev/null
    log_json "set-subscription" "ok" "subscription=$SUBSCRIPTION_ID"
  fi
fi

SERVER_FQDN="${SERVER_NAME}.postgres.database.azure.com"

read_keyvault_secret() {
  local version_out
  if [[ $DRY_RUN -eq 1 ]]; then
    log_json "read-secret" "dry-run" "az keyvault secret show --vault-name $KEY_VAULT_NAME --name $SECRET_NAME"
    CURRENT_SECRET=""
    SECRET_VERSION="dry-run"
    return 0
  fi
  version_out=$(az keyvault secret show \
    --vault-name "$KEY_VAULT_NAME" \
    --name "$SECRET_NAME" \
    --query '{value:value,id:id}' -o json 2>&1) || {
      log_json "read-secret" "error" "$version_out"
      exit 1
  }
  CURRENT_SECRET=$(printf '%s' "$version_out" | python3 -c 'import json,sys;print(json.load(sys.stdin)["value"])')
  SECRET_VERSION=$(printf '%s' "$version_out" | python3 -c 'import json,sys;print(json.load(sys.stdin)["id"].rsplit("/",1)[-1])')
  log_json "read-secret" "ok" "vault=$KEY_VAULT_NAME secret=$SECRET_NAME version=$SECRET_VERSION"
}

probe_connection() {
  local password="$1"
  local checked_at status result
  checked_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  if [[ $DRY_RUN -eq 1 ]]; then
    log_json "probe-connection" "dry-run" "psql postgres://${ADMIN_USER}@${SERVER_FQDN}:5432/postgres?sslmode=require"
    PROBE_STATUS="dry-run"
    return 0
  fi
  set +e
  result=$(PGPASSWORD="$password" psql \
    "host=${SERVER_FQDN} port=5432 dbname=postgres user=${ADMIN_USER} sslmode=require connect_timeout=10" \
    -v ON_ERROR_STOP=1 -At -c "SELECT 1;" 2>&1)
  status=$?
  set -e

  if [[ $status -eq 0 ]]; then
    PROBE_STATUS="ok"
    log_json "probe-connection" "ok" "checked_at=$checked_at server=$SERVER_FQDN user=$ADMIN_USER"
    return 0
  fi

  if echo "$result" | grep -qiE 'password authentication failed|invalidpassword'; then
    PROBE_STATUS="invalid_password"
    log_json "probe-connection" "invalid_password" "checked_at=$checked_at server=$SERVER_FQDN user=$ADMIN_USER"
    return 2
  fi

  PROBE_STATUS="unreachable"
  log_json "probe-connection" "unreachable" "checked_at=$checked_at server=$SERVER_FQDN detail=${result//$'\n'/ }"
  return 3
}

apply_password_to_server() {
  local password="$1"
  if [[ $DRY_RUN -eq 1 ]]; then
    log_json "apply-password" "dry-run" "az postgres flexible-server update --name $SERVER_NAME --resource-group $RESOURCE_GROUP --admin-password ****"
    return 0
  fi
  local update_out
  set +e
  update_out=$(az postgres flexible-server update \
    --resource-group "$RESOURCE_GROUP" \
    --name "$SERVER_NAME" \
    --admin-password "$password" 2>&1)
  local rc=$?
  set -e
  if [[ $rc -ne 0 ]]; then
    log_json "apply-password" "error" "${update_out//$'\n'/ }"
    return 1
  fi
  log_json "apply-password" "ok" "server=$SERVER_NAME"
  return 0
}

set_keyvault_secret() {
  local value="$1"
  if [[ $DRY_RUN -eq 1 ]]; then
    log_json "set-secret" "dry-run" "az keyvault secret set --vault-name $KEY_VAULT_NAME --name $SECRET_NAME --value ****"
    return 0
  fi
  local out
  set +e
  out=$(az keyvault secret set \
    --vault-name "$KEY_VAULT_NAME" \
    --name "$SECRET_NAME" \
    --value "$value" \
    --query 'id' -o tsv 2>&1)
  local rc=$?
  set -e
  if [[ $rc -ne 0 ]]; then
    log_json "set-secret" "error" "${out//$'\n'/ }"
    return 1
  fi
  log_json "set-secret" "ok" "vault=$KEY_VAULT_NAME secret=$SECRET_NAME id=${out##*/}"
  return 0
}

generate_password() {
  # 40-char PostgreSQL-safe password (alnum + limited special chars).
  local raw
  raw=$(openssl rand -base64 64 | tr -dc 'A-Za-z0-9@#$%' | head -c 40)
  if [[ ${#raw} -lt 40 ]]; then
    log_json "generate-password" "error" "openssl produced insufficient entropy"
    exit 1
  fi
  printf '%s' "$raw"
}

report_probe_result() {
  local checked_at
  checked_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  printf '{"status":"%s","server":"%s","user":"%s","secret_version":"%s","checked_at":"%s"}\n' \
    "$PROBE_STATUS" "$SERVER_FQDN" "$ADMIN_USER" "${SECRET_VERSION:-unknown}" "$checked_at"
}

case "$MODE" in
  probe)
    read_keyvault_secret
    if [[ $DRY_RUN -eq 1 ]]; then
      probe_connection ""
      report_probe_result
      exit 0
    fi
    set +e
    probe_connection "$CURRENT_SECRET"
    probe_rc=$?
    set -e
    report_probe_result
    exit $probe_rc
    ;;

  rotate-from-keyvault)
    read_keyvault_secret
    if [[ $DRY_RUN -eq 0 ]]; then
      set +e
      probe_connection "$CURRENT_SECRET"
      probe_rc=$?
      set -e
      if [[ $probe_rc -eq 0 ]]; then
        PROBE_STATUS="already_in_sync"
        log_json "rotate-from-keyvault" "already_in_sync" "no-op"
        report_probe_result
        exit 0
      fi
      if [[ $probe_rc -eq 3 ]]; then
        report_probe_result
        exit 3
      fi
    fi
    apply_password_to_server "$CURRENT_SECRET" || exit 1
    if [[ $DRY_RUN -eq 1 ]]; then
      PROBE_STATUS="dry-run"
      report_probe_result
      exit 0
    fi
    set +e
    probe_connection "$CURRENT_SECRET"
    probe_rc=$?
    set -e
    report_probe_result
    if [[ $probe_rc -eq 0 ]]; then
      exit 0
    fi
    log_json "rotate-from-keyvault" "error" "post-rotation probe still failing (rc=$probe_rc)"
    exit 1
    ;;

  rotate-new)
    read_keyvault_secret
    PREVIOUS_SECRET="$CURRENT_SECRET"
    if [[ $DRY_RUN -eq 1 ]]; then
      log_json "generate-password" "dry-run" "openssl rand | tr | head -c 40"
      apply_password_to_server "dry-run"
      set_keyvault_secret "dry-run"
      PROBE_STATUS="dry-run"
      report_probe_result
      exit 0
    fi
    NEW_SECRET=$(generate_password)
    log_json "generate-password" "ok" "length=${#NEW_SECRET}"
    apply_password_to_server "$NEW_SECRET" || exit 1
    if ! set_keyvault_secret "$NEW_SECRET"; then
      log_json "rotate-new" "error" "Key Vault update failed; rolling back DB password"
      apply_password_to_server "$PREVIOUS_SECRET" || log_json "rollback" "error" "rollback failed"
      exit 1
    fi
    set +e
    probe_connection "$NEW_SECRET"
    probe_rc=$?
    set -e
    report_probe_result
    if [[ $probe_rc -ne 0 ]]; then
      log_json "rotate-new" "error" "post-rotation probe failed (rc=$probe_rc); attempting rollback"
      apply_password_to_server "$PREVIOUS_SECRET" || log_json "rollback" "error" "rollback failed"
      set_keyvault_secret "$PREVIOUS_SECRET" || log_json "rollback" "error" "KV rollback failed"
      exit 1
    fi
    exit 0
    ;;
esac
