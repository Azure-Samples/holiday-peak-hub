# 014 — Deploy Pipeline Hardening (April 2026)

**Status**: Resolved  
**PRs**: #813, #814, #827, #828, #829, #830, #831, #832, #833  
**Category**: CI/CD, Infrastructure  
**Created**: April 13, 2026

## Summary

A series of cascading blockers were discovered and fixed when deploying the
full AKS backend (28 services) for the first time after the agent timeout
defense-in-depth changes (PR #810). Nine PRs addressed issues spanning the
build matrix parser, change detection, Bicep provisioning, and ACR network
access restoration.

## Issues Fixed

| PR | Issue | Root Cause | Fix |
|----|-------|-----------|-----|
| #813 | Image builds targeted wrong service | Python parser in `build-aks-images` reset `project_path` after iterating past the target service | Early `break` after finding the matching service |
| #814 | `LIB_CHANGED` not triggered | `holiday-peak-lib` version unchanged across deploys | Bumped to 0.2.1 to trigger full rebuild |
| #827 | CRUD service skipped in deploy | `serviceFilter` didn't force `CRUD_CHANGED=true` when crud-service was in filter | Set `CRUD_CHANGED=true` when `crud-service` appears in filter |
| #828 | Empty infra outputs with `skipProvision` | `azd env refresh` not called when skipping provision | Added `azd env refresh` step for `skipProvision=true` |
| #829 | Bicep provision failure in centralus | `Microsoft.ApiCenter/services` unavailable in region | Made ApiCenter conditional on region support |
| #830 | ACR export policy blocked public access | `exportPolicy: disabled` prevents `publicNetworkAccess` toggle on Premium ACR | Enable export policy before toggling network access |
| #831 | ACR data-plane auth failure | `defaultAction: Deny` caused `CONNECTIVITY_REFRESH_TOKEN_ERROR` during builds | Use `defaultAction: Allow` during build window + readiness loop |
| #832 | ACR restore validation false positive | Validating `defaultAction` after disabling `publicNetworkAccess` — Azure reports `Deny` | Skip `defaultAction` validation when public access is `Disabled` |
| #833 | Empty POSTGRES_HOST after provision | `azd provision` exited non-zero due to `RoleAssignmentExists`, outputs not saved | Run `azd env refresh` after the RoleAssignmentExists fallback |

## Key Lessons

1. **azd provision failure modes**: When `azd provision` fails, it does not
   write outputs to the environment — even if all infrastructure resources
   were successfully deployed. The `RoleAssignmentExists` error is a trailing
   conflict that doesn't affect actual resource creation.

2. **ACR Premium network access**: Premium ACR with export policy disabled
   and public access disabled requires a specific sequence to enable network
   access for builds: enable export policy first, then toggle public access,
   then set `defaultAction: Allow`, then wait for data-plane readiness.

3. **Bicep role assignment idempotency**: Azure rejects role assignments for
   the same principal+role+scope if a different assignment name (guid) is
   used. AVM modules generate their own GUIDs — changing module versions or
   inputs can cause `RoleAssignmentExists` conflicts. The workflow fallback
   handles this for non-prod environments.

4. **Change detection with filters**: When using `serviceFilter` to target
   specific services, dependent services (like CRUD for agent services) must
   be explicitly included in the change cascade.

## Architecture Impact

- The deploy workflow now has defense-in-depth for infrastructure output
  propagation: outputs flow from Bicep → azd environment → workflow outputs
  → downstream jobs, with `azd env refresh` as a fallback when provision
  partially fails.

- ACR network access management follows a save/restore pattern with
  validation gates that account for Azure's eventual consistency in network
  rule reporting.
