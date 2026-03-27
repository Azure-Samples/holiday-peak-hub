# Customer Dashboard Personalization

## Purpose

Use this walkthrough to validate the current dashboard experience, especially the live recommendation flow that combines customer profile, product, pricing, ranking, and compose endpoints.

## Current State Summary

| Item | Current behavior |
| --- | --- |
| Role required | `customer` |
| Main navigation access | `Dashboard` in the top navigation |
| Primary route | `/dashboard` |
| Working status | Implemented and working |

## Exact Click Path

1. Sign in as a customer.
2. Click `Dashboard` in the top navigation.
3. Review recent orders.
4. Use the `Recommended for You` card.
5. Optionally refresh recommendations with a different customer ID and SKU.

## Step-by-step walkthrough

1. Open `/dashboard`.
2. Confirm the page header says `My Dashboard`.
3. Review the four stat cards at the top.
4. Note the current behavior of those cards:
   - `Total Orders` is live
   - `Wishlist Items` shows `Unavailable`
   - `Saved Addresses` shows `Unavailable`
   - `Rewards Points` shows `Unavailable`
5. In `Recent Orders`, click `View All` if you want to move to the orders portfolio.
6. Move to the `Recommended for You` card.
7. Confirm the explanatory text says this flow uses catalog, profile, pricing, ranking, and compose endpoints.

## How to run the personalization flow

1. Look for the two input fields above the button row:
   - `Customer ID`
   - `Product SKU`
2. If the page seeded those fields automatically from recent order history, keep the values.
3. If the fields are empty, enter a valid customer ID and product SKU.
4. Click `Refresh Recommendations`.
5. Wait for the results grid to populate.
6. If pricing data is returned, confirm the `Offer preview` line appears.
7. Review the personalized recommendation cards shown below.

## How to interpret the current status messages

| Status | Meaning |
| --- | --- |
| `Loading personalized recommendations.` | The orchestration call is still running. |
| `Showing X personalized recommendation(s).` | The request succeeded and returned results. |
| `No recommendations available for this customer and SKU.` | The flow completed successfully but returned no ranked items. |
| Error message with backend status | The request failed and exposed the API error state. |

## Quick actions area

The right-side `Quick Actions` card gives you fast links to:

1. `View All Orders`
2. `Edit Profile`
3. `My Wishlist`
4. `Browse Categories`

## Current limitations you should document honestly

1. Rewards progress is not backed by a live contract yet.
2. Saved addresses are not backed by a live contract yet.
3. Wishlist persistence is not backed by a live contract yet.
4. The page correctly shows unavailable states instead of fabricated values.
