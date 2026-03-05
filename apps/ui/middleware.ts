import { NextRequest, NextResponse } from 'next/server';

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
 */
const ADMIN_REQUIRED_SEGMENTS = ['/admin'];

/**
 * Read the msal-auth cookie value set by AuthContext after a successful login.
 * The value is a comma-separated list of roles, e.g. "customer" or "staff,admin".
 */
function getAuthRoles(request: NextRequest): string[] {
  const raw = request.cookies.get('msal-auth')?.value;
  if (!raw) return [];
  return raw.split(',').map((r) => r.trim()).filter(Boolean);
}

function pathMatchesSegments(pathname: string, segments: string[]): boolean {
  return segments.some(
    (seg) => pathname === seg || pathname.startsWith(`${seg}/`)
  );
}

export function middleware(request: NextRequest): NextResponse {
  const { pathname } = request.nextUrl;

  const requiresAdmin = pathMatchesSegments(pathname, ADMIN_REQUIRED_SEGMENTS);
  const requiresStaff = pathMatchesSegments(pathname, STAFF_REQUIRED_SEGMENTS);
  const requiresAuth = pathMatchesSegments(pathname, AUTH_REQUIRED_SEGMENTS);

  // Public route — pass through
  if (!requiresAdmin && !requiresStaff && !requiresAuth) {
    return NextResponse.next();
  }

  const roles = getAuthRoles(request);

  // Not authenticated — redirect to login
  if (roles.length === 0) {
    const loginUrl = new URL(LOGIN_PATH, request.url);
    loginUrl.searchParams.set('redirect', pathname);
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
    '/admin/:path*',
  ],
};
