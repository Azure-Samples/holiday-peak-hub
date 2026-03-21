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

describe('/agent-api proxy route env handling', () => {
  const originalEnv = process.env;

  beforeEach(() => {
    jest.resetModules();
    process.env = { ...originalEnv };
    delete process.env.NEXT_PUBLIC_AGENT_API_URL;
    delete process.env.AGENT_API_URL;
    delete process.env.NEXT_PUBLIC_CRUD_API_URL;
    delete process.env.NEXT_PUBLIC_API_URL;
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

  it('returns explicit 502 config diagnostics when no agent proxy base URL is configured', async () => {
    const route = await import('../../app/agent-api/[...path]/route');
    const response = await route.GET(makeRequest('http://localhost/agent-api/ecommerce-catalog-search/invoke'), {
      params: Promise.resolve({ path: ['ecommerce-catalog-search', 'invoke'] }),
    });

    expect(response.status).toBe(502);
    await expect(response.json()).resolves.toEqual(
      expect.objectContaining({
        error: 'Agent API proxy is not configured for backend routing.',
        proxy: expect.objectContaining({
          failureKind: 'config',
          attemptedPath: '/agents/ecommerce-catalog-search/invoke',
          method: 'GET',
          remediation: expect.any(Array),
        }),
      }),
    );
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('returns 502 with sanitized diagnostics when upstream agent fetch throws', async () => {
    process.env.NEXT_PUBLIC_AGENT_API_URL = 'https://apim.example.azure-api.net/agents';
    (global.fetch as jest.Mock).mockRejectedValue(new Error('connect ETIMEDOUT'));

    const route = await import('../../app/agent-api/[...path]/route');
    const response = await route.GET(makeRequest('http://localhost/agent-api/ecommerce-product-detail-enrichment/invoke'), {
      params: Promise.resolve({ path: ['ecommerce-product-detail-enrichment', 'invoke'] }),
    });

    expect(response.status).toBe(502);
    await expect(response.json()).resolves.toEqual(
      expect.objectContaining({
        error: 'Agent API proxy could not reach upstream service.',
        proxy: expect.objectContaining({
          failureKind: 'network',
          sourceKey: 'NEXT_PUBLIC_AGENT_API_URL',
          attemptedPath: '/agents/ecommerce-product-detail-enrichment/invoke',
          method: 'GET',
          upstreamError: 'connect ETIMEDOUT',
        }),
      }),
    );
  });

  it('rejects non-APIM agent URL in proxy policy guard', async () => {
    process.env.NEXT_PUBLIC_AGENT_API_URL = 'https://agents.internal.example.net/agents';
    process.env = {
      ...process.env,
      NODE_ENV: 'production',
    };

    const route = await import('../../app/agent-api/[...path]/route');
    const response = await route.GET(makeRequest('http://localhost/agent-api/ecommerce-catalog-search/invoke'), {
      params: Promise.resolve({ path: ['ecommerce-catalog-search', 'invoke'] }),
    });

    expect(response.status).toBe(502);
    await expect(response.json()).resolves.toEqual(
      expect.objectContaining({
        error: 'Agent API proxy rejected a non-APIM upstream target URL.',
        proxy: expect.objectContaining({
          failureKind: 'policy',
          sourceKey: 'NEXT_PUBLIC_AGENT_API_URL',
          attemptedPath: '/agents/ecommerce-catalog-search/invoke',
        }),
      }),
    );
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('allows local loopback agent URL for development runtime', async () => {
    process.env.NEXT_PUBLIC_AGENT_API_URL = 'http://localhost:8100/agents';
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

    const route = await import('../../app/agent-api/[...path]/route');
    await route.GET(makeRequest('http://localhost/agent-api/ecommerce-catalog-search/invoke'), {
      params: Promise.resolve({ path: ['ecommerce-catalog-search', 'invoke'] }),
    });

    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:8100/agents/ecommerce-catalog-search/invoke',
      expect.objectContaining({ method: 'GET' }),
    );
  });

  it('returns 502 upstream diagnostics when upstream responds with 502', async () => {
    process.env.NEXT_PUBLIC_AGENT_API_URL = 'https://apim.example.azure-api.net/agents';
    (global.fetch as jest.Mock).mockResolvedValue({
      body: null,
      status: 502,
      statusText: 'Bad Gateway',
      headers: new Headers({
        'content-type': 'application/json',
        'x-request-id': 'agent-upstream-req-123',
      }),
      json: jest.fn(async () => ({
        error: 'Agent dependency timeout',
      })),
      text: jest.fn(async () => ''),
    });

    const route = await import('../../app/agent-api/[...path]/route');
    const response = await route.GET(makeRequest('http://localhost/agent-api/ecommerce-catalog-search/invoke'), {
      params: Promise.resolve({ path: ['ecommerce-catalog-search', 'invoke'] }),
    });

    expect(response.status).toBe(502);
    await expect(response.json()).resolves.toEqual(
      expect.objectContaining({
        error: 'Agent API proxy received a bad gateway response from upstream.',
        proxy: expect.objectContaining({
          failureKind: 'upstream',
          attemptedPath: '/agents/ecommerce-catalog-search/invoke',
          method: 'GET',
          upstreamStatus: 502,
          upstreamStatusText: 'Bad Gateway',
          upstreamError: 'Agent dependency timeout',
          upstreamRequestId: 'agent-upstream-req-123',
        }),
      }),
    );
  });
});
