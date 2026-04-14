# ACR Export-Policy Governance

This document describes the governance model for handling ACR registries with `exportPolicy` disabled during tested-image builds.

## Problem

When ACR has `exportPolicy` set to `disabled` (a common security posture for production registries), GitHub-hosted runners cannot push images because:

- Public network access is disabled by default.
- Re-enabling public access fails when export policy is disabled.
- The runner has no private network path to the registry.

## Solution: Temporary Least-Privilege ACR Access

The `deploy-azd.yml` workflow implements a three-phase access pattern:

### Phase 1: Prepare (`prepare-acr-build-access` job)

1. Records the current ACR public network access state and default network action.
2. If public access is `Disabled` and `autoAllowAcrRunnerIp` is `true`:
   - Enables public network access with `defaultAction=Deny` (least-open posture).
   - Does NOT set `defaultAction=Allow` — only the runner IP is allowlisted.

### Phase 2: Build (`build-aks-images` matrix job)

1. Each matrix job resolves the runner's egress IP.
2. Adds the runner IP to the ACR network rules (if not already present).
3. Builds and pushes the image to ACR.
4. Removes the runner IP from the ACR network rules (cleanup step, runs on `always()`).

### Phase 3: Restore (`restore-acr-build-access` job)

1. Runs on `always()` after all build jobs complete.
2. Restores the original `defaultAction` value.
3. Restores the original `publicNetworkAccess` state (re-disables if it was disabled).
4. Validates the restored state matches the original.

## Security Properties

| Property | Guarantee |
|----------|-----------|
| Public access window | Only during build phase; restored immediately after |
| Network scope | Only the runner's egress IP is allowlisted; `defaultAction=Deny` blocks all others |
| Runner IP cleanup | Per-job cleanup on `always()` + global restore job |
| State restoration | Verified by comparing pre/post ACR configuration |
| Export policy | Not modified — remains disabled throughout |

## Configuration

| Input | Default | Purpose |
|-------|---------|---------|
| `autoAllowAcrRunnerIp` | `true` | Enable the temporary access pattern |

Set `autoAllowAcrRunnerIp=false` to skip this behavior entirely (builds will fail if ACR is not reachable from the runner).

## Audit Trail

Every deploy run logs:

- `public_network_access_before`: Original ACR public access state.
- `default_action_before`: Original network default action.
- `public_access_temporarily_enabled`: Whether temporary access was needed.
- `runner_ip_allowlist_added`: Whether the runner IP was added per-job.

These values are visible in the GitHub Actions run logs for post-incident review.
