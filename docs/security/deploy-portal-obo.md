# Deploy-portal OBO contract

> **Audience.** Security reviewers, retailer architects, internal builders.
>
> **Owner.** Platform engineering team.
>
> **Source of truth.** This document, plus the Bicep skeleton at
> [`infra/deploy-portal/main.bicep`](../../infra/deploy-portal/main.bicep) and the
> rate-limit library at
> [`apps/ui/lib/deploy/rateLimits.ts`](../../apps/ui/lib/deploy/rateLimits.ts).

This document pins the On-Behalf-Of (OBO) OAuth contract for the
deploy-portal service, per **Issue #1031 / Epic #1039**.

## TL;DR

- The deploy-portal service has **zero standing RBAC** on any customer
  subscription.
- Every ARM call against a customer subscription happens **on behalf of the
  signed-in user** via OBO token exchange — never via the service identity.
- Consent is **incremental** and **narrowed to the chosen subscription**
  before the first ARM call.
- Tokens are **never written to logs**, **never persisted**, and **never
  forwarded** to any third-party.

## Why OBO, not service principal

A service principal with broad Owner/Contributor privileges on customer
subscriptions would be a load-bearing security incident waiting to happen.
A leaked SP secret = every customer subscription is at risk simultaneously.

OBO eliminates the standing-privilege blast radius:

- The user's token is short-lived (60 minutes by default; 5 minutes
  refresh window).
- The token is scoped to the resources the user has consented to.
- A token leak compromises **one user's session**, not the entire
  customer base.

## Token flow

```mermaid
sequenceDiagram
    participant User
    participant Browser
    participant DeployPortalSPA
    participant DeployPortalAPI
    participant Entra as Microsoft Entra
    participant ARM as Azure Resource Manager

    User->>Browser: Visit /deploy/configure
    Browser->>DeployPortalSPA: Sign-in (User.Read)
    DeployPortalSPA->>Entra: Authorization code flow + PKCE
    Entra-->>DeployPortalSPA: Access token (User.Read)
    Note right of DeployPortalSPA: Step 1 sign-in done; tenant selected.

    User->>DeployPortalSPA: Pick subscription
    DeployPortalSPA->>Entra: Incremental consent — request<br/>https://management.azure.com/user_impersonation<br/>narrowed to /subscriptions/{subId}
    Entra-->>DeployPortalSPA: Access token (ARM scope, narrowed)

    DeployPortalSPA->>DeployPortalAPI: POST /preflight {token, subId, rg, region, agents}
    DeployPortalAPI->>Entra: OBO exchange using user token
    Entra-->>DeployPortalAPI: ARM token on behalf of user
    DeployPortalAPI->>ARM: Pre-flight checks (read quota, list RGs)
    ARM-->>DeployPortalAPI: Results
    DeployPortalAPI-->>DeployPortalSPA: Pre-flight panel data

    User->>DeployPortalSPA: Click "Launch"
    DeployPortalSPA->>DeployPortalAPI: POST /deploy {token, payload}
    DeployPortalAPI->>Entra: OBO exchange (fresh)
    Entra-->>DeployPortalAPI: ARM token (fresh)
    DeployPortalAPI->>ARM: ARM template deployment (Incremental, onErrorDeployment SpecificDeployment)
    ARM-->>DeployPortalAPI: Deployment id
    DeployPortalAPI-->>DeployPortalSPA: 202 Accepted + deploymentId
```

## Scopes and consent

| Step | Scope requested | Why |
|------|-----------------|-----|
| Sign-in | `User.Read` | Surface the user's name, email, tenant id. |
| Subscription pick | `https://management.azure.com/user_impersonation` narrowed to `/subscriptions/{subId}` | Read subscription state; list resource groups. |
| Pre-flight | (no new scope) | Reuses ARM scope from the previous step. |
| Deploy | (no new scope) | Reuses ARM scope from the previous step. |
| Cleanup | (no new scope) | Reuses ARM scope from the previous step. |

**No incremental consent is asked for after the subscription pick.** Every
subsequent action runs under the same narrowed ARM scope.

If the user picks a different subscription on a subsequent visit, a fresh
incremental consent is requested. The previous narrow consent is not
preserved across subscription changes.

## Token handling

- The user's access token is **never persisted** server-side.
- The OBO-exchanged ARM token is held in memory for the duration of a
  single API request, then released.
- The user's refresh token is held only in the SPA, in memory; not in
  `localStorage`, not in `sessionStorage`, not in cookies.
- The deploy-portal service has its own managed identity that authenticates
  to Cosmos and Key Vault. **That identity has zero RBAC on any customer
  subscription.** Quarterly RBAC audit verifies this.

## Audit logging

Every ARM call carries the user's anonymized OID and the anonymized
subscription id:

```json
{
  "evt": "deploy.arm-call",
  "method": "PUT",
  "path": "/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Resources/deployments/{name}",
  "oid": "oid_<sha256[0:12]>",
  "sub": "sub_<sha256[0:12]>",
  "rg": "<resource group name, plaintext>",
  "outcome": "200 | 4xx | 5xx",
  "at": "<ISO timestamp>"
}
```

The anonymization happens in `apps/ui/lib/deploy/rateLimits.ts`
(`anonymizeOid`, `anonymizeSubscriptionId`). Both are pure functions; the
SHA-256 prefix is deterministic per OID/sub but reversible only with the
plaintext input.

## Threat model

| Threat | Mitigation |
|--------|------------|
| OAuth scope creep — service ends up with broad ARM privileges | OBO only; no service-side standing RBAC; quarterly RBAC audit. |
| Stolen access token | Short TTL (60 min default); refresh token stays in SPA memory; no token persistence. |
| Stolen refresh token | Refresh token rotation on use; revocation immediately disables further exchanges. |
| Replay against ARM | ARM enforces token validation; deploy-portal additionally rate-limits per OID. |
| Cross-tenant token | v1 single-tenant. Cross-tenant tokens are explicitly rejected at the OBO exchange step (Entra returns `unauthorized_client`). |
| Privilege escalation through a malicious agent definition | Catalog content is repo-controlled; PR review required; signed module artifacts. |
| Privilege escalation through ARM template injection | Template parameters are typed and validated; only fields the user supplies in the configure form reach the deployment. |
| Token leakage in logs | Audit forwarder filters `Authorization`, `Set-Cookie`, `x-ms-client-principal` headers before write. |

## Pen-test scope

The third-party or Microsoft Red Team penetration test (gated pre-GA per
Epic #1039) MUST cover:

1. OBO scope creep — verify a token narrowed to subscription A cannot
   reach subscription B.
2. Cross-tenant token — verify a token from a different tenant is
   rejected at the OBO exchange.
3. ARM passthrough abuse — verify the user-supplied configure form fields
   cannot inject parameters into the ARM template that escape sanitisation.
4. Refresh-token theft — verify a stolen refresh token is bounded by the
   sub scope and is revocable.
5. Rate-limit bypass — verify the per-OID counter cannot be evaded by
   recycling the OID.

## Configuration

Required env (server-side only):

```
DEPLOY_PORTAL_TENANT_ID = <Microsoft Entra tenant id>
DEPLOY_PORTAL_API_CLIENT_ID = <Entra app registration id for the API>
DEPLOY_PORTAL_API_CLIENT_SECRET = <stored in Key Vault, never in logs>
DEPLOY_PORTAL_REDIRECT_URI = https://<host>/auth/callback
```

The deploy-portal SPA reads only:

```
NEXT_PUBLIC_DEPLOY_PORTAL_API_URL = <APIM gateway URL>
NEXT_PUBLIC_DEPLOY_PORTAL_CLIENT_ID = <Entra app registration id for the SPA>
NEXT_PUBLIC_DEPLOY_PORTAL_TENANT_ID = <Microsoft Entra tenant id>
```

The SPA never sees the API client secret. The API never sees the user's
client-side state.

## Anti-patterns

- ❌ Don't use a service principal with `Contributor` on the customer
  subscription. OBO only.
- ❌ Don't persist the user's access or refresh tokens server-side.
- ❌ Don't request consent for ARM scopes that are not needed for the
  current step.
- ❌ Don't ship a v1 with cross-tenant support; defer to a separate ADR.
- ❌ Don't write tokens, sub IDs, or emails to logs in plaintext.

## Cross-references

- [Bicep skeleton — deploy-portal main](../../infra/deploy-portal/main.bicep)
- [Bicep skeleton — deploy-portal module](../../infra/deploy-portal/modules/portal.bicep)
- [Rate-limit library](../../apps/ui/lib/deploy/rateLimits.ts)
- [Cleanup contract](../governance/deploy-portal-cleanup-contract.md)
- [`/retailers/security`](../../apps/ui/app/(retailer)/retailers/security/page.tsx) — public security posture
- Issue #1031, Issue #1027, Issue #1034, Issue #1035

## Changelog

| Date | Change | Owner |
|------|--------|-------|
| 2025-11-04 | Initial baseline (Issue #1031 / Epic #1039) | tech-manager |
