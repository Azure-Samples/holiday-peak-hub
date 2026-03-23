import { NextResponse } from 'next/server';

export const AUTH_COOKIE_NAME = 'msal-auth';

const ALLOWED_ROLES = new Set(['customer', 'staff', 'admin']);
const DEFAULT_COOKIE_TTL_SECONDS = 60 * 60 * 12;
const DEV_FALLBACK_SECRET = 'holiday-peak-dev-auth-secret';

type AuthCookiePayload = {
  roles: string[];
  iat: number;
  exp: number;
};

function getAuthCookieSecret(): string {
  if (process.env.AUTH_COOKIE_SECRET) {
    return process.env.AUTH_COOKIE_SECRET;
  }

  return DEV_FALLBACK_SECRET;
}

function toBinaryString(bytes: Uint8Array): string {
  let result = '';
  bytes.forEach((byte) => {
    result += String.fromCharCode(byte);
  });
  return result;
}

function encodeUtf8(value: string): Uint8Array {
  const encoded = unescape(encodeURIComponent(value));
  const bytes = new Uint8Array(encoded.length);
  for (let i = 0; i < encoded.length; i += 1) {
    bytes[i] = encoded.charCodeAt(i);
  }
  return bytes;
}

function decodeUtf8(bytes: Uint8Array): string {
  let binary = '';
  bytes.forEach((byte) => {
    binary += String.fromCharCode(byte);
  });
  return decodeURIComponent(escape(binary));
}

function toBufferSource(bytes: Uint8Array): BufferSource {
  return bytes as unknown as BufferSource;
}

function toBase64Url(bytes: Uint8Array): string {
  return btoa(toBinaryString(bytes))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/g, '');
}

function fromBase64Url(value: string): Uint8Array {
  const base64 = value.replace(/-/g, '+').replace(/_/g, '/');
  const padding = '='.repeat((4 - (base64.length % 4)) % 4);
  const binary = atob(base64 + padding);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

function normalizeRoles(roles: string[]): string[] {
  return Array.from(
    new Set(
      roles
        .map((role) => role.trim().toLowerCase())
        .filter((role) => ALLOWED_ROLES.has(role)),
    ),
  );
}

async function getSigningKey(secret: string): Promise<CryptoKey> {
  return crypto.subtle.importKey(
    'raw',
    toBufferSource(encodeUtf8(secret)),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign', 'verify'],
  );
}

export function isDevAuthMockEnabled(): boolean {
  return true;
}

export async function createSignedAuthCookieValue(
  roles: string[],
  ttlSeconds: number = DEFAULT_COOKIE_TTL_SECONDS,
): Promise<string> {
  const secret = getAuthCookieSecret();
  if (!secret) {
    throw new Error('AUTH_COOKIE_SECRET is required in production.');
  }

  const normalizedRoles = normalizeRoles(roles);
  if (normalizedRoles.length === 0) {
    throw new Error('At least one valid role is required to create auth cookie.');
  }

  if (!Number.isFinite(ttlSeconds) || ttlSeconds <= 0) {
    throw new Error('Auth cookie TTL must be a positive number of seconds.');
  }

  const issuedAt = Math.floor(Date.now() / 1000);
  const payload: AuthCookiePayload = {
    roles: normalizedRoles,
    iat: issuedAt,
    exp: issuedAt + ttlSeconds,
  };

  const payloadJson = JSON.stringify(payload);
  const payloadEncoded = toBase64Url(encodeUtf8(payloadJson));
  const signingKey = await getSigningKey(secret);
  const signature = await crypto.subtle.sign(
    'HMAC',
    signingKey,
    toBufferSource(encodeUtf8(payloadEncoded)),
  );
  const signatureEncoded = toBase64Url(new Uint8Array(signature));

  return `${payloadEncoded}.${signatureEncoded}`;
}

export async function readAuthRolesFromCookie(rawValue: string | undefined): Promise<string[]> {
  if (!rawValue || !rawValue.includes('.')) {
    return [];
  }

  const secret = getAuthCookieSecret();
  if (!secret) {
    return [];
  }

  const [payloadEncoded, signatureEncoded] = rawValue.split('.', 2);
  if (!payloadEncoded || !signatureEncoded) {
    return [];
  }

  const signingKey = await getSigningKey(secret);
  const signatureBytes = fromBase64Url(signatureEncoded);
  const isValid = await crypto.subtle.verify(
    'HMAC',
    signingKey,
    toBufferSource(signatureBytes),
    toBufferSource(encodeUtf8(payloadEncoded)),
  );

  if (!isValid) {
    return [];
  }

  try {
    const payloadJson = decodeUtf8(fromBase64Url(payloadEncoded));
    const payload = JSON.parse(payloadJson) as AuthCookiePayload;
    if (
      !Array.isArray(payload.roles)
      || typeof payload.iat !== 'number'
      || typeof payload.exp !== 'number'
      || !Number.isFinite(payload.iat)
      || !Number.isFinite(payload.exp)
      || payload.iat <= 0
      || payload.exp <= payload.iat
    ) {
      return [];
    }

    const now = Math.floor(Date.now() / 1000);
    if (payload.exp <= now) {
      return [];
    }

    return normalizeRoles(payload.roles);
  } catch {
    return [];
  }
}

export function setAuthCookie(response: NextResponse, value: string): void {
  response.cookies.set({
    name: AUTH_COOKIE_NAME,
    value,
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'strict',
    path: '/',
    maxAge: DEFAULT_COOKIE_TTL_SECONDS,
  });
}

export function clearAuthCookie(response: NextResponse): void {
  response.cookies.set({
    name: AUTH_COOKIE_NAME,
    value: '',
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'strict',
    path: '/',
    expires: new Date(0),
  });
}
