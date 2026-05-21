import type { ReactElement } from 'react';
import { MaturityBadge, type MaturityLevel } from '../atoms/MaturityBadge';

/**
 * FeatureMatrix — capability matrix (ADR-035 §54 / Issue #1059).
 *
 * Used on `/builders` (capabilities shipped vs. roadmap) and `/deploy` (what
 * gets deployed, in what region, what is mocked vs. real). Every row carries
 * a `MaturityBadge` so a vaporware claim cannot ship as "available."
 *
 * `availability` is a deliberate enum:
 *   - `available`    : production-grade, ready to use today
 *   - `preview`      : limited preview / dogfood
 *   - `roadmap`      : planned; honest about absence
 *   - `mocked`       : synthetic on first run (deploy-flow only)
 *
 * The component renders a structured table; consumers cannot smuggle prose.
 */
export type FeatureMatrixAvailability = 'available' | 'preview' | 'roadmap' | 'mocked';

export type FeatureMatrixRow = {
  capability: string;
  /** Short summary cell. */
  summary: string;
  availability: FeatureMatrixAvailability;
  maturity: MaturityLevel;
  /** Optional region scope (used on /deploy). */
  region?: string;
};

export type FeatureMatrixProps = {
  /** Matrix headline. */
  headline: string;
  /** Optional one-sentence description. */
  description?: string;
  /** Show a "Region" column (default: false; turn on for `/deploy`). */
  showRegion?: boolean;
  rows: FeatureMatrixRow[];
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

const AVAILABILITY_PILL_STYLE: Record<FeatureMatrixAvailability, { background: string; color: string }> = {
  available: {
    background: 'color-mix(in srgb, var(--hp-success, #16a34a) 12%, transparent)',
    color: 'var(--hp-success, #16a34a)',
  },
  preview: {
    background: 'color-mix(in srgb, var(--hp-warning, #f59e0b) 14%, transparent)',
    color: 'var(--hp-warning, #f59e0b)',
  },
  roadmap: {
    background: 'color-mix(in srgb, var(--sys-text-muted, var(--hp-text-muted)) 12%, transparent)',
    color: 'var(--sys-text-muted, var(--hp-text-muted))',
  },
  mocked: {
    background: 'color-mix(in srgb, var(--sys-action-primary, var(--hp-primary)) 10%, transparent)',
    color: 'var(--sys-action-primary, var(--hp-primary))',
  },
};

const AVAILABILITY_LABEL: Record<FeatureMatrixAvailability, string> = {
  available: 'Available',
  preview: 'Preview',
  roadmap: 'Roadmap',
  mocked: 'Mocked',
};

function AvailabilityPill({
  availability,
}: {
  availability: FeatureMatrixAvailability;
}): ReactElement {
  const style = AVAILABILITY_PILL_STYLE[availability];
  return (
    <span
      data-feature-matrix-availability={availability}
      style={{
        display: 'inline-flex',
        padding: '0.125rem 0.5rem',
        fontSize: '0.75rem',
        fontWeight: 600,
        borderRadius: '999px',
        background: style.background,
        color: style.color,
      }}
    >
      {AVAILABILITY_LABEL[availability]}
    </span>
  );
}

export function FeatureMatrix({
  headline,
  description,
  showRegion = false,
  rows,
  testId,
}: FeatureMatrixProps): ReactElement {
  return (
    <section
      data-testid={testId}
      data-feature-matrix=""
      style={SECTION_STYLE}
    >
      <header>
        <h2 style={HEADLINE_STYLE}>{headline}</h2>
        {description ? <p style={DESCRIPTION_STYLE}>{description}</p> : null}
      </header>
      <div style={{ overflowX: 'auto' }}>
        <table style={TABLE_STYLE}>
          <thead>
            <tr>
              <th style={TH_STYLE} scope="col">Capability</th>
              <th style={TH_STYLE} scope="col">Summary</th>
              <th style={TH_STYLE} scope="col">Availability</th>
              {showRegion ? (
                <th style={TH_STYLE} scope="col">Region</th>
              ) : null}
              <th style={TH_STYLE} scope="col">Maturity</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.capability}>
                <td style={TD_LABEL_STYLE}>{row.capability}</td>
                <td style={TD_MUTED_STYLE}>{row.summary}</td>
                <td style={TD_STYLE}>
                  <AvailabilityPill availability={row.availability} />
                </td>
                {showRegion ? <td style={TD_MUTED_STYLE}>{row.region ?? '—'}</td> : null}
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
