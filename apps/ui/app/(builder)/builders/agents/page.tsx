import type { Metadata } from 'next';

import { AgentCatalog } from '@/components/molecules/AgentCatalog';
import { CallToAction } from '@/components/molecules/CallToAction';
import { Hero } from '@/components/molecules/Hero';
import { AGENT_CATALOG_DOMAINS } from '@/lib/agents/catalog';
import { buildMetadata } from '@/lib/seo';

export const metadata: Metadata = buildMetadata({
  section: 'builder',
  title: 'Agent Catalog',
  description:
    'Builder-side catalog for the 26 retail agents: bounded contexts, maturity, cost bands, and per-agent runtime contract pages.',
  path: '/builders/agents',
});

export default function BuilderAgentsCatalogPage() {
  return (
    <>
      <Hero
        kind="audience-page"
        headline="The agent catalog, wired to runtime contracts."
        sub="Browse the 26 retail agents by bounded context. Each card links to the builder detail page with mode, collaborators, KPIs, schemas, and trace entry points."
        primaryCta={{ label: 'See live telemetry', href: '/builders/telemetry' }}
        secondaryCta={{ label: 'Read MCP patterns', href: '/builders/patterns' }}
        testId="builder-agents-hero"
      />
      <AgentCatalog
        testId="builder-agents-catalog"
        domains={AGENT_CATALOG_DOMAINS}
        costPopulation="design-partner traffic samples"
        costMethodology="weekly telemetry snapshot, Q4 2025"
        costSampleSize={3}
        agentHref={(slug) => `/builders/agents/${slug}`}
      />
      <CallToAction
        tone="audience-pair"
        headline="Need the system view behind the cards?"
        primary={{ label: 'Read the architecture', href: '/builders/architecture' }}
        secondary={{ label: 'Switch to retailer catalog', href: '/retailers/agents' }}
        testId="builder-agents-cta-pair"
      />
    </>
  );
}