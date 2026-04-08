import { NextRequest } from 'next/server';

jest.mock('next/server', () => {
  class MockNextResponse {
    public readonly status: number;
    public readonly headers: Headers;

    constructor(_body?: unknown, init?: { status?: number; headers?: HeadersInit }) {
      this.status = init?.status ?? 200;
      this.headers = new Headers(init?.headers);
    }

    static json(body: unknown, init?: { status?: number; headers?: HeadersInit }) {
      return {
        status: init?.status ?? 200,
        headers: new Headers(init?.headers),
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
    delete process.env.AGC_FRONTEND_HOSTNAME;
    delete process.env.AGC_HOSTNAME;
    delete process.env.AGC_FRONTEND_SCHEME;
    delete process.env.ADMIN_AGENT_ACTIVITY_SERVICES;
    delete process.env.NEXT_PUBLIC_FOUNDRY_STUDIO_URL;
    delete process.env.FOUNDRY_STUDIO_URL;
    delete process.env.NEXT_PUBLIC_FOUNDRY_PROJECT_URL;
    delete process.env.FOUNDRY_PROJECT_URL;
    delete process.env.NEXT_PUBLIC_FOUNDRY_TRACES_URL;
    delete process.env.FOUNDRY_TRACES_URL;
    delete process.env.NEXT_PUBLIC_FOUNDRY_EVALUATIONS_URL;
    delete process.env.FOUNDRY_EVALUATIONS_URL;
    delete process.env.PROJECT_ENDPOINT;
    delete process.env.FOUNDRY_ENDPOINT;
    delete process.env.PROJECT_NAME;
    delete process.env.FOUNDRY_PROJECT_NAME;
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

  it('returns fallback payload when /api/products upstream fetch throws', async () => {
    process.env.NEXT_PUBLIC_CRUD_API_URL = 'https://apim.example.azure-api.net';
    (global.fetch as jest.Mock).mockRejectedValue(new Error('connect ETIMEDOUT'));

    const route = await import('../../app/api/[...path]/route');
    const response = await route.GET(makeRequest('http://localhost/api/products'), {
      params: Promise.resolve({ path: ['products'] }),
    });

    expect(response.status).toBe(200);
    expect(response.headers.get('x-holiday-peak-proxy-source')).toBe('NEXT_PUBLIC_CRUD_API_URL');
    expect(response.headers.get('x-holiday-peak-proxy-failure-kind')).toBe('network');
    expect(response.headers.get('x-holiday-peak-proxy-fallback')).toBe('products-read-empty-network');
    await expect(response.json()).resolves.toEqual([]);
  });

  it('returns fallback payload when /api/categories upstream fetch throws', async () => {
    process.env.NEXT_PUBLIC_CRUD_API_URL = 'https://apim.example.azure-api.net';
    (global.fetch as jest.Mock).mockRejectedValue(new Error('connect ETIMEDOUT'));

    const route = await import('../../app/api/[...path]/route');
    const response = await route.GET(makeRequest('http://localhost/api/categories'), {
      params: Promise.resolve({ path: ['categories'] }),
    });

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual([]);
  });

  it('returns fallback payload when /api/products upstream times out', async () => {
    process.env.NEXT_PUBLIC_CRUD_API_URL = 'https://apim.example.azure-api.net';

    const timeoutError = Object.assign(new Error('The operation timed out.'), {
      name: 'TimeoutError',
    });

    (global.fetch as jest.Mock).mockRejectedValue(timeoutError);

    const route = await import('../../app/api/[...path]/route');
    const response = await route.GET(makeRequest('http://localhost/api/products'), {
      params: Promise.resolve({ path: ['products'] }),
    });

    expect(response.status).toBe(200);
    expect(global.fetch).toHaveBeenCalledWith(
      'https://apim.example.azure-api.net/api/products',
      expect.objectContaining({
        method: 'GET',
        signal: expect.anything(),
      }),
    );
    expect(response.headers.get('x-holiday-peak-proxy-failure-kind')).toBe('network');
    expect(response.headers.get('x-holiday-peak-proxy-fallback')).toBe('products-read-empty-network');
    await expect(response.json()).resolves.toEqual([]);
  });

  it('only attaches timeout signals to fallback-protected catalog reads', async () => {
    process.env.NEXT_PUBLIC_CRUD_API_URL = 'https://apim.example.azure-api.net';
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

    await route.GET(makeRequest('http://localhost/api/orders'), {
      params: Promise.resolve({ path: ['orders'] }),
    });

    const catalogFetchInit = (global.fetch as jest.Mock).mock.calls[0][1] as RequestInit;
    const ordersFetchInit = (global.fetch as jest.Mock).mock.calls[1][1] as RequestInit;

    expect(catalogFetchInit).toEqual(
      expect.objectContaining({
        method: 'GET',
        signal: expect.anything(),
      }),
    );
    expect('signal' in ordersFetchInit).toBe(false);
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

  it('returns fallback payload when /api/products upstream responds with 502', async () => {
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

    expect(response.status).toBe(200);
    expect(response.headers.get('x-holiday-peak-proxy-source')).toBe('NEXT_PUBLIC_CRUD_API_URL');
    expect(response.headers.get('x-holiday-peak-proxy-failure-kind')).toBe('upstream');
    expect(response.headers.get('x-holiday-peak-proxy-fallback')).toBe('products-read-empty-upstream-502');
    expect(response.headers.get('x-holiday-peak-proxy-fallback-upstream-status')).toBe('502');
    await expect(response.json()).resolves.toEqual([]);
  });

  it('returns fallback payload when /api/products upstream responds with 503 after retry', async () => {
    process.env.NEXT_PUBLIC_CRUD_API_URL = 'https://apim.example.azure-api.net';
    (global.fetch as jest.Mock).mockResolvedValue(
      {
        body: null,
        status: 503,
        statusText: 'Service Unavailable',
        headers: new Headers({
          'content-type': 'application/json',
          'x-request-id': 'upstream-req-503',
        }),
        json: jest.fn(async () => ({
          error: 'Service unavailable',
        })),
        text: jest.fn(async () => ''),
      },
    );

    const route = await import('../../app/api/[...path]/route');
    const response = await route.GET(makeRequest('http://localhost/api/products'), {
      params: Promise.resolve({ path: ['products'] }),
    });

    expect(response.status).toBe(200);
    expect(global.fetch).toHaveBeenCalledTimes(2);
    expect(response.headers.get('x-holiday-peak-proxy-source')).toBe('NEXT_PUBLIC_CRUD_API_URL');
    expect(response.headers.get('x-holiday-peak-proxy-failure-kind')).toBe('upstream');
    expect(response.headers.get('x-holiday-peak-proxy-fallback')).toBe('products-read-empty-upstream-503');
    expect(response.headers.get('x-holiday-peak-proxy-fallback-upstream-status')).toBe('503');
    await expect(response.json()).resolves.toEqual([]);
  });

  it('returns fallback payload when /api/categories upstream responds with 502', async () => {
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
    const response = await route.GET(makeRequest('http://localhost/api/categories'), {
      params: Promise.resolve({ path: ['categories'] }),
    });

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual([]);
  });

  it('keeps intentional 502 payload contract for non-fallback endpoints', async () => {
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
    const response = await route.GET(makeRequest('http://localhost/api/orders'), {
      params: Promise.resolve({ path: ['orders'] }),
    });

    expect(response.status).toBe(502);
    await expect(response.json()).resolves.toEqual(
      expect.objectContaining({
        error: 'API proxy received a bad gateway response from upstream.',
        proxy: expect.objectContaining({
          failureKind: 'upstream',
          attemptedPath: '/api/orders',
          method: 'GET',
          upstreamStatus: 502,
          upstreamStatusText: 'Bad Gateway',
          upstreamError: 'Backend dependency timeout',
          upstreamRequestId: 'upstream-req-123',
        }),
      }),
    );
  });

  it('aggregates live agent activity from /agents/* fallback chain when admin upstream route is unavailable', async () => {
    process.env.NEXT_PUBLIC_CRUD_API_URL = 'https://apim.example.azure-api.net';
    process.env.ADMIN_AGENT_ACTIVITY_SERVICES = 'ecommerce-catalog-search';

    (global.fetch as jest.Mock).mockImplementation(async (url: string) => {
      if (url.includes('/api/admin/agent-activity?time_range=15m')) {
        return {
          body: null,
          ok: false,
          status: 404,
          statusText: 'Not Found',
          headers: new Headers({ 'content-type': 'application/json' }),
        };
      }

      if (url.includes('/agents/ecommerce-catalog-search/agent/traces')) {
        return {
          body: null,
          ok: true,
          status: 200,
          statusText: 'OK',
          headers: new Headers({ 'content-type': 'application/json' }),
          json: jest.fn(async () => ({
            service: 'ecommerce-catalog-search',
            traces: [
              {
                timestamp: '2026-03-23T10:00:00.000Z',
                service: 'ecommerce-catalog-search',
                name: 'catalog.search',
                outcome: 'success',
                metadata: {
                  trace_id: 'trace-123',
                  duration_ms: 42,
                  model_tier: 'slm',
                  model_name: 'gpt-fast',
                  input_tokens: 10,
                  output_tokens: 20,
                },
              },
            ],
          })),
        };
      }

      if (url.includes('/agents/ecommerce-catalog-search/agent/metrics')) {
        return {
          body: null,
          ok: true,
          status: 200,
          statusText: 'OK',
          headers: new Headers({ 'content-type': 'application/json' }),
          json: jest.fn(async () => ({
            service: 'ecommerce-catalog-search',
            enabled: true,
            counts: {
              model_invocation: 1,
            },
          })),
        };
      }

      if (url.includes('/agents/ecommerce-catalog-search/agent/evaluation/latest')) {
        return {
          body: null,
          ok: true,
          status: 200,
          statusText: 'OK',
          headers: new Headers({ 'content-type': 'application/json' }),
          json: jest.fn(async () => ({
            service: 'ecommerce-catalog-search',
            latest: {
              overall_score: 0.91,
              pass_rate: 0.88,
              model_name: 'gpt-fast',
            },
          })),
        };
      }

      throw new Error(`Unexpected URL: ${url}`);
    });

    const route = await import('../../app/api/[...path]/route');
    const response = await route.GET(makeRequest('http://localhost/api/admin/agent-activity?time_range=15m'), {
      params: Promise.resolve({ path: ['admin', 'agent-activity'] }),
    });

    expect(response.status).toBe(200);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/agents/ecommerce-catalog-search/agent/traces'),
      expect.objectContaining({ method: 'GET' }),
    );
    await expect(response.json()).resolves.toEqual(
      expect.objectContaining({
        tracing_enabled: true,
        health_cards: expect.arrayContaining([
          expect.objectContaining({ id: 'ecommerce-catalog-search' }),
        ]),
        trace_feed: expect.arrayContaining([
          expect.objectContaining({
            trace_id: 'trace-123',
            agent_name: 'ecommerce-catalog-search',
          }),
        ]),
        model_usage: expect.any(Array),
      }),
    );
  });

  it('uses readiness probes for admin service fallback when telemetry routes are unavailable', async () => {
    process.env.NEXT_PUBLIC_CRUD_API_URL = 'https://apim.example.azure-api.net';

    (global.fetch as jest.Mock).mockImplementation(async (url: string) => {
      if (url.includes('/api/admin/ecommerce/catalog')) {
        return {
          body: null,
          ok: false,
          status: 404,
          statusText: 'Not Found',
          headers: new Headers({ 'content-type': 'application/json' }),
        };
      }

      if (url.includes('/agents/ecommerce-catalog-search/agent/traces')) {
        return {
          body: null,
          ok: false,
          status: 404,
          statusText: 'Not Found',
          headers: new Headers({ 'content-type': 'application/json' }),
        };
      }

      if (url.includes('/agents/ecommerce-catalog-search/agent/metrics')) {
        return {
          body: null,
          ok: false,
          status: 404,
          statusText: 'Not Found',
          headers: new Headers({ 'content-type': 'application/json' }),
        };
      }

      if (url.includes('/agents/ecommerce-catalog-search/agent/evaluation/latest')) {
        return {
          body: null,
          ok: false,
          status: 404,
          statusText: 'Not Found',
          headers: new Headers({ 'content-type': 'application/json' }),
        };
      }

      if (url.includes('/agents/ecommerce-catalog-search/health')) {
        return {
          body: null,
          ok: true,
          status: 200,
          statusText: 'OK',
          headers: new Headers({ 'content-type': 'application/json' }),
          json: jest.fn(async () => ({ healthy: true })),
        };
      }

      if (url.includes('/agents/ecommerce-catalog-search/ready')) {
        return {
          body: null,
          ok: true,
          status: 200,
          statusText: 'OK',
          headers: new Headers({ 'content-type': 'application/json' }),
          json: jest.fn(async () => ({ ready: true, foundry_ready: true })),
        };
      }

      throw new Error(`Unexpected URL: ${url}`);
    });

    const route = await import('../../app/api/[...path]/route');
    const response = await route.GET(makeRequest('http://localhost/api/admin/ecommerce/catalog'), {
      params: Promise.resolve({ path: ['admin', 'ecommerce', 'catalog'] }),
    });

    expect(response.status).toBe(200);
    expect(response.headers.get('x-holiday-peak-proxy-fallback')).toBe('admin-service-live-aggregate');

    const payload = await response.json();
    expect(payload).toEqual(
      expect.objectContaining({
        domain: 'ecommerce',
        service: 'catalog',
        agent_service: 'ecommerce-catalog-search',
        status_cards: expect.any(Array),
        activity: [],
        app_surface: expect.objectContaining({
          source: 'apim-readiness',
          liveness_ok: true,
          readiness_ok: true,
          links: expect.objectContaining({
            health: 'https://apim.example.azure-api.net/agents/ecommerce-catalog-search/health',
            ready: 'https://apim.example.azure-api.net/agents/ecommerce-catalog-search/ready',
          }),
        }),
        foundry_surface: expect.objectContaining({
          foundry_ready: true,
          links: expect.objectContaining({
            studio: 'https://ai.azure.com',
            project: 'https://ai.azure.com',
            traces: 'https://ai.azure.com',
            evaluations: 'https://ai.azure.com',
          }),
        }),
      }),
    );
    expect(payload.status_cards.some((card: { status: string }) => card.status !== 'unknown')).toBe(true);
  });

  it('uses direct AGC readiness probes when APIM readiness probes fail', async () => {
    process.env.NEXT_PUBLIC_CRUD_API_URL = 'https://apim.example.azure-api.net';
    process.env.AGC_FRONTEND_HOSTNAME = 'agc.internal.example.com';
    process.env.AGC_FRONTEND_SCHEME = 'http';

    (global.fetch as jest.Mock).mockImplementation(async (url: string) => {
      if (url.includes('/api/admin/ecommerce/catalog')) {
        return {
          body: null,
          ok: false,
          status: 404,
          statusText: 'Not Found',
          headers: new Headers({ 'content-type': 'application/json' }),
        };
      }

      if (url.includes('/agents/ecommerce-catalog-search/agent/traces')) {
        return {
          body: null,
          ok: false,
          status: 404,
          statusText: 'Not Found',
          headers: new Headers({ 'content-type': 'application/json' }),
        };
      }

      if (url.includes('/agents/ecommerce-catalog-search/agent/metrics')) {
        return {
          body: null,
          ok: false,
          status: 404,
          statusText: 'Not Found',
          headers: new Headers({ 'content-type': 'application/json' }),
        };
      }

      if (url.includes('/agents/ecommerce-catalog-search/agent/evaluation/latest')) {
        return {
          body: null,
          ok: false,
          status: 404,
          statusText: 'Not Found',
          headers: new Headers({ 'content-type': 'application/json' }),
        };
      }

      if (url.includes('/agents/ecommerce-catalog-search/health')) {
        return {
          body: null,
          ok: false,
          status: 503,
          statusText: 'Service Unavailable',
          headers: new Headers({ 'content-type': 'application/json' }),
        };
      }

      if (url.includes('/agents/ecommerce-catalog-search/ready')) {
        return {
          body: null,
          ok: false,
          status: 503,
          statusText: 'Service Unavailable',
          headers: new Headers({ 'content-type': 'application/json' }),
        };
      }

      if (url.includes('http://agc.internal.example.com/ecommerce-catalog-search/health')) {
        return {
          body: null,
          ok: true,
          status: 200,
          statusText: 'OK',
          headers: new Headers({ 'content-type': 'application/json' }),
          json: jest.fn(async () => ({ healthy: true })),
        };
      }

      if (url.includes('http://agc.internal.example.com/ecommerce-catalog-search/ready')) {
        return {
          body: null,
          ok: false,
          status: 404,
          statusText: 'Not Found',
          headers: new Headers({ 'content-type': 'application/json' }),
        };
      }

      if (url.includes('http://agc.internal.example.com/ready')) {
        return {
          body: null,
          ok: true,
          status: 200,
          statusText: 'OK',
          headers: new Headers({ 'content-type': 'application/json' }),
          json: jest.fn(async () => ({ ready: true, foundry_ready: true })),
        };
      }

      throw new Error(`Unexpected URL: ${url}`);
    });

    const route = await import('../../app/api/[...path]/route');
    const response = await route.GET(makeRequest('http://localhost/api/admin/ecommerce/catalog'), {
      params: Promise.resolve({ path: ['admin', 'ecommerce', 'catalog'] }),
    });

    expect(response.status).toBe(200);
    expect(response.headers.get('x-holiday-peak-proxy-fallback')).toBe('admin-service-live-aggregate');
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('http://agc.internal.example.com/ecommerce-catalog-search/health'),
      expect.objectContaining({ method: 'GET' }),
    );
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('http://agc.internal.example.com/ready'),
      expect.objectContaining({ method: 'GET' }),
    );

    const payload = await response.json();
    expect(payload).toEqual(
      expect.objectContaining({
        app_surface: expect.objectContaining({
          source: 'agc-direct-readiness',
          liveness_ok: true,
          readiness_ok: true,
          links: expect.objectContaining({
            health: 'http://agc.internal.example.com/ecommerce-catalog-search/health',
            ready: 'http://agc.internal.example.com/ecommerce-catalog-search/ready',
          }),
        }),
      }),
    );
    expect(payload.status_cards.some((card: { status: string }) => card.status !== 'unknown')).toBe(true);
  });

  it('aggregates staff review queue from truth-hitl invoke when staff upstream route is unavailable', async () => {
    process.env.NEXT_PUBLIC_CRUD_API_URL = 'https://apim.example.azure-api.net';

    (global.fetch as jest.Mock).mockImplementation(async (url: string, init?: RequestInit) => {
      if (url.includes('/api/staff/review?page=1&page_size=20')) {
        return {
          body: null,
          ok: false,
          status: 404,
          statusText: 'Not Found',
          headers: new Headers({ 'content-type': 'application/json' }),
        };
      }

      if (url.includes('/agents/truth-hitl/invoke')) {
        expect(init?.method).toBe('POST');
        return {
          body: null,
          ok: true,
          status: 200,
          statusText: 'OK',
          headers: new Headers({ 'content-type': 'application/json' }),
          json: jest.fn(async () => ({
            items: [
              {
                id: 'attr-123',
                entity_id: 'prd-001',
                product_title: 'Demo Product',
                category: 'Electronics',
                field_name: 'material',
                current_value: 'plastic',
                proposed_value: 'aluminum',
                confidence: 0.91,
                source: 'ai',
                proposed_at: '2026-03-23T10:00:00.000Z',
                status: 'pending',
              },
            ],
            count: 1,
          })),
        };
      }

      throw new Error(`Unexpected URL: ${url}`);
    });

    const route = await import('../../app/api/[...path]/route');
    const response = await route.GET(makeRequest('http://localhost/api/staff/review?page=1&page_size=20'), {
      params: Promise.resolve({ path: ['staff', 'review'] }),
    });

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual(
      expect.objectContaining({
        items: expect.arrayContaining([
          expect.objectContaining({
            id: 'attr-123',
            entity_id: 'prd-001',
          }),
        ]),
        total: 1,
        page: 1,
        page_size: 20,
      }),
    );
  });

  it('keeps non-agent routes unchanged when upstream returns 404', async () => {
    process.env.NEXT_PUBLIC_CRUD_API_URL = 'https://apim.example.azure-api.net';
    (global.fetch as jest.Mock).mockResolvedValue({
      body: null,
      status: 404,
      statusText: 'Not Found',
      headers: new Headers({
        'content-type': 'application/json',
      }),
    });

    const route = await import('../../app/api/[...path]/route');
    const response = await route.GET(makeRequest('http://localhost/api/products'), {
      params: Promise.resolve({ path: ['products'] }),
    });

    expect(response.status).toBe(404);
    expect(global.fetch).toHaveBeenCalledTimes(1);
    expect(global.fetch).toHaveBeenCalledWith(
      'https://apim.example.azure-api.net/api/products',
      expect.objectContaining({ method: 'GET' }),
    );
  });
});
