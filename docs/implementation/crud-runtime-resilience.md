# CRUD Runtime Resilience Improvements (2026-03-06)

## Scope

Hardened `apps/crud-service` list endpoints and readiness checks to prevent recurring runtime `500` errors on:

- `GET /api/products`
- `GET /api/categories`

## Changes

- Auth convergence groundwork (Phase 2):
  - CRUD runtime settings now default `POSTGRES_AUTH_MODE` to `password` for deterministic baseline behavior.
  - Entra auth remains supported as explicit opt-in (`POSTGRES_AUTH_MODE=entra`).
  - AZD CRUD env generators (`generate-crud-env.sh` and `generate-crud-env.ps1`) now resolve auth mode from azd outputs with `password` as default fallback.
  - In `password` mode, `POSTGRES_USER` resolves to explicit admin user output; in `entra` mode, generators preserve workload-user resolution fallback.

- Added PostgreSQL pool health tracking in `BaseRepository`:
  - Captures pool initialization errors in `_pool_init_error`.
  - Provides `check_pool_health()` with a live `SELECT 1` probe.
  - Converts pool acquisition failures to explicit runtime errors with stable messaging.
  - Skips malformed DB row payloads during query hydration instead of crashing request flows.

- Hardened route-level behavior for list endpoints:
  - Repository/transient runtime failures now return `503 Service Unavailable` with endpoint-specific messages.
  - Invalid repository result shapes (`None` or non-iterable outputs) are now treated as transient backend failures and return stable `503` responses instead of `TypeError` `500`.
  - Malformed records are filtered out using per-record Pydantic validation, so one bad row does not fail the whole response.

- Hardened optional authentication path:
  - `get_current_user_optional` now catches unexpected runtime failures from token validation/JWKS code paths.
  - These failures are logged as warnings and the request continues as anonymous, preventing `/api/products` from leaking `500` for optional-auth scenarios.

- Improved readiness signaling:
  - Startup records DB pool init failure on app state (`db_pool_init_error`).
  - `GET /ready` now includes a `postgres` check and returns `503` when DB runtime state is unhealthy.
  - Follow-up fix: readiness now probes current pool health first and clears stale startup init errors when the pool recovers, preventing permanent degraded state from transient bootstrap failures.

## Regression Tests Added

- `apps/crud-service/tests/integration/test_products_api.py`
  - `test_list_products_skips_malformed_records`
  - `test_list_products_repo_failure_returns_503`
  - `test_list_products_none_repo_result_returns_503`
  - `test_list_products_non_iterable_repo_result_returns_503`

- `apps/crud-service/tests/integration/test_categories_api.py`
  - `test_list_categories_anonymous_returns_data`
  - `test_list_categories_skips_malformed_records`
  - `test_list_categories_repo_failure_returns_503`
  - `test_list_categories_none_repo_result_returns_503`
  - `test_list_categories_non_iterable_repo_result_returns_503`

- `apps/crud-service/tests/unit/test_auth_jwks.py`
  - `test_optional_auth_runtime_failure_returns_none`

- `apps/crud-service/tests/unit/test_health.py`
  - `test_readiness_degraded_when_postgres_init_failed`
  - `test_readiness_recovers_when_postgres_pool_is_healthy`
  - readiness shape assertion now includes `postgres`

## Post-Review Fixes (2026-03-06)

- Addressed focused review finding where stale startup DB init errors could keep `/ready` degraded after transient failures.
- Added explicit test coverage for recovery path.
- Preserved existing degraded behavior for true dependency failures.
