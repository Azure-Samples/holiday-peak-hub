import type { Metadata } from 'next';

import { CallToAction } from '@/components/molecules/CallToAction';
import { DeployPreviewBanner } from '@/components/molecules/DeployPreviewBanner';
import { Hero } from '@/components/molecules/Hero';
import { TrackPanel, type TrackPhase, type TrackStep } from '@/components/molecules/TrackPanel';
import { buildMetadata } from '@/lib/seo';

export const metadata: Metadata = buildMetadata({
  section: 'deploy',
  description:
    'Live deployment tracking with SignalR-driven status. Clean-up-now and Delete-this-deployment actions are always available.',
  path: '/deploy/track',
});

type Params = { id: string };

const DEMO_STEPS: TrackStep[] = [
  { id: 'queue', label: 'Queued', phase: 'queued', detail: 'Awaiting capacity in the deploy-portal worker pool.' },
  { id: 'preflight', label: 'Pre-flight checks', phase: 'preflight', detail: 'Quota, capacity, RG availability re-verified.' },
  { id: 'provision', label: 'Provisioning Azure resources', phase: 'provisioning', detail: 'AKS, AGC, Cosmos, Foundry deployments, Key Vault.' },
  { id: 'configure', label: 'Configuring agents', phase: 'configuring', detail: 'Wiring SLM/LLM targets, MCP endpoints, three-tier memory.' },
  { id: 'verify', label: 'Verifying', phase: 'verifying', detail: 'Smoke tests against the deployed agents.' },
];

const PHASE: TrackPhase = 'provisioning';

/**
 * `/deploy/track/[id]` — running-deployment status (Issue #1032 / Epic #1039).
 *
 * v1: server-rendered snapshot. The SignalR client subscription that
 * refreshes the panel in-place lands when the deploy-portal API publishes
 * the status hub. The panel is real and reusable.
 *
 * Hard rules from Epic #1039:
 *   - "Clean up now" is the PRIMARY action — even on a successful deploy.
 *   - "Delete this deployment" requires type-the-RG confirmation.
 *   - 30-day audit retention surfaced.
 *
 * Subscription IDs are scrubbed before rendering (sub_<sha256[0:12]>).
 */
export default async function DeployTrackPage({
  params,
}: {
  params: Promise<Params>;
}) {
  const { id } = await params;

  return (
    <>
      <DeployPreviewBanner testId="deploy-track-preview-banner" maturity="preview" />
      <Hero
        kind="audience-page"
        headline="Live deployment status."
        sub="The track view updates in real time once SignalR is wired (#1032). Clean-up and Delete are always available."
        primaryCta={{ label: 'Back to /deploy', href: '/deploy' }}
        secondaryCta={{ label: 'Read the cleanup contract', href: '/docs/governance/deploy-portal-cleanup-contract' }}
        testId="deploy-track-hero"
      />
      <TrackPanel
        testId="deploy-track-panel"
        deploymentId={id}
        resourceGroup="rg-hph-preview"
        region="westeurope"
        subscriptionAlias="sub_********"
        steps={DEMO_STEPS}
        currentPhase={PHASE}
        retentionDays={30}
        cleanupHref={`/deploy/track/${id}/cleanup`}
        deleteHref={`/deploy/track/${id}/delete`}
        maturity="preview"
      />
      <CallToAction
        tone="single"
        headline="Deployment misbehaving?"
        primary={{ label: 'Clean up now', href: `/deploy/track/${id}/cleanup` }}
        caption="Cleanup deletes everything that the deploy-portal provisioned in your subscription. Audit log entry is retained for 30 days."
        testId="deploy-track-cta"
      />
    </>
  );
}
