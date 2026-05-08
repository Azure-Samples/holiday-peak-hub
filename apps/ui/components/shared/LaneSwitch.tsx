'use client';

import Link from 'next/link';
import type { ReactNode } from 'react';

import type { Persona } from '@/lib/persona/types';
import { setPersonaCookie } from './setPersonaCookie';

/**
 * Audience lanes addressable from the LaneSwitch component.
 * Distinct from `Persona` because the home lane is not a persona.
 */
export type LaneAudience = 'retailer' | 'builder' | 'deploy';

type LaneSwitchProps = {
  /** Current audience lane the user is on. */
  from: LaneAudience;
  /** Audience lane the CTA navigates to. */
  to: LaneAudience;
  /** Optional override for the rendered copy. Defaults to the curated map. */
  children?: ReactNode;
};

const COPY: Record<LaneAudience, Record<LaneAudience, string>> = {
  retailer: {
    retailer: 'Stay on the retailer lane',
    builder: "I'm building on this platform — show me the architecture",
    deploy: 'Skip ahead — let me deploy it',
  },
  builder: {
    retailer: 'I run a retail business — show me the value',
    builder: 'Stay on the builder lane',
    deploy: 'Skip ahead — let me deploy it',
  },
  deploy: {
    retailer: 'I run a retail business — show me the value',
    builder: "I'm building on this platform — show me the architecture",
    deploy: 'Stay on the deploy lane',
  },
};

const HREF: Record<LaneAudience, string> = {
  retailer: '/retailers',
  builder: '/builders',
  deploy: '/deploy',
};

/**
 * LaneSwitch — copy-aware, accessible cross-lane CTA.
 *
 * Per ADR-034 every page under `/retailers/*`, `/builders/*`, and `/deploy/*`
 * must render a LaneSwitch so SEO landings remain valid entry points and either
 * audience can switch lanes when they need to.
 *
 * The persona cookie is updated as a hint when the user switches — but **only
 * as a hint**: it controls copy ordering and default-tab selection, never
 * content gating. See `apps/ui/lib/persona/`.
 */
export function LaneSwitch({ from, to, children }: LaneSwitchProps) {
  if (from === to) {
    // No-op rendering when from === to. Useful when consumers compute the
    // pair dynamically and would otherwise need a guard at every call site.
    return null;
  }

  const handleClick = () => {
    // Soft persona update: switching lanes is the user's clearest signal of
    // their current persona. We update the cookie as a hint only.
    if (to !== 'deploy') {
      setPersonaCookie(to as Persona);
    }
  };

  return (
    <Link
      href={HREF[to]}
      onClick={handleClick}
      data-lane-from={from}
      data-lane-to={to}
      className="inline-flex items-center gap-2 rounded-full border border-[var(--hp-border,#e5e7eb)] px-4 py-2 text-sm font-medium text-[var(--hp-section-accent)] transition-colors hover:bg-[var(--hp-section-accent-soft,rgba(0,0,0,0.04))] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--hp-focus,#e88a1a)]"
      aria-label={`Switch to the ${to} lane`}
    >
      <span aria-hidden="true">→</span>
      <span>{children ?? COPY[from][to]}</span>
    </Link>
  );
}

export default LaneSwitch;
