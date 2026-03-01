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
