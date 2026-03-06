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
          sourceKey: 'NEXT_PUBLIC_AGENT_API_URL',
          attemptedPath: '/agents/ecommerce-product-detail-enrichment/invoke',
        }),
      }),
    );
  });
});
