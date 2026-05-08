'use client';

import Link from 'next/link';
import { useCallback } from 'react';

import type { Persona } from '@/lib/persona/types';
import { setPersonaCookie } from './setPersonaCookie';

type HomeSplitHeroProps = {
  /**
   * Resolved persona, computed server-side via `resolvePersonaFromRequest`.
   * Used **only** to pick the default tab order — never to gate content.
   */
  persona: Persona | null;
};

const RETAILER_CTA = (
  <CTA
    href="/retailers"
    audience="retailer"
    eyebrow="I'm a retailer"
    body="See the business outcomes — agents, ROI, case studies, comparators."
    accent="text-[var(--hp-retailer-accent)]"
  />
);

const BUILDER_CTA = (
  <CTA
    href="/builders"
    audience="builder"
    eyebrow="I'm a builder"
    body="See the architecture — ADRs, patterns, telemetry, reference implementation."
    accent="text-[var(--hp-builder-accent)]"
  />
);

/**
 * HomeSplitHero — two equally-weighted CTAs, persona-aware ordering.
 *
 * Per ADR-034 §1:
 *   - Single headline, two equally-weighted CTAs (no visual hierarchy difference).
 *   - No carousel, no autoplay video, no scroll-jacking.
 *   - Persona is a HINT, not a GATE: it only controls which CTA renders first.
 *
 * Both CTAs always render. The "default tab" picked by the persona shows up
 * in the visual top-left slot but the alternative is just as accessible —
 * SEO and screen-reader order match visual order, and the headline calls out
 * both options equally.
 */
export function HomeSplitHero({ persona }: HomeSplitHeroProps) {
  const handleAudienceClick = useCallback(
    (clicked: Persona) => {
      // Soft persona update: clicking a CTA on `/` is the user's clearest
      // signal of audience identity (per ADR-034 §3 cookie contract).
      setPersonaCookie(clicked);
    },
    [],
  );

  const orderedCtas =
    persona === 'builder'
      ? [
          { key: 'builder', node: BUILDER_CTA, audience: 'builder' as Persona },
          {
            key: 'retailer',
            node: RETAILER_CTA,
            audience: 'retailer' as Persona,
          },
        ]
      : [
          {
            key: 'retailer',
            node: RETAILER_CTA,
            audience: 'retailer' as Persona,
          },
          { key: 'builder', node: BUILDER_CTA, audience: 'builder' as Persona },
        ];

  return (
    <nav
      aria-label="Audience selection"
      className="grid grid-cols-1 gap-4 sm:grid-cols-2"
      data-resolved-persona={persona ?? 'none'}
    >
      {orderedCtas.map(({ key, node, audience }) => (
        <span
          key={key}
          onClick={() => handleAudienceClick(audience)}
          // Wrapping span only carries the click handler so we can record the
          // soft persona signal. Keyboard activations bubble through the
          // <Link> child (Enter / Space).
        >
          {node}
        </span>
      ))}
    </nav>
  );
}

type CTAProps = {
  href: string;
  audience: 'retailer' | 'builder';
  eyebrow: string;
  body: string;
  accent: string;
};

function CTA({ href, audience, eyebrow, body, accent }: CTAProps) {
  return (
    <Link
      href={href}
      data-audience={audience}
      className="group flex flex-col items-start rounded-xl border border-[var(--hp-border,#e5e7eb)] bg-white p-6 text-left shadow-sm transition hover:shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2"
    >
      <span
        className={`mb-2 text-sm font-semibold uppercase tracking-wide ${accent}`}
      >
        {eyebrow}
      </span>
      <span className="text-base text-[var(--hp-text,#111827)]">{body}</span>
    </Link>
  );
}

export default HomeSplitHero;
