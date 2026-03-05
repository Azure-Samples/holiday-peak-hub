# UI CRUD Route Alignment (2026-03-01)

## What was fixed

- Replaced static storefront rendering with live backend data for homepage, category, product, and search pages.
- Added missing internal routes so navigation links resolve correctly:
  - `/shop` → catalog
  - `/deals` → search shortcut
  - `/orders` → CRUD orders table
  - `/cart` → CRUD cart table
  - `/wishlist` → live catalog-based list
  - `/agents/product-enrichment-chat` → direct agent chat UI
- Replaced mock staff screens with CRUD-backed consulting tables:
  - `/staff/requests` (tickets + returns)
  - `/staff/logistics` (shipments)
  - `/staff/sales` (analytics summary)

## Backend endpoint mapping now used by UI

- `GET /api/products`
- `GET /api/products/{id}`
- `GET /api/categories`
- `GET /api/cart`
- `DELETE /api/cart/items/{product_id}`
- `DELETE /api/cart`
- `GET /api/orders`
- `GET /api/orders/{id}`
- `GET /api/staff/tickets`
- `GET /api/staff/returns`
- `GET /api/staff/shipments`
- `GET /api/staff/analytics/summary`
- `POST /agents/ecommerce-product-detail-enrichment/invoke`

## Notes

- Wishlist persistence is still not exposed by current CRUD endpoints; the page now clearly communicates this and stays functional.
- Staff routes require staff authorization from backend auth policy.
- Added a Next.js server route proxy at `/api/*` (`apps/ui/app/api/[...path]/route.ts`) so SWA calls forward to `${NEXT_PUBLIC_CRUD_API_URL}/api/*` consistently in production.
- Browser-side API clients now use same-origin routes (`/api/*` and `/agent-api/*`) to avoid APIM CORS failures from the SWA origin.

## Entra provisioning update (2026-03-02)

- `azd` `postprovision` now runs `.infra/azd/hooks/ensure-entra-ui-app.ps1` / `.infra/azd/hooks/ensure-entra-ui-app.sh` before model deployment.
- The hook creates or updates a single-tenant Entra app registration for UI login and sets these azd env values automatically:
  - `NEXT_PUBLIC_ENTRA_CLIENT_ID`
  - `NEXT_PUBLIC_ENTRA_TENANT_ID`
  - `ENTRA_CLIENT_ID`
  - `ENTRA_TENANT_ID`
- Redirect URIs are maintained idempotently and include local development (`http://localhost:3000` and `/auth/callback`) plus SWA callback URLs when `staticWebAppDefaultHostname` is available.
- CRUD env generation hooks now source `ENTRA_TENANT_ID` and `ENTRA_CLIENT_ID` from azd env values instead of leaving them blank.

## UI showcase redesign update (2026-03-05)

- Updated the core storefront showcase experience to be mobile-first while keeping desktop demo quality and existing route contracts.
- Kept route compatibility intact for:
  - `/`
  - `/category?slug=...`
  - `/product?id=...`
  - `/agents/product-enrichment-chat`
- Introduced an explicit two-layer interaction model in UI copy and CTAs:
  - `Catalog Layer`: factual product/category browsing through CRUD-backed catalog data.
  - `Agent Layer`: interpretation/enrichment via Product Enrichment Chat.
- Refreshed visual system in `apps/ui/app/globals.css` with new design tokens:
  - Warm retail palette with strong contrast and semantic tokens (`--hp-*`).
  - Showcase shell/card primitives for consistent composition.
  - Reduced-motion safeguards and consistent focus-visible treatment.
- Updated the main UX surfaces:
  - `apps/ui/components/organisms/Navigation.tsx`
  - `apps/ui/components/organisms/HeroSlider.tsx`
  - `apps/ui/components/organisms/ProductGrid.tsx`
  - `apps/ui/components/molecules/ProductCard.tsx`
  - `apps/ui/components/organisms/ChatWidget.tsx`
  - `apps/ui/components/templates/MainLayout.tsx`
  - `apps/ui/app/page.tsx`
  - `apps/ui/app/category/CategoryPageClient.tsx`
- Accessibility and semantics improvements included:
  - Skip link to `#main-content`.
  - Better landmark usage and aria labeling for interactive regions.
  - Product lists/cards marked for assistive technology context.

### Validation snapshot

- Frontend diagnostics: no editor errors in redesigned files.
- `yarn --cwd apps/ui test --watch=false`: all 5 test suites pass (69 tests total) after adding test harness mocks for Stripe + `matchMedia` and aligning smoke-test hook mocks.
- `yarn --cwd apps/ui type-check`: still reports existing baseline typing issues in legacy component files outside this showcase redesign scope.
