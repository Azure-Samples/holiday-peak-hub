import type { Metadata } from 'next';

import { CallToAction } from '@/components/molecules/CallToAction';
import { Hero } from '@/components/molecules/Hero';
import { RegistryTable, type RegistryTableRow } from '@/components/molecules/RegistryTable';
import { buildMetadata } from '@/lib/seo';
import { loadEnablementIndex } from '@/lib/enablement/registry';

export const metadata: Metadata = buildMetadata({
  section: 'builder',
  description: 'Internal sales enablement for the Microsoft Retail GTM group. Battle cards, demo scripts, win/loss, customer quotes. Currency contract enforces hide-on-expiry — no stale graveyards.',
  path: '/builders/enablement',
});

/**
 * `/builders/enablement` — index of currency-managed sales enablement assets
 * (Issue #1051 / Issue #1052 / Epic #1053).
 *
 * Currency contract enforced by `loadEnablementIndex()`:
 *   - Every asset has `owner` (GitHub handle) + `last_reviewed` (ISO date).
 *   - Expiry by class:
 *       battle cards     → 90 days
 *       demo scripts     → 180 days
 *       win/loss         → immutable
 *       customer quotes  → only when `attribution_status = approved`
 *   - Expired assets are HIDDEN, not stale-rendered.
 *
 * The page also surfaces an "expired count" so the GTM lead knows the
 * graveyard size without it leaking onto the surface.
 */
export default function EnablementIndexPage() {
  const idx = loadEnablementIndex();

  const rows: RegistryTableRow[] = idx.assets.map((a) => ({
    key: a.slug,
    cells: [
      { kind: 'link', value: a.title, href: a.href },
      { kind: 'badge', value: a.kind },
      { kind: 'text', value: a.owner },
      { kind: 'text', value: a.lastReviewed },
      { kind: 'text', value: `${a.daysToExpiry} d` },
    ],
  }));

  return (
    <>
      <Hero
        kind="audience-page"
        headline="Sales enablement for Microsoft Retail GTM."
        sub={`${idx.assets.length} live assets · ${idx.expiredCount} expired (hidden by design). Currency contract enforced.`}
        primaryCta={{ label: 'See architecture', href: '/builders/architecture' }}
        secondaryCta={{ label: 'See pattern catalog', href: '/builders/patterns' }}
        testId="enablement-index-hero"
      />
      <RegistryTable
        testId="enablement-index-table"
        headline="Live assets"
        description="Every asset has an owner (GitHub handle) and a last_reviewed date. Battle cards expire after 90 days, demo scripts after 180 days, win/loss is immutable, customer quotes render only when attribution is approved. Expired assets are HIDDEN — not stale-rendered."
        columns={['Asset', 'Class', 'Owner', 'Last reviewed', 'Days to expiry']}
        rows={rows}
        banner={
          idx.expiredCount > 0
            ? {
                tone: 'warn',
                text: `${idx.expiredCount} asset(s) expired and hidden. Refresh under .github/skills/gtm-enablement/.`,
              }
            : { tone: 'info', text: 'All live assets within currency window.' }
        }
        emptyState={{
          headline: 'No live enablement assets right now.',
          body: 'Either nothing has been authored yet, or every asset is expired. Authors: see docs/governance/enablement-currency-contract.md.',
        }}
      />
      <CallToAction
        tone="single"
        headline="Currency contract"
        primary={{ label: 'Read the contract', href: '/docs/governance/enablement-currency-contract' }}
        caption="Why we hide expired assets instead of stale-rendering them."
        testId="enablement-index-cta-contract"
      />
    </>
  );
}
