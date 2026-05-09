import {
  DEFAULT_RATE_LIMITS,
  anonymizeOid,
  anonymizeSubscriptionId,
  buildRateAuditEntry,
  evaluateRateLimit,
} from '../../lib/deploy/rateLimits';

/**
 * Pin the deploy-portal rate-limit policy from Epic #1039 / Issue #1034.
 * The library is pure-function so we exercise every branch.
 */

const FRESH = {
  activeDeployments24h: 0,
  totalDeployments30d: 0,
  preflightsLastMinute: 0,
  preflightsLastHour: 0,
  tenantBurstFlagged: false,
};

describe('anonymizeOid / anonymizeSubscriptionId', () => {
  it('produces deterministic short hashes', () => {
    expect(anonymizeOid('user-1')).toBe(anonymizeOid('user-1'));
    expect(anonymizeOid('user-1')).not.toBe(anonymizeOid('user-2'));
  });

  it('uses the oid_ prefix', () => {
    expect(anonymizeOid('x')).toMatch(/^oid_[a-f0-9]{12}$/);
  });

  it('uses the sub_ prefix', () => {
    expect(anonymizeSubscriptionId('00000000-0000-0000-0000-000000000000')).toMatch(/^sub_[a-f0-9]{12}$/);
  });

  it('returns oid_missing for empty input', () => {
    expect(anonymizeOid('')).toBe('oid_missing');
  });

  it('returns sub_missing for empty input', () => {
    expect(anonymizeSubscriptionId('')).toBe('sub_missing');
  });
});

describe('evaluateRateLimit — preflight action', () => {
  it('allows a fresh preflight', () => {
    expect(evaluateRateLimit('preflight', FRESH)).toEqual({ decision: 'allow' });
  });

  it('denies when preflight-per-minute exceeded', () => {
    const state = { ...FRESH, preflightsLastMinute: DEFAULT_RATE_LIMITS.preflightsPerMinute };
    expect(evaluateRateLimit('preflight', state)).toEqual({
      decision: 'deny',
      reason: 'preflight-rate-limited',
    });
  });

  it('requires CAPTCHA when preflight-per-hour exceeded', () => {
    const state = {
      ...FRESH,
      preflightsLastMinute: 0,
      preflightsLastHour: DEFAULT_RATE_LIMITS.captchaThresholdPerHour,
    };
    expect(evaluateRateLimit('preflight', state)).toEqual({ decision: 'allow-with-captcha' });
  });
});

describe('evaluateRateLimit — deploy action', () => {
  it('allows a fresh deploy', () => {
    expect(evaluateRateLimit('deploy', FRESH)).toEqual({ decision: 'allow' });
  });

  it('denies when 3-active threshold exceeded', () => {
    const state = { ...FRESH, activeDeployments24h: DEFAULT_RATE_LIMITS.activeDeploymentsPer24h };
    expect(evaluateRateLimit('deploy', state)).toEqual({
      decision: 'deny',
      reason: 'too-many-active',
    });
  });

  it('denies when 10-per-30d threshold exceeded', () => {
    const state = { ...FRESH, totalDeployments30d: DEFAULT_RATE_LIMITS.totalDeploymentsPer30d };
    expect(evaluateRateLimit('deploy', state)).toEqual({
      decision: 'deny',
      reason: 'too-many-30d',
    });
  });
});

describe('evaluateRateLimit — cleanup action', () => {
  it('always allows cleanup, even at saturation', () => {
    const state = {
      ...FRESH,
      activeDeployments24h: 999,
      totalDeployments30d: 999,
      preflightsLastMinute: 999,
    };
    expect(evaluateRateLimit('cleanup', state)).toEqual({ decision: 'allow' });
  });
});

describe('evaluateRateLimit — tenant burst short-circuit', () => {
  it('denies any action when the tenant has been flagged', () => {
    const state = { ...FRESH, tenantBurstFlagged: true };
    expect(evaluateRateLimit('preflight', state)).toEqual({ decision: 'deny', reason: 'tenant-burst' });
    expect(evaluateRateLimit('deploy', state)).toEqual({ decision: 'deny', reason: 'tenant-burst' });
    expect(evaluateRateLimit('cleanup', state)).toEqual({ decision: 'deny', reason: 'tenant-burst' });
  });
});

describe('buildRateAuditEntry', () => {
  it('emits anonymized oid + sub', () => {
    const entry = buildRateAuditEntry({
      action: 'deploy',
      decision: { decision: 'deny', reason: 'too-many-active' },
      oid: 'user-42',
      subscriptionId: '00000000-0000-0000-0000-000000000000',
      pathname: '/deploy/preflight',
    });
    expect(entry.oid).toMatch(/^oid_[a-f0-9]{12}$/);
    expect(entry.sub).toMatch(/^sub_[a-f0-9]{12}$/);
    expect(entry.evt).toBe('deploy.rate-limit');
    expect(entry.action).toBe('deploy');
    expect(entry.decision).toBe('deny');
    expect(entry.reason).toBe('too-many-active');
  });

  it('omits sub when none is supplied', () => {
    const entry = buildRateAuditEntry({
      action: 'preflight',
      decision: { decision: 'allow' },
      oid: 'user-42',
      pathname: '/deploy/preflight',
    });
    expect(entry.sub).toBeUndefined();
  });
});
