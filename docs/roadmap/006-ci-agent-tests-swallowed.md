# 006: CI Agent Tests Silently Swallowed

**Severity**: Medium  
**Category**: CI/CD  
**Discovered**: February 2026

## Summary

The CI pipeline uses `|| true` when running agent service tests, which masks all test failures. Agent tests could be completely broken and CI would still pass.

## Current Behavior

In `.github/workflows/test.yml`, app test execution previously included:

```bash
pytest apps/*/tests || true
```

This means:
- If all agent tests pass → CI passes ✅
- If all agent tests fail → CI still passes ✅ (incorrect)

## Expected Behavior

Agent tests should fail the CI pipeline if any test fails. The `|| true` should be removed and replaced with proper error handling.

## Root Cause

The `|| true` was likely added as a temporary workaround when agent tests had import errors or missing dependencies during early development. It was never removed.

## Impact

- Agent test regressions are invisible in CI
- Code merged to `main` may have broken agent tests
- False confidence in test suite health

## Suggested Fix

1. Remove `|| true` from agent test execution in CI
2. Fix any agent tests that currently fail
3. If some agents genuinely cannot be tested in CI (e.g., require Azure services), mark those tests with `@pytest.mark.skip(reason="requires Azure")` instead
4. Add a CI gate: all test commands must exit 0

## Files Modified

- `.github/workflows/test.yml` — Removed `|| true` from app test execution so failures are no longer masked
