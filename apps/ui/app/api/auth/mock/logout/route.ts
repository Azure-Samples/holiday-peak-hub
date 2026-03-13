import { NextResponse } from 'next/server';

import { clearAuthCookie, isDevAuthMockEnabled } from '@/lib/auth/authCookie';

export async function POST(): Promise<NextResponse> {
  if (!isDevAuthMockEnabled()) {
    return NextResponse.json({ error: 'Mock authentication is disabled.' }, { status: 403 });
  }

  const response = NextResponse.json({ ok: true }, { status: 200 });
  clearAuthCookie(response);
  return response;
}
