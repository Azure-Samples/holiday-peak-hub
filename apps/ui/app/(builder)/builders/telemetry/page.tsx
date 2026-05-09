import type { Metadata } from 'next';

import { CallToAction } from '@/components/molecules/CallToAction';
import { Hero } from '@/components/molecules/Hero';
import { TelemetryEmbed } from '@/components/molecules/TelemetryEmbed';
import { buildMetadata } from '@/lib/seo';

export const metadata: Metadata = buildMetadata({
  section: 'builder',
  description:
    'Public demo App Insights workbook. Hourly refresh. No customer data — this is the public demo deployment, not production customer telemetry.',
  path: '/builders/telemetry',
});

const WORKBOOK_URL = process.env.NEXT_PUBLIC_TELEMETRY_WORKBOOK_URL ?? '';

/**
 * `/builders/telemetry` — App Insights workbook iframe with demo banner
 * (Issue #1050 / Epic #1053).
 *
 * The workbook URL is configured via env (set during SWA deploy when the
 * public-demo workbook is provisioned). When absent, the embed renders a
 * placeholder explaining how to wire it. The banner renders unconditionally,
 * BEFORE the iframe in source order.
 */
export default function BuilderTelemetryPage() {
  return (
    <>
      <Hero
        kind="audience-page"
        headline="The runtime, on the page."
        sub="App Insights workbook from the public demo deployment. No customer data. Hourly refresh."
        primaryCta={{ label: 'See architecture diagrams', href: '/builders/architecture' }}
        secondaryCta={{ label: 'Browse pattern catalog', href: '/builders/patterns' }}
        testId="builder-telemetry-hero"
      />
      <TelemetryEmbed
        testId="builder-telemetry-embed"
        workbookUrl={WORKBOOK_URL || undefined}
        caption="Workbook source: infra/observability/workbooks/public-demo.bicep. Ingestion is capped at the data-source level to control cost."
      />
      <CallToAction
        tone="audience-pair"
        headline="Want the contract behind these spans?"
        primary={{ label: 'See ADR-024 (agent communication)', href: 'https://github.com/Azure-Samples/holiday-peak-hub/blob/main/docs/architecture/adrs/adr-024-agent-communication-policy.md' }}
        secondary={{ label: 'See pattern catalog', href: '/builders/patterns' }}
        testId="builder-telemetry-cta-pair"
      />
    </>
  );
}
