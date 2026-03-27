# Customer Order Tracking and Logistics Enrichment

## Purpose

Use this walkthrough to inspect the current customer-facing logistics view for an order, including tracking data, ETA data, and carrier information when those enrichments are present.

## Current State Summary

| Item | Current behavior |
| --- | --- |
| Role required | `customer` |
| Primary route | `/order/{id}` |
| Main navigation access | `My Orders` from the profile dropdown |
| Working status | Implemented and working |

## Exact Click Path

1. Open the profile dropdown.
2. Click `My Orders`.
3. Click an order ID.
4. Review the order summary and the `Agent Enrichment` card.

## Step-by-step walkthrough

1. Open `/orders`.
2. Find the order you want to inspect.
3. Click the order ID link in the first column.
4. Confirm the order detail screen shows:
   - the `Order Details` heading
   - the order ID
   - the status badge
   - the ordered items table
5. Scroll to the card labeled `Agent Enrichment`.
6. Review each logistics payload block that is present:
   - `tracking`
   - `eta`
   - `carrier`
7. If a block is missing, the page leaves that section out instead of inventing placeholder data.

## What the logistics area is for

The current customer tracking experience is intentionally transparent. It shows raw enrichment payloads in formatted JSON blocks so the user or tester can confirm the backend is attaching tracking, ETA, and carrier context to the order.

## What success looks like

| Check | Expected result |
| --- | --- |
| Order open | Order details load without access error |
| Logistics data present | JSON blocks appear in `Agent Enrichment` |
| Logistics data absent | The page states `No tracking enrichment available.` or simply omits empty payloads |

## Important note

This page is both a customer tracking surface and a diagnostic surface. It is not yet a polished parcel-tracking timeline UI.
