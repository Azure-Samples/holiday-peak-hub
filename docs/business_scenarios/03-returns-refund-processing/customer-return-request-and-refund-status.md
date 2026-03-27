# Customer Return Request and Refund Status

## Purpose

Use this walkthrough when you want to create a return from the customer surface and then follow the lifecycle through the order and orders pages.

## Current State Summary

| Item | Current behavior |
| --- | --- |
| Role required | `customer` |
| Main navigation access | Order access is available from the profile dropdown under `My Orders` |
| Primary routes | `/orders`, `/order/{id}` |
| Working status | Implemented and working |

## Exact Click Path

1. Open the profile dropdown.
2. Click `My Orders`.
3. Choose an order.
4. Click `Request Return` on the orders page, or submit the `Create Return` form on the order detail page.
5. Revisit the same order and monitor the lifecycle table until staff completes the next steps.

## Path A: Request a return from the orders list

1. Open `/orders`.
2. Use `Filter by order id or status` if you need to narrow the list.
3. Locate the target order row.
4. Click `Request Return`.
5. Wait for the inline feedback under the button.
6. A successful request shows a message like `Return {id} created with status requested.`
7. If a return is already active, the row shows `Return lifecycle in progress: ...` and the button is disabled.

## Path B: Request a return from the order detail page

1. On `/orders`, click the order ID link.
2. On `/order/{id}`, scroll to the `Create Return` card.
3. Read the lifecycle note explaining the sequence:
   - requested
   - approved or rejected
   - received
   - restocked
   - refunded
4. In `Reason for return`, enter a customer-friendly reason.
5. Click `Create Return`.
6. Wait for one of these messages:
   - success: `Return request created. Staff review SLA target is 24 hours.`
   - failure: `Return could not be created. Verify order ownership and lifecycle constraints.`

## How to read return status on the order page

1. Stay on `/order/{id}`.
2. Scroll to `Returns for this order`.
3. Review the table columns:
   - `Return`
   - `Status`
   - `Refund`
   - `Requested`
   - `Approved`
   - `Received`
   - `Restocked`
   - `Refunded`
4. Read the status detail text under the lifecycle state.
5. Read the refund detail text under the refund column.

## What each lifecycle state means in the current UI

| Status | What the customer should understand |
| --- | --- |
| `requested` | The return was submitted and is waiting for staff review. |
| `approved` | Staff approved the return and is waiting for the item to be received. |
| `received` | The item was received and is waiting for warehouse verification. |
| `restocked` | The item is back in stock and refund processing can proceed. |
| `refunded` | The money was issued back to the original payment method. |
| `rejected` | The request was closed without refund eligibility. |

## How to verify the same request from the orders list

1. Go back to `/orders`.
2. Find the same order.
3. Confirm the return area now shows the active lifecycle state.
4. Use this page when you want the quick portfolio view of all orders, not the detailed timestamp history.

## Success checklist

| Check | Expected result |
| --- | --- |
| Orders page | `Request Return` button is available for eligible orders |
| Order detail page | `Create Return` form accepts a reason |
| Success state | A new return record appears in the returns table |
| Lifecycle tracking | Timestamp columns fill in as staff transitions the return |

## Scope Boundary

Customer pages do not move the lifecycle beyond the initial request. Staff users must perform approval, receipt, restock, and refund transitions.
