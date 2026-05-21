import type { Metadata } from 'next';

import { AgentCatalog } from '@/components/molecules/AgentCatalog';
import { CallToAction } from '@/components/molecules/CallToAction';
import { Hero } from '@/components/molecules/Hero';
import { AGENT_CATALOG_DOMAINS } from '@/lib/agents/catalog';
import { buildMetadata } from '@/lib/seo';

export const metadata: Metadata = buildMetadata({
  section: 'retailer',
  description:
    'The 26 agents the platform ships, grouped by bounded context. Per-agent cost-per-1k-requests with a confidence interval; per-agent maturity badge.',
  path: '/retailers/agents',
});

/**
 * `/retailers/agents` — agent catalog (Issue #1041).
 */
export default function RetailerAgentsCatalogPage() {
  return (
    <>
      <Hero
        kind="audience-page"
        headline="The 26 agents shipped today."
        sub="Each row carries a per-1k-request cost band and a maturity badge. The full live SLO + canary view lives on the builder side at /builders/agents."
        primaryCta={{ label: 'See the methodology', href: '/docs/methodology/retailer-roi' }}
        secondaryCta={{ label: 'Compare to point solutions', href: '/retailers/comparators' }}
        testId="retailer-agents-hero"
      />
      <AgentCatalog
        testId="retailer-agents-catalog"
        domains={AGENT_CATALOG_DOMAINS}
        costPopulation="design-partner traffic samples"
        costMethodology="weekly telemetry snapshot, Q4 2025"
        costSampleSize={3}
      />
      <CallToAction
        tone="audience-pair"
        headline="Want the deeper view?"
        primary={{ label: 'Run the ROI calculator', href: '/retailers/roi' }}
        secondary={{ label: 'Read the architecture', href: '/builders/architecture' }}
        testId="retailer-agents-cta-pair"
      />
    </>
  );
}
