import { NextRequest, NextResponse } from 'next/server';

import {
  createSignedAuthCookieValue,
  isDevAuthMockEnabled,
  setAuthCookie,
} from '@/lib/auth/authCookie';

type MockRole = 'customer' | 'staff' | 'admin';

const VALID_ROLES: MockRole[] = ['customer', 'staff', 'admin'];

function isMockRole(value: unknown): value is MockRole {
  return typeof value === 'string' && VALID_ROLES.includes(value as MockRole);
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  if (!isDevAuthMockEnabled()) {
    return NextResponse.json({ error: 'Mock authentication is disabled.' }, { status: 403 });
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid request body.' }, { status: 400 });
  }

  const role = (body as { role?: unknown })?.role;
  if (!isMockRole(role)) {
    return NextResponse.json(
      { error: 'Invalid role. Supported roles: customer, staff, admin.' },
      { status: 400 },
    );
  }

  const cookieValue = await createSignedAuthCookieValue([role]);
  const response = NextResponse.json({ ok: true, role }, { status: 200 });
  setAuthCookie(response, cookieValue);

  return response;
}
