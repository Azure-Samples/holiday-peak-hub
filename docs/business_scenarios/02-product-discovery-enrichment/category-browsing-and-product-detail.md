# Category Browsing and Product Detail Exploration

## Purpose

Use this walkthrough to navigate from category discovery into a product detail page and exercise the current enrichment-focused controls on that screen.

## Current State Summary

| Item | Current behavior |
| --- | --- |
| Role required | Public or signed-in customer |
| Main navigation access | `Catalog` in the top navigation |
| Primary routes | `/categories`, `/category?slug=...`, `/product/{id}` |
| Working status | Implemented and working |

## Exact Click Path

1. Click `Catalog` in the top navigation.
2. On the category view, choose a category.
3. On the category collection page, click a product card.
4. On the product page, review the enrichment panels.
5. Optionally run the fit-evaluation prompt.

## Step 1: Open the category experience

1. Click `Catalog` in the header.
2. The application routes to `/category?slug=all`.
3. If you want the category index instead, open `/categories` directly.
4. On `/categories`, confirm you see category cards with:
   - the category name
   - the category description
   - the `Agent-ready` badge
5. If you are on the categories index, click any category card.

## Step 2: Use the collection page

1. On `/category?slug=...`, confirm you can see the product listing.
2. Use the sort control to switch among options such as:
   - relevance
   - price ascending
   - price descending
   - rating
   - newest
3. Switch between grid view and list view if needed.
4. Click any product card title or image.

## Step 3: Review the product page layout

1. Confirm the product page shows:
   - breadcrumb navigation
   - category buttons on the left side
   - large product image
   - `Agent Enriched` badge
   - stock badge
   - title, description, and price
2. If available, confirm the `Enriched description` card appears.
3. Review the enrichment-oriented rails:
   - `UseCaseTags`
   - `Complements`
   - `Alternatives`

## Step 4: Run the fit evaluation flow

1. Click `Does this fits my case?`.
2. Confirm a prompt card opens with the label `Describe your use case`.
3. Enter a concrete scenario, for example: `I need this for business travel and long battery life.`
4. Click `Evaluate fit`.
5. Wait for the response card named `Use case evaluation`.
6. Review the returned blocks:
   - verdict badge such as `Fits`, `Partially fits`, or `Does not fit`
   - confidence
   - recommendation
   - `Why it fits`
   - `Possible constraints`
7. Read the compact `AgentMessageDisplay` block at the bottom of the card.

## Step 5: Use the visible enrichment trigger button carefully

1. The product page currently exposes a `Trigger enrichment job` button.
2. This is an operational control, not a normal customer-shopping control.
3. Click it only if you are intentionally testing the enrichment pipeline.
4. If the request succeeds, the page shows a message similar to `Queued at ...`.

## Important caveat about cart behavior

The product page displays an `Add to Cart` button, but in the current UI that button only tracks the click and does not populate the cart. Do not use that button as proof of a fully wired cart flow.

## Success checklist

| Check | Expected result |
| --- | --- |
| Category discovery | Category cards or full catalog collection render |
| Product open | Product detail page loads without backend error |
| Enrichment content | Use-case tags and related rails are visible when data exists |
| Fit prompt | Use case evaluation renders after submission |
| Trigger button | Optional queue confirmation appears if pipeline trigger succeeds |
