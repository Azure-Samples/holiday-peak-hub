'use client';

import type { ReactElement } from 'react';

/**
 * ConfidenceInterval — the metric-honesty atom (ADR-035 §54 / Issue #1057).
 *
 * Every composite that renders a number must include a `ConfidenceInterval`
 * (or a citation that includes one) — encoded at the type level on the
 * composite props. A `ValueProp` carrying a numeric claim without a
 * `ConfidenceInterval` is a compile error.
 *
 * The render shape is deliberately verbose:
 *
 *   "4–7 hours → 35–55 minutes (n=3 design partners, observed Jan 2026)"
 *
 * The verbosity is the point — readers see the band, the sample size, and
 * the methodology before they see the headline number.
 */
export type ConfidenceIntervalProps = {
  /** Lower bound of the band in human-readable form. */
  lower: string;
  /** Upper bound of the band in human-readable form. */
  upper: string;
  /** Unit (e.g., "minutes", "%", "queries/sec"). */
  unit: string;
  /** Sample size in absolute count (e.g., 3 design partners). */
  sampleSize: number;
  /** Population descriptor (e.g., "design partners", "internal benchmarks"). */
  population: string;
  /** Methodology descriptor (e.g., "observed Jan 2026", "synthetic load test"). */
  methodology: string;
  /** Optional baseline value for delta presentation (e.g., before-after). */
  baseline?: { lower: string; upper: string; unit: string };
  /** Test hook. */
  testId?: string;
};

/**
 * Render a confidence-interval annotation as inline content. Has no
 * `className` escape hatch.
 */
export function ConfidenceInterval(props: ConfidenceIntervalProps): ReactElement {
  const { lower, upper, unit, sampleSize, population, methodology, baseline, testId } = props;
  const band = `${lower}–${upper} ${unit}`;
  const baselineBand = baseline ? `${baseline.lower}–${baseline.upper} ${baseline.unit}` : null;
  return (
    <span
      data-testid={testId}
      data-confidence
      style={{
        display: 'inline-flex',
        flexDirection: 'column',
        gap: '0.125rem',
        fontSize: '0.875rem',
        lineHeight: 1.4,
        color: 'var(--sys-text-muted, var(--hp-text-muted))',
      }}
    >
      <span style={{ fontVariantNumeric: 'tabular-nums', color: 'var(--sys-text, var(--hp-text))' }}>
        {baselineBand ? (
          <>
            {baselineBand}
            <span aria-hidden="true" style={{ margin: '0 0.5rem' }}>
              →
            </span>
            <strong>{band}</strong>
          </>
        ) : (
          <strong>{band}</strong>
        )}
      </span>
      <span style={{ fontSize: '0.75rem' }}>
        n={sampleSize} {population}, {methodology}
      </span>
    </span>
  );
}
