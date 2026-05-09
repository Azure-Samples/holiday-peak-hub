/**
 * Log-scrub helpers for the deploy-portal (Issue #1035 / Epic #1039).
 *
 * Hard rules from Epic #1039:
 *   - Subscription IDs MUST be scrubbed before write to any log/audit.
 *   - Email addresses MUST be scrubbed before write.
 *   - Authorization headers MUST never reach the audit forwarder in
 *     plaintext.
 *   - Pure functions only. The audit forwarder lives in another layer;
 *     this module exports the building blocks.
 *
 * The deterministic scrubbed forms match `apps/ui/lib/deploy/rateLimits.ts`:
 *   - subscription id → "sub_<sha256[0:12]>"
 *   - email           → "<sha256[0:12]>@scrubbed.local"
 */

import { createHash } from 'node:crypto';

const SHORT_HASH_LENGTH = 12;
const UUID_REGEXP =
  /\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/gi;
const EMAIL_REGEXP = /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi;
const REDACT_HEADERS = new Set([
  'authorization',
  'set-cookie',
  'cookie',
  'x-ms-client-principal',
  'x-ms-client-principal-id',
  'x-ms-client-principal-name',
  'x-ms-arr-clientcert',
  'x-ms-token-aad-id-token',
  'x-ms-token-aad-access-token',
  'x-ms-token-aad-refresh-token',
]);

const sha256Short = (value: string): string =>
  createHash('sha256').update(value).digest('hex').slice(0, SHORT_HASH_LENGTH);

/** Scrub a subscription id to a deterministic short hash. */
export function scrubSubscriptionId(value: string): string {
  return `sub_${sha256Short(value)}`;
}

/** Scrub an email to a deterministic short hash + neutral domain. */
export function scrubEmail(value: string): string {
  return `${sha256Short(value)}@scrubbed.local`;
}

/** Scrub an OID / object id to a deterministic short hash. */
export function scrubOid(value: string): string {
  return `oid_${sha256Short(value)}`;
}

/** Replace UUIDs and emails inline in a free-text string. */
export function scrubText(input: string): string {
  return input
    .replace(UUID_REGEXP, (m) => scrubSubscriptionId(m.toLowerCase()))
    .replace(EMAIL_REGEXP, (m) => scrubEmail(m.toLowerCase()));
}

/**
 * Scrub a header bag — drop sensitive headers entirely; pass through the
 * rest with their values inline-scrubbed.
 */
export function scrubHeaders(
  headers: Record<string, string | string[] | undefined>,
): Record<string, string | string[]> {
  const out: Record<string, string | string[]> = {};
  for (const [k, v] of Object.entries(headers)) {
    if (v === undefined) continue;
    if (REDACT_HEADERS.has(k.toLowerCase())) {
      out[k] = '[redacted]';
      continue;
    }
    out[k] = Array.isArray(v) ? v.map(scrubText) : scrubText(v);
  }
  return out;
}

type Json = string | number | boolean | null | Json[] | { [k: string]: Json };

/** Recursively scrub a JSON-shaped object. Strings are inline-scrubbed. */
export function scrubObject(input: Json): Json {
  if (input === null || typeof input === 'boolean' || typeof input === 'number') {
    return input;
  }
  if (typeof input === 'string') {
    return scrubText(input);
  }
  if (Array.isArray(input)) {
    return input.map(scrubObject);
  }
  const out: { [k: string]: Json } = {};
  for (const [k, v] of Object.entries(input)) {
    if (REDACT_HEADERS.has(k.toLowerCase())) {
      out[k] = '[redacted]';
      continue;
    }
    out[k] = scrubObject(v as Json);
  }
  return out;
}
