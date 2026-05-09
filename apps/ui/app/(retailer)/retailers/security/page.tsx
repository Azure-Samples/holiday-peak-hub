import type { Metadata } from 'next';

import { CallToAction } from '@/components/molecules/CallToAction';
import { Hero } from '@/components/molecules/Hero';
import { RegistryTable, type RegistryTableRow } from '@/components/molecules/RegistryTable';
import { buildMetadata } from '@/lib/seo';

export const metadata: Metadata = buildMetadata({
  section: 'retailer',
  description:
    'Security posture: SOC 2 Type II in scope (deployment service), GDPR DSR contact, PCI explicitly out-of-scope, OBO OAuth contract, log scrubbing, deploy-portal pen-test cadence.',
  path: '/retailers/security',
});

/**
 * `/retailers/security` — security posture page (Issue #1037 / Epic #1039).
 *
 * Hard rules from Epic #1039:
 *   - SOC 2 Type II in scope for the deployment service.
 *   - GDPR DSR contact published.
 *   - PCI explicitly OUT-OF-SCOPE.
 *   - Pen-test cadence stated.
 *
 * No guesswork. Every row carries a current status (in-scope / out-of-scope /
 * planned) and a verification date. Honest > marketing.
 */

const STANDARDS_ROWS: RegistryTableRow[] = [
  {
    key: 'soc2-type2-deploy-portal',
    cells: [
      { kind: 'text', value: 'SOC 2 Type II — deploy-portal service' },
      { kind: 'badge', value: 'In scope' },
      { kind: 'text', value: 'Audit window opens with deploy-portal GA. Working with auditor TBD.' },
      { kind: 'text', value: 'Q4 2025' },
    ],
  },
  {
    key: 'gdpr',
    cells: [
      { kind: 'text', value: 'GDPR — DSR contact + processor obligations' },
      { kind: 'badge', value: 'In scope' },
      { kind: 'link', value: 'privacy@holiday-peak-hub.example', href: 'mailto:privacy@holiday-peak-hub.example' },
      { kind: 'text', value: '2025-11-04' },
    ],
  },
  {
    key: 'pci',
    cells: [
      { kind: 'text', value: 'PCI DSS — payment-card data handling' },
      { kind: 'badge', value: 'Out of scope' },
      { kind: 'text', value: 'The platform does not process card-holder data; checkout integrations are reference-only.' },
      { kind: 'text', value: '2025-11-04' },
    ],
  },
  {
    key: 'iso-27001',
    cells: [
      { kind: 'text', value: 'ISO 27001 — information security management' },
      { kind: 'badge', value: 'Planned' },
      { kind: 'text', value: 'Inherits Microsoft platform certifications via Azure-Samples; standalone certification deferred.' },
      { kind: 'text', value: '2026 H1 target' },
    ],
  },
];

const CONTROLS_ROWS: RegistryTableRow[] = [
  {
    key: 'obo-oauth',
    cells: [
      { kind: 'text', value: 'OBO OAuth — narrow, time-bound, scoped to chosen sub' },
      { kind: 'badge', value: 'Enforced' },
      { kind: 'link', value: 'OBO contract', href: '/docs/security/deploy-portal-obo' },
      { kind: 'text', value: '2025-11-04' },
    ],
  },
  {
    key: 'service-rbac',
    cells: [
      { kind: 'text', value: 'Service identity has zero standing RBAC on customer subscriptions' },
      { kind: 'badge', value: 'Enforced' },
      { kind: 'text', value: 'Quarterly RBAC audit; deploy-portal MI provisioned with no Owner / Contributor at the sub scope.' },
      { kind: 'text', value: '2025-11-04' },
    ],
  },
  {
    key: 'log-scrubbing',
    cells: [
      { kind: 'text', value: 'Log scrubbing — sub IDs + emails replaced before write' },
      { kind: 'badge', value: 'Enforced' },
      { kind: 'text', value: 'Audit-log forwarder anonymizes sub_<sha256[0:12]> and oid_<sha256[0:12]> at the boundary.' },
      { kind: 'text', value: '2025-11-04' },
    ],
  },
  {
    key: 'rate-limit',
    cells: [
      { kind: 'text', value: 'Rate limit + abuse detection (per OID, per IP, CAPTCHA, manual-review)' },
      { kind: 'badge', value: 'Enforced' },
      { kind: 'text', value: '3 active deployments / 24 h, 10 / 30 d, 1 pre-flight / minute, CAPTCHA after 3 / hour.' },
      { kind: 'text', value: '2025-11-04' },
    ],
  },
  {
    key: 'pen-test',
    cells: [
      { kind: 'text', value: 'Penetration test — third-party or Microsoft Red Team' },
      { kind: 'badge', value: 'Required pre-GA' },
      { kind: 'text', value: 'Test scope includes OBO scope creep, cross-tenant token, ARM passthrough abuse.' },
      { kind: 'text', value: 'Pre-GA gate' },
    ],
  },
  {
    key: 'incident-response',
    cells: [
      { kind: 'text', value: 'Incident response — 24/7 on-call + 4 h RTO for security events' },
      { kind: 'badge', value: 'In flight' },
      { kind: 'link', value: 'See ops runbook', href: 'https://github.com/Azure-Samples/holiday-peak-hub/blob/main/docs/ops/incident-response.md' },
      { kind: 'text', value: 'Q4 2025' },
    ],
  },
];

export default function RetailerSecurityPage() {
  return (
    <>
      <Hero
        kind="audience-page"
        headline="Security posture, on the page."
        sub="What's in scope, what isn't, what's enforced, and what's planned. Verification dates per row. No hand-waving."
        primaryCta={{ label: 'Read the OBO contract', href: '/docs/security/deploy-portal-obo' }}
        secondaryCta={{ label: 'Read the cleanup contract', href: '/docs/governance/deploy-portal-cleanup-contract' }}
        testId="retailer-security-hero"
      />
      <RegistryTable
        testId="retailer-security-standards-table"
        headline="Standards & certifications"
        description="What we are certified on, what we will be, what we explicitly are not. PCI is OUT-OF-SCOPE because the platform does not process card-holder data."
        columns={['Standard', 'Status', 'Notes', 'Verified']}
        rows={STANDARDS_ROWS}
      />
      <RegistryTable
        testId="retailer-security-controls-table"
        headline="Controls in production"
        description="The technical controls enforced in production today. Each row links to the canonical contract or run-book."
        columns={['Control', 'Status', 'Detail', 'Verified']}
        rows={CONTROLS_ROWS}
      />
      <CallToAction
        tone="audience-pair"
        headline="Want to dig in?"
        primary={{ label: 'Read the OBO contract', href: '/docs/security/deploy-portal-obo' }}
        secondary={{ label: 'Read the cleanup contract', href: '/docs/governance/deploy-portal-cleanup-contract' }}
        testId="retailer-security-cta-pair"
      />
    </>
  );
}
