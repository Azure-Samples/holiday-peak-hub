import type { ReactElement } from 'react';
import Link from 'next/link';

/**
 * TryThisInTheAppCta — link from a docs page back to the live app surface
 * (Issue #1024 / Epic #1026).
 *
 * Renders inside markdown via the docs build (mkdocs/overrides/) when a
 * page declares `try_link:` front-matter. On the SWA the doc subtree is
 * mounted under `/docs/`, so the `appHref` resolves on the same origin.
 *
 * The component itself is just a primitive consumed in two places:
 *   1. mkdocs Material override that injects the CTA at the bottom of any
 *      doc page with `try_link:` front-matter.
 *   2. SWA app pages that want to surface a "try this" affordance.
 *
 * This is the React side; the mkdocs Material override for the markdown
 * side lives in `mkdocs/overrides/`.
 */

export type TryThisInTheAppCtaProps = {
  appHref: string;
  /** Display label, e.g., "Try the deploy portal". */
  label: string;
  /** Optional second-line context. */
  caption?: string;
  testId?: string;
};

const SECTION_STYLE = {
  display: 'flex',
  flexDirection: 'column' as const,
  alignItems: 'flex-start',
  gap: '0.375rem',
  padding: 'clamp(1.25rem, 3vw, 2rem) 1.5rem',
  background: 'var(--sys-surface-accent, var(--hp-primary-soft))',
  borderRadius: 'var(--radius-lg, 1rem)',
  maxWidth: '52rem',
  margin: '0 auto',
  width: '100%',
};

const LABEL_STYLE = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: '0.5rem',
  padding: '0.5rem 1rem',
  borderRadius: 'var(--radius-md, 0.5rem)',
  background: 'var(--sys-action-primary, var(--hp-primary))',
  color: 'var(--sys-action-primary-foreground, white)',
  fontWeight: 600,
  textDecoration: 'none' as const,
  fontSize: '0.9375rem',
};

const CAPTION_STYLE = {
  fontSize: '0.8125rem',
  color: 'var(--sys-text-muted, var(--hp-text-muted))',
};

export function TryThisInTheAppCta({
  appHref,
  label,
  caption,
  testId,
}: TryThisInTheAppCtaProps): ReactElement {
  return (
    <aside data-testid={testId} data-try-this-in-the-app style={SECTION_STYLE}>
      <Link href={appHref} style={LABEL_STYLE} data-app-href={appHref}>
        <span aria-hidden="true">▶︎</span>
        <span>{label}</span>
      </Link>
      {caption ? <p style={CAPTION_STYLE}>{caption}</p> : null}
    </aside>
  );
}
