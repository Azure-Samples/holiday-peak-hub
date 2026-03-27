# Checkout Inventory Signals and Reservation Protection

## Purpose

Use this walkthrough to verify the inventory-assistance portion of checkout: health signals, reservation creation, reservation outcomes, and safe fallback behavior when helper services are unavailable.

## Current State Summary

| Item | Current behavior |
| --- | --- |
| Role required | `customer` |
| Entry point | `/checkout` with a non-empty cart |
| Main UI location | Right-side order summary card in checkout |
| Working status | Implemented and working |

## Before You Start

1. Sign in as a customer.
2. Open checkout with items already present in the cart.
3. Reach the checkout page and advance to the payment step.

## Exact Click Path

1. Open checkout.
2. Complete the shipping form.
3. Click `Continue to Payment`.
4. Review the `Scenario 04 Signals` section in the order summary.
5. If needed, use the retry buttons or `Continue without live signals`.
6. Complete payment and confirm the order redirect.

## What this section is proving

The `Scenario 04 Signals` block is the customer-visible evidence that checkout is consulting the inventory helper surfaces while still allowing the transaction to continue when those helpers are temporarily unavailable.

## What to look for in the `Scenario 04 Signals` block

1. `Health: X healthy • Y low • Z out`
2. `Threshold breaches`
3. `Replenishment triggers`
4. A `Reservation outcomes` subsection

## Normal path walkthrough

1. Complete Step 1 of checkout.
2. Click `Continue to Payment`.
3. Wait for the payment step to load.
4. In the right-side summary, verify the helper block is visible.
5. If the health call succeeds, confirm you see live counts for healthy, low, and out-of-stock products.
6. If reservations have already been created for the checkout attempt, confirm the reservation outcome area lists lines such as `SKU: created`.
7. Complete payment.
8. After finalization, reservations should move from temporary holds into confirmed holds behind the scenes.

## Unavailable-helper fallback walkthrough

1. If helper endpoints are unavailable, the block will show a red warning message.
2. Read the guidance before clicking anything.
3. Use `Retry signal checks` first.
4. If the warning persists and you still want to continue the demo, click `Continue without live signals`.
5. Confirm the status text changes to `Continuing without live assistant signals. Checkout remains available.`
6. Proceed with payment only after you confirm this fallback message is visible.

## Reservation-specific troubleshooting buttons

Use these buttons only when the checkout sidebar presents them:

1. `Retry health check`
   - Use when the inventory health call failed.
2. `Retry reservation outcomes`
   - Use when reservation state lookup failed.
3. `Retry signal checks`
   - Use when you want to refresh both helper areas together.

## What the reservation messages mean

| Message type | Meaning |
| --- | --- |
| `No reservation outcomes yet` | You have not created item holds yet for the current checkout attempt. |
| `SKU: created` | A hold exists, but payment is not finalized yet. |
| `SKU: confirmed` | Payment completed and the reservation was finalized. |
| `SKU: released` | The hold was rolled back or the checkout attempt was abandoned. |

## Expected success signals

| Check | Expected result |
| --- | --- |
| Payment step opens | Checkout setup completed successfully |
| Sidebar helper block appears | Inventory helper UI is active |
| Retry path exists | The page remains resilient when helper data is unavailable |
| Successful completion | Checkout redirects to the order detail page |

## Scope Boundary

This walkthrough documents the customer-visible inventory controls inside checkout. Staff-side replenishment or warehouse action screens are not part of the current customer UI.
