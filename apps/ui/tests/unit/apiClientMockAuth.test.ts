import type { InternalAxiosRequestConfig } from 'axios';

describe('api client dev mock auth headers', () => {
  const originalEnv = process.env;

  beforeEach(() => {
    jest.resetModules();
    localStorage.clear();
    sessionStorage.clear();
    process.env = { ...originalEnv };
  });

  afterAll(() => {
    process.env = originalEnv;
  });

  async function runRequestInterceptor(config: InternalAxiosRequestConfig) {
    const clientModule = await import('../../lib/api/client');
    const requestInterceptor = (
      clientModule.apiClient.interceptors.request as unknown as {
        handlers: Array<{ fulfilled: (cfg: InternalAxiosRequestConfig) => Promise<InternalAxiosRequestConfig> }>;
      }
    ).handlers[0].fulfilled;

    return requestInterceptor(config);
  }

  it('adds bearer authorization when auth token exists', async () => {
    process.env.NEXT_PUBLIC_DEV_AUTH_MOCK = 'true';
    sessionStorage.setItem('auth_token', 'token-123');

    const config = await runRequestInterceptor({ headers: {} } as InternalAxiosRequestConfig);

    expect(config.headers.Authorization).toBe('Bearer token-123');
    expect(config.headers['X-Dev-Auth-Mock']).toBeUndefined();
  });

  it('adds explicit mock auth headers in non-production mock mode without bearer token', async () => {
    process.env.NEXT_PUBLIC_DEV_AUTH_MOCK = 'true';
    process.env = { ...process.env, NODE_ENV: 'development' };

    localStorage.setItem(
      'mock_auth_user',
      JSON.stringify({
        user_id: 'mock-staff',
        email: 'mock.staff@local.dev',
        name: 'Mock Staff',
        roles: ['staff'],
      }),
    );

    const config = await runRequestInterceptor({ headers: {} } as InternalAxiosRequestConfig);

    expect(config.headers.Authorization).toBeUndefined();
    expect(config.headers['X-Dev-Auth-Mock']).toBe('true');
    expect(config.headers['X-Dev-Auth-Roles']).toBe('staff');
    expect(config.headers['X-Dev-Auth-User-Id']).toBe('mock-staff');
    expect(config.headers['X-Dev-Auth-Email']).toBe('mock.staff@local.dev');
    expect(config.headers['X-Dev-Auth-Name']).toBe('Mock Staff');
  });

  it('does not add mock auth headers in production even when mock flag is set', async () => {
    process.env.NEXT_PUBLIC_DEV_AUTH_MOCK = 'true';
    process.env = { ...process.env, NODE_ENV: 'production' };

    localStorage.setItem(
      'mock_auth_user',
      JSON.stringify({
        user_id: 'mock-admin',
        roles: ['admin'],
      }),
    );

    const config = await runRequestInterceptor({ headers: {} } as InternalAxiosRequestConfig);

    expect(config.headers['X-Dev-Auth-Mock']).toBeUndefined();
    expect(config.headers['X-Dev-Auth-Roles']).toBeUndefined();
    expect(config.headers.Authorization).toBeUndefined();
  });
});
