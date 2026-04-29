# UI

## Purpose
Provides the Next.js frontend for Holiday Peak Hub operations and workflows.

## Responsibilities
- Render admin and operations interfaces for retail workflows.
- Call backend APIs for transactional and intelligence scenarios.
- Provide a single web entry point for platform users.

## Key endpoints or interfaces
- Next.js app interface served through the standard web root.
- API integration targets are configured through frontend environment variables.

## Run/Test commands
```bash
yarn --cwd apps/ui install
yarn --cwd apps/ui dev
yarn --cwd apps/ui test
yarn --cwd apps/ui test:coverage
yarn --cwd apps/ui test:e2e
yarn --cwd apps/ui lint
yarn --cwd apps/ui type-check
```

## Coverage and quality gates
- Jest enforces global coverage thresholds (`branches/functions/lines/statements >= 60%`) in `apps/ui/jest.config.js`.
- Baseline critical-flow E2E coverage runs through Playwright (`apps/ui/tests/e2e/critical-flows.spec.ts`).
- Executive demo and operator regression coverage now also includes `apps/ui/tests/e2e/demo-narrative.spec.ts`, `apps/ui/tests/e2e/dark-mode-regression.spec.ts`, and `apps/ui/tests/e2e/cockpit-readiness.spec.ts`.
- Focused unit coverage also validates telemetry persistence for enrichment-backed product loads and graph-summary enrichment calls.

## Configuration notes
- Uses frontend environment variables for backend/API URLs and auth integration.
- Build and runtime behavior are controlled by `apps/ui/package.json` scripts.
- Uses Next.js and TypeScript toolchain configured in the UI app directory.
- Commerce drill-down routes now share `CommerceAgentLayout`, which standardizes the primary-stage robot, side-cast robot, and compact telemetry chip across cart, search, category, product, checkout, orders, order detail, and hint pages.
- Agent profile drawers now expose input/output schemas, curated sample invocations, SSE-backed sample streaming, and an in-place trace explorer backed by the existing admin monitor APIs.
- The compact telemetry chip now hydrates from persisted `_telemetry` emitted by sample streaming, search, product enrichment, and graph-summary invoke paths instead of placeholder state.
- Order detail now keeps `logistics-route-issue-detection` visible as the default side cast until a return flow is actively opened, at which point the duet swaps to returns plus support assistance.
