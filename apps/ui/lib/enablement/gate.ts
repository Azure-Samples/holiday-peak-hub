/**
 * Server-side gate for `/builders/enablement/*` (Issue #1051 / Epic #1053).
 *
 * Hard rules from Epic #1053:
 *   - Microsoft tenant filter + `Microsoft Retail GTM` group filter.
 *   - Server-side enforcement (NOT client-side).
 *   - Failures redirect to `/builders/architecture`.
 *   - Audit log per access.
 *
 * Implementation contract
 * =======================
 * The gate reads three pieces of state on the server:
 *
 *   1. The Entra ID JWT carried in `Authorization: Bearer <token>` or the
 *      Static Web Apps `x-ms-client-principal` header.
 *   2. The `tid` (tenant id) claim — must match `ENABLEMENT_TENANT_ID`.
 *   3. The `groups` claim (or roles) — must include
 *      `ENABLEMENT_GROUP_ID` (the Microsoft Retail GTM security group OID).
 *
 * If any of those checks fail, the gate returns null and the calling layout
 * issues a `redirect('/builders/architecture')`.
 *
 * Audit logging
 * =============
 * Every access (allow OR deny) writes to console.info as a structured JSON
 * line; the SWA log forwarder ships it to App Insights. Log format:
 *
 *     {
 *       "evt": "enablement.access",
 *       "decision": "allow" | "deny",
 *       "reason": "ok" | "no-principal" | "wrong-tenant" | "wrong-group" | "config-missing",
 *       "tenant_id": "<tid claim>",
 *       "user_oid": "<oid claim>",
 *       "path": "<request path>",
 *       "at": "<ISO timestamp>"
 *     }
 *
 * Configuration
 * =============
 * Required env (server-side only, never NEXT_PUBLIC_*):
 *
 *     ENABLEMENT_TENANT_ID = <Microsoft tenant id GUID>
 *     ENABLEMENT_GROUP_ID  = <Microsoft Retail GTM security group OID>
 *
 * If either is missing, every request DENIES with reason "config-missing".
 * This is the safe default — the gate fails closed, not open.
 */

export type EnablementPrincipal = {
  tenantId: string;
  userOid: string;
  groups: string[];
  displayName?: string;
};

export type EnablementGateResult =
  | { allowed: true; principal: EnablementPrincipal }
  | {
      allowed: false;
      reason: 'no-principal' | 'wrong-tenant' | 'wrong-group' | 'config-missing';
    };

const TENANT_ID = process.env.ENABLEMENT_TENANT_ID ?? '';
const GROUP_ID = process.env.ENABLEMENT_GROUP_ID ?? '';

/**
 * Decode the SWA `x-ms-client-principal` header value. Returns null when the
 * header is absent or malformed.
 *
 * @see https://learn.microsoft.com/azure/static-web-apps/user-information
 */
export function decodeSwaPrincipal(headerValue: string | null | undefined): EnablementPrincipal | null {
  if (!headerValue) return null;
  try {
    const decoded = Buffer.from(headerValue, 'base64').toString('utf-8');
    const parsed = JSON.parse(decoded) as {
      identityProvider?: string;
      userId?: string;
      userDetails?: string;
      userRoles?: string[];
      claims?: Array<{ typ: string; val: string }>;
    };
    const claims = parsed.claims ?? [];
    const tenantId =
      claims.find((c) => c.typ === 'tid' || c.typ === 'http://schemas.microsoft.com/identity/claims/tenantid')
        ?.val ?? '';
    const userOid =
      claims.find((c) => c.typ === 'oid' || c.typ === 'http://schemas.microsoft.com/identity/claims/objectidentifier')
        ?.val ?? parsed.userId ?? '';
    const groups = claims
      .filter((c) => c.typ === 'groups' || c.typ === 'http://schemas.microsoft.com/ws/2008/06/identity/claims/groups')
      .map((c) => c.val);
    return {
      tenantId,
      userOid,
      groups,
      displayName: parsed.userDetails,
    };
  } catch {
    return null;
  }
}

export function evaluateGate(principal: EnablementPrincipal | null): EnablementGateResult {
  if (!TENANT_ID || !GROUP_ID) return { allowed: false, reason: 'config-missing' };
  if (!principal) return { allowed: false, reason: 'no-principal' };
  if (principal.tenantId !== TENANT_ID) return { allowed: false, reason: 'wrong-tenant' };
  if (!principal.groups.includes(GROUP_ID)) return { allowed: false, reason: 'wrong-group' };
  return { allowed: true, principal };
}

export function logAccess(
  decision: 'allow' | 'deny',
  reason: 'ok' | 'no-principal' | 'wrong-tenant' | 'wrong-group' | 'config-missing',
  principal: EnablementPrincipal | null,
  pathname: string,
): void {
  // structured single-line audit log; SWA log forwarder ships to App Insights
  // eslint-disable-next-line no-console
  console.info(
    JSON.stringify({
      evt: 'enablement.access',
      decision,
      reason,
      tenant_id: principal?.tenantId ?? null,
      user_oid: principal?.userOid ?? null,
      path: pathname,
      at: new Date().toISOString(),
    }),
  );
}

export function denyMessage(
  reason: 'no-principal' | 'wrong-tenant' | 'wrong-group' | 'config-missing',
): string {
  switch (reason) {
    case 'no-principal':
      return 'You are not signed in. This subtree is only available to the Microsoft Retail GTM group.';
    case 'wrong-tenant':
      return 'Your tenant is not authorised. This subtree is gated to the Microsoft tenant.';
    case 'wrong-group':
      return 'Your account is not in the Microsoft Retail GTM group. Ask the GTM lead to add you.';
    case 'config-missing':
    default:
      return 'Enablement gating is not configured for this deployment. Set ENABLEMENT_TENANT_ID and ENABLEMENT_GROUP_ID to enable it.';
  }
}
