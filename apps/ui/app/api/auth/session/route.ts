import { NextRequest, NextResponse } from 'next/server';

import { resolveCrudApiBaseUrl } from '@/app/api/_shared/base-url-resolver';
import {
  clearAuthCookie,
  createSignedAuthCookieValue,
  isDevAuthMockEnabled,
  setAuthCookie,
} from '@/lib/auth/authCookie';

type UserProfileResponse = {
  roles?: unknown;
};

function parseAuthorizationHeader(request: NextRequest): string | null {
  const authorization = request.headers.get('authorization');
  if (!authorization || !authorization.toLowerCase().startsWith('bearer ')) {
    return null;
  }

  return authorization;
}

function normalizeRoles(rawRoles: unknown): string[] {
  if (!Array.isArray(rawRoles)) {
    return [];
  }

  return rawRoles.filter((role): role is string => typeof role === 'string');
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  if (isDevAuthMockEnabled()) {
    return NextResponse.json(
      { error: 'Session auth cookie endpoint is disabled while dev mock mode is enabled.' },
      { status: 403 },
    );
  }

  const authorization = parseAuthorizationHeader(request);
  if (!authorization) {
    return NextResponse.json({ error: 'Authorization token is required.' }, { status: 401 });
  }

  const { baseUrl } = resolveCrudApiBaseUrl();
  if (!baseUrl) {
    return NextResponse.json(
      { error: 'CRUD API base URL is not configured for session validation.' },
      { status: 500 },
    );
  }

  let profileResponse: Response;
  try {
    profileResponse = await fetch(`${baseUrl}/api/auth/me`, {
      method: 'GET',
      headers: {
        Authorization: authorization,
      },
      cache: 'no-store',
    });
  } catch {
    return NextResponse.json({ error: 'Unable to validate user session.' }, { status: 502 });
  }

  if (!profileResponse.ok) {
    if (profileResponse.status === 401 || profileResponse.status === 403) {
      return NextResponse.json({ error: 'Invalid authentication token.' }, { status: 401 });
    }

    return NextResponse.json({ error: 'Unable to validate user session.' }, { status: 502 });
  }

  let profileBody: UserProfileResponse;
  try {
    profileBody = (await profileResponse.json()) as UserProfileResponse;
  } catch {
    return NextResponse.json({ error: 'Invalid profile response.' }, { status: 502 });
  }

  const roles = normalizeRoles(profileBody.roles);
  if (roles.length === 0) {
    return NextResponse.json({ error: 'User roles are missing from profile.' }, { status: 403 });
  }

  const cookieValue = await createSignedAuthCookieValue(roles);
  const response = NextResponse.json({ ok: true }, { status: 200 });
  setAuthCookie(response, cookieValue);
  return response;
}

export async function DELETE(): Promise<NextResponse> {
  const response = NextResponse.json({ ok: true }, { status: 200 });
  clearAuthCookie(response);
  return response;
}
