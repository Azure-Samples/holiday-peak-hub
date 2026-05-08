# ADR-033: UI as a Modular Monolith on Static Web Apps (Path 2)

**Status**: Accepted
**Date**: 2026-05-08
**Deciders**: Architecture Team, Ricardo Cataldi
**Tags**: frontend, deployment, modular-monolith, static-web-apps, decoupling
**References**: [ADR-011](adr-011-nextjs-app-router.md), [ADR-012](adr-012-atomic-design-system.md), [ADR-016](adr-016-api-client-architecture.md), [ADR-017](adr-017-deployment-strategy.md), [ADR-021](adr-021-apim-agc-edge.md)

## Context

`apps/ui` (Next.js 16.2 + React 19 + Tailwind 4) deploys inside the same AKS rollout pipeline as the backend services. This couples three things that have no business being coupled:

1. **Release cadence** — every UI tweak waits for the AKS + Flux + Helm cycle.
2. **Failure blast radius** — a backend rollback affects UI uptime even when the UI didn't change.
3. **CI minutes** — the UI-only quality gate (`ui-quality`) shares CI capacity with backend lint and test gates.

Two paths were evaluated:

| Dimension | Path 1 — UI in AKS, multi-app federation | **Path 2 — UI on SWA, modular monolith (chosen)** |
|-----------|-------------------------------------------|---------------------------------------------------|
| Cadence | Coupled to backend rollout | Independent — SWA push on UI commit |
| Cost | AKS pod + ingress | SWA serverless (free / standard tier) |
| Operability | Same as backend | Separate dashboard, own SLO |
| Modularity | Multi-app micro-frontend (build-time orchestration) | Modular monolith (single Next.js app, internal feature modules) |
| Risk | Higher fragmentation, federation complexity | Lower — proven Next.js patterns; reversible |
| Ship velocity | Slower (federation tooling work) | Faster (lift-and-shift, then modularize) |

Path 2 was chosen on three rounds of deliberation plus adversarial review. The dissent argued micro-frontends scale better at very large team counts; the rebuttal noted there is one product team today, so micro-frontend complexity is unjustified and the modular-monolith refactor remains reversible.

## Decision

### 1. Modular-Monolith Directory Contract

```
apps/ui/
├── src/
│   ├── app/                          # Next.js App Router routes only — no business logic
│   │   ├── crm/.../page.tsx          # routes import from src/features/crm/*
│   │   ├── ecommerce/.../page.tsx
│   │   └── ...
│   ├── features/
│   │   ├── crm/                      # one feature module per bounded context
│   │   │   ├── components/
│   │   │   ├── hooks/
│   │   │   ├── api.ts                # the only file allowed to import from src/shared/api
│   │   │   ├── types.ts
│   │   │   └── index.ts              # public surface — only exports listed here are reachable from app/
│   │   └── ... (ecommerce, inventory, logistics, product-management, search, truth)
│   └── shared/
│       ├── api/                      # apiClient, agentApiClient, auth headers
│       ├── auth/
│       ├── design-system/            # Tailwind tokens, primitives
│       ├── layout/
│       └── telemetry/                # OTEL JS, App Insights browser SDK
└── eslint.config.mjs                 # no-restricted-imports enforces feature isolation
```

ESLint rule (mandatory):

```js
{
  rules: {
    'no-restricted-imports': ['error', {
      patterns: [
        {
          group: ['../features/*/!(index)', '../features/*/internal/*'],
          message: 'Import features only via their public index.ts',
        },
      ],
    }],
  },
}
```

A cross-feature import outside `src/shared/` is a defect; the lint rule blocks it at PR time.

### 2. Static Web Apps Deployment

- New Bicep module under `infra/swa-ui/` (or extension of `infra/main.bicep`) provisioning the SWA resource and bindings.
- New workflow `.github/workflows/deploy-ui-swa.yml`, path-filtered on `apps/ui/**` and `infra/swa-ui/**`.
- Preview environments enabled per PR.
- SWA built-in auth disabled; existing MSAL flow preserved verbatim.
- Output mode (`static` or `hybrid`) chosen during phase-A inventory based on which Next.js features `apps/ui` actively uses (server actions / RSC require `hybrid`).

### 3. Cutover Mechanism — DNS-Weighted Strangler Fig

DNS weighted records (Azure DNS or Front Door) for the public UI hostname:

| Step | SWA % | AKS % | Hold | Exit gate |
|------|-------|-------|------|-----------|
| 0 | 0 | 100 | n/a | baseline collected |
| 1 | 5 | 95 | 24 h | LCP P75 ≤ baseline + 10 %; INP P75 ≤ baseline + 10 %; CLS unchanged; 5xx parity |
| 2 | 25 | 75 | 24 h | same |
| 3 | 50 | 50 | 24 h | same |
| 4 | 100 | 0 | 30 min steady | same |
| 5 | 100 | 0 (chart deleted) | n/a | post-mortem template completed |

A breach in any step halts the ramp. A breach inside the first 90 s of a step rolls back automatically (DNS weight reverts). DNS TTLs are lowered to 60 s during the ramp and restored after stabilization.

### 4. Hard Sunset

The AKS UI Helm chart is deleted **in the same PR** that ramps to 100 % SWA. No long-lived coexistence. Reverting that PR restores the AKS chart from history if a post-100 % issue forces a regression.

### 5. Telemetry Parity

- Browser-side OTEL spans tagged with `deploy.target ∈ {aks, swa}` for the duration of the ramp.
- Mandatory browser-side attributes (mirroring the spirit of ADR-031): `service.name=ui`, `service.version=<git sha>`, `route` (Next.js route), `tenant.id` (when authenticated), `deploy.target`.
- App Insights workbook updated to filter by `deploy.target`; engineers compare like-for-like.
- Core Web Vitals collected via App Insights browser SDK.
- Server actions / RSC spans propagate `traceparent` to backend agent / CRUD calls.

### 6. Routing Discipline

- Frontend → CRUD: HTTPS REST via APIM (unchanged).
- Frontend → Agent: HTTPS REST via APIM (unchanged).
- Frontend never participates in agent-to-agent calls (those are MCP only, internal — per ADR-030).

## Consequences

### Positive

- UI release cadence decouples from backend cadence — UI ships on commit, not on Flux cycle.
- Backend rollbacks no longer take down the UI.
- SWA preview environments per PR shorten the QA loop.
- Modular-monolith feature isolation makes future extraction (to a separate repo, or to multi-app federation) cheaper.
- Lower hosting cost for the UI tier.

### Negative

- Adds a second deployment surface (SWA) to operate.
- Hybrid Next.js features (edge runtime, ISR, image optimization) need explicit verification under SWA.
- Browser telemetry must be tagged `deploy.target` during the ramp to avoid mixed dashboards.

### Risks

| Risk | Mitigation |
|------|------------|
| SWA hybrid mode incompatible with a Next.js feature `apps/ui` uses (server actions, edge runtime, image optimization, ISR). | Inventory current Next.js feature usage in phase A before SWA provisioning. Pin Next.js version. Replace incompatible features before phase B. |
| Refactor introduces feature-reach regressions (broken imports, missing exports). | Per-feature PRs; each feature gets green CI before the next starts. ESLint isolation rule enforced from day one. |
| LCP regresses on SWA due to cold start. | Pre-render where possible; edge caching; validate in preview before ramp. |
| DNS weighted ramp partially fails — half-cutover state. | Runbook keeps AKS UI healthy throughout; weights reversible in < 60 s. Documented in `docs/ops/runbooks/ui-swa-cutover.md`. |
| Auth regression — SWA built-in auth interferes with MSAL flow. | SWA built-in auth disabled; existing MSAL flow unchanged. Rehearsed in preview before phase C step 1. |
| Browser telemetry diverges between AKS UI and SWA UI during the ramp. | `deploy.target` attribute lets dashboards split. Workbook queries adjusted. |

## Alternatives Considered

### Alternative A — Path 1: UI in AKS with multi-app federation

Rejected. Module Federation / micro-frontends solve a team-scale problem we do not have. Adopting them today would add federation tooling, build orchestration, and cross-app version coordination for zero immediate benefit.

### Alternative B — Replace Next.js with another framework (Astro, Remix, etc.)

Rejected. ADR-011 pins Next.js with App Router. Switching frameworks is out of scope; the decoupling concern is solved without a framework swap.

### Alternative C — Deploy UI to Container Apps instead of SWA

Considered. Container Apps would preserve container-image discipline but lose SWA's preview-per-PR ergonomics and serverless cost profile. Path 2 chooses SWA explicitly for the cadence and cost wins.

## Implementation

| Component | File / Location | Change |
|-----------|----------------|--------|
| ADR | `docs/architecture/adrs/adr-033-ui-modular-monolith-on-swa.md` | This file |
| Bicep | `infra/swa-ui/` (new) | SWA resource, custom domain bindings, Key Vault refs |
| Workflow | `.github/workflows/deploy-ui-swa.yml` | Path-filtered SWA deploy + preview environments |
| Refactor | `apps/ui/src/features/<context>/` | Modular monolith layout per directory contract |
| ESLint | `apps/ui/eslint.config.mjs` | `no-restricted-imports` rule |
| Cutover runbook | `docs/ops/runbooks/ui-swa-cutover.md` (new) | DNS weights, exit gates, rollback procedure |
| Telemetry | `apps/ui/src/shared/telemetry/` | Browser OTEL with `deploy.target` |
| Workbook | `docs/ops/workbooks/ui-cwv.json` (new) | Core Web Vitals split by `deploy.target` |

## Verification

- **Contract test**: a Jest test that imports from a non-`shared` cross-feature path **must fail** in CI (assert via ESLint errors).
- **Smoke**: SWA preview environment renders home, CRM, eCommerce, inventory, logistics, product-management, search, and truth sections without console errors.
- **Performance**: Playwright + Lighthouse runs in CI on the SWA preview, asserts LCP / INP / CLS thresholds.
- **Resilience**: rollback drill — manually flip DNS weights back to 100 % AKS; verify within 60 s end-to-end. Rehearsed before phase C step 4.
- **Telemetry parity**: workbook query reconstructs a request from browser → agent → CRUD with full `traceparent` chain; verified for both `deploy.target` values during the ramp.
- **Auth parity**: MSAL flow rehearsed against SWA preview before phase C step 1.

## Pattern References

- **Strangler Fig** — microservices.io. The AKS UI is gradually strangled by the SWA UI behind weighted DNS.
- **Modular Monolith** — feature modules with explicit public surfaces, ESLint-enforced boundaries. Reversible to multi-app federation later.
- **Canary Release** — microservices.io. The DNS ramp is the canary mechanism for the UI tier.

## References

- [ADR-011 — Next.js 15 with App Router for Frontend](adr-011-nextjs-app-router.md)
- [ADR-012 — Atomic Design System for Component Library](adr-012-atomic-design-system.md)
- [ADR-016 — API Client Architecture](adr-016-api-client-architecture.md)
- [ADR-017 — Deployment Strategy: azd Provisioning + Flux CD GitOps](adr-017-deployment-strategy.md)
- [ADR-021 — APIM + AGC as the Canonical AKS Edge](adr-021-apim-agc-edge.md)
- [Static Web Apps documentation](https://learn.microsoft.com/azure/static-web-apps/)
- [Next.js 16 documentation](https://nextjs.org/docs)
