jest.mock('next/server', () => {
  return {
    NextRequest: jest.fn(),
    NextResponse: {
      next: jest.fn(() => ({ type: 'next' })),
      redirect: jest.fn((url: URL) => ({
        type: 'redirect',
        url: url.pathname + (url.search || ''),
      })),
    },
  };
});

import { NextResponse } from 'next/server';

import { createSignedAuthCookieValue } from '../../lib/auth/authCookie';
import { config, middleware } from '../../middleware';

const mockNext = NextResponse.next as jest.Mock;
const mockRedirect = NextResponse.redirect as jest.Mock;

function makeRequest(pathname: string, cookies: Record<string, string> = {}) {
  return {
    nextUrl: new URL(`http://localhost${pathname}`),
    url: `http://localhost${pathname}`,
    cookies: {
      get: (name: string) => (cookies[name] ? { value: cookies[name] } : undefined),
    },
  } as any;
}

beforeEach(() => {
  process.env.AUTH_COOKIE_SECRET = 'test-auth-cookie-secret';
  mockNext.mockClear();
  mockRedirect.mockClear();
});

afterAll(() => {
  delete process.env.AUTH_COOKIE_SECRET;
});

describe('middleware matcher config', () => {
  it('exports a matcher array covering protected segments', () => {
    expect(config.matcher).toEqual(
      expect.arrayContaining([
        expect.stringContaining('/dashboard'),
        expect.stringContaining('/staff'),
        expect.stringContaining('/admin'),
      ]),
    );
  });
});

describe('middleware – public routes', () => {
  it('passes through the homepage', async () => {
    await middleware(makeRequest('/'));
    expect(mockNext).toHaveBeenCalledTimes(1);
    expect(mockRedirect).not.toHaveBeenCalled();
  });

  it('passes through product pages', async () => {
    await middleware(makeRequest('/product/123'));
    expect(mockNext).toHaveBeenCalledTimes(1);
  });
});

describe('middleware – protected routes', () => {
  it('redirects unauthenticated user from /dashboard to login', async () => {
    await middleware(makeRequest('/dashboard'));
    expect(mockRedirect).toHaveBeenCalledTimes(1);
    const redirectUrl: URL = mockRedirect.mock.calls[0][0];
    expect(redirectUrl.pathname).toBe('/auth/login');
    expect(redirectUrl.searchParams.get('redirect')).toBe('/dashboard');
  });

  it('rejects unsigned cookie values and redirects to login', async () => {
    await middleware(makeRequest('/orders', { 'msal-auth': 'customer' }));
    expect(mockRedirect).toHaveBeenCalledTimes(1);
    const redirectUrl: URL = mockRedirect.mock.calls[0][0];
    expect(redirectUrl.pathname).toBe('/auth/login');
  });

  it('allows signed customer role through /orders', async () => {
    const signedCookie = await createSignedAuthCookieValue(['customer']);
    await middleware(makeRequest('/orders', { 'msal-auth': signedCookie }));
    expect(mockNext).toHaveBeenCalledTimes(1);
  });

  it('allows signed staff role through /staff/logistics', async () => {
    const signedCookie = await createSignedAuthCookieValue(['staff']);
    await middleware(makeRequest('/staff/logistics', { 'msal-auth': signedCookie }));
    expect(mockNext).toHaveBeenCalledTimes(1);
    expect(mockRedirect).not.toHaveBeenCalled();
  });

  it('redirects signed staff role away from /admin', async () => {
    const signedCookie = await createSignedAuthCookieValue(['staff']);
    await middleware(makeRequest('/admin', { 'msal-auth': signedCookie }));
    expect(mockRedirect).toHaveBeenCalledTimes(1);
    const redirectUrl: URL = mockRedirect.mock.calls[0][0];
    expect(redirectUrl.pathname).toBe('/');
  });

  it('allows signed admin role through /admin', async () => {
    const signedCookie = await createSignedAuthCookieValue(['admin']);
    await middleware(makeRequest('/admin', { 'msal-auth': signedCookie }));
    expect(mockNext).toHaveBeenCalledTimes(1);
    expect(mockRedirect).not.toHaveBeenCalled();
  });

  it('rejects invalid signed cookie and redirects to login', async () => {
    await middleware(makeRequest('/checkout', { 'msal-auth': 'invalid.payload' }));
    expect(mockRedirect).toHaveBeenCalledTimes(1);
    const redirectUrl: URL = mockRedirect.mock.calls[0][0];
    expect(redirectUrl.pathname).toBe('/auth/login');
  });

  it('redirects expired signed cookie to login', async () => {
    const dateNowSpy = jest.spyOn(Date, 'now').mockReturnValue(1_700_000_000_000);
    const signedCookie = await createSignedAuthCookieValue(['customer'], 5);
    dateNowSpy.mockReturnValue(1_700_000_010_000);

    await middleware(makeRequest('/checkout', { 'msal-auth': signedCookie }));
    expect(mockRedirect).toHaveBeenCalledTimes(1);
    const redirectUrl: URL = mockRedirect.mock.calls[0][0];
    expect(redirectUrl.pathname).toBe('/auth/login');
    expect(redirectUrl.searchParams.get('redirect')).toBe('/checkout');

    dateNowSpy.mockRestore();
  });
});
