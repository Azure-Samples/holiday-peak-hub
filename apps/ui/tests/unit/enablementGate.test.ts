/**
 * Unit tests for the enablement gate (Issue #1051 / Epic #1053).
 */

import {
  decodeSwaPrincipal,
  evaluateGate,
  denyMessage,
} from '../../lib/enablement/gate';

const TENANT = '11111111-1111-1111-1111-111111111111';
const GROUP = '22222222-2222-2222-2222-222222222222';

function buildSwaHeader(claims: Array<{ typ: string; val: string }>, userId = 'u-1', userDetails = 'Test User'): string {
  const payload = {
    identityProvider: 'aad',
    userId,
    userDetails,
    userRoles: ['authenticated'],
    claims,
  };
  return Buffer.from(JSON.stringify(payload), 'utf-8').toString('base64');
}

describe('decodeSwaPrincipal', () => {
  it('returns null on missing header', () => {
    expect(decodeSwaPrincipal(null)).toBeNull();
    expect(decodeSwaPrincipal(undefined)).toBeNull();
  });

  it('returns null on malformed base64 / json', () => {
    expect(decodeSwaPrincipal('not-base64-not-json')).toBeNull();
  });

  it('parses tenant id, user oid, and groups from claims', () => {
    const header = buildSwaHeader([
      { typ: 'tid', val: TENANT },
      { typ: 'oid', val: 'user-oid' },
      { typ: 'groups', val: GROUP },
      { typ: 'groups', val: 'other-group' },
    ]);
    const principal = decodeSwaPrincipal(header);
    expect(principal?.tenantId).toBe(TENANT);
    expect(principal?.userOid).toBe('user-oid');
    expect(principal?.groups).toEqual(expect.arrayContaining([GROUP, 'other-group']));
  });
});

describe('evaluateGate', () => {
  const ORIGINAL_TENANT = process.env.ENABLEMENT_TENANT_ID;
  const ORIGINAL_GROUP = process.env.ENABLEMENT_GROUP_ID;

  afterEach(() => {
    process.env.ENABLEMENT_TENANT_ID = ORIGINAL_TENANT;
    process.env.ENABLEMENT_GROUP_ID = ORIGINAL_GROUP;
    jest.resetModules();
  });

  it('denies with config-missing when tenant or group env is absent (fail closed)', async () => {
    delete process.env.ENABLEMENT_TENANT_ID;
    delete process.env.ENABLEMENT_GROUP_ID;
    jest.resetModules();
    const { evaluateGate: ev } = await import('../../lib/enablement/gate');
    const result = ev({
      tenantId: TENANT,
      userOid: 'oid',
      groups: [GROUP],
    });
    expect(result.allowed).toBe(false);
    if (!result.allowed) expect(result.reason).toBe('config-missing');
  });

  it('denies with no-principal when env is set but principal is null', async () => {
    process.env.ENABLEMENT_TENANT_ID = TENANT;
    process.env.ENABLEMENT_GROUP_ID = GROUP;
    jest.resetModules();
    const { evaluateGate: ev } = await import('../../lib/enablement/gate');
    const result = ev(null);
    expect(result.allowed).toBe(false);
    if (!result.allowed) expect(result.reason).toBe('no-principal');
  });

  it('denies with wrong-tenant when tenant mismatches', async () => {
    process.env.ENABLEMENT_TENANT_ID = TENANT;
    process.env.ENABLEMENT_GROUP_ID = GROUP;
    jest.resetModules();
    const { evaluateGate: ev } = await import('../../lib/enablement/gate');
    const result = ev({
      tenantId: 'wrong-tenant',
      userOid: 'oid',
      groups: [GROUP],
    });
    expect(result.allowed).toBe(false);
    if (!result.allowed) expect(result.reason).toBe('wrong-tenant');
  });

  it('denies with wrong-group when group is missing', async () => {
    process.env.ENABLEMENT_TENANT_ID = TENANT;
    process.env.ENABLEMENT_GROUP_ID = GROUP;
    jest.resetModules();
    const { evaluateGate: ev } = await import('../../lib/enablement/gate');
    const result = ev({
      tenantId: TENANT,
      userOid: 'oid',
      groups: ['other-group-only'],
    });
    expect(result.allowed).toBe(false);
    if (!result.allowed) expect(result.reason).toBe('wrong-group');
  });

  it('allows when tenant + group match', async () => {
    process.env.ENABLEMENT_TENANT_ID = TENANT;
    process.env.ENABLEMENT_GROUP_ID = GROUP;
    jest.resetModules();
    const { evaluateGate: ev } = await import('../../lib/enablement/gate');
    const result = ev({
      tenantId: TENANT,
      userOid: 'oid',
      groups: [GROUP, 'something-else'],
    });
    expect(result.allowed).toBe(true);
  });
});

describe('denyMessage', () => {
  it('returns a non-empty message for every reason', () => {
    for (const r of ['no-principal', 'wrong-tenant', 'wrong-group', 'config-missing'] as const) {
      const msg = denyMessage(r);
      expect(msg.length).toBeGreaterThan(0);
    }
  });
});
