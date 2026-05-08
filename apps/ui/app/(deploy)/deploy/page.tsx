import type { Metadata } from 'next';

import { CallToAction } from '@/components/molecules/CallToAction';
import { DeployStepCluster } from '@/components/molecules/DeployStepCluster';
import { DocsCardCluster } from '@/components/molecules/DocsCardCluster';
import { FeatureMatrix } from '@/components/molecules/FeatureMatrix';
import { Hero } from '@/components/molecules/Hero';
import { buildMetadata } from '@/lib/seo';

export const metadata: Metadata = buildMetadata({
  section: 'deploy',
  description:
    'Deploy agentic retail to your Azure tenant. Synthetic data on first run. AGC 90-second rollback. Five steps, end to end.',
  path: '/deploy',
});

/**
 * `/deploy` — operational audience page (ADR-034 §1 / ADR-035 §54 / Issue #1059).
 *
 * Composition order (locked at v1, see `docs/ui/ux-patterns.md`):
 *
 *   1. `<Hero kind="audience-page">` — operational headline naming prerequisites, single CTA.
 *   2. `<DeployStepCluster>` — 5 steps (sign in, pick subscription, name deployment, review estimated cost, launch).
 *      Steps 1 and 4 are stateful (the actual sign-in and live cost preview ship in epic #1039).
 *      The cluster is the only stateful client composite on `/deploy`.
 *   3. `<FeatureMatrix>` — what gets deployed, in what region, what is mocked vs. real.
 *   4. `<DocsCardCluster>` — what to do after deploy, rollback procedure, tear-down.
 *   5. `<CallToAction tone="single">` — start CTA at the bottom (mirror of the hero CTA).
 *
 * The cost-preview step (step 4) shows a range with an explicit
 * non-contractual disclaimer and a more-prominent link to the canonical
 * Azure cost calculator than the in-page number. Legal text is one short
 * sentence per ADR-035 §54.
 */
export default function DeployIndexPage() {
  return (
    <>
      <Hero
        kind="audience-page"
        headline="Deploy agentic retail to your Azure tenant."
        sub="Prerequisites: an Azure subscription and a Microsoft Entra tenant. The first run uses synthetic data so you can poke at it without lighting up real spend."
        primaryCta={{ label: 'Start', href: '#deploy-steps' }}
        secondaryCta={{
          label: 'Open the canonical Azure cost calculator',
          href: 'https://azure.microsoft.com/en-us/pricing/calculator/',
        }}
        testId="deploy-hero"
      />
      <DeployStepCluster
        testId="deploy-steps"
        headline="Five steps, end to end"
        description="Steps 1 and 4 require client-side state (sign-in flow, live cost preview). The other steps are server-rendered."
        steps={[
          {
            headline: 'Sign in',
            summary:
              'Authenticate with the Microsoft Entra tenant that owns the subscription you want to deploy to. We never see your credentials.',
            stateful: true,
          },
          {
            headline: 'Pick a subscription',
            summary:
              'Choose the subscription and resource group. We surface only the ones you have Owner or Contributor on.',
          },
          {
            headline: 'Name the deployment',
            summary:
              'Give the deployment a short, lowercase name (used as a prefix for the resource names). Region selection happens here too.',
          },
          {
            headline: 'Review the estimated cost',
            summary:
              'A live range based on Azure Retail Prices. Estimated, varies by region; not a contractual quote.',
            stateful: true,
          },
          {
            headline: 'Launch',
            summary:
              'We hand off to ARM, then stream live status. If anything is unhealthy after launch, AGC rolls the slot back in 90 seconds.',
          },
        ]}
      />
      <FeatureMatrix
        testId="deploy-feature-matrix"
        headline="What gets deployed"
        description="Region and maturity per capability. We do not list roadmap items as available."
        showRegion
        rows={[
          {
            capability: 'CRUD service (FastAPI)',
            summary: 'Transactional service for products, orders, cart. Container Apps + Cosmos DB.',
            availability: 'available',
            region: 'Same as deployment',
            maturity: 'design-partner',
          },
          {
            capability: '26 agent services',
            summary: 'CRM, ecommerce, inventory, logistics, product-management, search, truth.',
            availability: 'available',
            region: 'Same as deployment',
            maturity: 'design-partner',
          },
          {
            capability: 'Three-tier memory',
            summary: 'Redis (hot), Cosmos DB (warm), Blob Storage (cold).',
            availability: 'available',
            region: 'Same as deployment',
            maturity: 'design-partner',
          },
          {
            capability: 'AGC blue-green',
            summary: 'Application Gateway for Containers, weighted canary, 90-second rollback.',
            availability: 'preview',
            region: 'Same as deployment',
            maturity: 'preview',
          },
          {
            capability: 'Synthetic data on first run',
            summary: 'Mock products, orders, customers seeded so you can poke at the platform.',
            availability: 'mocked',
            region: 'In-cluster',
            maturity: 'preview',
          },
        ]}
      />
      <DocsCardCluster
        testId="deploy-docs"
        headline="After you deploy"
        cards={[
          {
            kicker: 'Runbook',
            title: 'What to do after deploy',
            description: 'Smoke checks, sample queries, switching to your real data.',
            href: '/docs/ops/post-deploy',
          },
          {
            kicker: 'Runbook',
            title: 'Rollback procedure',
            description: 'How AGC rolls back automatically, and how to roll back manually if needed.',
            href: '/docs/ops/rollback',
          },
          {
            kicker: 'Runbook',
            title: 'Tear-down',
            description: 'Delete the resource group and re-claim the spend in one step.',
            href: '/docs/ops/teardown',
          },
        ]}
      />
      <CallToAction
        tone="single"
        headline="Ready when you are."
        primary={{ label: 'Start', href: '#deploy-steps' }}
        caption="Synthetic data first. Switch to your real data after you've poked at the platform."
        testId="deploy-cta-start"
      />
    </>
  );
}
