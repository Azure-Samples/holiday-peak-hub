import type { ReactElement } from 'react';
import Link from 'next/link';

/**
 * DocsCard — link card to a documentation surface (ADR-035 §54 / Issue #1059).
 *
 * Used as a cluster on `/builders` and `/deploy` to link directly into mkdocs
 * sections (`architecture/`, `governance/`, `ops/`) and post-deploy runbooks.
 *
 * The card exposes a `kind` so future telemetry can distinguish docs traffic
 * from the marketing surface. Composites have no `className` escape hatch.
 */
export type DocsCardProps = {
  /** Title of the doc target. */
  title: string;
  /** One-sentence summary of what the doc carries. */
  description: string;
  /** Deep link into mkdocs / repo doc. */
  href: string;
  /** External or internal link. External links open in a new tab. */
  external?: boolean;
  /** Optional kicker (e.g., "Architecture", "Governance"). */
  kicker?: string;
  testId?: string;
};

const CARD_STYLE = {
  display: 'flex',
  flexDirection: 'column' as const,
  gap: '0.5rem',
  padding: '1.25rem',
  borderRadius: 'var(--radius-lg, 1rem)',
  border: '1px solid var(--sys-border, var(--hp-border))',
  background: 'var(--sys-surface, var(--hp-surface))',
  textDecoration: 'none' as const,
  color: 'var(--sys-text, var(--hp-text))',
};

const KICKER_STYLE = {
  fontSize: '0.75rem',
  fontWeight: 600,
  textTransform: 'uppercase' as const,
  letterSpacing: '0.08em',
  color: 'var(--sys-text-muted, var(--hp-text-muted))',
};

const TITLE_STYLE = {
  fontSize: '1.0625rem',
  fontWeight: 600,
  lineHeight: 1.3,
};

const DESCRIPTION_STYLE = {
  fontSize: '0.9375rem',
  lineHeight: 1.5,
  color: 'var(--sys-text-muted, var(--hp-text-muted))',
};

export function DocsCard({
  title,
  description,
  href,
  external,
  kicker,
  testId,
}: DocsCardProps): ReactElement {
  if (external) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noreferrer noopener"
        data-testid={testId}
        data-docs-card=""
        style={CARD_STYLE}
      >
        {kicker ? <span style={KICKER_STYLE}>{kicker}</span> : null}
        <span style={TITLE_STYLE}>{title}</span>
        <span style={DESCRIPTION_STYLE}>{description}</span>
      </a>
    );
  }
  return (
    <Link href={href} data-testid={testId} data-docs-card="" style={CARD_STYLE}>
      {kicker ? <span style={KICKER_STYLE}>{kicker}</span> : null}
      <span style={TITLE_STYLE}>{title}</span>
      <span style={DESCRIPTION_STYLE}>{description}</span>
    </Link>
  );
}
