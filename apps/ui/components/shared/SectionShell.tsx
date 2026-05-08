'use client';

import type { ReactNode } from 'react';
import Link from 'next/link';

export type SectionVariant = 'home' | 'retailer' | 'builder' | 'deploy' | 'docs';

type SectionShellProps = {
  variant: SectionVariant;
  children: ReactNode;
  /** Optional breadcrumb slot rendered above the section content. */
  breadcrumb?: ReactNode;
  /** Optional lane-switch slot. Used by the audience-IA persona switcher. */
  laneSwitch?: ReactNode;
};

const VARIANT_LABEL: Record<SectionVariant, string> = {
  home: 'Holiday Peak Hub',
  retailer: 'For Retailers',
  builder: 'For Builders',
  deploy: 'Deploy',
  docs: 'Documentation',
};

/**
 * Map a section variant to its audience taxonomy class (ADR-034 §3 / ADR-035
 * §50). The `data-audience` attribute drives the `[data-audience="…"]`
 * selectors in `app/styles/tokens.system.css`. The `audience-*` className
 * mirrors it for grep + dev-tool clarity.
 */
const VARIANT_AUDIENCE: Record<SectionVariant, 'retailer' | 'builder' | 'deploy' | 'neutral'> = {
  home: 'neutral',
  retailer: 'retailer',
  builder: 'builder',
  deploy: 'deploy',
  docs: 'neutral',
};

/**
 * SectionShell — the single shell consumed by every audience route group.
 *
 * Per ADR-034 the shell only handles:
 *   - tokens (variant + audience attributes on the wrapper for CSS scoping)
 *   - top-level brand mark + section label
 *   - breadcrumb slot
 *   - lane-switch slot (filled by the audience-IA persona switcher)
 *
 * Section-specific chrome (heroes, dashboards, calculators, etc.) stays
 * inside the section's own layout and pages — the shell does NOT grow into
 * a god-component.
 */
export function SectionShell({
  variant,
  children,
  breadcrumb,
  laneSwitch,
}: SectionShellProps) {
  const audience = VARIANT_AUDIENCE[variant];
  return (
    <div
      data-section={variant}
      data-audience={audience}
      className={`audience-${audience} flex min-h-screen flex-col`}
    >
      <header className="border-b border-[var(--hp-border,#e5e7eb)] bg-white">
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-6 py-4">
          <Link
            href="/"
            className="flex items-baseline gap-2 text-base font-semibold text-[var(--hp-text,#111827)] hover:opacity-80"
          >
            <span>Holiday Peak Hub</span>
            <span
              aria-hidden="true"
              className="text-xs font-medium uppercase tracking-widest text-[var(--hp-muted,#6b7280)]"
            >
              {VARIANT_LABEL[variant]}
            </span>
          </Link>
          {laneSwitch ? <div className="ml-auto">{laneSwitch}</div> : null}
        </div>
        {breadcrumb ? (
          <div className="mx-auto w-full max-w-7xl px-6 pb-3 text-sm text-[var(--hp-muted,#6b7280)]">
            {breadcrumb}
          </div>
        ) : null}
      </header>
      <main className="flex-1">{children}</main>
      <footer className="border-t border-[var(--hp-border,#e5e7eb)] bg-white">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-2 px-6 py-6 text-sm text-[var(--hp-muted,#6b7280)] sm:flex-row sm:items-center sm:justify-between">
          <span>© Holiday Peak Hub — Microsoft Azure-Samples</span>
          <nav aria-label="Footer">
            <ul className="flex flex-wrap gap-4">
              <li>
                <Link href="/retailers" className="hover:underline">
                  For Retailers
                </Link>
              </li>
              <li>
                <Link href="/builders" className="hover:underline">
                  For Builders
                </Link>
              </li>
              <li>
                <Link href="/deploy" className="hover:underline">
                  Deploy
                </Link>
              </li>
              <li>
                <Link href="/docs" className="hover:underline">
                  Docs
                </Link>
              </li>
            </ul>
          </nav>
        </div>
      </footer>
    </div>
  );
}

export default SectionShell;
