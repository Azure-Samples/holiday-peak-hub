import type { Metadata } from 'next';
import Link from 'next/link';

import { HomeSplitHero } from '@/components/shared/HomeSplitHero';
import { resolvePersonaFromRequest } from '@/lib/persona/resolve';

import { buildMetadata } from '@/lib/seo';

export const metadata: Metadata = buildMetadata({
  section: 'home',
  description:
    'An audience-segmented router. Retailers see business outcomes; builders see architecture and reference implementation. Pick your lane.',
  path: '/',
});

type HomePageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
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
 * Persona is resolved server-side and forwarded to the client HomeSplitHero
 * to pick the default tab order. Persona is a HINT, not a GATE — both CTAs
 * always render.
 */
export default async function HomePage({ searchParams }: HomePageProps) {
  const resolvedSearchParams = await searchParams;
  const persona = await resolvePersonaFromRequest(resolvedSearchParams);

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
        <HomeSplitHero persona={persona} />
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
