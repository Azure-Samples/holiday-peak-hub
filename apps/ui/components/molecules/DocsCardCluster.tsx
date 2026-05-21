import type { ReactElement } from 'react';
import { DocsCard, type DocsCardProps } from './DocsCard';

/**
 * DocsCardCluster — labelled grid of `DocsCard`s (ADR-035 §54 / Issue #1059).
 *
 * Used on `/builders` and `/deploy` to surface clusters of doc-target links
 * (architecture, governance, ops, post-deploy runbooks, rollback, tear-down).
 * The cluster owns its own heading and grid layout so the audience-route
 * page-level code stays free of inline layout (per ADR-035 §49 / Issue #1058
 * L-3 — audience routes have no `style={{}}`).
 */
export type DocsCardClusterProps = {
  headline: string;
  cards: ReadonlyArray<DocsCardProps>;
  testId?: string;
};

const SECTION_STYLE = {
  display: 'flex',
  flexDirection: 'column' as const,
  gap: '1rem',
  padding: 'clamp(2rem, 5vw, 3rem) 1.5rem',
  maxWidth: '72rem',
  margin: '0 auto',
  width: '100%',
};

const HEADLINE_STYLE = {
  fontSize: 'clamp(1.25rem, 2.4vw, 1.75rem)',
  fontWeight: 700,
  lineHeight: 1.25,
  color: 'var(--sys-text, var(--hp-text))',
};

const GRID_STYLE = {
  display: 'grid',
  gap: '1rem',
  gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 18rem), 1fr))',
};

export function DocsCardCluster({ headline, cards, testId }: DocsCardClusterProps): ReactElement {
  const headingId = `${testId ?? 'docs-card-cluster'}-heading`;
  return (
    <section
      data-testid={testId}
      data-docs-card-cluster=""
      aria-labelledby={headingId}
      style={SECTION_STYLE}
    >
      <h2 id={headingId} style={HEADLINE_STYLE}>
        {headline}
      </h2>
      <div style={GRID_STYLE}>
        {cards.map((card) => (
          <DocsCard key={card.href} {...card} />
        ))}
      </div>
    </section>
  );
}
