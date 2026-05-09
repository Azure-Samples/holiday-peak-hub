import {
  scrubEmail,
  scrubHeaders,
  scrubObject,
  scrubOid,
  scrubSubscriptionId,
  scrubText,
} from '../../lib/deploy/logScrub';

/**
 * Pin the deploy-portal log-scrub contract from Epic #1039 / Issue #1035.
 * No subscription id, no email, no auth header should reach the audit
 * forwarder in plaintext.
 */

describe('scrubSubscriptionId / scrubOid / scrubEmail', () => {
  it('produces deterministic prefixed hashes', () => {
    expect(scrubSubscriptionId('00000000-0000-0000-0000-000000000000')).toMatch(/^sub_[a-f0-9]{12}$/);
    expect(scrubOid('user-42')).toMatch(/^oid_[a-f0-9]{12}$/);
    expect(scrubEmail('alice@example.com')).toMatch(/^[a-f0-9]{12}@scrubbed\.local$/);
  });

  it('different inputs produce different hashes', () => {
    expect(scrubSubscriptionId('a')).not.toEqual(scrubSubscriptionId('b'));
    expect(scrubEmail('alice@example.com')).not.toEqual(scrubEmail('bob@example.com'));
  });
});

describe('scrubText', () => {
  it('replaces UUIDs and emails inline', () => {
    const input = 'deployment 11111111-2222-3333-4444-555555555555 by alice@example.com failed';
    const out = scrubText(input);
    expect(out).not.toMatch(/11111111-2222-3333-4444-555555555555/);
    expect(out).not.toMatch(/alice@example\.com/);
    expect(out).toMatch(/sub_[a-f0-9]{12}/);
    expect(out).toMatch(/[a-f0-9]{12}@scrubbed\.local/);
  });

  it('leaves plain prose untouched', () => {
    expect(scrubText('Hello world')).toBe('Hello world');
  });
});

describe('scrubHeaders', () => {
  it('redacts sensitive headers', () => {
    const out = scrubHeaders({
      Authorization: 'Bearer eyJ...',
      Cookie: 'session=abc',
      'X-Ms-Token-Aad-Access-Token': 'eyJ...',
      'User-Agent': 'jest',
    });
    expect(out['Authorization']).toBe('[redacted]');
    expect(out['Cookie']).toBe('[redacted]');
    expect(out['X-Ms-Token-Aad-Access-Token']).toBe('[redacted]');
    expect(out['User-Agent']).toBe('jest');
  });

  it('inline-scrubs UUIDs in non-sensitive header values', () => {
    const out = scrubHeaders({
      'X-Correlation-Id': '11111111-2222-3333-4444-555555555555',
    });
    expect(out['X-Correlation-Id']).toMatch(/^sub_[a-f0-9]{12}$/);
  });
});

describe('scrubObject', () => {
  it('recursively scrubs strings, redacts sensitive keys', () => {
    const out = scrubObject({
      sub: '11111111-2222-3333-4444-555555555555',
      authorization: 'Bearer eyJ...',
      meta: {
        contact: 'alice@example.com',
        ok: true,
        retries: 3,
      },
      tags: ['support', 'alice@example.com'],
    });
    expect(out).toMatchObject({
      authorization: '[redacted]',
      meta: { ok: true, retries: 3 },
    });
    const recovered = out as { sub: string; meta: { contact: string }; tags: string[] };
    expect(recovered.sub).toMatch(/^sub_[a-f0-9]{12}$/);
    expect(recovered.meta.contact).toMatch(/^[a-f0-9]{12}@scrubbed\.local$/);
    expect(recovered.tags[1]).toMatch(/^[a-f0-9]{12}@scrubbed\.local$/);
  });
});
