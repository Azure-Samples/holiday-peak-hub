# Frontend Development Rules and Policies

**Version**: 2.0  
**Last Updated**: 2026-03-11  
**Owner**: Frontend Team

## Scope

Applies to `apps/ui/` and all front-end libraries/components used by the UI application.

## Runtime and Tooling Baseline

Derived from `apps/ui/package.json`, `apps/ui/.eslintrc.json`, and `apps/ui/tsconfig.json`:

- **Framework**: Next.js `^16.2.0-canary.17`
- **UI runtime**: React 19
- **Language**: TypeScript strict mode
- **Styling**: Tailwind CSS 3.4.0
- **State/query**: Redux Toolkit + TanStack Query
- **Linting**: ESLint 8 (`eslint@^8.57.1`)
- **Testing**: Jest + React Testing Library

## Mandatory Standards

### Architecture and components

- Use App Router conventions and role-based route protection.
- Keep atomic design hierarchy (atoms/molecules/organisms/templates/pages).
- Keep AG-UI and ACP-related contract attributes where required.
- Reuse shared UI patterns; avoid one-off component drift.

### Type safety and quality

- TypeScript strict mode is mandatory.
- No unchecked `any` in new code unless documented and justified.
- Keep imports sorted and avoid dead exports.

### Security and identity

- Front-end authentication uses Microsoft Entra ID (`@azure/msal-browser`, `@azure/msal-react`).
- Do not store secrets in client code or static configuration.
- Keep API access routed through configured gateway endpoints.

## Testing and Validation Policy

- Unit/component tests are required for non-trivial UI behavior.
- Integration behavior for critical flows (checkout, order tracking, auth) must be validated before release.
- Coverage target follows repo baseline (75% minimum), with higher targets recommended for core UI modules.

## Performance and Accessibility

- Optimize critical rendering path and minimize client bundle regressions.
- Prefer server components where feasible and data-safe.
- Keep semantic HTML, keyboard accessibility, and accessible labels on interactive controls.

## Environment Alignment

Front-end deployment and smoke behavior is environment-governed by infrastructure workflows:

- `deploy-azd-dev.yml` supports default dev rollout and optional `uiOnly`
- `deploy-azd-prod.yml` runs from stable tags only
- `deploy-azd.yml` executes APIM/API smoke checks before and after UI deployment

For detailed environment policies, see [Infrastructure Governance](infrastructure-governance.md#environment-policy-matrix).

## ADR References

- ADR-015 Next.js App Router
- ADR-016 Atomic Design System
- ADR-017 AG-UI Protocol
- ADR-018 ACP Frontend
- ADR-019 Authentication and RBAC
- ADR-020 API Client Architecture
- ADR-021 azd-first deployment
