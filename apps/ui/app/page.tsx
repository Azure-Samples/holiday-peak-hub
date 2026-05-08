import Link from 'next/link';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Holiday Peak Hub — Intelligent Retail Platform',
  description:
    'An audience-segmented router. Retailers see business outcomes; builders see architecture and reference implementation. Pick your lane.',
};

/**
 * ADR-034 §1 audience-router home.
 *
 * Hard rules:
 *   - Single headline, two equally-weighted CTAs.
 *   - No carousel, no autoplay video, no scroll-jacking.
 *   - Passes the 5-second test for both audiences.
 *   - Same brand mark across both lanes; warm tokens for /retailers, cool tokens for /builders.
 *   - en-US copy only.
 *
 * This is intentionally a server component: no client-side state, no agents,
 * no telemetry beyond static link clicks (handled by App Router).
 */
export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-6 py-16 text-center">
      <div className="max-w-3xl">
        <p className="mb-4 text-sm font-semibold uppercase tracking-widest text-[var(--hp-muted,#6b7280)]">
          Holiday Peak Hub
        </p>
        <h1 className="mb-6 text-4xl font-bold leading-tight sm:text-5xl">
          Intelligent retail, built on Azure&apos;s agentic platform.
        </h1>
        <p className="mb-10 text-lg text-[var(--hp-muted,#6b7280)]">
          Pick your lane. We route you to the right depth of detail.
        </p>
        <nav
          aria-label="Audience selection"
          className="grid grid-cols-1 gap-4 sm:grid-cols-2"
        >
          <Link
            href="/retailers"
            className="group flex flex-col items-start rounded-xl border border-[var(--hp-border,#e5e7eb)] bg-white p-6 text-left shadow-sm transition hover:shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2"
            data-audience="retailer"
          >
            <span className="mb-2 text-sm font-semibold uppercase tracking-wide text-[var(--hp-retailer-accent,#b45309)]">
              I&apos;m a retailer
            </span>
            <span className="text-base text-[var(--hp-text,#111827)]">
              See the business outcomes — agents, ROI, case studies, comparators.
            </span>
          </Link>
          <Link
            href="/builders"
            className="group flex flex-col items-start rounded-xl border border-[var(--hp-border,#e5e7eb)] bg-white p-6 text-left shadow-sm transition hover:shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2"
            data-audience="builder"
          >
            <span className="mb-2 text-sm font-semibold uppercase tracking-wide text-[var(--hp-builder-accent,#1d4ed8)]">
              I&apos;m a builder
            </span>
            <span className="text-base text-[var(--hp-text,#111827)]">
              See the architecture — ADRs, patterns, telemetry, reference implementation.
            </span>
          </Link>
        </nav>
        <p className="mt-10 text-sm text-[var(--hp-muted,#6b7280)]">
          Just looking around?{' '}
          <Link href="/docs" className="underline hover:no-underline">
            Read the docs
          </Link>
          .
        </p>
      </div>
    </main>
  );
}
