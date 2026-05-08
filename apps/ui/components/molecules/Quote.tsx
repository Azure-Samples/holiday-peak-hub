import type { ReactElement } from 'react';
import { MaturityBadge, type MaturityLevel } from '../atoms/MaturityBadge';

/**
 * Quote — social-proof composite (ADR-035 §54 / Issue #1059).
 *
 * Honesty enforcement (compile-time):
 *   - `maturity` is REQUIRED. Quotes carry a maturity badge so a "design
 *     partner" voice cannot be presented as a production reference and
 *     vice versa.
 *   - On `/` (audience-router) we render this composite ONLY when the
 *     consumer can supply a `production` quote. The page does not render a
 *     `<Quote>` slot at all if no production quote exists. (See
 *     `app/page.tsx`.)
 *
 * Tone is implicit — the audience tokens emitted by the parent shell drive
 * the surface treatment via `[data-audience="…"]`. There is no className
 * escape hatch.
 */
export type QuoteProps = {
  body: string;
  attribution: { name: string; role: string; org?: string };
  maturity: MaturityLevel;
  testId?: string;
};

const SECTION_STYLE = {
  display: 'flex',
  flexDirection: 'column' as const,
  alignItems: 'center',
  gap: '1rem',
  padding: 'clamp(2rem, 4vw, 3rem) 1.5rem',
  background: 'var(--sys-surface, var(--hp-surface))',
  borderRadius: 'var(--radius-lg, 1rem)',
  textAlign: 'center' as const,
  maxWidth: '52rem',
  margin: '0 auto',
};

const BODY_STYLE = {
  fontSize: 'clamp(1.125rem, 2vw, 1.375rem)',
  lineHeight: 1.5,
  fontStyle: 'italic' as const,
  color: 'var(--sys-text, var(--hp-text))',
};

const ATTRIBUTION_STYLE = {
  fontSize: '0.875rem',
  color: 'var(--sys-text-muted, var(--hp-text-muted))',
};

export function Quote({ body, attribution, maturity, testId }: QuoteProps): ReactElement {
  return (
    <figure
      data-testid={testId}
      data-quote=""
      data-maturity={maturity}
      style={SECTION_STYLE}
    >
      <blockquote style={BODY_STYLE}>“{body}”</blockquote>
      <figcaption style={ATTRIBUTION_STYLE}>
        <strong>{attribution.name}</strong>
        {attribution.role ? <>, {attribution.role}</> : null}
        {attribution.org ? <> · {attribution.org}</> : null}
      </figcaption>
      <MaturityBadge level={maturity} />
    </figure>
  );
}
