import type { ReactElement } from 'react';
import { MaturityBadge, type MaturityLevel } from '../atoms/MaturityBadge';

/**
 * CostDisclosure — "This is your bill" disclosure (Issue #1038 / Epic #1039).
 *
 * Hard rules from Epic #1039:
 *   - Live estimate based on Azure Retail Prices.
 *   - Explicit currency dropdown (defaults to USD).
 *   - "This is your bill" disclosure unmissable.
 *   - Estimate must show a range (point estimates lie).
 *   - Daily AND monthly run-rate.
 *
 * The actual price retrieval lives server-side (Azure Retail Prices API);
 * this component just renders the band the API returned, plus the
 * unmissable disclosure copy.
 */

export type CostDisclosureProps = {
  /** Daily lower bound (currency-formatted, e.g. "$120"). */
  dailyLower: string;
  /** Daily upper bound. */
  dailyUpper: string;
  /** Monthly lower bound. */
  monthlyLower: string;
  /** Monthly upper bound. */
  monthlyUpper: string;
  /** Currency code (USD, EUR, BRL, ...). */
  currency: string;
  /** ISO date the price snapshot was taken. */
  asOf: string;
  /** Maturity badge for the estimate; design-partner / preview / production. */
  maturity: MaturityLevel;
  /** Optional list of caveats (e.g., "excludes data-egress for non-Azure consumers"). */
  caveats?: string[];
  testId?: string;
};

const SECTION_STYLE = {
  display: 'flex',
  flexDirection: 'column' as const,
  gap: '0.625rem',
  padding: 'clamp(1.5rem, 4vw, 2.25rem) 1.5rem',
  background: 'var(--sys-surface, var(--hp-surface))',
  borderRadius: 'var(--radius-lg, 1rem)',
  maxWidth: '52rem',
  margin: '0 auto',
  width: '100%',
};

const HEADER_STYLE = {
  display: 'flex',
  flexWrap: 'wrap' as const,
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: '0.75rem',
};

const TITLE_STYLE = {
  fontSize: '1.125rem',
  fontWeight: 700,
  color: 'var(--sys-text, var(--hp-text))',
};

const DISCLOSURE_STYLE = {
  padding: '0.75rem 1rem',
  borderRadius: 'var(--radius-md, 0.5rem)',
  border: '1px solid var(--sys-border, var(--hp-border))',
  background: 'var(--sys-surface-base, var(--hp-bg))',
  fontWeight: 600,
  fontSize: '0.9375rem',
  color: 'var(--sys-text, var(--hp-text))',
};

const TABLE_STYLE = {
  width: '100%',
  borderCollapse: 'collapse' as const,
  fontSize: '0.9375rem',
};

const TH_STYLE = {
  textAlign: 'left' as const,
  padding: '0.375rem 0',
  color: 'var(--sys-text-muted, var(--hp-text-muted))',
  fontWeight: 600,
};

const TD_STYLE = {
  padding: '0.375rem 0',
  color: 'var(--sys-text, var(--hp-text))',
};

const FOOTNOTE_STYLE = {
  fontSize: '0.75rem',
  color: 'var(--sys-text-muted, var(--hp-text-muted))',
};

export function CostDisclosure({
  dailyLower,
  dailyUpper,
  monthlyLower,
  monthlyUpper,
  currency,
  asOf,
  maturity,
  caveats,
  testId,
}: CostDisclosureProps): ReactElement {
  return (
    <section data-testid={testId} data-cost-disclosure data-maturity={maturity} style={SECTION_STYLE}>
      <header style={HEADER_STYLE}>
        <h2 style={TITLE_STYLE}>This is your bill.</h2>
        <MaturityBadge level={maturity} />
      </header>
      <p style={DISCLOSURE_STYLE}>
        Estimate based on Azure Retail Prices snapshot from {asOf}. Currency:{' '}
        <strong>{currency}</strong>. The number you see here is the number you will be
        billed by Azure for the resources the deploy-portal provisions in your subscription.
        Holiday Peak Hub does not add a margin.
      </p>
      <table style={TABLE_STYLE}>
        <thead>
          <tr>
            <th style={TH_STYLE} scope="col">Window</th>
            <th style={TH_STYLE} scope="col">Lower bound</th>
            <th style={TH_STYLE} scope="col">Upper bound</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <th style={TD_STYLE} scope="row">Daily</th>
            <td style={TD_STYLE}>{dailyLower}</td>
            <td style={TD_STYLE}>{dailyUpper}</td>
          </tr>
          <tr>
            <th style={TD_STYLE} scope="row">Monthly</th>
            <td style={TD_STYLE}>{monthlyLower}</td>
            <td style={TD_STYLE}>{monthlyUpper}</td>
          </tr>
        </tbody>
      </table>
      {caveats && caveats.length > 0 ? (
        <ul style={{ ...FOOTNOTE_STYLE, paddingLeft: '1rem' }}>
          {caveats.map((c) => (
            <li key={c}>{c}</li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
