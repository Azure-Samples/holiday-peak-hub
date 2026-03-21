import { NextRequest } from 'next/server';

jest.mock('next/server', () => {
  class MockNextResponse {
    public readonly status: number;

    constructor(_body?: unknown, init?: { status?: number }) {
      this.status = init?.status ?? 200;
    }

    static json(body: unknown, init?: { status?: number }) {
      return {
        status: init?.status ?? 200,
        json: async () => body,
      };
    }
  }

  return {
    NextResponse: MockNextResponse,
  };
});

describe('/api proxy route env handling', () => {
  const originalEnv = process.env;

  beforeEach(() => {
    jest.resetModules();
    process.env = { ...originalEnv };
    delete process.env.NEXT_PUBLIC_CRUD_API_URL;
    delete process.env.NEXT_PUBLIC_API_URL;
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
    delete process.env.CRUD_API_URL;
    global.fetch = jest.fn();
  });

  afterEach(() => {
    process.env = originalEnv;
    jest.restoreAllMocks();
  });

  function makeRequest(url: string): NextRequest {
    return {
      method: 'GET',
      headers: new Headers({
        host: 'localhost',
      }),
      nextUrl: new URL(url),
      arrayBuffer: jest.fn(async () => new ArrayBuffer(0)),
    } as unknown as NextRequest;
  }

  it('builds upstream URL from NEXT_PUBLIC_API_URL fallback', async () => {
    process.env.NEXT_PUBLIC_API_URL = 'https://apim.example.azure-api.net/';

    (global.fetch as jest.Mock).mockResolvedValue(
      {
        body: null,
        status: 200,
        statusText: 'OK',
        headers: new Headers({
          'content-type': 'application/json',
        }),
      },
    );

    const route = await import('../../app/api/[...path]/route');
    await route.GET(makeRequest('http://localhost/api/products?category=shoes'), {
      params: Promise.resolve({ path: ['products'] }),
    });

    expect(global.fetch).toHaveBeenCalledWith(
      'https://apim.example.azure-api.net/api/products?category=shoes',
      expect.objectContaining({ method: 'GET' }),
    );
  });

  it('builds upstream URL from NEXT_PUBLIC_API_BASE_URL fallback', async () => {
    process.env.NEXT_PUBLIC_API_BASE_URL = 'https://apim-base.example.azure-api.net/';

    (global.fetch as jest.Mock).mockResolvedValue(
      {
        body: null,
        status: 200,
        statusText: 'OK',
        headers: new Headers({
          'content-type': 'application/json',
        }),
      },
    );

    const route = await import('../../app/api/[...path]/route');
    await route.GET(makeRequest('http://localhost/api/categories'), {
      params: Promise.resolve({ path: ['categories'] }),
    });

    expect(global.fetch).toHaveBeenCalledWith(
      'https://apim-base.example.azure-api.net/api/categories',
      expect.objectContaining({ method: 'GET' }),
    );
  });

  it('returns explicit 502 config diagnostics when no proxy base URL is configured', async () => {
    const route = await import('../../app/api/[...path]/route');
    const response = await route.GET(makeRequest('http://localhost/api/categories'), {
      params: Promise.resolve({ path: ['categories'] }),
    });

    expect(response.status).toBe(502);
    await expect(response.json()).resolves.toEqual(
      expect.objectContaining({
        error: 'API proxy is not configured for backend routing.',
        proxy: expect.objectContaining({
          failureKind: 'config',
          attemptedPath: '/api/categories',
          method: 'GET',
          remediation: expect.any(Array),
        }),
      }),
    );
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('returns 502 with sanitized diagnostics when upstream fetch throws', async () => {
    process.env.NEXT_PUBLIC_CRUD_API_URL = 'https://apim.example.azure-api.net';
    (global.fetch as jest.Mock).mockRejectedValue(new Error('connect ETIMEDOUT'));

    const route = await import('../../app/api/[...path]/route');
    const response = await route.GET(makeRequest('http://localhost/api/products'), {
      params: Promise.resolve({ path: ['products'] }),
    });

    expect(response.status).toBe(502);
    await expect(response.json()).resolves.toEqual(
      expect.objectContaining({
        error: 'API proxy could not reach upstream service.',
        proxy: expect.objectContaining({
          failureKind: 'network',
          sourceKey: 'NEXT_PUBLIC_CRUD_API_URL',
          attemptedPath: '/api/products',
          method: 'GET',
          upstreamError: 'connect ETIMEDOUT',
        }),
      }),
    );
  });

  it('rejects non-APIM upstream URL in proxy policy guard', async () => {
    process.env.NEXT_PUBLIC_CRUD_API_URL = 'https://backend.internal.example.net';
    process.env = {
      ...process.env,
      NODE_ENV: 'production',
    };

    const route = await import('../../app/api/[...path]/route');
    const response = await route.GET(makeRequest('http://localhost/api/products'), {
      params: Promise.resolve({ path: ['products'] }),
    });

    expect(response.status).toBe(502);
    await expect(response.json()).resolves.toEqual(
      expect.objectContaining({
        error: 'API proxy rejected a non-APIM upstream target URL.',
        proxy: expect.objectContaining({
          failureKind: 'policy',
          sourceKey: 'NEXT_PUBLIC_CRUD_API_URL',
          attemptedPath: '/api/products',
        }),
      }),
    );
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('allows local loopback URL for development runtime', async () => {
    process.env.NEXT_PUBLIC_CRUD_API_URL = 'http://localhost:8000';
    process.env = {
      ...process.env,
      NODE_ENV: 'development',
    };

    (global.fetch as jest.Mock).mockResolvedValue({
      body: null,
      status: 200,
      statusText: 'OK',
      headers: new Headers({
        'content-type': 'application/json',
      }),
    });

    const route = await import('../../app/api/[...path]/route');
    await route.GET(makeRequest('http://localhost/api/products'), {
      params: Promise.resolve({ path: ['products'] }),
    });

    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/products',
      expect.objectContaining({ method: 'GET' }),
    );
  });

  it('returns 502 upstream diagnostics when upstream responds with 502', async () => {
    process.env.NEXT_PUBLIC_CRUD_API_URL = 'https://apim.example.azure-api.net';
    (global.fetch as jest.Mock).mockResolvedValue(
      {
        body: null,
        status: 502,
        statusText: 'Bad Gateway',
        headers: new Headers({
          'content-type': 'application/json',
          'x-request-id': 'upstream-req-123',
        }),
        json: jest.fn(async () => ({
          error: 'Backend dependency timeout',
        })),
        text: jest.fn(async () => ''),
      },
    );

    const route = await import('../../app/api/[...path]/route');
    const response = await route.GET(makeRequest('http://localhost/api/products'), {
      params: Promise.resolve({ path: ['products'] }),
    });

    expect(response.status).toBe(502);
    await expect(response.json()).resolves.toEqual(
      expect.objectContaining({
        error: 'API proxy received a bad gateway response from upstream.',
        proxy: expect.objectContaining({
          failureKind: 'upstream',
          attemptedPath: '/api/products',
          method: 'GET',
          upstreamStatus: 502,
          upstreamStatusText: 'Bad Gateway',
          upstreamError: 'Backend dependency timeout',
          upstreamRequestId: 'upstream-req-123',
        }),
      }),
    );
  });
});
