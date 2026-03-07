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

  it('returns explicit 500 when no proxy base URL is configured', async () => {
    const route = await import('../../app/api/[...path]/route');
    const response = await route.GET(makeRequest('http://localhost/api/categories'), {
      params: Promise.resolve({ path: ['categories'] }),
    });

    expect(response.status).toBe(500);
    await expect(response.json()).resolves.toEqual(
      expect.objectContaining({
        error: expect.stringContaining('NEXT_PUBLIC_CRUD_API_URL'),
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
          sourceKey: 'NEXT_PUBLIC_CRUD_API_URL',
          attemptedPath: '/api/products',
        }),
      }),
    );
  });
});
