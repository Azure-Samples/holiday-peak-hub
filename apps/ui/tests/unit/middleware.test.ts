// Mock next/server before importing middleware
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
import { middleware, config } from '../../middleware';

const mockNext = NextResponse.next as jest.Mock;
const mockRedirect = NextResponse.redirect as jest.Mock;

/**
 * Build a minimal NextRequest-compatible object for the middleware.
 */
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
  mockNext.mockClear();
  mockRedirect.mockClear();
});

describe('middleware matcher config', () => {
  it('exports a matcher array covering protected segments', () => {
    expect(config.matcher).toEqual(
      expect.arrayContaining([
        expect.stringContaining('/dashboard'),
        expect.stringContaining('/staff'),
        expect.stringContaining('/admin'),
      ])
    );
  });
});

describe('middleware – public routes', () => {
  it('passes through the homepage', () => {
    middleware(makeRequest('/'));
    expect(mockNext).toHaveBeenCalledTimes(1);
    expect(mockRedirect).not.toHaveBeenCalled();
  });

  it('passes through product pages', () => {
    middleware(makeRequest('/product/123'));
    expect(mockNext).toHaveBeenCalledTimes(1);
  });

  it('passes through category pages', () => {
    middleware(makeRequest('/category/electronics'));
    expect(mockNext).toHaveBeenCalledTimes(1);
  });
});

describe('middleware – protected routes (no cookie)', () => {
  const protectedPaths = [
    '/dashboard',
    '/profile',
    '/checkout',
    '/orders',
    '/order/ORD-001',
    '/wishlist',
    '/cart',
  ];

  protectedPaths.forEach((path) => {
    it(`redirects unauthenticated user from ${path} to login`, () => {
      middleware(makeRequest(path));
      expect(mockRedirect).toHaveBeenCalledTimes(1);
      const redirectUrl: URL = mockRedirect.mock.calls[0][0];
      expect(redirectUrl.pathname).toBe('/auth/login');
      expect(redirectUrl.searchParams.get('redirect')).toBe(path);
    });
  });
});

describe('middleware – staff routes', () => {
  it('redirects unauthenticated user from /staff/logistics to login', () => {
    middleware(makeRequest('/staff/logistics'));
    expect(mockRedirect).toHaveBeenCalledTimes(1);
    const url: URL = mockRedirect.mock.calls[0][0];
    expect(url.pathname).toBe('/auth/login');
  });

  it('redirects customer (no staff role) from /staff/logistics to home', () => {
    middleware(makeRequest('/staff/logistics', { 'msal-auth': 'customer' }));
    expect(mockRedirect).toHaveBeenCalledTimes(1);
    const url: URL = mockRedirect.mock.calls[0][0];
    expect(url.pathname).toBe('/');
  });

  it('allows staff user through /staff/logistics', () => {
    middleware(makeRequest('/staff/logistics', { 'msal-auth': 'staff' }));
    expect(mockNext).toHaveBeenCalledTimes(1);
    expect(mockRedirect).not.toHaveBeenCalled();
  });

  it('allows admin user through /staff routes', () => {
    middleware(makeRequest('/staff/sales', { 'msal-auth': 'admin' }));
    expect(mockNext).toHaveBeenCalledTimes(1);
  });
});

describe('middleware – admin routes', () => {
  it('redirects unauthenticated user from /admin to login', () => {
    middleware(makeRequest('/admin'));
    expect(mockRedirect).toHaveBeenCalledTimes(1);
    const url: URL = mockRedirect.mock.calls[0][0];
    expect(url.pathname).toBe('/auth/login');
  });

  it('redirects staff user (no admin role) from /admin to home', () => {
    middleware(makeRequest('/admin', { 'msal-auth': 'staff' }));
    expect(mockRedirect).toHaveBeenCalledTimes(1);
    const url: URL = mockRedirect.mock.calls[0][0];
    expect(url.pathname).toBe('/');
  });

  it('allows admin user through /admin', () => {
    middleware(makeRequest('/admin', { 'msal-auth': 'admin' }));
    expect(mockNext).toHaveBeenCalledTimes(1);
    expect(mockRedirect).not.toHaveBeenCalled();
  });

  it('allows admin user through nested /admin/crm', () => {
    middleware(makeRequest('/admin/crm', { 'msal-auth': 'admin' }));
    expect(mockNext).toHaveBeenCalledTimes(1);
  });
});

describe('middleware – authenticated customer on customer-only routes', () => {
  it('allows customer through /dashboard', () => {
    middleware(makeRequest('/dashboard', { 'msal-auth': 'customer' }));
    expect(mockNext).toHaveBeenCalledTimes(1);
    expect(mockRedirect).not.toHaveBeenCalled();
  });

  it('allows customer through /orders', () => {
    middleware(makeRequest('/orders', { 'msal-auth': 'customer' }));
    expect(mockNext).toHaveBeenCalledTimes(1);
  });

  it('allows customer through /checkout', () => {
    middleware(makeRequest('/checkout', { 'msal-auth': 'customer' }));
    expect(mockNext).toHaveBeenCalledTimes(1);
  });
});


describe('middleware matcher config', () => {
  it('exports a matcher array covering protected segments', () => {
    expect(config.matcher).toEqual(
      expect.arrayContaining([
        expect.stringContaining('/dashboard'),
        expect.stringContaining('/staff'),
        expect.stringContaining('/admin'),
      ])
    );
  });
});

describe('middleware – public routes', () => {
  it('passes through the homepage', () => {
    middleware(makeRequest('/'));
    expect(mockNext).toHaveBeenCalledTimes(1);
    expect(mockRedirect).not.toHaveBeenCalled();
  });

  it('passes through product pages', () => {
    middleware(makeRequest('/product/123'));
    expect(mockNext).toHaveBeenCalledTimes(1);
  });

  it('passes through category pages', () => {
    middleware(makeRequest('/category/electronics'));
    expect(mockNext).toHaveBeenCalledTimes(1);
  });
});

describe('middleware – protected routes (no cookie)', () => {
  const protectedPaths = [
    '/dashboard',
    '/profile',
    '/checkout',
    '/orders',
    '/order/ORD-001',
    '/wishlist',
    '/cart',
  ];

  protectedPaths.forEach((path) => {
    it(`redirects unauthenticated user from ${path} to login`, () => {
      middleware(makeRequest(path));
      expect(mockRedirect).toHaveBeenCalledTimes(1);
      const redirectUrl: URL = mockRedirect.mock.calls[0][0];
      expect(redirectUrl.pathname).toBe('/auth/login');
      expect(redirectUrl.searchParams.get('redirect')).toBe(path);
    });
  });
});

describe('middleware – staff routes', () => {
  it('redirects unauthenticated user from /staff/logistics to login', () => {
    middleware(makeRequest('/staff/logistics'));
    expect(mockRedirect).toHaveBeenCalledTimes(1);
    const url: URL = mockRedirect.mock.calls[0][0];
    expect(url.pathname).toBe('/auth/login');
  });

  it('redirects customer (no staff role) from /staff/logistics to home', () => {
    middleware(makeRequest('/staff/logistics', { 'msal-auth': 'customer' }));
    expect(mockRedirect).toHaveBeenCalledTimes(1);
    const url: URL = mockRedirect.mock.calls[0][0];
    expect(url.pathname).toBe('/');
  });

  it('allows staff user through /staff/logistics', () => {
    middleware(makeRequest('/staff/logistics', { 'msal-auth': 'staff' }));
    expect(mockNext).toHaveBeenCalledTimes(1);
    expect(mockRedirect).not.toHaveBeenCalled();
  });

  it('allows admin user through /staff routes', () => {
    middleware(makeRequest('/staff/sales', { 'msal-auth': 'admin' }));
    expect(mockNext).toHaveBeenCalledTimes(1);
  });
});

describe('middleware – admin routes', () => {
  it('redirects unauthenticated user from /admin to login', () => {
    middleware(makeRequest('/admin'));
    expect(mockRedirect).toHaveBeenCalledTimes(1);
    const url: URL = mockRedirect.mock.calls[0][0];
    expect(url.pathname).toBe('/auth/login');
  });

  it('redirects staff user (no admin role) from /admin to home', () => {
    middleware(makeRequest('/admin', { 'msal-auth': 'staff' }));
    expect(mockRedirect).toHaveBeenCalledTimes(1);
    const url: URL = mockRedirect.mock.calls[0][0];
    expect(url.pathname).toBe('/');
  });

  it('allows admin user through /admin', () => {
    middleware(makeRequest('/admin', { 'msal-auth': 'admin' }));
    expect(mockNext).toHaveBeenCalledTimes(1);
    expect(mockRedirect).not.toHaveBeenCalled();
  });

  it('allows admin user through nested /admin/crm', () => {
    middleware(makeRequest('/admin/crm', { 'msal-auth': 'admin' }));
    expect(mockNext).toHaveBeenCalledTimes(1);
  });
});

describe('middleware – authenticated customer on customer-only routes', () => {
  it('allows customer through /dashboard', () => {
    middleware(makeRequest('/dashboard', { 'msal-auth': 'customer' }));
    expect(mockNext).toHaveBeenCalledTimes(1);
    expect(mockRedirect).not.toHaveBeenCalled();
  });

  it('allows customer through /orders', () => {
    middleware(makeRequest('/orders', { 'msal-auth': 'customer' }));
    expect(mockNext).toHaveBeenCalledTimes(1);
  });

  it('allows customer through /checkout', () => {
    middleware(makeRequest('/checkout', { 'msal-auth': 'customer' }));
    expect(mockNext).toHaveBeenCalledTimes(1);
  });
});
