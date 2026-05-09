import type { Metadata } from 'next';

import { CallToAction } from '@/components/molecules/CallToAction';
import { Hero } from '@/components/molecules/Hero';
import { ValuePropGrid } from '@/components/molecules/ValuePropGrid';
import { buildMetadata } from '@/lib/seo';

export const metadata: Metadata = buildMetadata({
  section: 'retailer',
  description:
    'Why this platform: open-source, Azure-native, multi-agent orchestration with bounded contexts, deploys on your tenant. Three pillars, every metric carries a confidence interval.',
  path: '/retailers/value',
});

/**
 * `/retailers/value` — three-pillar value proposition (Issue #1040).
 *
 * Differentiation messaging is the four-column claim distilled into a hero
 * sub and reinforced by three pillars: scope, economics, trust.
 *
 * Hard rules from Epic #1046:
 *   - No vanity metrics. Every number carries a confidence interval.
 *   - "Why us, not them" callout links to /retailers/comparators.
 *   - One brand, one domain — no microsites.
 */
export default function RetailerValuePage() {
  return (
    <>
      <Hero
        kind="audience-page"
        headline="The agent platform that survives procurement, audit, and a real ops meeting."
        sub="Open-source, Azure-native, multi-agent orchestration with bounded contexts — deployed on your own tenant. No vendor lock-in, no opaque models, no vanity metrics."
        primaryCta={{ label: 'See it on your data', href: '/deploy' }}
        secondaryCta={{ label: 'Book a 20-minute walkthrough', href: '/contact' }}
        testId="retailer-value-hero"
      />
      <ValuePropGrid
        testId="retailer-value-pillars"
        cardinality="three-to-five"
        items={[
          {
            kind: 'quantitative',
            headline: 'Scope: bounded-context agents, not a single oracle.',
            body: '26 agents across 7 bounded contexts (CRM, e-commerce, inventory, logistics, product management, search, truth). Each agent owns its data, its policies, and its failure modes — so a returns-triage outage cannot break replenishment.',
            maturity: 'design-partner',
            confidence: {
              lower: '26',
              upper: '26',
              unit: 'production agents shipped to design partners',
              sampleSize: 3,
              population: 'design-partner deployments',
              methodology: 'count, observed Q4 2025',
            },
          },
          {
            kind: 'quantitative',
            headline: 'Economics: per-agent cost ceilings you can plan against.',
            body: 'Each agent has documented per-1k-request cost ceilings, daily caps, and SLM-first routing. The expensive LLM only runs when the SLM cannot decide. Buyers get the same answer for less.',
            maturity: 'design-partner',
            confidence: {
              lower: '60',
              upper: '85',
              unit: '% of requests handled by SLM (no LLM call)',
              sampleSize: 3,
              population: 'design-partner traffic samples',
              methodology: 'measured over 30-day windows, Q4 2025',
            },
          },
          {
            kind: 'qualitative',
            headline: 'Trust: deployed on your tenant; auditable; reversible.',
            body: 'Bicep-defined infrastructure on your Azure subscription. Every agent decision is logged with the policies it consulted and the data it read. AGC blue-green rollback in 90s. Exit and portability are first-class — your data stays in your tenant.',
            maturity: 'design-partner',
          },
        ]}
      />
      <CallToAction
        tone="single"
        headline="Why us, not them?"
        primary={{
          label: 'See the comparator matrix',
          href: '/retailers/comparators',
        }}
        caption="Point-solution AI vendors lined up against this platform. Every cell carries the date it was verified and the source of the claim."
        testId="retailer-value-cta-comparators"
      />
      <CallToAction
        tone="audience-pair"
        headline="Pick your next stop."
        primary={{
          label: 'Browse the agent catalog',
          href: '/retailers/agents',
        }}
        secondary={{
          label: 'Switch to the builder lane',
          href: '/builders',
        }}
        testId="retailer-value-cta-pair"
      />
    </>
  );
}
