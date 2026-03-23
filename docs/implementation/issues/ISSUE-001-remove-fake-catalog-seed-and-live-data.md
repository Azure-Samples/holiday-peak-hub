# ISSUE-001 — Remove fake catalog seed and live data

## Problem

Live demo catalog contains unrealistic placeholder categories and products (for example: `Purpose Brother`, `Performance Knowledge`, `Offer Kind`) that degrade credibility.

## Scope

- Remove fake categories and associated products from live data.
- Ensure seed path cannot reintroduce those fake entities.
- Keep curated catalog categories/products only.

## Acceptance Criteria

- [ ] Live endpoint `/api/categories` no longer returns fake category names.
- [ ] Products tied to removed fake categories are no longer returned by `/api/products`.
- [x] `apps/crud-service/src/crud_service/scripts/seed_demo_data.py` includes cleanup logic for those fake categories/products.
- [x] Cleanup is idempotent and safe for repeated executions.

## Validation

- Query `https://blue-meadow-00fcb8810.4.azurestaticapps.net/api/categories` and confirm absence of fake names.
- Query `https://blue-meadow-00fcb8810.4.azurestaticapps.net/api/products?limit=300` and confirm no products belong to removed fake category IDs.

## Implementation Notes

- Added a pre-seed purge in `seed_demo_data.py` that removes:
  - Legacy seeded categories not in curated category IDs.
  - Known fake category names (e.g., `Purpose Brother`, `Offer Kind`).
  - Seeded products tied to non-curated/fake categories (plus legacy `demo-prd-*` records).
- Added unit tests in `apps/crud-service/tests/unit/test_seed_demo_data.py` to verify:
  - Affected-row parsing from SQL command status.
  - Cleanup targeting behavior.
  - Idempotent behavior when no rows match.
