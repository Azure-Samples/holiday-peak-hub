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
