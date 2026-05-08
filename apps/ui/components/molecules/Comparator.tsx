import type { ReactElement } from 'react';
import { MaturityBadge, type MaturityLevel } from '../atoms/MaturityBadge';

/**
 * Comparator — before/after table (ADR-035 §54 / Issue #1059).
 *
 * Honesty enforcement (compile-time):
 *   - `maturity` is REQUIRED on the comparator AND on every row.
 *     A row without maturity is a compile error.
 *   - The comparator is a structured table, not a marketing prose block —
 *     consumers cannot smuggle prose claims through this composite.
 *
 * Typical use is a 3-row table contrasting a manual workflow (column 1) with
 * the agent-assisted workflow (column 2). The column headers are required
 * to keep the comparison legible without context.
 */
export type ComparatorRow = {
  /** Row label (e.g., "Replenishment review time"). */
  label: string;
  /** Manual / before value. */
  before: string;
  /** Agent / after value. */
  after: string;
  /** Per-row maturity — non-optional at the type level. */
  maturity: MaturityLevel;
};

export type ComparatorProps = {
  kind: 'before-after';
  /** Headline above the table. */
  headline: string;
  /** Optional one-sentence description. */
  description?: string;
  /** Column headers (e.g., `["Manual workflow", "Agent-assisted"]`). */
  columns: [string, string];
  rows: [ComparatorRow, ComparatorRow, ComparatorRow] | ComparatorRow[];
  /** Comparator-level maturity (worst-case across rows). */
  maturity: MaturityLevel;
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
};

const HEADLINE_STYLE = {
  fontSize: 'clamp(1.25rem, 2.4vw, 1.75rem)',
  fontWeight: 700,
  lineHeight: 1.25,
  color: 'var(--sys-text, var(--hp-text))',
};

const DESCRIPTION_STYLE = {
  fontSize: '0.9375rem',
  lineHeight: 1.55,
  color: 'var(--sys-text-muted, var(--hp-text-muted))',
};

const TABLE_STYLE = {
  width: '100%',
  borderCollapse: 'collapse' as const,
  fontSize: '0.9375rem',
};

const TH_STYLE = {
  textAlign: 'left' as const,
  padding: '0.75rem 0.875rem',
  borderBottom: '1px solid var(--sys-border, var(--hp-border))',
  fontWeight: 600,
  color: 'var(--sys-text, var(--hp-text))',
};

const TD_STYLE = {
  padding: '0.75rem 0.875rem',
  borderBottom: '1px solid var(--sys-border, var(--hp-border))',
  verticalAlign: 'top' as const,
  color: 'var(--sys-text, var(--hp-text))',
};

const TD_LABEL_STYLE = { ...TD_STYLE, fontWeight: 600 };

const TD_MUTED_STYLE = { ...TD_STYLE, color: 'var(--sys-text-muted, var(--hp-text-muted))' };

export function Comparator({
  headline,
  description,
  columns,
  rows,
  maturity,
  testId,
}: ComparatorProps): ReactElement {
  return (
    <section
      data-testid={testId}
      data-comparator="before-after"
      data-maturity={maturity}
      style={SECTION_STYLE}
    >
      <header style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.75rem' }}>
        <h2 style={HEADLINE_STYLE}>{headline}</h2>
        <MaturityBadge level={maturity} />
      </header>
      {description ? <p style={DESCRIPTION_STYLE}>{description}</p> : null}
      <div style={{ overflowX: 'auto' }}>
        <table style={TABLE_STYLE}>
          <thead>
            <tr>
              <th style={TH_STYLE} scope="col">
                {/* Empty header for the row-label column */}
              </th>
              <th style={TH_STYLE} scope="col">
                {columns[0]}
              </th>
              <th style={TH_STYLE} scope="col">
                {columns[1]}
              </th>
              <th style={TH_STYLE} scope="col">
                Maturity
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.label}>
                <td style={TD_LABEL_STYLE}>{row.label}</td>
                <td style={TD_MUTED_STYLE}>{row.before}</td>
                <td style={TD_STYLE}>{row.after}</td>
                <td style={TD_STYLE}>
                  <MaturityBadge level={row.maturity} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
