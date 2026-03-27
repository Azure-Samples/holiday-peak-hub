# Staff HITL Review and Decisioning

## Purpose

Use this walkthrough to review AI-proposed product changes, approve or reject them, edit proposed values, and inspect audit history.

## Current State Summary

| Item | Current behavior |
| --- | --- |
| Role required | `staff` or `admin` |
| Primary routes | `/staff/review`, `/staff/review/{entityId}` |
| Main navigation access | Best entry point is from `Enrichment Monitor` or direct URL |
| Working status | Implemented and working |

## Exact Click Path

1. Open `Enrichment Monitor` and click `Open HITL review queue`, or go directly to `/staff/review`.
2. Filter or sort the queue.
3. Click `Review` on the target row.
4. Approve, edit, or reject the proposed attributes.

## Step 1: Work the review queue

1. Open `/staff/review`.
2. Confirm the page title is `AI Review Queue`.
3. Review the summary cards:
   - `Pending`
   - `Approved Today`
   - `Rejected Today`
   - `Avg Confidence`
4. Use any of the filters:
   - `Filter by category`
   - `Min confidence (0–1)`
   - `Max confidence (0–1)`
   - `Filter by source`
5. Use the `Sort by` dropdown above the table.
6. In the table, review these columns:
   - `Product`
   - `Category`
   - `Field`
   - `Proposed Value`
   - `Confidence`
   - `Source`
   - `Proposed At`
   - `Action`
7. Click `Review` for the entity you want.

## Step 2: Review a single entity

1. Confirm the detail screen shows the product image, title, category, and entity ID.
2. Review the completeness bar.
3. In the right-side `Bulk Actions` card, note the buttons:
   - `Approve All`
   - `Reject All`
   - `Back to Queue`
4. Scroll to `Proposed Attributes`.

## Step 3: Decide proposal by proposal

For each proposal card:

1. Compare `Original value` with `Enriched value`.
2. Review confidence and source badges.
3. Read any intent, reasoning, and evidence sections.
4. Choose one action:
   - `Approve`
   - `Edit`
   - `Reject`
5. If you choose `Edit`, change the text in `Edited value` and click `Save Edit`.
6. If you choose `Reject`, enter a `Rejection reason` and click `Confirm Reject`.

## Step 4: Validate the audit trail

1. Scroll to `Audit History`.
2. Confirm the timeline reflects the actions you just took.
3. Use this section as the final verification point that the review action persisted.

## Success checklist

| Check | Expected result |
| --- | --- |
| Queue page | Filters, stats, and rows all render |
| Review page | Proposed attributes and audit history are visible |
| Approve/Edit/Reject | Action controls update proposal state |
| Audit history | New review decisions appear in the timeline |
