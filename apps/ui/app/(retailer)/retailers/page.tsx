import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'For Retailers — Holiday Peak Hub',
  description:
    'Business outcomes, agent catalog, ROI calculator, comparators, and case studies for retail leaders.',
};

/**
 * Placeholder hero for `/retailers`.
 *
 * Real content lands in epic #1046 (Retailer-Facing Value Pages):
 * - #1040 hero + 3-pillar value proposition
 * - #1041 agent catalog (27 agents, domain grouping, cost/1k)
 * - #1042 interactive ROI calculator with confidence intervals
 * - #1043 comparators matrix
 * - #1044 case studies with maturity badges
 * - #1045 cost-model methodology + Azure Retail Prices integration
 */
export default function RetailersIndexPage() {
  return (
    <section className="mx-auto w-full max-w-3xl px-6 py-16 text-center">
      <p className="mb-4 text-sm font-semibold uppercase tracking-widest text-[var(--hp-retailer-accent,#b45309)]">
        For Retailers
      </p>
      <h1 className="mb-6 text-4xl font-bold leading-tight">
        Built for the people who run the business.
      </h1>
      <p className="mb-10 text-lg text-[var(--hp-muted,#6b7280)]">
        Agents, ROI, case studies, and comparators land here. This is the
        skeleton that epic{' '}
        <a
          href="https://github.com/Azure-Samples/holiday-peak-hub/issues/1046"
          className="underline hover:no-underline"
        >
          #1046
        </a>{' '}
        fills out.
      </p>
      <div className="grid grid-cols-1 gap-4 text-left sm:grid-cols-2">
        <Link
          href="/builders"
          className="rounded-xl border border-[var(--hp-border,#e5e7eb)] p-4 hover:shadow-sm"
        >
          <span className="block text-sm font-semibold uppercase tracking-wide text-[var(--hp-builder-accent,#1d4ed8)]">
            Looking for the architecture?
          </span>
          <span className="mt-1 block text-sm text-[var(--hp-muted,#6b7280)]">
            Switch to the builder lane →
          </span>
        </Link>
        <Link
          href="/deploy"
          className="rounded-xl border border-[var(--hp-border,#e5e7eb)] p-4 hover:shadow-sm"
        >
          <span className="block text-sm font-semibold uppercase tracking-wide text-[var(--hp-text,#111827)]">
            Try it yourself
          </span>
          <span className="mt-1 block text-sm text-[var(--hp-muted,#6b7280)]">
            One-click deployment portal →
          </span>
        </Link>
      </div>
    </section>
  );
}
