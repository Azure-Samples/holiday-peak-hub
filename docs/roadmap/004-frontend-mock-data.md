# 004: Frontend Pages Use Mock/Hardcoded Data

**Severity**: High  
**Category**: Frontend  
**Discovered**: February 2026

## Summary

10 of 11 frontend pages use hardcoded mock data instead of calling the backend API through the TypeScript service/hook layer. The API integration layer (services + React Query hooks) is fully implemented but not wired into the page components.

## Affected Pages

| Page | Route | Status | Notes |
|------|-------|--------|-------|
| Homepage | `/` | ❌ Mock data | Uses inline `featuredProducts` array |
| Category | `/category/[slug]` | ❌ Mock data | Hardcoded product list |
| Product Detail | `/product/[id]` | ❌ Mock data | Static product object |
| Reviews | `/product/[id]/reviews` | ❌ Mock data | Inline review array |
| Checkout | `/checkout` | ❌ Mock data | Hardcoded cart items |
| Order Tracking | `/my-orders` | ❌ Mock data | Static order list |
| Dashboard | `/dashboard` | ❌ Mock data | Inline metrics |
| Profile | `/profile` | ❌ Mock data | Static user object |
| Staff Sales | `/staff/sales` | ❌ Mock data | Hardcoded analytics |
| Staff Requests | `/staff/requests` | ❌ Mock data | Static ticket list |
| Staff Shippings | `/staff/shippings` | ⚠️ Partial | Some API integration |

## Available Integration Layer (Unused)

These are implemented and tested but not imported by page components:

- `lib/services/productService.ts` → `useProducts()`, `useProduct(id)`
- `lib/services/cartService.ts` → `useCart()`
- `lib/services/orderService.ts` → `useOrders()`, `useOrder(id)`, `useTrackOrder(id)`
- `lib/services/authService.ts` → used by AuthContext only
- `lib/services/userService.ts` → `useUser()`
- `lib/services/checkoutService.ts` → `useCheckout()`

## Suggested Fix

For each page:
1. Remove hardcoded data arrays
2. Import the corresponding React Query hook
3. Add loading/error states using hook status
4. Add Suspense boundaries or loading skeletons

## Priority Order

1. Homepage (`/`) — highest traffic
2. Product Detail (`/product/[id]`) — critical for cart conversion
3. Category (`/category/[slug]`) — browsing flow
4. Checkout (`/checkout`) — revenue path
5. Remaining pages in order of user impact

## Files to Modify

- `apps/ui/app/page.tsx`
- `apps/ui/app/category/[slug]/page.tsx`
- `apps/ui/app/product/[id]/page.tsx`
- `apps/ui/app/product/[id]/reviews/page.tsx`
- `apps/ui/app/checkout/page.tsx`
- `apps/ui/app/my-orders/page.tsx`
- `apps/ui/app/dashboard/page.tsx`
- `apps/ui/app/profile/page.tsx`
- `apps/ui/app/staff/sales/page.tsx`
- `apps/ui/app/staff/requests/page.tsx`
