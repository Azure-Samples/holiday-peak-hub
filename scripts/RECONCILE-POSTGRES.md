# Reconcile PostgreSQL Admin Password

`reconcile-postgres-password.sh` (bash) and `reconcile-postgres-password.ps1` (PowerShell 7+)
keep the `postgres-admin-password` Key Vault secret and the Azure Database for
PostgreSQL Flexible Server **admin password** in sync. Both scripts accept the
same parameters and exit codes so they can be used interchangeably from CI or
operator workstations.

## Modes

| Mode | Writes? | Purpose |
| ---- | ------- | ------- |
| `probe` (default) | No | Read the Key Vault secret and attempt `SELECT 1;` against the server. |
| `rotate-from-keyvault` | Yes (DB) | Re-apply the current Key Vault secret as the server admin password. Use when the live pod reports `InvalidPasswordError` but the Key Vault secret is trusted. |
| `rotate-new` | Yes (DB + KV) | Generate a fresh 40-char password, update the server and Key Vault, rollback on probe failure. |

## Exit codes

| Code | Meaning |
| ---- | ------- |
| `0` | Success or `already_in_sync`. |
| `1` | Configuration error or rotation failure. |
| `2` | Probe failed with `invalid_password` (Key Vault secret does not match the server). |
| `3` | Server unreachable (network / firewall / VNet isolation). |

## Structured output

Every step emits a single-line JSON log record with fields
`step`, `mode`, `status`, `detail`, `ts`. The final record of a `probe` or
rotation run is a summary object with `status`, `server`, `user`,
`secret_version`, `checked_at`.

## Safety

- `--dry-run` prints planned actions but does **not** call any `az` write
  commands or `psql`.
- `rotate-new` attempts to roll the server and Key Vault back to the previous
  secret if the post-rotation probe fails.
- Passwords are passed to `psql` via `PGPASSWORD` (not via the command line) to
  avoid exposure in process listings.

## When to run which mode

| Situation | Mode |
| --------- | ---- |
| Daily / CI gate health check | `probe` |
| Live pod reports `psycopg.errors.InvalidPasswordError` and Key Vault holds the canonical password | `rotate-from-keyvault` |
| Scheduled rotation, or recovering from an unknown-state secret | `rotate-new` |

## Usage

### Bash

```bash
scripts/shell/ops/reconcile-postgres-password.sh \
  --subscription-id "$AZURE_SUBSCRIPTION_ID" \
  --resource-group holidaypeakhub405-dev-rg \
  --server-name holidaypeakhub405-dev-postgres \
  --key-vault-name holidaypeakhub405-dev-kv \
  --mode probe
```

### PowerShell

```powershell
./scripts/powershell/ops/reconcile-postgres-password.ps1 `
  -SubscriptionId $env:AZURE_SUBSCRIPTION_ID `
  -ResourceGroup holidaypeakhub405-dev-rg `
  -ServerName holidaypeakhub405-dev-postgres `
  -KeyVaultName holidaypeakhub405-dev-kv `
  -Mode probe
```

## Required tools

Both scripts require `az` and `psql` on `PATH`; `rotate-new` additionally
requires `openssl` (bash) or built-in `System.Security.Cryptography`
(PowerShell).
