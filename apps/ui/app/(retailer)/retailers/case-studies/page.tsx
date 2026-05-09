import type { Metadata } from 'next';

import { CallToAction } from '@/components/molecules/CallToAction';
import { CaseStudyEmptyState } from '@/components/molecules/CaseStudyEmptyState';
import { Hero } from '@/components/molecules/Hero';
import { buildMetadata } from '@/lib/seo';

export const metadata: Metadata = buildMetadata({
  section: 'retailer',
  description:
    'Reference customers at production maturity will be featured here. Until then, this page is empty by design. No stock-photo case studies, no retroactive logos.',
  path: '/retailers/case-studies',
});

/**
 * `/retailers/case-studies` — case studies (Issue #1044).
 *
 * Hard rules from Epic #1046:
 *   - Maturity badge per case study; design-partner / preview / production.
 *   - Empty state until first reference at production maturity.
 *   - Logos only with written permission. No aspirational placeholders.
 *
 * v1: empty state + design-partner list (anonymized at v1; named when
 * written permission lands).
 */
export default function RetailerCaseStudiesPage() {
  return (
    <>
      <Hero
        kind="audience-page"
        headline="Case studies, when they exist."
        sub="No published references at production maturity yet. We are working with three design partners; they get named here when they give us written permission."
        primaryCta={{ label: 'Become a design partner', href: '/contact?topic=design-partner' }}
        secondaryCta={{ label: 'See the methodology', href: '/docs/methodology/retailer-roi' }}
        testId="retailer-case-studies-hero"
      />
      <CaseStudyEmptyState
        testId="retailer-case-studies-empty"
        maturity="design-partner"
      />
      <CallToAction
        tone="audience-pair"
        headline="Want a number that is yours, not ours?"
        primary={{ label: 'Run the ROI calculator', href: '/retailers/roi' }}
        secondary={{ label: 'See the comparator matrix', href: '/retailers/comparators' }}
        testId="retailer-case-studies-cta-pair"
      />
    </>
  );
}
