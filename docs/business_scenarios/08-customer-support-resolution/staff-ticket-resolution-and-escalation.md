# Staff Ticket Resolution and Escalation

## Purpose

Use this walkthrough to create support tickets, update status, assign ownership, escalate complex work, and resolve tickets from the staff console.

## Current State Summary

| Item | Current behavior |
| --- | --- |
| Role required | `staff` or `admin` |
| Primary route | `/staff/requests` |
| Main navigation access | Direct route entry is required today |
| Working status | Implemented and working |

## Before You Start

1. Sign in as `staff`.
2. If development mock login is enabled, use `/auth/login` and click `Sign in as Staff`.
3. Open `/staff/requests` directly.

## Exact Click Path

1. Open `/staff/requests`.
2. Stay on the `Tickets` tab.
3. Use `Create Ticket` to open a new request.
4. Use `Ticket Actions` to update, escalate, or resolve an existing ticket.

## Step 1: Filter the shared staff workspace

1. Confirm the page title is `Customer Requests`.
2. In the global filter box, type an ID, status, subject, or order reference if you want to narrow the lists.
3. Keep the `Tickets` tab selected for this workflow.

## Step 2: Create a ticket

1. In the `Create Ticket` card, complete:
   - `User ID *`
   - `Subject *`
   - `Priority`
   - `Description`
2. Click `Create Ticket`.
3. If you miss a required field, the screen shows validation guidance under the form.
4. On success, the newly created ticket becomes selectable in the action area.

## Step 3: Select a ticket for action

1. In `Ticket Actions`, open the `Ticket *` dropdown.
2. Select the ticket you want to work on.
3. Confirm the screen populates the current status and assignee automatically.

## Step 4: Update the ticket

1. Change `Status` if needed.
2. Change `Assignee ID` if the ticket needs to move to a different owner.
3. Optionally fill `Reason`.
4. Click `Update`.
5. Wait for the blue status text `Updating...` to disappear.

## Step 5: Escalate the ticket

1. Keep the ticket selected.
2. Enter a non-empty value in `Reason`.
3. Click `Escalate`.
4. Confirm the UI no longer shows the hint `Escalate requires a reason.`
5. Wait for the action to complete.

## Step 6: Resolve the ticket

1. Enter an optional `Resolution note`.
2. Optionally keep a `Reason` value.
3. Click `Resolve`.
4. Wait for the completion state.

## Step 7: Confirm the result in the tickets table

1. Scroll to the tickets table.
2. Locate the ticket row.
3. Confirm the row now reflects the updated status and assignee.
4. Review the table columns:
   - `Ticket`
   - `Subject`
   - `Priority`
   - `Status`
   - `Assignee`
   - `Created`

## Important scope note

The `Returns` tab on the same page belongs to the reverse-logistics workflow and should be documented using the returns scenario, not this support-ticket guide.
