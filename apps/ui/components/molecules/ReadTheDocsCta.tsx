import type { ReactElement } from 'react';
import Link from 'next/link';

/**
 * ReadTheDocsCta — bottom-of-page link from a value/pattern page to the
 * canonical mkdocs deep page (Issue #1025 / Epic #1026).
 *
 * Pattern: every value page on `/retailers/*` and pattern page on
 * `/builders/*` ends with a "Read the docs" CTA referencing the mkdocs
 * page that holds the deep treatment. The CTA is opt-in per page; pages
 * with no canonical doc just don't render it.
 *
 * `docsHref` is a SAME-DOMAIN absolute path under `/docs/`; `mkdocs` is
 * mounted as a sub-path so we never leave the SWA host.
 */

export type ReadTheDocsCtaProps = {
  docsHref: string;
  /** Display label, e.g., "Read the architecture overview". */
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
  background: 'var(--sys-surface-base, var(--hp-bg))',
  borderRadius: 'var(--radius-lg, 1rem)',
  border: '1px dashed var(--sys-border, var(--hp-border))',
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
  background: 'var(--sys-surface, var(--hp-surface))',
  border: '1px solid var(--sys-border, var(--hp-border))',
  color: 'var(--sys-text, var(--hp-text))',
  fontWeight: 600,
  textDecoration: 'none' as const,
  fontSize: '0.9375rem',
};

const CAPTION_STYLE = {
  fontSize: '0.8125rem',
  color: 'var(--sys-text-muted, var(--hp-text-muted))',
};

export function ReadTheDocsCta({
  docsHref,
  label,
  caption,
  testId,
}: ReadTheDocsCtaProps): ReactElement {
  return (
    <aside data-testid={testId} data-read-the-docs style={SECTION_STYLE}>
      <Link href={docsHref} style={LABEL_STYLE} data-docs-href={docsHref}>
        <span aria-hidden="true">📘</span>
        <span>{label}</span>
      </Link>
      {caption ? <p style={CAPTION_STYLE}>{caption}</p> : null}
    </aside>
  );
}
