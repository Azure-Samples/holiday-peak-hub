# Staff Logistics Tracking Console

## Purpose

Use this walkthrough to operate the current staff shipment-monitoring screen.

## Current State Summary

| Item | Current behavior |
| --- | --- |
| Role required | `staff` or `admin` |
| Primary route | `/staff/logistics` |
| Main navigation access | No direct main-navbar link today |
| Recommended access method | Open the route directly after signing in as staff |
| Working status | Implemented and working |

## Before You Start

1. Sign in as `staff`.
2. If development mock login is enabled, open `/auth/login` and click `Sign in as Staff`.
3. Open `/staff/logistics` directly in the browser.

## Exact Workflow

1. Load `/staff/logistics`.
2. Wait for the shipment table to populate.
3. Use the filter box to narrow the list.
4. Review shipment status across the visible columns.

## Step-by-step walkthrough

1. Confirm the page header shows `Logistics Tracking`.
2. Click inside the filter field with the placeholder `Filter by shipment id, order id, tracking number or status`.
3. Type one search term at a time, for example:
   - a shipment ID
   - an order ID
   - a carrier tracking number
   - a status such as `in_transit`
4. Watch the table update live without a submit button.
5. Review these columns:
   - `Shipment`
   - `Order`
   - `Carrier`
   - `Tracking`
   - `Status`
   - `Created`

## What success looks like

| Check | Expected result |
| --- | --- |
| Page load | Shipment table renders |
| Filtering | Rows update as you type |
| Data quality | IDs, carrier, tracking number, status, and timestamps are visible |

## Current limitation

This screen is a monitoring table only. It does not expose shipment editing or exception resolution controls yet.
