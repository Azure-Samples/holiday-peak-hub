import type { Metadata } from 'next';

import { CallToAction } from '@/components/molecules/CallToAction';
import { Hero } from '@/components/molecules/Hero';
import { ValuePropGrid } from '@/components/molecules/ValuePropGrid';
import { HomeShell } from '@/components/templates/HomeShell';
import { buildMetadata } from '@/lib/seo';

export const metadata: Metadata = buildMetadata({
  section: 'home',
  description:
    'Pick your lane. Retailers see business outcomes; builders see architecture and reference implementation. Same brand, two cognitive models.',
  path: '/',
});

/**
 * `/` — audience-router home (ADR-034 §1 / ADR-035 §54 / Issue #1059).
 *
 * Composition order is locked at v1 and documented in `docs/ui/ux-patterns.md`:
 *
 *   1. `<Hero kind="audience-router">` — single headline, two equally-weighted CTAs.
 *   2. `<ValuePropGrid cardinality="three">` — Hick's-Law cardinality lock.
 *   3. (No `<Quote>` here — we render only when a production-maturity quote exists.)
 *   4. `<CallToAction tone="audience-pair">` — second-pass CTA per NN/g research.
 *
 * Anti-patterns rejected: no third CTA, no carousel, no autoplay video,
 * no scroll-jacking, no synthetic case studies.
 */
export default function HomePage() {
  return (
    <HomeShell>
      <Hero
        kind="audience-router"
        headline="Intelligent retail, built on Azure's agentic platform."
        sub="Pick your lane. We route you to the right depth of detail."
        primaryCta={{ label: "I'm a retailer", href: '/retailers' }}
        secondaryCta={{ label: "I'm a builder", href: '/builders' }}
        testId="home-hero"
      />
      <ValuePropGrid
        testId="home-value-props"
        cardinality="three"
        items={[
          {
            kind: 'qualitative',
            headline: 'Outcomes for the people who run the business.',
            body: 'Replenishment, segmentation, returns, support — agents that deliver decisions, not dashboards. Every metric on /retailers carries a confidence interval.',
            maturity: 'design-partner',
          },
          {
            kind: 'qualitative',
            headline: 'Architecture for the people who build the business.',
            body: '26 agents across 7 bounded contexts on Azure Foundry. MCP-only agent-to-agent. Three-tier memory. Every claim on /builders carries a maturity badge.',
            maturity: 'design-partner',
          },
          {
            kind: 'qualitative',
            headline: 'Deploy to your tenant in minutes.',
            body: 'A guided deploy flow that targets your Azure subscription. Synthetic data on first run. AGC 90-second blue-green rollback if anything looks wrong.',
            maturity: 'preview',
          },
        ]}
      />
      <CallToAction
        tone="audience-pair"
        headline="Where do you want to start?"
        primary={{ label: 'See retailer outcomes', href: '/retailers' }}
        secondary={{ label: 'See the architecture', href: '/builders' }}
        testId="home-cta-pair"
      />
    </HomeShell>
  );
}
