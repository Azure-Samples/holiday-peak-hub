import type { ReactElement } from 'react';
import Link from 'next/link';

/**
 * CallToAction — the conversion composite (ADR-035 §54 / Issue #1057).
 *
 * Discriminated by `tone`:
 *   - `audience-pair` : two equally-weighted CTAs (used as the `/` second-pass
 *                        per NN/g research and on retailer/builder pages
 *                        as the bottom CTA bar).
 *   - `single`        : single primary CTA + optional caption.
 *   - `procurement`   : procurement-tone CTA with explicit RFP / Trust Center
 *                        link, surfaced near the footer of `/retailers`.
 *
 * Composites have no `className` escape hatch.
 */
export type CallToActionAudiencePairProps = {
  tone: 'audience-pair';
  headline: string;
  primary: { label: string; href: string };
  secondary: { label: string; href: string };
  testId?: string;
};

export type CallToActionSingleProps = {
  tone: 'single';
  headline: string;
  primary: { label: string; href: string };
  caption?: string;
  testId?: string;
};

export type CallToActionProcurementProps = {
  tone: 'procurement';
  headline: string;
  primary: { label: string; href: string };
  trustCenter: { label: string; href: string };
  testId?: string;
};

export type CallToActionProps =
  | CallToActionAudiencePairProps
  | CallToActionSingleProps
  | CallToActionProcurementProps;

const SECTION_STYLE = {
  display: 'flex',
  flexDirection: 'column' as const,
  alignItems: 'center',
  gap: '1rem',
  padding: 'clamp(2rem, 5vw, 3.5rem) 1.5rem',
  background: 'var(--sys-surface-accent, var(--hp-primary-soft))',
  borderRadius: 'var(--radius-lg, 1rem)',
  textAlign: 'center' as const,
};

const HEADLINE_STYLE = {
  fontSize: 'clamp(1.25rem, 2.5vw, 1.875rem)',
  fontWeight: 700,
  lineHeight: 1.25,
  color: 'var(--sys-text, var(--hp-text))',
  maxWidth: '40rem',
};

const PRIMARY_STYLE = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: '0.5rem',
  padding: '0.75rem 1.25rem',
  borderRadius: 'var(--radius-md, 0.75rem)',
  background: 'var(--sys-action-primary, var(--hp-primary))',
  color: 'var(--sys-action-primary-foreground, white)',
  fontWeight: 600,
  textDecoration: 'none' as const,
};

const SECONDARY_STYLE = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: '0.5rem',
  padding: '0.75rem 1.25rem',
  borderRadius: 'var(--radius-md, 0.75rem)',
  border: '1px solid var(--sys-border-accent, var(--hp-border))',
  color: 'var(--sys-text, var(--hp-text))',
  fontWeight: 600,
  textDecoration: 'none' as const,
  background: 'transparent',
};

const CAPTION_STYLE = {
  fontSize: '0.875rem',
  color: 'var(--sys-text-muted, var(--hp-text-muted))',
};

export function CallToAction(props: CallToActionProps): ReactElement {
  return (
    <section data-testid={props.testId} data-cta-tone={props.tone} style={SECTION_STYLE}>
      <h2 style={HEADLINE_STYLE}>{props.headline}</h2>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', justifyContent: 'center' }}>
        <Link href={props.primary.href} style={PRIMARY_STYLE}>
          {props.primary.label}
        </Link>
        {props.tone === 'audience-pair' ? (
          <Link href={props.secondary.href} style={PRIMARY_STYLE}>
            {props.secondary.label}
          </Link>
        ) : null}
        {props.tone === 'procurement' ? (
          <Link href={props.trustCenter.href} style={SECONDARY_STYLE}>
            {props.trustCenter.label}
          </Link>
        ) : null}
      </div>
      {props.tone === 'single' && props.caption ? <p style={CAPTION_STYLE}>{props.caption}</p> : null}
    </section>
  );
}
