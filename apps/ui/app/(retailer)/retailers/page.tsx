import type { Metadata } from 'next';

import { AgentCardCluster } from '@/components/molecules/AgentCardCluster';
import { CallToAction } from '@/components/molecules/CallToAction';
import { Comparator } from '@/components/molecules/Comparator';
import { Hero } from '@/components/molecules/Hero';
import { ValuePropGrid } from '@/components/molecules/ValuePropGrid';
import { buildMetadata } from '@/lib/seo';

export const metadata: Metadata = buildMetadata({
  section: 'retailer',
  description:
    'Business outcomes, agent catalog, comparators, and procurement starting points for retail leaders. Every metric carries a confidence interval; every claim carries a maturity badge.',
  path: '/retailers',
});

/**
 * `/retailers` — warm-cognitive-model audience page (ADR-034 §1 / ADR-035 §54 / Issue #1059).
 *
 * Composition order (locked at v1, see `docs/ui/ux-patterns.md`):
 *
 *   1. `<Hero kind="audience-page">` — outcome-led headline, single CTA.
 *   2. `<ValuePropGrid cardinality="three-to-five">` — every numbered card carries `<ConfidenceInterval>`.
 *   3. `<Comparator kind="before-after">` — manual workflow vs. agent-assisted, maturity-required.
 *   4. `<AgentCardCluster>` — six representative retail agents linking into `/builders/agents/<slug>`.
 *   5. (Optional `<Quote>` — rendered only when a production-maturity reference exists. Currently omitted.)
 *   6. `<CallToAction tone="single">` — book-a-walkthrough CTA.
 *   7. `<CallToAction tone="procurement">` — RFP-tone CTA near the footer with Trust Center link.
 *
 * Anti-patterns rejected: no carousel of trusted-by logos, no autoplay video,
 * no value-prop card lacking a citation when it carries a number.
 */
export default function RetailersIndexPage() {
  return (
    <>
      <Hero
        kind="audience-page"
        headline="Stop wrestling spreadsheets. Decide faster, with citations."
        sub="Replenishment review, segmentation, returns triage, and support — agents that surface the decision and the math behind it."
        primaryCta={{ label: 'See it on your data', href: '/deploy' }}
        secondaryCta={{ label: 'Book a 20-minute walkthrough', href: '/contact' }}
        testId="retailers-hero"
      />
      <ValuePropGrid
        testId="retailers-value-props"
        cardinality="three-to-five"
        items={[
          {
            kind: 'quantitative',
            headline: 'Replenishment review time, cut from hours to minutes.',
            body: 'Inventory agents reconcile sell-through with on-hand and inbound, then propose orders for buyer review. Buyers ship the queue, they do not build it.',
            maturity: 'design-partner',
            confidence: {
              lower: '35',
              upper: '55',
              unit: 'minutes per buyer per day',
              baseline: { lower: '4', upper: '7', unit: 'hours per buyer per day' },
              sampleSize: 3,
              population: 'design-partner buyers',
              methodology: 'observed time-on-task, 4-week baseline',
            },
          },
          {
            kind: 'quantitative',
            headline: 'Returns triage with explicit reasoning, not a black box.',
            body: 'Every return decision carries the rule that fired, the agent that proposed it, and the data points the agent looked at. Disputes are auditable.',
            maturity: 'design-partner',
            confidence: {
              lower: '18',
              upper: '28',
              unit: '% reduction in dispute escalations',
              sampleSize: 2,
              population: 'design-partner returns desks',
              methodology: 'side-by-side over 6 weeks',
            },
          },
          {
            kind: 'qualitative',
            headline: 'Segmentation that reads like a brief, not a model card.',
            body: 'Customer-segment agents emit human-readable rationales (recency, frequency, AOV deltas, channel mix) that a marketing manager can defend in a campaign review.',
            maturity: 'design-partner',
          },
        ]}
      />
      <Comparator
        kind="before-after"
        headline="Where the time goes — manual workflow vs. agent-assisted."
        description="Three observed workflows from design partners. Each row carries its own maturity badge."
        columns={['Manual workflow', 'Agent-assisted']}
        rows={[
          {
            label: 'Replenishment review',
            before: 'Buyer pivots in 4 sheets, builds order list, emails vendor',
            after: 'Agent proposes orders; buyer approves or edits',
            maturity: 'design-partner',
          },
          {
            label: 'Segmentation refresh',
            before: 'Analyst writes SQL, hands off to marketing, 2-day cycle',
            after: 'Agent emits brief + segment, marketing edits in place',
            maturity: 'design-partner',
          },
          {
            label: 'Returns triage',
            before: 'Agent reads ticket, looks up policy, replies in 8–12 min',
            after: 'Agent drafts response with policy citation; agent edits and sends',
            maturity: 'preview',
          },
        ]}
        maturity="design-partner"
        testId="retailers-comparator"
      />
      <AgentCardCluster
        testId="retailers-agents"
        headline="Six representative agents"
        agents={[
          {
            domain: 'Inventory',
            name: 'JIT Replenishment',
            description:
              'Proposes vendor orders from sell-through, on-hand, and inbound — surfaced for buyer approval.',
            href: '/builders/agents/inventory-jit-replenishment',
          },
          {
            domain: 'Inventory',
            name: 'Reservation Validation',
            description:
              'Holds inventory across cart, checkout, and fulfillment; rolls back ghost holds.',
            href: '/builders/agents/inventory-reservation-validation',
          },
          {
            domain: 'CRM',
            name: 'Segmentation & Personalization',
            description:
              'Emits readable customer-segment briefs with RFV / channel-mix rationale.',
            href: '/builders/agents/crm-segmentation-personalization',
          },
          {
            domain: 'Logistics',
            name: 'ETA Computation',
            description:
              'Composes carrier and route signals into a confidence-banded ETA per order.',
            href: '/builders/agents/logistics-eta-computation',
          },
          {
            domain: 'Logistics',
            name: 'Returns Support',
            description: 'Triages returns against policy, drafts response, escalates exceptions.',
            href: '/builders/agents/logistics-returns-support',
          },
          {
            domain: 'Catalog',
            name: 'Product Detail Enrichment',
            description:
              'Backfills attributes from supplier feeds + image evidence; agent-led, human-reviewed.',
            href: '/builders/agents/ecommerce-product-detail-enrichment',
          },
        ]}
      />
      <CallToAction
        tone="single"
        headline="Want to see this on your data?"
        primary={{ label: 'Book a 20-minute walkthrough', href: '/contact' }}
        caption="A solutions engineer pairs with a buyer / analyst from your team and runs the agent on a representative slice."
        testId="retailers-cta-walkthrough"
      />
      <CallToAction
        tone="procurement"
        headline="Procurement, security, or compliance?"
        primary={{ label: 'Request the RFP packet', href: '/contact?topic=rfp' }}
        trustCenter={{ label: 'Visit the Trust Center', href: '/docs/governance' }}
        testId="retailers-cta-procurement"
      />
    </>
  );
}
