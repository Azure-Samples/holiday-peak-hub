/**
 * Rate-limit + abuse-detection contract for the deploy-portal
 * (Issue #1034 / Epic #1039).
 *
 * Pure-function library — testable without infrastructure. The actual
 * counters live in a backing store (Redis / Cosmos) wired by the API; this
 * module only encodes the policy.
 *
 * Hard rules from Epic #1039:
 *   - 3 active deployments per Entra OID per 24 h.
 *   - 10 total deployments per Entra OID per 30 days.
 *   - 1 pre-flight per OID per minute.
 *   - CAPTCHA after the third pre-flight in 1 h.
 *   - Manual-review flag for tenant bursts.
 *   - All decisions logged with `oid_<sha256[0:12]>` (no plaintext OIDs).
 */

import { createHash } from 'node:crypto';

export type RateAction = 'preflight' | 'deploy' | 'cleanup';

export type RateState = {
  /** Active deployments in the last 24 h. */
  activeDeployments24h: number;
  /** Total deployments in the last 30 days. */
  totalDeployments30d: number;
  /** Pre-flights in the last minute. */
  preflightsLastMinute: number;
  /** Pre-flights in the last hour (used to gate CAPTCHA). */
  preflightsLastHour: number;
  /** Whether tenant-wide burst has been flagged for manual review. */
  tenantBurstFlagged: boolean;
};

export type RateLimitConfig = {
  activeDeploymentsPer24h: number;
  totalDeploymentsPer30d: number;
  preflightsPerMinute: number;
  captchaThresholdPerHour: number;
  /** Burst threshold for tenant-wide manual review. */
  tenantBurstPer1h: number;
};

export const DEFAULT_RATE_LIMITS: RateLimitConfig = {
  activeDeploymentsPer24h: 3,
  totalDeploymentsPer30d: 10,
  preflightsPerMinute: 1,
  captchaThresholdPerHour: 3,
  tenantBurstPer1h: 25,
};

export type RateDecision =
  | { decision: 'allow' }
  | { decision: 'allow-with-captcha' }
  | { decision: 'deny'; reason: 'too-many-active' | 'too-many-30d' | 'preflight-rate-limited' | 'tenant-burst' };

/**
 * Anonymize an Entra OID into an opaque audit-log key.
 *
 * Output format: `oid_<sha256[0:12]>`. The prefix is stable so the audit
 * forwarder can recognise the field without leaking PII.
 */
export function anonymizeOid(oid: string): string {
  if (!oid) return 'oid_missing';
  const hash = createHash('sha256').update(oid).digest('hex').slice(0, 12);
  return `oid_${hash}`;
}

/**
 * Anonymize a subscription id into an audit-log key.
 *
 * Output format: `sub_<sha256[0:12]>`. Used to scrub sub IDs from logs
 * (#1035).
 */
export function anonymizeSubscriptionId(sub: string): string {
  if (!sub) return 'sub_missing';
  const hash = createHash('sha256').update(sub).digest('hex').slice(0, 12);
  return `sub_${hash}`;
}

/**
 * Evaluate the rate-limit + abuse policy for a given action and current
 * counters. Pure function.
 */
export function evaluateRateLimit(
  action: RateAction,
  state: RateState,
  config: RateLimitConfig = DEFAULT_RATE_LIMITS,
): RateDecision {
  if (state.tenantBurstFlagged) {
    return { decision: 'deny', reason: 'tenant-burst' };
  }

  if (action === 'preflight') {
    if (state.preflightsLastMinute >= config.preflightsPerMinute) {
      return { decision: 'deny', reason: 'preflight-rate-limited' };
    }
    if (state.preflightsLastHour >= config.captchaThresholdPerHour) {
      return { decision: 'allow-with-captcha' };
    }
    return { decision: 'allow' };
  }

  if (action === 'deploy') {
    if (state.activeDeployments24h >= config.activeDeploymentsPer24h) {
      return { decision: 'deny', reason: 'too-many-active' };
    }
    if (state.totalDeployments30d >= config.totalDeploymentsPer30d) {
      return { decision: 'deny', reason: 'too-many-30d' };
    }
    return { decision: 'allow' };
  }

  // cleanup is always allowed — we do not gate the user from cleaning up.
  return { decision: 'allow' };
}

/**
 * Render a structured audit-log entry for a rate-limit decision.
 * Subscription IDs and OIDs are anonymized.
 */
export function buildRateAuditEntry(input: {
  action: RateAction;
  decision: RateDecision;
  oid: string;
  subscriptionId?: string;
  pathname: string;
}): Record<string, unknown> {
  return {
    evt: 'deploy.rate-limit',
    action: input.action,
    decision: input.decision.decision,
    reason: 'reason' in input.decision ? input.decision.reason : undefined,
    oid: anonymizeOid(input.oid),
    sub: input.subscriptionId ? anonymizeSubscriptionId(input.subscriptionId) : undefined,
    path: input.pathname,
    at: new Date().toISOString(),
  };
}
