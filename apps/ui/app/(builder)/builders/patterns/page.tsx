import type { Metadata } from 'next';

import { CallToAction } from '@/components/molecules/CallToAction';
import { Hero } from '@/components/molecules/Hero';
import { RegistryTable, type RegistryTableRow } from '@/components/molecules/RegistryTable';
import { buildMetadata } from '@/lib/seo';

export const metadata: Metadata = buildMetadata({
  section: 'builder',
  description:
    'The locked pattern catalog: modular monolith, MCP-only A2A with hop counter, AGC blue-green canary, three-tier memory, OTEL contract, dual design tokens. Every pattern carries a maturity badge and links to its source.',
  path: '/builders/patterns',
});

/**
 * `/builders/patterns` — locked pattern catalog (Issue #1049 / Epic #1053).
 *
 * The list is locked in the epic. v1 ships these six patterns; new patterns
 * arrive only by ADR. Source links point to the ADR or canonical doc that
 * pins the pattern.
 *
 * Curation discipline:
 *   - The list is the closed set per the epic — adding requires an ADR.
 *   - Every pattern has a maturity badge.
 *   - "Status" is meaningful — preview vs. production vs. design-partner.
 */

type PatternRow = {
  key: string;
  name: string;
  oneLine: string;
  source: { label: string; href: string };
  maturity: 'design-partner' | 'preview' | 'production';
  tags: string[];
};

const PATTERNS: PatternRow[] = [
  {
    key: 'modular-monolith',
    name: 'Modular monolith on Static Web Apps',
    oneLine:
      'apps/ui ships as one deployment unit with feature isolation under src/features/<context>/. No microfrontend complexity.',
    source: {
      label: 'ADR-033',
      href: 'https://github.com/Azure-Samples/holiday-peak-hub/blob/main/docs/architecture/adrs/adr-033-ui-modular-monolith-swa.md',
    },
    maturity: 'preview',
    tags: ['frontend', 'deployment', 'swa'],
  },
  {
    key: 'mcp-only-a2a',
    name: 'MCP-only agent-to-agent (with hop counter)',
    oneLine:
      'Agents communicate exclusively over MCP. The hop counter caps recursive A2A calls and surfaces in telemetry.',
    source: {
      label: 'ADR-024',
      href: 'https://github.com/Azure-Samples/holiday-peak-hub/blob/main/docs/architecture/adrs/adr-024-agent-communication-policy.md',
    },
    maturity: 'design-partner',
    tags: ['agents', 'protocol', 'observability'],
  },
  {
    key: 'agc-canary',
    name: 'AGC weighted blue-green canary',
    oneLine:
      'Application Gateway for Containers routes weighted traffic between blue and green slots; unhealthy rolls back in 90 seconds without operator intervention.',
    source: {
      label: 'ADR-021',
      href: 'https://github.com/Azure-Samples/holiday-peak-hub/blob/main/docs/architecture/adrs/adr-021-apim-agc-edge.md',
    },
    maturity: 'preview',
    tags: ['azure', 'rollback', 'agc'],
  },
  {
    key: 'three-tier-memory',
    name: 'Three-tier memory (hot / warm / cold)',
    oneLine:
      'Hot in Redis (sub-ms), warm in Cosmos (durable + queryable), cold in Blob (cheap + replayable). Promotion and demotion are first-class.',
    source: {
      label: 'ADR-007',
      href: 'https://github.com/Azure-Samples/holiday-peak-hub/blob/main/docs/architecture/adrs/adr-007-memory-tiers.md',
    },
    maturity: 'design-partner',
    tags: ['memory', 'state', 'azure'],
  },
  {
    key: 'otel-contract',
    name: 'OTEL contract for agent telemetry',
    oneLine:
      'Every agent call emits a typed OTEL span with model target (SLM / LLM), token counts, hop counter, and tenant id.',
    source: {
      label: 'docs/observability/otel.md',
      href: 'https://github.com/Azure-Samples/holiday-peak-hub/blob/main/docs/observability/otel.md',
    },
    maturity: 'design-partner',
    tags: ['observability', 'telemetry'],
  },
  {
    key: 'dual-design-tokens',
    name: 'Dual design tokens (retailer warm / builder cool)',
    oneLine:
      'Two token sheets cover retailer-warm and builder-cool palettes; routes are scoped via cascade-layer overrides. ADR-035 §1-§2 pins the contract.',
    source: {
      label: 'ADR-035',
      href: 'https://github.com/Azure-Samples/holiday-peak-hub/blob/main/docs/architecture/adrs/adr-035-ui-design-system.md',
    },
    maturity: 'preview',
    tags: ['design-system', 'tokens', 'ui'],
  },
];

function patternToRow(p: PatternRow): RegistryTableRow {
  return {
    key: p.key,
    cells: [
      { kind: 'text', value: p.name },
      { kind: 'text', value: p.oneLine },
      { kind: 'link', value: p.source.label, href: p.source.href },
      { kind: 'maturity', level: p.maturity },
      { kind: 'tags', values: p.tags },
    ],
  };
}

export default function BuilderPatternsPage() {
  return (
    <>
      <Hero
        kind="audience-page"
        headline="The pattern catalog."
        sub="Six patterns hold the platform together. New patterns arrive only by ADR — the catalog is intentionally closed."
        primaryCta={{ label: 'See ADR registry', href: '/builders/adrs' }}
        secondaryCta={{ label: 'See architecture diagrams', href: '/builders/architecture' }}
        testId="builder-patterns-hero"
      />
      <RegistryTable
        testId="builder-patterns-table"
        headline="Locked patterns"
        description="The platform's six load-bearing patterns. Each links to the ADR or canonical doc that pins it."
        columns={['Pattern', 'One line', 'Source', 'Maturity', 'Tags']}
        rows={PATTERNS.map(patternToRow)}
      />
      <CallToAction
        tone="audience-pair"
        headline="Want to see the runtime numbers?"
        primary={{ label: 'See live telemetry workbook', href: '/builders/telemetry' }}
        secondary={{ label: 'Switch to retailer view', href: '/retailers' }}
        testId="builder-patterns-cta-pair"
      />
    </>
  );
}
