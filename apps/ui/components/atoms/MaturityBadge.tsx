'use client';

import type { ReactElement } from 'react';

/**
 * MaturityBadge — the honesty-enforcing atom (ADR-035 §54 / Issue #1057).
 *
 * Every composite that renders a claim, a number, or a quote must accept
 * a `MaturityBadge` at the type level. A `Comparator`, `ValueProp`, or
 * `Quote` rendered without `MaturityBadge` is a compile error — see the
 * discriminated union types in `apps/ui/components/molecules/`.
 *
 * The four levels are deliberate and ordered:
 *   - production   : in production today on real customer data
 *   - design-partner : observed on real customer data inside a paid
 *                      design-partner engagement; not generally available
 *   - preview      : limited internal-preview / dogfood; honest about scope
 *   - internal     : framework-internal claim; never describes a customer
 *
 * No fifth level. Adding one requires amending ADR-035 §54.
 */
export type MaturityLevel = 'production' | 'design-partner' | 'preview' | 'internal';

const MATURITY_COPY: Record<MaturityLevel, { label: string; tone: 'success' | 'info' | 'warning' | 'neutral' }> = {
  production: { label: 'Production', tone: 'success' },
  'design-partner': { label: 'Design partner', tone: 'info' },
  preview: { label: 'Preview', tone: 'warning' },
  internal: { label: 'Internal', tone: 'neutral' },
};

const TONE_STYLE: Record<MaturityLevel, { background: string; color: string; border: string }> = {
  production: {
    background: 'color-mix(in srgb, var(--hp-success, #16a34a) 12%, transparent)',
    color: 'var(--hp-success, #16a34a)',
    border: 'color-mix(in srgb, var(--hp-success, #16a34a) 35%, transparent)',
  },
  'design-partner': {
    background: 'color-mix(in srgb, var(--sys-action-primary, var(--hp-primary)) 10%, transparent)',
    color: 'var(--sys-action-primary, var(--hp-primary))',
    border: 'color-mix(in srgb, var(--sys-action-primary, var(--hp-primary)) 30%, transparent)',
  },
  preview: {
    background: 'color-mix(in srgb, var(--hp-warning, #f59e0b) 14%, transparent)',
    color: 'var(--hp-warning, #f59e0b)',
    border: 'color-mix(in srgb, var(--hp-warning, #f59e0b) 35%, transparent)',
  },
  internal: {
    background: 'color-mix(in srgb, var(--sys-text-muted, var(--hp-text-muted)) 12%, transparent)',
    color: 'var(--sys-text, var(--hp-text))',
    border: 'color-mix(in srgb, var(--sys-text-muted, var(--hp-text-muted)) 30%, transparent)',
  },
};

export type MaturityBadgeProps = {
  level: MaturityLevel;
  /** Optional descriptor visible to assistive tech (e.g., "production maturity badge"). */
  ariaLabel?: string;
  /** Test hook. */
  testId?: string;
};

/**
 * Render a maturity-level pill. Has no `className` escape hatch — composites
 * always render the badge in the same visual surface.
 */
export function MaturityBadge({ level, ariaLabel, testId }: MaturityBadgeProps): ReactElement {
  const { label } = MATURITY_COPY[level];
  const style = TONE_STYLE[level];
  return (
    <span
      role="status"
      aria-label={ariaLabel ?? `${label} maturity`}
      data-testid={testId}
      data-maturity={level}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.375rem',
        padding: '0.125rem 0.5rem',
        fontSize: '0.75rem',
        fontWeight: 600,
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        borderRadius: 'var(--radius-sm, 0.5rem)',
        background: style.background,
        color: style.color,
        border: `1px solid ${style.border}`,
        whiteSpace: 'nowrap',
      }}
    >
      <span aria-hidden="true" style={{ width: '0.375rem', height: '0.375rem', borderRadius: '50%', background: style.color }} />
      {label}
    </span>
  );
}
