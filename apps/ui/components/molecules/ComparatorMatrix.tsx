import type { ReactElement } from 'react';
import { MaturityBadge, type MaturityLevel } from '../atoms/MaturityBadge';

/**
 * ComparatorMatrix — vendor-by-criteria matrix (Issue #1043 / Epic #1046).
 *
 * Honesty enforcement:
 *   - Every cell carries a `verified` date string and an optional `source`.
 *   - The matrix as a whole carries a maturity badge.
 *   - The set of vendors is locked to point-solution AI vendors per the
 *     epic — full commerce platforms (Salesforce, Shopify, SAP) are
 *     intentionally NOT in scope (category error).
 *
 * Layout: rows are vendors, columns are criteria. The first column carries
 * the vendor name. The remaining columns are criteria; each cell renders a
 * short verdict + the verification footer.
 */

export type ComparatorMatrixCell = {
  /** Short verdict ("Yes", "Partial", "No", or a one-line note). */
  verdict: string;
  /** Optional one-line explanation for the cell. */
  note?: string;
  /** Date the cell was last verified, ISO format (e.g., "2025-11-04"). */
  verified: string;
  /** Optional source URL or citation key. */
  source?: string;
};

export type ComparatorMatrixVendor = {
  key: string;
  /** Vendor brand name (e.g., "Algolia"). */
  name: string;
  /** One-line vendor positioning. */
  positioning: string;
  /** Cells keyed by criterion key. */
  cells: Record<string, ComparatorMatrixCell>;
};

export type ComparatorMatrixCriterion = {
  key: string;
  /** Column header (e.g., "Open source"). */
  label: string;
  /** Optional sub-header explanation. */
  hint?: string;
};

export type ComparatorMatrixProps = {
  headline: string;
  description?: string;
  criteria: ComparatorMatrixCriterion[];
  vendors: ComparatorMatrixVendor[];
  maturity: MaturityLevel;
  /** Note appended below the matrix to disclose comparator-set scope. */
  scopeNote?: string;
  testId?: string;
};

const SECTION_STYLE = {
  display: 'flex',
  flexDirection: 'column' as const,
  gap: '1rem',
  padding: 'clamp(2rem, 5vw, 3rem) 1.5rem',
  background: 'var(--sys-surface, var(--hp-surface))',
  borderRadius: 'var(--radius-lg, 1rem)',
  maxWidth: '72rem',
  margin: '0 auto',
  width: '100%',
};

const HEADLINE_STYLE = {
  fontSize: 'clamp(1.25rem, 2.4vw, 1.75rem)',
  fontWeight: 700,
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
  fontSize: '0.875rem',
};

const TH_STYLE = {
  textAlign: 'left' as const,
  padding: '0.625rem 0.75rem',
  borderBottom: '1px solid var(--sys-border, var(--hp-border))',
  fontWeight: 600,
  color: 'var(--sys-text, var(--hp-text))',
  verticalAlign: 'top' as const,
};

const TH_HINT_STYLE = {
  fontSize: '0.75rem',
  fontWeight: 400,
  color: 'var(--sys-text-muted, var(--hp-text-muted))',
};

const TD_STYLE = {
  padding: '0.625rem 0.75rem',
  borderBottom: '1px solid var(--sys-border, var(--hp-border))',
  verticalAlign: 'top' as const,
  color: 'var(--sys-text, var(--hp-text))',
};

const VENDOR_CELL_STYLE = {
  ...TD_STYLE,
  fontWeight: 600,
};

const VENDOR_POSITION_STYLE = {
  display: 'block',
  fontSize: '0.75rem',
  fontWeight: 400,
  color: 'var(--sys-text-muted, var(--hp-text-muted))',
};

const NOTE_STYLE = {
  fontSize: '0.8125rem',
  color: 'var(--sys-text-muted, var(--hp-text-muted))',
};

const VERIFIED_STYLE = {
  fontSize: '0.75rem',
  color: 'var(--sys-text-muted, var(--hp-text-muted))',
};

export function ComparatorMatrix({
  headline,
  description,
  criteria,
  vendors,
  maturity,
  scopeNote,
  testId,
}: ComparatorMatrixProps): ReactElement {
  return (
    <section
      data-testid={testId}
      data-comparator-matrix
      data-maturity={maturity}
      style={SECTION_STYLE}
    >
      <header
        style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.75rem' }}
      >
        <h2 style={HEADLINE_STYLE}>{headline}</h2>
        <MaturityBadge level={maturity} />
      </header>
      {description ? <p style={DESCRIPTION_STYLE}>{description}</p> : null}
      <div style={{ overflowX: 'auto' }}>
        <table style={TABLE_STYLE}>
          <thead>
            <tr>
              <th style={TH_STYLE} scope="col">
                Vendor
              </th>
              {criteria.map((c) => (
                <th key={c.key} style={TH_STYLE} scope="col">
                  {c.label}
                  {c.hint ? <span style={TH_HINT_STYLE}>{` — ${c.hint}`}</span> : null}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {vendors.map((v) => (
              <tr key={v.key} data-vendor-key={v.key}>
                <td style={VENDOR_CELL_STYLE} scope="row">
                  {v.name}
                  <span style={VENDOR_POSITION_STYLE}>{v.positioning}</span>
                </td>
                {criteria.map((c) => {
                  const cell = v.cells[c.key];
                  if (!cell) {
                    return (
                      <td key={c.key} style={TD_STYLE} data-criterion-key={c.key}>
                        <span style={NOTE_STYLE}>—</span>
                      </td>
                    );
                  }
                  return (
                    <td key={c.key} style={TD_STYLE} data-criterion-key={c.key}>
                      <span>{cell.verdict}</span>
                      {cell.note ? (
                        <span style={{ display: 'block', ...NOTE_STYLE }}>{cell.note}</span>
                      ) : null}
                      <span style={{ display: 'block', ...VERIFIED_STYLE }}>
                        Last verified {cell.verified}
                        {cell.source ? ` · ${cell.source}` : ''}
                      </span>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {scopeNote ? <p style={NOTE_STYLE}>{scopeNote}</p> : null}
    </section>
  );
}
