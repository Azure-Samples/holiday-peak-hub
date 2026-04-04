import { NextRequest, NextResponse } from 'next/server';

import { AUTH_COOKIE_NAME, readAuthRolesFromCookie } from './lib/auth/authCookie';

const LOGIN_PATH = '/auth/login';

/**
 * Route segments that require any authenticated user.
 */
const AUTH_REQUIRED_SEGMENTS = [
  '/dashboard',
  '/profile',
  '/checkout',
  '/orders',
  '/order',
  '/wishlist',
  '/cart',
];

/**
 * Route segments that require the "staff" (or "admin") role.
 */
const STAFF_REQUIRED_SEGMENTS = ['/staff'];

/**
 * Route segments that require the "admin" role.
 * Admin pages are publicly accessible for dev/demo environments.
 */
const ADMIN_REQUIRED_SEGMENTS: string[] = [];

/**
 * Read the server-signed msal-auth cookie value set by auth session endpoints.
 */
async function getAuthRoles(request: NextRequest): Promise<string[]> {
  const raw = request.cookies.get(AUTH_COOKIE_NAME)?.value;
  return readAuthRolesFromCookie(raw);
}

function pathMatchesSegments(pathname: string, segments: string[]): boolean {
  return segments.some(
    (seg) => pathname === seg || pathname.startsWith(`${seg}/`)
  );
}

export async function proxy(request: NextRequest): Promise<NextResponse> {
  const { pathname } = request.nextUrl;

  const requiresAdmin = pathMatchesSegments(pathname, ADMIN_REQUIRED_SEGMENTS);
  const requiresStaff = pathMatchesSegments(pathname, STAFF_REQUIRED_SEGMENTS);
  const requiresAuth = pathMatchesSegments(pathname, AUTH_REQUIRED_SEGMENTS);

  // Public route — pass through
  if (!requiresAdmin && !requiresStaff && !requiresAuth) {
    return NextResponse.next();
  }

  const roles = await getAuthRoles(request);

  // Not authenticated — redirect to login
  if (roles.length === 0) {
    const loginUrl = new URL(LOGIN_PATH, request.url);
    const redirectTarget = `${pathname}${request.nextUrl.search}`;
    loginUrl.searchParams.set('redirect', redirectTarget);
    return NextResponse.redirect(loginUrl);
  }

  // Admin-only routes
  if (requiresAdmin && !roles.includes('admin')) {
    return NextResponse.redirect(new URL('/', request.url));
  }

  // Staff routes (staff or admin)
  if (requiresStaff && !roles.includes('staff') && !roles.includes('admin')) {
    return NextResponse.redirect(new URL('/', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    '/dashboard/:path*',
    '/profile/:path*',
    '/checkout/:path*',
    '/orders/:path*',
    '/order/:path*',
    '/wishlist/:path*',
    '/cart/:path*',
    '/staff/:path*',
  ],
};
