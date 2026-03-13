# 005: Lib Config Test Failures (Schema Drift)

**Severity**: Medium  
**Category**: Testing  
**Discovered**: February 2026

## Summary

10 tests in `lib/tests/test_config.py` fail due to schema drift between `MemorySettings`, `ServiceSettings`, `PostgresSettings` Pydantic models and the test expectations.

## Failing Tests

1. `TestMemorySettings::test_create_from_env`
2. `TestMemorySettings::test_missing_required_env_uses_defaults`
3. `TestMemorySettings::test_redis_url_format`
4. `TestServiceSettings::test_create_from_env`
5. `TestServiceSettings::test_optional_monitor_connection_string`
6. `TestServiceSettings::test_monitor_connection_string_defaults_to_none`
7. `TestPostgresSettings::test_create_from_env`
8. `TestPostgresSettings::test_postgres_dsn_format_validation`
9. `TestSettingsIntegration::test_all_settings_from_env`
10. `TestSettingsIntegration::test_settings_immutability`

## Root Cause

The settings models in `lib/src/holiday_peak_lib/config/settings.py` were updated during the PostgreSQL migration and APIM integration (PR #24), but the corresponding test assertions in `test_config.py` were not updated to match the new field names, defaults, and validation rules.

## Impact

- 10 of 175 tests fail (165 pass)
- Reported lib coverage: 73% (some config code paths untested)
- CI passes because agent tests use `|| true` (see issue #006)

## Suggested Fix

1. Read current `settings.py` to understand the actual field names and defaults
2. Update `test_config.py` assertions to match current schema
3. Add new tests for PostgreSQL settings added in PR #24
4. Verify all 175 tests pass after fix

## Files to Modify

- `lib/tests/test_config.py` — Update test assertions
- `lib/src/holiday_peak_lib/config/settings.py` — Reference (do not modify)

## Resolution (2026-03-12)

Issue #29 was resolved with minimal scope by isolating environment-file loading in tests only.

- Updated `lib/tests/test_config.py` to instantiate `MemorySettings`, `ServiceSettings`, `PostgresSettings`, and `TruthLayerSettings` with `_env_file=None`.
- No runtime settings model changes were made in `lib/src/holiday_peak_lib/config/settings.py`.
- Validation run: `python -m pytest lib/tests/test_config.py -q` → `20 passed`.
