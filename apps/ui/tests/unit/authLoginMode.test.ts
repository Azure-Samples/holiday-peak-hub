describe('msalConfig login mode', () => {
  const originalEnv = process.env;

  beforeEach(() => {
    jest.resetModules();
    process.env = {
      ...originalEnv,
      NODE_ENV: 'test',
    };
    delete process.env.NEXT_PUBLIC_ENTRA_CLIENT_ID;
    delete process.env.NEXT_PUBLIC_ENTRA_TENANT_ID;
    delete process.env.NEXT_PUBLIC_DEV_AUTH_MOCK;
    delete process.env.NEXT_PUBLIC_DEV_AUTH_MOCK_ALLOW_PROD;
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  it('reports Entra config error when Entra and mock mode are both disabled', async () => {
    const config = await import('../../lib/auth/msalConfig');
    expect(config.isDevAuthMockUiEnabled).toBe(false);
    expect(config.isEntraConfigured).toBe(false);
    expect(config.getEntraConfigError()).toBe("Couldn't proceed with your login.");
  });

  it('does not report Entra config error when dev mock mode is enabled', async () => {
    process.env.NEXT_PUBLIC_DEV_AUTH_MOCK = 'true';
    const config = await import('../../lib/auth/msalConfig');
    expect(config.isDevAuthMockUiEnabled).toBe(true);
    expect(config.getEntraConfigError()).toBeNull();
  });

  it('forces dev mock mode off in production runtime', async () => {
    process.env = { ...process.env, NODE_ENV: 'production' } as NodeJS.ProcessEnv;
    process.env.NEXT_PUBLIC_DEV_AUTH_MOCK = 'true';
    const config = await import('../../lib/auth/msalConfig');
    expect(config.isDevAuthMockUiEnabled).toBe(false);
  });

  it('allows mock mode in production when explicit override is enabled', async () => {
    process.env = { ...process.env, NODE_ENV: 'production' } as NodeJS.ProcessEnv;
    process.env.NEXT_PUBLIC_DEV_AUTH_MOCK = 'true';
    process.env.NEXT_PUBLIC_DEV_AUTH_MOCK_ALLOW_PROD = 'true';
    const config = await import('../../lib/auth/msalConfig');
    expect(config.isDevAuthMockUiEnabled).toBe(true);
    expect(config.getEntraConfigError()).toBeNull();
  });
});
