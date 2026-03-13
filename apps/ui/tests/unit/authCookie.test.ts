import {
  createSignedAuthCookieValue,
  readAuthRolesFromCookie,
} from '../../lib/auth/authCookie';

describe('authCookie', () => {
  let dateNowSpy: jest.SpyInstance<number, []>;

  beforeEach(() => {
    process.env.AUTH_COOKIE_SECRET = 'test-auth-cookie-secret';
    dateNowSpy = jest.spyOn(Date, 'now').mockReturnValue(1_700_000_000_000);
  });

  afterEach(() => {
    dateNowSpy.mockRestore();
  });

  afterAll(() => {
    delete process.env.AUTH_COOKIE_SECRET;
  });

  it('creates a signed cookie and verifies roles', async () => {
    const value = await createSignedAuthCookieValue(['staff']);
    const roles = await readAuthRolesFromCookie(value);
    expect(roles).toEqual(['staff']);
  });

  it('rejects tampered signed cookie payload', async () => {
    const value = await createSignedAuthCookieValue(['admin']);
    const [payload, signature] = value.split('.', 2);
    const tampered = `${payload}x.${signature}`;
    const roles = await readAuthRolesFromCookie(tampered);
    expect(roles).toEqual([]);
  });

  it('rejects unsigned legacy role cookie values', async () => {
    const roles = await readAuthRolesFromCookie('customer,staff');
    expect(roles).toEqual([]);
  });

  it('rejects expired signed cookies', async () => {
    const value = await createSignedAuthCookieValue(['customer'], 5);
    dateNowSpy.mockReturnValue(1_700_000_010_000);
    const roles = await readAuthRolesFromCookie(value);
    expect(roles).toEqual([]);
  });
});
