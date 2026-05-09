import type { Metadata } from 'next';

import { CallToAction } from '@/components/molecules/CallToAction';
import { ConfigureForm } from '@/components/molecules/ConfigureForm';
import { DeployPreviewBanner } from '@/components/molecules/DeployPreviewBanner';
import { Hero } from '@/components/molecules/Hero';
import { buildMetadata } from '@/lib/seo';

export const metadata: Metadata = buildMetadata({
  section: 'deploy',
  description:
    'Configure your Azure deployment. Sign in with Microsoft Entra; pick a subscription, resource group, and region. The deploy-portal service has zero standing RBAC on your subscription.',
  path: '/deploy/configure',
});

const REGIONS = [
  { code: 'westeurope', label: 'West Europe (default; data-residency)' },
  { code: 'eastus2', label: 'East US 2' },
  { code: 'brazilsouth', label: 'Brazil South' },
];

/**
 * `/deploy/configure` — Entra sign-in + sub/RG/location form (Issue #1029 /
 * Epic #1039).
 *
 * v1: pure form. The OBO sign-in handshake + subscription dropdown
 * population happens server-side once the deploy-portal API ships
 * (#1031).
 */
export default function DeployConfigurePage() {
  return (
    <>
      <DeployPreviewBanner testId="deploy-configure-preview-banner" maturity="preview" />
      <Hero
        kind="audience-page"
        headline="Configure your deployment."
        sub="Sign in with Microsoft Entra. Pick a subscription, resource group, and region. We never see your credentials."
        primaryCta={{ label: 'Run pre-flight checks →', href: '#configure-form' }}
        secondaryCta={{ label: 'Back to catalog', href: '/deploy/catalog' }}
        testId="deploy-configure-hero"
      />
      <ConfigureForm
        testId="deploy-configure-form"
        maturity="preview"
        regions={REGIONS}
        action="/deploy/preflight"
      />
      <CallToAction
        tone="single"
        headline="Why so many fields?"
        primary={{ label: 'Read the OBO contract', href: '/docs/security/deploy-portal-obo' }}
        caption="The deploy-portal service has zero standing RBAC on your subscription. Each field narrows the consent we ask for."
        testId="deploy-configure-cta"
      />
    </>
  );
}
