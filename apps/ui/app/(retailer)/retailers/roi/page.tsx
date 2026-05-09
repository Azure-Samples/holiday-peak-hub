import type { Metadata } from 'next';

import { CallToAction } from '@/components/molecules/CallToAction';
import { Hero } from '@/components/molecules/Hero';
import { ROICalculator } from '@/components/molecules/ROICalculator';
import { buildMetadata } from '@/lib/seo';

export const metadata: Metadata = buildMetadata({
  section: 'retailer',
  description:
    'Illustrative monthly savings calculator with a confidence interval. Calculations run client-side; no data is collected. Coefficients calibrated against design partners.',
  path: '/retailers/roi',
});

/**
 * `/retailers/roi` — interactive ROI calculator (Issue #1042).
 *
 * Hard rules from Epic #1046:
 *   - "Illustrative" label until 3+ referenceable customer outcomes exist.
 *   - Confidence interval (±40 %) on every output. No point estimates.
 *   - Client-side computation only. No personal data collected. No email gate.
 *   - Methodology link inline + callout to the methodology document.
 */
export default function RetailerRoiPage() {
  return (
    <>
      <Hero
        kind="audience-page"
        headline="What might this be worth on your data?"
        sub="An illustrative calculator built from design-partner observations. Calculations run in your browser; no data is sent anywhere; no email gate."
        primaryCta={{ label: 'Read the methodology', href: '/docs/methodology/retailer-roi' }}
        secondaryCta={{ label: 'Browse the agent catalog', href: '/retailers/agents' }}
        testId="retailer-roi-hero"
      />
      <ROICalculator
        testId="retailer-roi-calculator"
        maturity="design-partner"
        methodologyHref="/docs/methodology/retailer-roi"
      />
      <CallToAction
        tone="audience-pair"
        headline="Want a number that is yours, not ours?"
        primary={{ label: 'Book a 20-minute walkthrough', href: '/contact' }}
        secondary={{ label: 'See the comparator matrix', href: '/retailers/comparators' }}
        testId="retailer-roi-cta-pair"
      />
    </>
  );
}
