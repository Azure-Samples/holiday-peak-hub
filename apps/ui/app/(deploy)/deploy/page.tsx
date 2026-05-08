import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Deploy — Holiday Peak Hub',
  description:
    'One-click deployment portal. Pick a scenario, configure, pre-flight, deploy, track, clean up — no GitHub account required.',
};

/**
 * Placeholder hero for `/deploy`.
 *
 * Real content lands in epic #1039 (One-Click Deployment Portal):
 * - #1027 deploy-portal Bicep module (Container Apps + APIM + Key Vault + Cosmos)
 * - #1028 catalog UI at /deploy/catalog with live cost estimator
 * - #1029 configure UI at /deploy/configure
 * - #1030 pre-flight backend (quota / capacity / RG) + UI
 * - #1031 OBO OAuth + ARM deployment kickoff
 * - #1032 SignalR-driven track UI at /deploy/track/<id>
 * - #1033 mid-flight failure cleanup contract
 * - #1034 rate limiting + abuse detection
 * - #1035 deployment metadata persistence + log scrubbing
 * - #1036 exit / portability action
 * - #1037 SOC 2 / GDPR / PCI posture for /retailers/security
 * - #1038 cost-transparency disclosure + Azure Retail Prices integration
 */
export default function DeployIndexPage() {
  return (
    <section className="mx-auto w-full max-w-3xl px-6 py-16 text-center">
      <p className="mb-4 text-sm font-semibold uppercase tracking-widest text-[var(--hp-text,#111827)]">
        Deploy
      </p>
      <h1 className="mb-6 text-4xl font-bold leading-tight">
        Spin up your own. No GitHub account required.
      </h1>
      <p className="mb-10 text-lg text-[var(--hp-muted,#6b7280)]">
        The one-click deployment portal lands here. This is the skeleton that
        epic{' '}
        <a
          href="https://github.com/Azure-Samples/holiday-peak-hub/issues/1039"
          className="underline hover:no-underline"
        >
          #1039
        </a>{' '}
        fills out.
      </p>
      <div className="grid grid-cols-1 gap-4 text-left sm:grid-cols-2">
        <Link
          href="/retailers"
          className="rounded-xl border border-[var(--hp-border,#e5e7eb)] p-4 hover:shadow-sm"
        >
          <span className="block text-sm font-semibold uppercase tracking-wide text-[var(--hp-retailer-accent,#b45309)]">
            Need the business case first?
          </span>
          <span className="mt-1 block text-sm text-[var(--hp-muted,#6b7280)]">
            See the retailer lane →
          </span>
        </Link>
        <Link
          href="/builders"
          className="rounded-xl border border-[var(--hp-border,#e5e7eb)] p-4 hover:shadow-sm"
        >
          <span className="block text-sm font-semibold uppercase tracking-wide text-[var(--hp-builder-accent,#1d4ed8)]">
            Want to read the architecture first?
          </span>
          <span className="mt-1 block text-sm text-[var(--hp-muted,#6b7280)]">
            See the builder lane →
          </span>
        </Link>
      </div>
    </section>
  );
}
