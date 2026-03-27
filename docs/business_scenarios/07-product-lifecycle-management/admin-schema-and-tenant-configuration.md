# Admin Schema and Tenant Configuration

## Purpose

Use this walkthrough to manage the Product Truth Layer governance screens that are currently implemented but not linked from the main admin landing page.

## Current State Summary

| Item | Current behavior |
| --- | --- |
| Role required | `admin` |
| Primary routes | `/admin/schemas`, `/admin/config` |
| Main navigation access | Direct route entry is required today |
| Working status | Implemented and working |

## Important note about navigation

These screens exist and work, but they are not exposed as tiles on the main admin portal yet. Open them directly in the browser after signing in as admin.

## Workflow A: Manage schemas on `/admin/schemas`

1. Open `/admin/schemas`.
2. Confirm the page title is `Schema Management`.
3. To create a schema, click `+ New Schema`.
4. Complete the top-level fields:
   - `Category`
   - `Version`
5. Click `+ Add Field` for each schema field you need.
6. For each field row, complete:
   - `Field name`
   - type selector
   - `Description (optional)`
   - `Required` checkbox if needed
7. Click `Save Schema`.
8. To edit an existing schema, click `Edit` on that schema card.
9. To delete a schema, click `Delete` and confirm the browser prompt.

## Workflow B: Manage tenant configuration on `/admin/config`

1. Open `/admin/config`.
2. Confirm the page title is `Tenant Configuration`.
3. Review or update `Auto-Approve Threshold (0–1)`.
4. Review the toggle section and set each one intentionally:
   - `Enrichment Enabled`
   - `HITL Review Enabled`
   - `PIM Writeback Enabled`
   - `Writeback Dry Run` when writeback is enabled
5. Review the `Feature Flags` section.
6. To add a new flag:
   - enter the flag key
   - click `Add Flag`
7. To toggle an existing flag, click its checkbox.
8. To remove an existing flag, click `Remove`.
9. Click `Save Configuration`.
10. Confirm the success banner `Configuration saved successfully.` appears.

## Success checklist

| Check | Expected result |
| --- | --- |
| Schema creation | New schema card appears after save |
| Schema edit | Existing schema reflects updated fields |
| Config save | Success banner appears |
| Feature flags | Added, toggled, and removed flags persist after save |
