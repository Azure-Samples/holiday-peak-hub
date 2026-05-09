/**
 * App-search page manifest (Issue #1022).
 *
 * The audience-IA route groups (`/retailers/*`, `/builders/*`, `/deploy/*`,
 * plus home) are enumerated here as the static source of truth for the
 * lightweight in-app search index (`AppSearchBox`).
 *
 * Rationale per ADR-034 and capability 42 — two search boxes, NOT one:
 *   - mkdocs Material's built-in search serves `/docs/*`.
 *   - This manifest powers the app-side search box rendered in the audience
 *     section shells.
 *   - Cross-discovery is achieved via explicit "Search the docs" link on the
 *     app box (and "Search the rest of the site" on the docs box, owned by
 *     mkdocs Material overrides — follow-up to this issue).
 *
 * The manifest is intentionally hand-curated rather than crawled from the
 * filesystem. This keeps the index deterministic, search relevance tunable,
 * and the build pipeline platform-independent. The Pagefind binary indexer
 * remains a v1.5 follow-up that consumes this same manifest as `addCustomRecord`
 * input — the data shape is forward-compatible with the Pagefind Node API.
 *
 * Acceptance-criteria traceability:
 *   - Search input rendered in section shells for /retailers/*, /builders/*,
 *     /deploy/* (and home). ✓ via `AppSearchBox` consuming this manifest.
 *   - Search input copy clarifies scope — done in `AppSearchBox` placeholder.
 *   - Cross-link to /docs/search/?q=<term> — done in `AppSearchBox` results.
 *   - Telemetry on cross-search clicks — done via `data-telemetry` event hook.
 */

export type AppAudience = 'home' | 'retailer' | 'builder' | 'deploy';

export type AppPage = {
  /** Absolute path served by Next.js App Router. */
  url: string;
  /** Title shown in result rows; matches the page <h1>. */
  title: string;
  /** Audience taxonomy bucket (mirrors SectionShell variant). */
  audience: AppAudience;
  /** One-sentence summary used as the result body. */
  description: string;
  /** Tokenization hints used by the lightweight matcher. */
  keywords: string[];
};

/**
 * Curated audience-IA page manifest.
 *
 * Order is editorial — most-trafficked landings first, then deep pages by
 * persona-relevance. The matcher does not depend on order; it is preserved
 * here for stable rendering in the empty-query suggestions.
 */
export const APP_PAGES: readonly AppPage[] = [
  {
    url: '/',
    title: 'Holiday Peak Hub',
    audience: 'home',
    description:
      'Audience-segmented platform for retail teams (value, agents, ROI), builders (architecture, ADRs, patterns), and operators (deploy preview).',
    keywords: ['home', 'overview', 'platform', 'audience', 'retail'],
  },
  // ---------- Retailer lane ----------
  {
    url: '/retailers',
    title: 'For Retailers',
    audience: 'retailer',
    description:
      'Retail outcomes — buyer-time savings, dispute reduction, and confidence-banded ROI for merchandising and operations teams.',
    keywords: ['retailer', 'overview', 'value', 'roi', 'merchandising'],
  },
  {
    url: '/retailers/value',
    title: 'Retailer value',
    audience: 'retailer',
    description:
      'Total addressable value for retail customers — 75% buyer-time savings on enrichment, 22% dispute reduction on returns, ±40% CI band.',
    keywords: ['value', 'savings', 'productivity', 'time-to-decision', 'tav', 'roi'],
  },
  {
    url: '/retailers/agents',
    title: 'Agent catalog (retailer view)',
    audience: 'retailer',
    description:
      '26 agent services across CRM, e-commerce, inventory, logistics, product management, search and the truth layer — described in business outcomes, not endpoints.',
    keywords: ['agents', 'catalog', 'capabilities', 'crm', 'ecommerce', 'inventory', 'logistics'],
  },
  {
    url: '/retailers/roi',
    title: 'ROI calculator',
    audience: 'retailer',
    description:
      'Pinned ROI methodology — 75% buyer-time savings, 22% dispute reduction, ±40% confidence-interval band. Adjustable input parameters.',
    keywords: ['roi', 'calculator', 'methodology', 'confidence interval', 'savings'],
  },
  {
    url: '/retailers/comparators',
    title: 'Comparators',
    audience: 'retailer',
    description:
      'Side-by-side comparator matrices — Holiday Peak Hub vs. point solutions and incumbent retail platforms across cost, latency, and connector breadth.',
    keywords: ['comparator', 'compare', 'vs', 'matrix', 'point solutions', 'incumbents'],
  },
  {
    url: '/retailers/case-studies',
    title: 'Case studies',
    audience: 'retailer',
    description:
      'Design-partner case studies and outcomes. Empty-state messaging tracks the design-partner intake pipeline until the first studies publish.',
    keywords: ['case studies', 'design partners', 'outcomes', 'evidence', 'customers'],
  },
  {
    url: '/retailers/security',
    title: 'Security posture (retailer view)',
    audience: 'retailer',
    description:
      'Security registry for retailers — control families, audit cadence, OBO contract for the deploy portal, and incident-response intake links.',
    keywords: ['security', 'compliance', 'controls', 'audit', 'obo', 'incident response'],
  },
  // ---------- Builder lane ----------
  {
    url: '/builders',
    title: 'For Builders',
    audience: 'builder',
    description:
      'Architecture, ADRs, design patterns, telemetry seams, and enablement gates — the engineering surface of Holiday Peak Hub.',
    keywords: ['builder', 'engineering', 'architecture', 'adrs', 'platform'],
  },
  {
    url: '/builders/architecture',
    title: 'Architecture registry',
    audience: 'builder',
    description:
      'Generated architecture-diagram registry indexing every Mermaid C4 view in /docs/architecture. Cross-links to mkdocs source.',
    keywords: ['architecture', 'c4', 'mermaid', 'diagrams', 'registry'],
  },
  {
    url: '/builders/adrs',
    title: 'ADR registry',
    audience: 'builder',
    description:
      'Generated ADR registry — every Architecture Decision Record indexed by status, audience, and ADR number. Cross-links to mkdocs ADR pages.',
    keywords: ['adr', 'decision', 'registry', 'governance', 'architecture'],
  },
  {
    url: '/builders/patterns',
    title: 'Design patterns',
    audience: 'builder',
    description:
      'Curated design-pattern catalog — circuit breaker, bulkhead, rate limiter, change-feed, OBO, idempotency. Each pattern links to a runnable reference.',
    keywords: ['patterns', 'circuit breaker', 'bulkhead', 'rate limiter', 'idempotency', 'obo'],
  },
  {
    url: '/builders/telemetry',
    title: 'Telemetry seams',
    audience: 'builder',
    description:
      'Tracing + metrics + log seams documented at the framework boundary — App Insights schema, OpenTelemetry exporter wiring, retention contracts.',
    keywords: ['telemetry', 'tracing', 'metrics', 'logs', 'app insights', 'opentelemetry'],
  },
  {
    url: '/builders/enablement',
    title: 'Enablement gate',
    audience: 'builder',
    description:
      'Server-side enablement gate + currency contract — controls which builder pages are visible per cohort and audits content currency.',
    keywords: ['enablement', 'gate', 'currency', 'cohort', 'governance'],
  },
  // ---------- Deploy lane ----------
  {
    url: '/deploy',
    title: 'Deploy',
    audience: 'deploy',
    description:
      'One-click deploy preview — pick agents, configure your subscription, run preflight checks, then track provisioning end-to-end.',
    keywords: ['deploy', 'azure', 'azd', 'preview', 'one-click'],
  },
  {
    url: '/deploy/catalog',
    title: 'Deploy — agent catalog',
    audience: 'deploy',
    description:
      '26 agents across 7 domains — pick which agents to provision in your one-click preview. Each domain group includes cost and latency profile.',
    keywords: ['deploy', 'catalog', 'agents', 'domains', 'pick'],
  },
  {
    url: '/deploy/configure',
    title: 'Deploy — configure',
    audience: 'deploy',
    description:
      'Configure your deploy preview — subscription, resource group, region, OBO consent. Inputs validated client-side before preflight.',
    keywords: ['deploy', 'configure', 'subscription', 'region', 'obo', 'consent'],
  },
  {
    url: '/deploy/preflight',
    title: 'Deploy — preflight checks',
    audience: 'deploy',
    description:
      'Six preflight checks — quota, RBAC, region availability, AGC capacity, cost guardrail, cleanup retention. All must pass before kickoff.',
    keywords: ['deploy', 'preflight', 'quota', 'rbac', 'region', 'cost', 'cleanup'],
  },
  {
    url: '/deploy/track',
    title: 'Deploy — track provisioning',
    audience: 'deploy',
    description:
      'Track your deploy preview phase-by-phase — Bicep what-if, role assignment, AKS rollout, AGC route, smoke validation, retention countdown.',
    keywords: ['deploy', 'track', 'provisioning', 'bicep', 'aks', 'agc', 'smoke'],
  },
];

/**
 * Audience filter shape consumed by `AppSearchBox`.
 * Always includes 'home' alongside the requested audience so the homepage
 * stays discoverable from inside any section.
 */
export const AUDIENCE_FILTER: Record<AppAudience, AppAudience[]> = {
  home: ['home', 'retailer', 'builder', 'deploy'],
  retailer: ['home', 'retailer'],
  builder: ['home', 'builder'],
  deploy: ['home', 'deploy'],
};
