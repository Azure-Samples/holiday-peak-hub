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
- API proxy base URL resolution now uses fallback aliases for backward compatibility:
  - `/api/*` route: `NEXT_PUBLIC_CRUD_API_URL` -> `NEXT_PUBLIC_API_URL` -> `NEXT_PUBLIC_API_BASE_URL` -> `CRUD_API_URL`.
  - `/agent-api/*` route: `NEXT_PUBLIC_AGENT_API_URL` -> `AGENT_API_URL` -> `${NEXT_PUBLIC_CRUD_API_URL}/agents` -> `${NEXT_PUBLIC_API_URL}/agents`.
  - Missing config now returns explicit HTTP 500 messages describing which env keys to set.
- UI deployment workflows now fail fast if API URL resolution is empty and set both `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_CRUD_API_URL` from the same validated source.

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

## Proxy diagnostics hardening (2026-03-06)

- Investigated frontend runtime path for `/api/products` and `/api/categories` under Next.js App Router and SWA deployment shape.
- `/api/*` proxy route (`apps/ui/app/api/[...path]/route.ts`) now returns structured `502` JSON when upstream fetch throws (DNS, timeout, connect refusal), including proxy metadata:
  - `sourceKey` used for base URL resolution.
  - `attemptedPath` requested upstream.
  - `baseUrl` used by the proxy.
- Client payload is sanitized and no longer includes raw upstream exception messages; details are logged server-side.
- `/agent-api/*` proxy route (`apps/ui/app/agent-api/[...path]/route.ts`) now has the same upstream exception handling behavior and returns structured `502` diagnostics with matching proxy metadata fields.
- Agent proxy `502` payload is likewise sanitized while preserving structured proxy context for diagnosis.
- Upstream HTTP responses are still passed through without status rewriting, so backend `4xx/5xx` failures remain visible to callers.
- Server-side API base URL resolution in `apps/ui/lib/api/client.ts` now follows the same fallback alias precedence as the `/api/*` proxy: `NEXT_PUBLIC_CRUD_API_URL` -> `NEXT_PUBLIC_API_URL` -> `CRUD_API_URL`.
- Client-side API error extraction (`apps/ui/lib/api/client.ts`) now recursively maps `detail`, `error`, `message`, `title`, and `msg` payload fields (including object-array patterns such as `detail: [{ msg: ... }]`) before falling back to Axios defaults.
- Category/product UI error states now render parsed error text plus backend status code when available:
  - `apps/ui/app/categories/page.tsx`
  - `apps/ui/app/category/CategoryPageClient.tsx`
- Added guardrail tests:
  - `apps/ui/tests/unit/apiProxyRouteEnv.test.ts`: verifies explicit `502` diagnostics on upstream fetch exceptions.
  - `apps/ui/tests/unit/agentApiProxyRouteEnv.test.ts`: verifies explicit `502` diagnostics for agent proxy upstream fetch exceptions.
  - `apps/ui/tests/unit/apiClientErrors.test.ts`: verifies payload-aware frontend error extraction.
  - `apps/ui/tests/unit/staticWebAppConfigParity.test.ts`: keeps `apps/ui/staticwebapp.config.json` and `apps/ui/public/staticwebapp.config.json` in parity to reduce SWA config drift risk.
