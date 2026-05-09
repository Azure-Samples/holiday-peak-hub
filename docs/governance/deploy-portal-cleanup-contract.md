# Deploy-portal cleanup contract

> **Audience.** Operators, retailers running deploy-portal-provisioned
> deployments, support engineers.
>
> **Owner.** Platform engineering team.

This document pins the mid-flight failure cleanup and explicit
"Clean up now" / "Delete this deployment" contracts for the deploy-portal,
per **Issue #1033 / Issue #1036 / Epic #1039**.

## TL;DR

- Mid-flight failure auto-cleans the partially-provisioned slot
  (ARM `mode: Incremental` + `onErrorDeployment.type: SpecificDeployment`).
- "Clean up now" is the **PRIMARY action** in the track view, even on a
  successful deployment.
- "Delete this deployment" requires **type-the-RG confirmation** so it
  cannot be triggered accidentally.
- Cleanup audit records are retained for **30 days**, then purged.

## ARM-side contract

Every deployment kicked off by the deploy-portal API uses:

```json
{
  "properties": {
    "mode": "Incremental",
    "onErrorDeployment": {
      "type": "SpecificDeployment",
      "deploymentName": "previous-known-good-baseline"
    },
    "template": { ... },
    "parameters": { ... }
  }
}
```

If the deployment fails partway through, ARM rolls back to the named
previous deployment. For first-time deployments (no previous baseline)
the cleanup logic deletes the orphaned resources via a follow-up
`Delete on RG` call, scoped to the resource group the user named in the
configure step.

## Track-view actions

The `/deploy/track/[id]` page surfaces **two actions** unconditionally:

| Action | Behaviour |
|--------|-----------|
| **Clean up now** (primary) | Deletes everything provisioned by the current deployment in the customer's resource group. Idempotent. |
| **Delete this deployment** (secondary) | Deletes the resource group itself. Requires the user to type the RG name into a confirmation field. |

The actions are present even on a healthy deployment so the user always
has an unambiguous exit. Hidden cleanup buttons would be a footgun.

### Type-the-RG confirmation

The "Delete this deployment" action uses a confirmation dialog that
requires the user to type the resource group name verbatim before the
action submits. Case-sensitive. No autocomplete. No shortcut.

The confirmation copy:

```
Type the resource group name to delete this deployment.
This will delete every resource in the RG and is irreversible.

Resource group: rg-hph-mytest

[                              ]   ← user types here

[Cancel]   [Delete deployment]
```

The submit button stays disabled until the typed value exactly matches
the RG name.

## Cleanup audit log

Every cleanup (auto or user-initiated) writes a structured audit record:

```json
{
  "evt": "deploy.cleanup",
  "trigger": "auto-onerror" | "user-cleanup-now" | "user-delete-rg",
  "deployment_id": "<deployment id>",
  "rg": "<resource group, plaintext>",
  "sub": "sub_<sha256[0:12]>",
  "oid": "oid_<sha256[0:12]>",
  "outcome": "ok | partial | failed",
  "at": "<ISO timestamp>"
}
```

Audit records live for **30 days** in the deploy-portal's Cosmos
container (default TTL 30 days configured at the container level in
`infra/deploy-portal/modules/portal.bicep`). After 30 days, records are
purged. The platform retains no longer-term record per data-minimization
policy.

## Scenarios

### Scenario 1: Auto-cleanup on mid-flight failure

1. User clicks "Launch" on `/deploy/preflight`.
2. ARM begins deployment.
3. Resource provisioning fails at step N (e.g., quota exhaustion).
4. ARM `onErrorDeployment` rolls back to baseline.
5. Deploy-portal API writes audit record with `trigger: auto-onerror`.
6. Track-view UI surfaces the failure reason and a remediation link.
7. User can still hit "Clean up now" to nuke any orphans the rollback
   missed.

### Scenario 2: User-initiated mid-flight cleanup

1. User clicks "Clean up now" while deployment is in `provisioning` phase.
2. Deploy-portal API issues a CancelDeployment + DeleteResourceGroup
   sequence.
3. ARM cancels the in-flight deployment and removes resources created so
   far.
4. Audit record written with `trigger: user-cleanup-now`.

### Scenario 3: Delete a healthy deployment

1. User clicks "Delete this deployment" on a healthy track view.
2. Confirmation dialog requires the user to type the RG name verbatim.
3. On confirm, deploy-portal API issues `DELETE
   /subscriptions/{sub}/resourceGroups/{rg}` via the user's OBO token.
4. ARM removes the RG and everything in it.
5. Audit record written with `trigger: user-delete-rg`.

## Anti-patterns

- ❌ Don't hide the cleanup actions behind a "Settings" submenu.
- ❌ Don't delete resources outside the user-specified RG.
- ❌ Don't allow "Delete this deployment" without type-the-RG confirmation.
- ❌ Don't retain audit records longer than 30 days.
- ❌ Don't store plaintext sub IDs or emails in cleanup audit records.

## Cross-references

- [OBO contract](../security/deploy-portal-obo.md)
- [`/deploy/track/[id]`](../../apps/ui/app/(deploy)/deploy/track/[id]/page.tsx) — track view
- [`TrackPanel`](../../apps/ui/components/molecules/TrackPanel.tsx) — molecule
- Issue #1033, Issue #1036, Issue #1035

## Changelog

| Date | Change | Owner |
|------|--------|-------|
| 2025-11-04 | Initial baseline (Issue #1033 / Issue #1036 / Epic #1039) | tech-manager |
