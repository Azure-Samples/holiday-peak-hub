import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'For Builders — Holiday Peak Hub',
  description:
    'Architecture, ADRs, patterns, telemetry, and the reference implementation for engineers building on the platform.',
};

/**
 * Placeholder hero for `/builders`.
 *
 * Real content lands in epic #1053 (Internal Technical Reference):
 * - #1047 /builders/architecture with auto-rendered Mermaid + downloadable artifacts
 * - #1048 /builders/adrs UI backed by scripts/ops/build_adr_registry.py
 * - #1049 /builders/patterns (modular monolith, MCP A2A, AGC canary, three-tier memory, OTEL)
 * - #1050 /builders/telemetry App Insights workbook iframe
 * - #1051 /builders/enablement role-gated subtree
 * - #1052 owner + last_reviewed front-matter contract for enablement assets
 */
export default function BuildersIndexPage() {
  return (
    <section className="mx-auto w-full max-w-3xl px-6 py-16 text-center">
      <p className="mb-4 text-sm font-semibold uppercase tracking-widest text-[var(--hp-builder-accent,#1d4ed8)]">
        For Builders
      </p>
      <h1 className="mb-6 text-4xl font-bold leading-tight">
        The architecture, the contracts, the receipts.
      </h1>
      <p className="mb-10 text-lg text-[var(--hp-muted,#6b7280)]">
        Architecture diagrams, ADRs, patterns, telemetry, and enablement land
        here. This is the skeleton that epic{' '}
        <a
          href="https://github.com/Azure-Samples/holiday-peak-hub/issues/1053"
          className="underline hover:no-underline"
        >
          #1053
        </a>{' '}
        fills out.
      </p>
      <div className="grid grid-cols-1 gap-4 text-left sm:grid-cols-2">
        <Link
          href="/retailers"
          className="rounded-xl border border-[var(--hp-border,#e5e7eb)] p-4 hover:shadow-sm"
        >
          <span className="block text-sm font-semibold uppercase tracking-wide text-[var(--hp-retailer-accent,#b45309)]">
            Looking for the business case?
          </span>
          <span className="mt-1 block text-sm text-[var(--hp-muted,#6b7280)]">
            Switch to the retailer lane →
          </span>
        </Link>
        <Link
          href="/deploy"
          className="rounded-xl border border-[var(--hp-border,#e5e7eb)] p-4 hover:shadow-sm"
        >
          <span className="block text-sm font-semibold uppercase tracking-wide text-[var(--hp-text,#111827)]">
            Spin up your own
          </span>
          <span className="mt-1 block text-sm text-[var(--hp-muted,#6b7280)]">
            One-click deployment portal →
          </span>
        </Link>
      </div>
    </section>
  );
}
