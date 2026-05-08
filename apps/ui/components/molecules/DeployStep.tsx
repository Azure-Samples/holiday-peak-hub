import type { ReactElement, ReactNode } from 'react';

/**
 * DeployStep — labeled step in a deploy flow (ADR-035 §54 / Issue #1059).
 *
 * Used as the cluster on `/deploy` (5 steps: sign in, pick subscription, name
 * deployment, review estimated cost, launch). Two of the steps are stateful
 * client composites (steps 1 and 4 — sign-in and cost preview); the rest
 * are server-rendered. The cluster as a whole is the only stateful client
 * composite on `/deploy`.
 *
 * `DeployStep` itself is **purely presentational** and server-renderable.
 * State / interactivity (the "Sign in" CTA, the cost preview range) is
 * supplied by the parent via the `actions` and `body` slots.
 */
export type DeployStepProps = {
  /** 1-based ordinal (rendered as "Step N"). */
  ordinal: number;
  /** Step headline. */
  headline: string;
  /** One-sentence summary. */
  summary: string;
  /** Optional richer body (passed through verbatim — used for the cost-preview range). */
  body?: ReactNode;
  /** Optional CTA / action area. */
  actions?: ReactNode;
  /** Mark steps that require client-side state ("Sign in", "Review cost"). */
  stateful?: boolean;
  testId?: string;
};

const CARD_STYLE = {
  display: 'flex',
  flexDirection: 'column' as const,
  gap: '0.625rem',
  padding: '1.25rem 1.5rem',
  borderRadius: 'var(--radius-lg, 1rem)',
  border: '1px solid var(--sys-border, var(--hp-border))',
  background: 'var(--sys-surface, var(--hp-surface))',
};

const ORDINAL_STYLE = {
  fontSize: '0.75rem',
  fontWeight: 700,
  textTransform: 'uppercase' as const,
  letterSpacing: '0.08em',
  color: 'var(--sys-text-muted, var(--hp-text-muted))',
};

const HEADLINE_STYLE = {
  fontSize: '1.0625rem',
  fontWeight: 600,
  lineHeight: 1.3,
  color: 'var(--sys-text, var(--hp-text))',
};

const SUMMARY_STYLE = {
  fontSize: '0.9375rem',
  lineHeight: 1.5,
  color: 'var(--sys-text-muted, var(--hp-text-muted))',
};

export function DeployStep({
  ordinal,
  headline,
  summary,
  body,
  actions,
  stateful,
  testId,
}: DeployStepProps): ReactElement {
  return (
    <article
      data-testid={testId}
      data-deploy-step={ordinal}
      data-stateful={stateful ? 'true' : 'false'}
      style={CARD_STYLE}
    >
      <span style={ORDINAL_STYLE}>Step {ordinal}</span>
      <h3 style={HEADLINE_STYLE}>{headline}</h3>
      <p style={SUMMARY_STYLE}>{summary}</p>
      {body ? <div>{body}</div> : null}
      {actions ? <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>{actions}</div> : null}
    </article>
  );
}
