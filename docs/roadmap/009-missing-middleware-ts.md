# 009: No middleware.ts for Route Protection

**Severity**: Medium  
**Category**: Frontend  
**Discovered**: February 2026

## Summary

The Next.js frontend lacks a `middleware.ts` file for server-side route protection. All route guarding relies on client-side checks in the `AuthContext`, which means protected pages briefly render before redirecting unauthenticated users.

## Current State

- No `apps/ui/middleware.ts` file exists
- Auth checks happen in `AuthContext.tsx` (client-side only)
- Protected pages flash their content before redirect
- No server-side token validation on page requests
- Staff and admin pages are accessible to any client that renders the URL

## Expected Behavior

- `middleware.ts` should intercept requests to protected routes before rendering
- Unauthenticated users should be redirected to login without seeing the page
- Role-based middleware should enforce:
  - `/dashboard`, `/profile`, `/checkout`, `/my-orders` → require `customer` role
  - `/staff/*` → require `staff` role
  - `/admin` → require `admin` role
- Public routes (`/`, `/category/*`, `/product/*`) should pass through

## Suggested Fix

1. Create `apps/ui/middleware.ts` with Next.js middleware API
2. Check for auth token in cookies/headers
3. Validate token claims (role) against route requirements
4. Redirect to `/login` (or `/`) if unauthorized
5. Configure `matcher` to only run on protected routes

```typescript
// apps/ui/middleware.ts
import { NextRequest, NextResponse } from 'next/server';

export function middleware(request: NextRequest) {
  const token = request.cookies.get('auth-token')?.value;
  // Validate and check roles...
}

export const config = {
  matcher: ['/dashboard/:path*', '/profile/:path*', '/checkout/:path*',
            '/my-orders/:path*', '/staff/:path*', '/admin/:path*'],
};
```

## Files to Create

- `apps/ui/middleware.ts` — Route protection middleware

## Files to Modify

- `apps/ui/contexts/AuthContext.tsx` — Remove redundant client-side redirects (keep as fallback)

## References

- [ADR-019](../architecture/adrs/adr-019-authentication-rbac.md) — Authentication & RBAC
- [Next.js Middleware docs](https://nextjs.org/docs/app/building-your-application/routing/middleware)
