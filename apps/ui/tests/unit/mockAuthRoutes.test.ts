jest.mock('next/server', () => {
  class MockNextResponse {
    public readonly status: number;

    public readonly cookies = {
      set: jest.fn(),
    };

    constructor(_body?: unknown, init?: { status?: number }) {
      this.status = init?.status ?? 200;
    }

    static json(body: unknown, init?: { status?: number }) {
      return {
        status: init?.status ?? 200,
        json: async () => body,
        cookies: {
          set: jest.fn(),
        },
      };
    }
  }

  return {
    NextResponse: MockNextResponse,
  };
});

describe('mock auth routes', () => {
  const originalEnv = process.env;
  const originalFetch = global.fetch;

  beforeEach(() => {
    jest.resetModules();
    process.env = {
      ...originalEnv,
      NODE_ENV: 'test',
      AUTH_COOKIE_SECRET: 'test-auth-cookie-secret',
    };
    delete process.env.DEV_AUTH_MOCK;
  });

  afterEach(() => {
    global.fetch = originalFetch;
    process.env = originalEnv;
  });

  it('login returns 403 when mock auth is disabled', async () => {
    const route = await import('../../app/api/auth/mock/login/route');
    const response = await route.POST({
      json: async () => ({ role: 'customer' }),
    } as any);

    expect(response.status).toBe(403);
    await expect(response.json()).resolves.toEqual(
      expect.objectContaining({ error: 'Mock authentication is disabled.' }),
    );
  });

  it('login sets signed auth cookie when enabled with valid role', async () => {
    process.env.DEV_AUTH_MOCK = 'true';
    const route = await import('../../app/api/auth/mock/login/route');

    const response = await route.POST({
      json: async () => ({ role: 'staff' }),
    } as any);

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual(
      expect.objectContaining({ ok: true, role: 'staff' }),
    );
    expect(response.cookies.set).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'msal-auth',
        httpOnly: true,
      }),
    );
  });

  it('login remains disabled in production even when DEV_AUTH_MOCK is true', async () => {
    process.env = {
      ...process.env,
      NODE_ENV: 'production',
      DEV_AUTH_MOCK: 'true',
    };
    const route = await import('../../app/api/auth/mock/login/route');

    const response = await route.POST({
      json: async () => ({ role: 'admin' }),
    } as any);

    expect(response.status).toBe(403);
    await expect(response.json()).resolves.toEqual(
      expect.objectContaining({ error: 'Mock authentication is disabled.' }),
    );
  });

  it('logout clears auth cookie when enabled', async () => {
    process.env.DEV_AUTH_MOCK = 'true';
    const route = await import('../../app/api/auth/mock/logout/route');

    const response = await route.POST();

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual(expect.objectContaining({ ok: true }));
    expect(response.cookies.set).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'msal-auth',
        value: '',
      }),
    );
  });

  it('session route returns 401 when authorization header is missing', async () => {
    process.env.NEXT_PUBLIC_CRUD_API_URL = 'https://crud.example.test';
    const route = await import('../../app/api/auth/session/route');

    const response = await route.POST({
      headers: {
        get: () => null,
      },
    } as any);

    expect(response.status).toBe(401);
    await expect(response.json()).resolves.toEqual(
      expect.objectContaining({ error: 'Authorization token is required.' }),
    );
  });

  it('session route validates token via CRUD and sets signed cookie', async () => {
    process.env.NEXT_PUBLIC_CRUD_API_URL = 'https://crud.example.test';
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ roles: ['staff'] }),
    } as Response);

    const route = await import('../../app/api/auth/session/route');

    const response = await route.POST({
      headers: {
        get: (name: string) => (name.toLowerCase() === 'authorization' ? 'Bearer token-123' : null),
      },
    } as any);

    expect(global.fetch).toHaveBeenCalledWith(
      'https://crud.example.test/api/auth/me',
      expect.objectContaining({
        method: 'GET',
        headers: expect.objectContaining({ Authorization: 'Bearer token-123' }),
      }),
    );
    expect(response.status).toBe(200);
    expect(response.cookies.set).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'msal-auth',
        httpOnly: true,
      }),
    );
  });
});
