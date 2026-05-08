import type { ReactElement, ReactNode } from 'react';
import { ConfidenceInterval, type ConfidenceIntervalProps } from '../atoms/ConfidenceInterval';
import { MaturityBadge, type MaturityLevel } from '../atoms/MaturityBadge';

/**
 * ValueProp — outcome-led value-proposition card (ADR-035 §54 / Issue #1057).
 *
 * Honesty enforcement (compile-time):
 *   - `maturity` is REQUIRED. There is no default. A `ValueProp` rendered
 *     without a maturity level is a type error.
 *   - When the card carries a metric, callers MUST pass `confidence`. The
 *     discriminated union below makes "claim with a number, no citation"
 *     impossible at compile time.
 *
 * Composites have no `className` escape hatch. The visual surface is bound
 * by the parent shell's `data-audience` attribute.
 */
type ValuePropBaseProps = {
  /** Single-sentence outcome (the headline). */
  headline: string;
  /** One-paragraph elaboration. */
  body: string;
  /** Maturity level — non-optional at the type level. */
  maturity: MaturityLevel;
  /** Optional reading-aid icon slot (keep purely decorative; aria-hidden). */
  icon?: ReactNode;
  /** Test hook. */
  testId?: string;
};

export type ValuePropQualitative = ValuePropBaseProps & {
  /** No metric — qualitative card. */
  kind: 'qualitative';
};

export type ValuePropQuantitative = ValuePropBaseProps & {
  /** Card carries a number — `confidence` required at the type level. */
  kind: 'quantitative';
  /** Required citation: band, sample, methodology. */
  confidence: ConfidenceIntervalProps;
};

export type ValuePropProps = ValuePropQualitative | ValuePropQuantitative;

const CARD_STYLE = {
  display: 'flex',
  flexDirection: 'column' as const,
  gap: '0.75rem',
  padding: '1.5rem',
  background: 'var(--sys-surface, var(--hp-surface))',
  border: '1px solid var(--sys-border, var(--hp-border))',
  borderRadius: 'var(--radius-lg, 1rem)',
  color: 'var(--sys-text, var(--hp-text))',
};

const HEADLINE_STYLE = {
  fontSize: '1.125rem',
  fontWeight: 600,
  lineHeight: 1.3,
};

const BODY_STYLE = {
  fontSize: '0.9375rem',
  lineHeight: 1.55,
  color: 'var(--sys-text-muted, var(--hp-text-muted))',
};

export function ValueProp(props: ValuePropProps): ReactElement {
  return (
    <article
      data-testid={props.testId}
      data-valueprop-kind={props.kind}
      data-maturity={props.maturity}
      style={CARD_STYLE}
    >
      {props.icon ? (
        <span aria-hidden="true" style={{ fontSize: '1.5rem', lineHeight: 1 }}>
          {props.icon}
        </span>
      ) : null}
      <header style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '0.75rem' }}>
        <h3 style={HEADLINE_STYLE}>{props.headline}</h3>
        <MaturityBadge level={props.maturity} />
      </header>
      <p style={BODY_STYLE}>{props.body}</p>
      {props.kind === 'quantitative' ? <ConfidenceInterval {...props.confidence} /> : null}
    </article>
  );
}
