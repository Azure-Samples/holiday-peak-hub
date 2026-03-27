# Customer Cart, Checkout, and Order Confirmation

## Purpose

Use this walkthrough when you want to validate the current customer checkout experience from cart review through order confirmation.

## Current State Summary

| Item | Current behavior |
| --- | --- |
| Role required | `customer` |
| Recommended entry point | `/cart` |
| Main navigation access | Cart icon in the top-right header |
| Checkout status | Implemented and working |
| Important limitation | The current storefront `Add to Cart` buttons are not wired to the cart mutation yet. Start this walkthrough with a cart that already contains items. |

## Before You Start

1. Sign in as a customer.
2. If development mock login is enabled, open `/auth/login` and click `Sign in as Customer`.
3. Make sure the cart already contains at least one item. If it is empty, this walkthrough cannot continue from the UI alone.

## Exact Click Path

1. Click the cart icon in the header.
2. On the `Cart` page, review the items table.
3. Click `Proceed to checkout`.
4. Complete the `Shipping Information` form.
5. Click `Continue to Payment`.
6. Choose a shipping method.
7. Complete the Stripe payment form.
8. Click `Pay & Place Order`.
9. Wait for the redirect to the order details page.

## Screen-by-Screen Walkthrough

### Step 1: Open the cart

1. Look at the header in the top-right area.
2. Click the cart icon.
3. Confirm you are on the `Cart` page.
4. Verify the page shows a table with these columns:
   - `Product`
   - `Quantity`
   - `Unit Price`
   - `Line Total`
   - `Actions`

### Step 2: Review or clean up the cart

1. If you want to remove one item, click `Remove` on that row.
2. If you want to empty the entire cart, click `Clear cart` in the page header.
3. Confirm the summary card at the bottom shows the `Total` value.
4. If the cart is empty, stop here and load cart data before testing checkout.

### Step 3: Enter shipping information

1. Click `Proceed to checkout`.
2. On the checkout screen, stay on `Step 1` with the title `Shipping Information`.
3. Fill in every required field exactly once:
   - `First Name (Required)`
   - `Last Name (Required)`
   - `Email Address (Required)`
   - `Phone Number (Required)`
   - `Street Address (Required)`
   - `City (Required)`
   - `State (Required)`
   - `ZIP Code (Required)`
4. Optionally enable `Save this address for future orders (Optional)`.
5. If you intentionally leave a field blank, the screen should show a red validation message directly under that field.
6. Click `Continue to Payment`.

## What should happen after shipping submission

1. The UI validates the form.
2. The UI validates checkout readiness.
3. The UI creates inventory reservations for the current cart items.
4. The UI creates the order record.
5. The UI creates a Stripe payment intent.
6. The page advances to the payment step.

If anything in that sequence fails before the order is created, the page should show a visible setup error message and keep you on the same screen.

## Step 4: Review shipping method and order summary

1. After the page advances, confirm you now see two cards in the main content area:
   - `Shipping Method`
   - `Payment Information`
2. In `Shipping Method`, choose one option:
   - `Standard Shipping`
   - `Express Shipping`
   - `Overnight Shipping`
3. Watch the order summary on the right side.
4. Confirm the summary updates these values:
   - `Subtotal`
   - `Shipping`
   - `Tax`
   - `Total`

## Step 5: Use the inventory signals block

1. In the order summary card, scroll to the section named `Scenario 04 Signals`.
2. Review the helper information shown there:
   - `Health`
   - `Threshold breaches`
   - `Replenishment triggers`
   - `Reservation outcomes`
3. If the helper services are temporarily unavailable, the page may show buttons such as:
   - `Retry signal checks`
   - `Continue without live signals`
   - `Retry health check`
   - `Retry reservation outcomes`
4. Use `Continue without live signals` only when you want to continue the demo despite unavailable helper telemetry.

## Step 6: Complete payment

1. Move to the `Payment Information` card.
2. Complete the Stripe payment element.
3. Click `Pay & Place Order`.
4. If the provider authorizes payment but final order completion fails, the screen may show `Retry Finalization`.
5. If that button appears, click it once and wait for the result.

## Step 7: Confirm the order was finalized

1. After a successful payment and reservation confirmation, the UI redirects to `/order/{id}`.
2. On the order detail screen, confirm you can see:
   - the order ID
   - the order status badge
   - the ordered item table
   - the total amount
3. Treat that redirect as the success state for this workflow.

## Expected Success Signals

| Check | Expected result |
| --- | --- |
| Cart page | Items and totals render without error |
| Shipping form | Required-field validation appears inline |
| Payment step | Shipping method selector and Stripe payment element appear |
| Finalization | Browser redirects to `/order/{id}` |
| Order page | Order metadata and items are visible |

## Troubleshooting

| Symptom | What it means right now |
| --- | --- |
| `Your cart is empty` | The checkout UI is working, but the storefront does not yet populate the cart from product cards. |
| `Cart could not be loaded` | Authentication or CRUD connectivity is failing. |
| `Payments are currently unavailable` | `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` or payment backend configuration is missing. |
| `Payment intent is not available` | Checkout setup failed before Stripe payment could be initialized. Go back to shipping and retry. |

## Scope Boundary

This walkthrough documents the current working checkout surface. It does not claim that cart population is fully user-drivable from the catalog UI yet.
