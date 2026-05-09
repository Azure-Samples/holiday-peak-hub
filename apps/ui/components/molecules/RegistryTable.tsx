import type { ReactElement } from 'react';
import { MaturityBadge, type MaturityLevel } from '../atoms/MaturityBadge';

/**
 * RegistryTable — sortable / filterable table for builder-side registries
 * (ADRs, patterns, architecture diagrams).  Issues #1047 #1048 #1049 / Epic #1053.
 *
 * Data shape: a list of rows, each row a list of cells. Cells can be plain
 * text or links. The first column is treated as the row identifier and
 * carries any maturity badge or status badge.
 *
 * Design rules:
 *   - Cool/builder design tokens only. No retailer warmth.
 *   - Fully static; no client-side filtering at v1 (search is a follow-up).
 *   - Empty-state surface when the source registry has zero entries.
 */

export type RegistryTableCell =
  | { kind: 'text'; value: string }
  | { kind: 'link'; value: string; href: string }
  | { kind: 'tags'; values: string[] }
  | { kind: 'maturity'; level: MaturityLevel }
  | { kind: 'badge'; value: string };

export type RegistryTableRow = {
  key: string;
  cells: RegistryTableCell[];
};

export type RegistryTableProps = {
  headline: string;
  description?: string;
  columns: string[];
  rows: RegistryTableRow[];
  /** Optional banner content (e.g., stale registry warning). */
  banner?: { tone: 'info' | 'warn'; text: string };
  /** Empty-state copy when rows is empty. */
  emptyState?: { headline: string; body: string };
  testId?: string;
};

const SECTION_STYLE = {
  display: 'flex',
  flexDirection: 'column' as const,
  gap: '1rem',
  padding: 'clamp(2rem, 5vw, 3rem) 1.5rem',
  background: 'var(--sys-surface, var(--hp-surface))',
  borderRadius: 'var(--radius-lg, 1rem)',
  maxWidth: '78rem',
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
  padding: '0.5rem 0.75rem',
  borderBottom: '1px solid var(--sys-border, var(--hp-border))',
  fontWeight: 600,
  color: 'var(--sys-text, var(--hp-text))',
};

const TD_STYLE = {
  padding: '0.5rem 0.75rem',
  borderBottom: '1px solid var(--sys-border, var(--hp-border))',
  verticalAlign: 'top' as const,
  color: 'var(--sys-text, var(--hp-text))',
};

const TAG_STYLE = {
  display: 'inline-flex',
  alignItems: 'center',
  padding: '0.125rem 0.5rem',
  borderRadius: '999px',
  border: '1px solid var(--sys-border, var(--hp-border))',
  fontSize: '0.75rem',
  marginRight: '0.25rem',
  marginBottom: '0.125rem',
  color: 'var(--sys-text-muted, var(--hp-text-muted))',
  background: 'var(--sys-surface-base, var(--hp-bg))',
};

const BADGE_STYLE = {
  display: 'inline-flex',
  alignItems: 'center',
  padding: '0.125rem 0.5rem',
  borderRadius: '0.375rem',
  fontSize: '0.75rem',
  fontWeight: 600,
  background: 'var(--sys-surface-base, var(--hp-bg))',
  border: '1px solid var(--sys-border, var(--hp-border))',
  color: 'var(--sys-text, var(--hp-text))',
};

const BANNER_BASE_STYLE = {
  padding: '0.625rem 0.875rem',
  borderRadius: 'var(--radius-md, 0.5rem)',
  fontSize: '0.875rem',
  border: '1px solid',
};

const BANNER_INFO_STYLE = {
  ...BANNER_BASE_STYLE,
  borderColor: 'var(--sys-border, var(--hp-border))',
  background: 'var(--sys-surface-base, var(--hp-bg))',
  color: 'var(--sys-text, var(--hp-text))',
};

const BANNER_WARN_STYLE = {
  ...BANNER_BASE_STYLE,
  borderColor: 'var(--sys-warning-border, var(--hp-warning-border))',
  background: 'var(--sys-warning-bg, var(--hp-warning-bg))',
  color: 'var(--sys-warning-text, var(--hp-warning-text))',
};

function renderCell(cell: RegistryTableCell): ReactElement {
  switch (cell.kind) {
    case 'text':
      return <span>{cell.value}</span>;
    case 'link':
      return (
        <a href={cell.href} style={{ color: 'var(--sys-link, var(--hp-link))' }}>
          {cell.value}
        </a>
      );
    case 'tags':
      return (
        <span>
          {cell.values.map((t) => (
            <span key={t} style={TAG_STYLE}>
              {t}
            </span>
          ))}
        </span>
      );
    case 'maturity':
      return <MaturityBadge level={cell.level} />;
    case 'badge':
      return <span style={BADGE_STYLE}>{cell.value}</span>;
    default:
      return <span>—</span>;
  }
}

export function RegistryTable({
  headline,
  description,
  columns,
  rows,
  banner,
  emptyState,
  testId,
}: RegistryTableProps): ReactElement {
  const bannerStyle =
    banner?.tone === 'warn' ? BANNER_WARN_STYLE : BANNER_INFO_STYLE;
  return (
    <section data-testid={testId} data-registry-table style={SECTION_STYLE}>
      <header>
        <h2 style={HEADLINE_STYLE}>{headline}</h2>
      </header>
      {description ? <p style={DESCRIPTION_STYLE}>{description}</p> : null}
      {banner ? <p style={bannerStyle} role="status">{banner.text}</p> : null}
      {rows.length === 0 ? (
        <div data-empty-state style={{ padding: '2rem 0', textAlign: 'center' }}>
          <p style={{ ...HEADLINE_STYLE, fontSize: '1.125rem' }}>
            {emptyState?.headline ?? 'No entries yet.'}
          </p>
          <p style={DESCRIPTION_STYLE}>
            {emptyState?.body ?? 'The source registry is empty.'}
          </p>
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={TABLE_STYLE}>
            <thead>
              <tr>
                {columns.map((c) => (
                  <th key={c} scope="col" style={TH_STYLE}>
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.key} data-row-key={r.key}>
                  {r.cells.map((cell, i) => (
                    <td key={`${r.key}:${i}`} style={TD_STYLE}>
                      {renderCell(cell)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
