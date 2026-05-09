# Documentation as part of the platform

> **Audience.** Builders contributing to the docs subtree, platform engineers
> running the SWA pipeline.
>
> **Owner.** Platform engineering team (build pipeline) + content librarian
> (content placement), per `.github/instructions/team-mapping.instructions.md`.

This document pins how the mkdocs Material site under `mkdocs/` is shipped
**as part of the platform**, mounted at `/docs/*` on the same SWA host —
not as a separate microsite. Per **Issue #1023 / Epic #1026**.

## TL;DR

- `mkdocs/mkdocs.yml` is the canonical config; `docs_dir: ../docs`.
- `mkdocs/requirements.txt` pins the toolchain (mkdocs Material + plugins).
- `.github/workflows/deploy-ui-swa.yml` runs `python -m mkdocs build`
  before the SWA upload step, with site output written to
  `apps/ui/public/docs/`.
- `apps/ui/staticwebapp.config.json` carries a `/docs/*` route block so
  SWA passes the path through to the built mkdocs site without falling
  back to the SPA.
- `apps/ui/public/docs/` is **gitignored**. The site is regenerated on
  every deploy.
- `--strict` mode is **off in v1**. The docs subtree carries ~130
  pre-existing link warnings; the workflow var `MKDOCS_STRICT_BUILD` flips
  strict mode on once those clear zero (final pass of #1021).

## Build flow

```mermaid
flowchart LR
  A[deploy-ui-swa workflow] --> B[Setup Python 3.13]
  B --> C[pip install -r mkdocs/requirements.txt]
  C --> D[mkdocs build --site-dir apps/ui/public/docs]
  D --> E[Next.js build]
  E --> F[SWA upload]
  F --> G[/ on SWA]
  F --> H[/docs/* on SWA]
```

The mkdocs build runs **before** the Next.js build so the doc subtree is
present when SWA snapshots `apps/ui/public/`.

## Cross-linking

Two molecules carry the docs ↔ app cross-link contract:

- `apps/ui/components/molecules/ReadTheDocsCta.tsx` (#1025) — bottom-of-page
  link from a value/pattern page to the canonical mkdocs deep page.
- `apps/ui/components/molecules/TryThisInTheAppCta.tsx` (#1024) — link
  from a docs page back to the live app surface.

Both molecules are server-rendered, accessible, and consume only the
audience-route ESLint contract (no `style={{}}` on audience pages, all
visual styling encapsulated in the molecule itself).

## Two search boxes, not one (deferred follow-up)

Per Epic #1026 the v2 ships **two search boxes**: mkdocs Material's
built-in search for `/docs/*`, plus a Pagefind index for `/retailers/*`,
`/builders/*`, `/deploy/*`. The Pagefind integration is deferred to a
follow-up; the first PR ships only the mkdocs build pipeline + cross-link
CTAs + sitemap deep-page expansion.

## Strict mode roadmap

- ✅ v1 (this PR) — workflow integration, non-strict build.
- ⏳ v1.1 — clean up the 130 pre-existing link warnings inherited from
  earlier editorial passes.
- ⏳ v1.2 — flip `vars.MKDOCS_STRICT_BUILD` to `true` so the workflow
  runs `mkdocs build --strict`.

The strict gate eventually catches:
- Broken in-doc links and missing anchors.
- Plugin errors.
- Theme override drift.

Until v1.2 the workflow runs non-strict and surfaces warnings only.

## Cross-references

- [Workflow](../../.github/workflows/deploy-ui-swa.yml)
- [mkdocs config](../../mkdocs/mkdocs.yml)
- [SWA route config](../../apps/ui/staticwebapp.config.json)
- [Sitemap](../../apps/ui/app/sitemap.ts)
- [`ReadTheDocsCta` molecule](../../apps/ui/components/molecules/ReadTheDocsCta.tsx)
- [`TryThisInTheAppCta` molecule](../../apps/ui/components/molecules/TryThisInTheAppCta.tsx)
- Issue #1021, Issue #1023, Issue #1024, Issue #1025

## Changelog

| Date | Change | Owner |
|------|--------|-------|
| 2025-11-04 | Initial baseline (Epic #1026) | tech-manager |
