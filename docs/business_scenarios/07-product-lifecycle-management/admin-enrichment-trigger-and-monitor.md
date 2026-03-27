# Admin Enrichment Trigger and Monitor

## Purpose

Use this walkthrough to manually queue product enrichment, monitor pipeline activity, and inspect an individual enrichment record.

## Current State Summary

| Item | Current behavior |
| --- | --- |
| Role required | `admin` |
| Main navigation access | `Admin` in the top navigation |
| Primary routes | `/admin`, `/admin/ecommerce/products`, `/admin/enrichment-monitor`, `/admin/enrichment-monitor/{entityId}` |
| Working status | Implemented and working |

## Exact Click Path

1. Click `Admin` in the main navigation.
2. In `E-Commerce Services`, click `Product Enrichment`.
3. Select a product and click `Trigger enrichment`.
4. Return to `Admin` and click `Enrichment Monitor`.
5. Click an entity ID in the active jobs table.

## Step 1: Queue an enrichment job

1. Open `/admin`.
2. In the `E-Commerce Services` section, click `Product Enrichment`.
3. Confirm the page title ends with `Products Service`.
4. In the trigger card, find:
   - the `Product ID` selector
   - the `Trigger enrichment` button
5. Pick a product from the dropdown.
6. Click `Trigger enrichment`.
7. Wait for the green confirmation message `Queued at ...`.

## Step 2: Review the service dashboard

1. Stay on the same screen for a moment.
2. Review the service status cards.
3. Review the `Activity` table.
4. Review the `Model usage` table.
5. Use the `Time range` selector if you want to narrow the window.
6. Use `Refresh` if you want to force an update after the trigger call.

## Step 3: Monitor the enrichment pipeline

1. Return to `/admin`.
2. Click `Enrichment Monitor`.
3. On the dashboard, confirm the top area shows:
   - status cards
   - `Active jobs`
   - `Throughput`
   - `Error log`
4. If the active-jobs table contains your entity, click the entity ID.

## Step 4: Inspect a specific entity

1. On `/admin/enrichment-monitor/{entityId}`, review the header for:
   - title
   - entity ID
   - pipeline status badge
   - confidence percentage
2. Use the quick-action buttons as needed:
   - `Open HITL queue`
   - `Review this entity`
   - `Quick approve`
   - `Quick reject`
3. Scroll down and inspect:
   - `Attribute differences`
   - image evidence
   - reasoning panel
4. Use `Related Trace` if you want to jump into agent observability.

## Success checklist

| Check | Expected result |
| --- | --- |
| Trigger action | `Queued at ...` confirmation appears |
| Monitor page | Active jobs and status cards render |
| Detail page | Attribute diffs, evidence, and reasoning are visible |

## Scope Boundary

This guide is about operational control and monitoring. Human review decisioning is documented separately.
