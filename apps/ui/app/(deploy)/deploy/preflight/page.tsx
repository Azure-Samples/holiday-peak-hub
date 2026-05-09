import type { Metadata } from 'next';

import { CallToAction } from '@/components/molecules/CallToAction';
import { DeployPreviewBanner } from '@/components/molecules/DeployPreviewBanner';
import { Hero } from '@/components/molecules/Hero';
import { PreflightPanel } from '@/components/molecules/PreflightPanel';
import { buildMetadata } from '@/lib/seo';

export const metadata: Metadata = buildMetadata({
  section: 'deploy',
  description:
    'Pre-flight checks: subscription quota, RG availability, Foundry capacity, region eligibility. Every red row carries a remediation link.',
  path: '/deploy/preflight',
});

/**
 * `/deploy/preflight` — green/red panel (Issue #1030 / Epic #1039).
 *
 * v1: ships with a curated set of pre-flight checks rendered as
 * mocked-passing. The actual check execution is wired by the deploy-portal
 * API. The panel UI is real and reusable.
 *
 * Real-time refresh of these checks happens on the SignalR-driven track
 * page (#1032).
 */
export default function DeployPreflightPage() {
  return (
    <>
      <DeployPreviewBanner testId="deploy-preflight-preview-banner" maturity="preview" />
      <Hero
        kind="audience-page"
        headline="Pre-flight checks."
        sub="Quota, capacity, RG availability, Foundry deployment limits. Every red row has a fix."
        primaryCta={{ label: 'Deploy →', href: '/deploy/configure' }}
        secondaryCta={{ label: 'Back to configure', href: '/deploy/configure' }}
        testId="deploy-preflight-hero"
      />
      <PreflightPanel
        testId="deploy-preflight-panel"
        headline="Pre-flight"
        description="These checks run against the subscription you signed in to. Subscription IDs are scrubbed in audit logs (sub_<sha256[0:12]>)."
        maturity="preview"
        checks={[
          {
            id: 'subscription-active',
            label: 'Subscription is active and reachable',
            verdict: 'pass',
            reason: 'OBO consent valid; subscription state Enabled.',
          },
          {
            id: 'rg-available',
            label: 'Resource group available',
            verdict: 'pass',
            reason: 'Resource group does not exist or is empty; safe to provision.',
          },
          {
            id: 'compute-quota',
            label: 'Compute quota sufficient',
            verdict: 'warn',
            reason: 'Current vCPU usage is 65%. Provisioning will succeed; consider quota increase before scale-out.',
            remediationHref:
              'https://learn.microsoft.com/azure/quotas/quickstart-increase-quota-portal',
          },
          {
            id: 'foundry-capacity',
            label: 'Azure AI Foundry capacity available',
            verdict: 'pass',
            reason: 'Selected SLM and LLM deployments have capacity in the chosen region.',
          },
          {
            id: 'region-eligibility',
            label: 'Region eligibility',
            verdict: 'pass',
            reason: 'westeurope is in the allowed deploy-portal regions list (default per data-residency policy).',
          },
          {
            id: 'rate-limits',
            label: 'Rate limits',
            verdict: 'pass',
            reason: 'Within 3 active deployments / 24 h and 10 / 30 d budget.',
          },
        ]}
      />
      <CallToAction
        tone="single"
        headline="Ready to deploy?"
        primary={{ label: 'Launch deployment →', href: '/deploy/track/preview' }}
        caption="Cleanup happens automatically on mid-flight failure. The track page surfaces a Clean-up-now action explicitly."
        testId="deploy-preflight-cta"
      />
    </>
  );
}
