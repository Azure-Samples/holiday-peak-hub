import type { ReactElement } from 'react';
import { MaturityBadge, type MaturityLevel } from '../atoms/MaturityBadge';

/**
 * CaseStudyEmptyState — empty state for /retailers/case-studies (Issue #1044 / Epic #1046).
 *
 * Hard rules from Epic #1046:
 *   - Empty state until a reference customer at "production" maturity exists.
 *   - Logos only with written permission. No aspirational placeholders.
 *   - Maturity badge required at the section level.
 *
 * The empty state is intentionally honest: "No published case studies yet"
 * with an invitation to be the first reference customer. This is the
 * canonical "honest beats marketing" surface.
 */

export type CaseStudyEmptyStateProps = {
  maturity: MaturityLevel;
  /** Optional list of design-partner names (only with written permission). */
  designPartners?: string[];
  testId?: string;
};

const SECTION_STYLE = {
  display: 'flex',
  flexDirection: 'column' as const,
  gap: '1rem',
  padding: 'clamp(2rem, 5vw, 3rem) 1.5rem',
  background: 'var(--sys-surface, var(--hp-surface))',
  borderRadius: 'var(--radius-lg, 1rem)',
  maxWidth: '64rem',
  margin: '0 auto',
  width: '100%',
  textAlign: 'center' as const,
};

const HEADLINE_STYLE = {
  fontSize: 'clamp(1.25rem, 2.4vw, 1.75rem)',
  fontWeight: 700,
  color: 'var(--sys-text, var(--hp-text))',
};

const BODY_STYLE = {
  fontSize: '0.9375rem',
  lineHeight: 1.6,
  color: 'var(--sys-text-muted, var(--hp-text-muted))',
  maxWidth: '40rem',
  margin: '0 auto',
};

const PARTNER_LIST_STYLE = {
  display: 'flex',
  flexWrap: 'wrap' as const,
  gap: '0.5rem',
  justifyContent: 'center',
  marginTop: '0.5rem',
};

const PARTNER_PILL_STYLE = {
  display: 'inline-flex',
  alignItems: 'center',
  padding: '0.25rem 0.625rem',
  borderRadius: '999px',
  border: '1px solid var(--sys-border, var(--hp-border))',
  fontSize: '0.8125rem',
  color: 'var(--sys-text-muted, var(--hp-text-muted))',
  background: 'var(--sys-surface-base, var(--hp-bg))',
};

const HEADER_STYLE = {
  display: 'flex',
  flexWrap: 'wrap' as const,
  alignItems: 'center',
  gap: '0.75rem',
  justifyContent: 'center',
};

export function CaseStudyEmptyState({
  maturity,
  designPartners,
  testId,
}: CaseStudyEmptyStateProps): ReactElement {
  return (
    <section data-testid={testId} data-case-study-empty data-maturity={maturity} style={SECTION_STYLE}>
      <header style={HEADER_STYLE}>
        <h2 style={HEADLINE_STYLE}>No published case studies yet — and we will not fake them.</h2>
        <MaturityBadge level={maturity} />
      </header>
      <p style={BODY_STYLE}>
        Reference customers at production maturity get featured here. Until then, this page stays
        empty by design. No stock-photo &ldquo;customer success stories.&rdquo; No retroactive logos. No quotes
        without written permission.
      </p>
      {designPartners && designPartners.length > 0 ? (
        <>
          <p style={BODY_STYLE}>
            Design partners working with the platform today (named with written permission):
          </p>
          <ul style={PARTNER_LIST_STYLE} aria-label="Design partners">
            {designPartners.map((p) => (
              <li key={p} style={PARTNER_PILL_STYLE}>
                {p}
              </li>
            ))}
          </ul>
        </>
      ) : null}
      <p style={BODY_STYLE}>
        Want to be the first published reference? Email <a href="mailto:partner@holiday-peak-hub.example">partner@holiday-peak-hub.example</a>.
      </p>
    </section>
  );
}
