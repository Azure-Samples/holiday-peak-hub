'use client';

import { useMemo, useState, type ChangeEvent, type ReactElement } from 'react';
import { MaturityBadge, type MaturityLevel } from '../atoms/MaturityBadge';

/**
 * ROICalculator — illustrative retail ROI estimator (Issue #1042 / Epic #1046).
 *
 * Honesty enforcement:
 *   - Required `maturity` prop. The calculator labels itself "Illustrative"
 *     until a reference customer at production maturity exists.
 *   - Outputs are rendered as a confidence band (±40 % of the central estimate)
 *     with the methodology link visible inline.
 *   - No personal data is collected. Calculations run client-side only.
 *
 * The math is deliberately transparent: monthly buyer-time savings × analyst
 * loaded cost + monthly returns-dispute reduction × dispute loaded cost. The
 * coefficients are documented in `docs/methodology/retailer-roi.md`.
 */
export type ROICalculatorProps = {
  maturity: MaturityLevel;
  methodologyHref: string;
  testId?: string;
};

type Inputs = {
  /** Number of buyers / merchandisers in the retailer's organization. */
  buyers: number;
  /** Hours per buyer per day spent on replenishment review (manual baseline). */
  buyerHoursPerDay: number;
  /** Loaded hourly cost of a buyer in USD. */
  buyerHourlyCost: number;
  /** Returns volume per month (units). */
  returnsPerMonth: number;
  /** Average dispute escalation cost in USD per disputed return. */
  disputeCost: number;
};

const DEFAULTS: Inputs = {
  buyers: 12,
  buyerHoursPerDay: 5,
  buyerHourlyCost: 65,
  returnsPerMonth: 4000,
  disputeCost: 28,
};

const SECTION_STYLE = {
  display: 'flex',
  flexDirection: 'column' as const,
  gap: '1.5rem',
  padding: 'clamp(2rem, 5vw, 3rem) 1.5rem',
  background: 'var(--sys-surface, var(--hp-surface))',
  borderRadius: 'var(--radius-lg, 1rem)',
  maxWidth: '64rem',
  margin: '0 auto',
  width: '100%',
};

const FORM_GRID = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
  gap: '1rem',
};

const FIELD_STYLE = {
  display: 'flex',
  flexDirection: 'column' as const,
  gap: '0.25rem',
};

const LABEL_STYLE = {
  fontSize: '0.8125rem',
  fontWeight: 600,
  color: 'var(--sys-text, var(--hp-text))',
};

const HINT_STYLE = {
  fontSize: '0.75rem',
  color: 'var(--sys-text-muted, var(--hp-text-muted))',
};

const INPUT_STYLE = {
  padding: '0.5rem 0.625rem',
  borderRadius: 'var(--radius-md, 0.75rem)',
  border: '1px solid var(--sys-border, var(--hp-border))',
  background: 'var(--sys-surface-base, var(--hp-bg))',
  color: 'var(--sys-text, var(--hp-text))',
  fontSize: '0.9375rem',
  fontVariantNumeric: 'tabular-nums' as const,
};

const RESULTS_STYLE = {
  display: 'flex',
  flexDirection: 'column' as const,
  gap: '0.5rem',
  padding: '1rem 1.25rem',
  borderRadius: 'var(--radius-md, 0.75rem)',
  border: '1px solid var(--sys-border, var(--hp-border))',
  background: 'var(--sys-surface-base, var(--hp-bg))',
};

const HEADLINE_STYLE = {
  fontSize: 'clamp(1.25rem, 2.2vw, 1.625rem)',
  fontWeight: 700,
  color: 'var(--sys-text, var(--hp-text))',
};

const BAND_STYLE = {
  fontSize: 'clamp(1.5rem, 2.6vw, 2rem)',
  fontWeight: 700,
  fontVariantNumeric: 'tabular-nums' as const,
  color: 'var(--sys-text, var(--hp-text))',
};

const CAPTION_STYLE = {
  fontSize: '0.8125rem',
  color: 'var(--sys-text-muted, var(--hp-text-muted))',
};

function formatUsd(value: number): string {
  if (!Number.isFinite(value) || value <= 0) return '$0';
  return value.toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  });
}

function clampNumber(value: string, fallback: number): number {
  const n = Number(value);
  if (!Number.isFinite(n) || n < 0) return fallback;
  return n;
}

export function ROICalculator({ maturity, methodologyHref, testId }: ROICalculatorProps): ReactElement {
  const [inputs, setInputs] = useState<Inputs>(DEFAULTS);

  const central = useMemo(() => {
    // Central estimate.
    // Time savings: agent reduces buyerHoursPerDay by ~75 % observed at
    //   design partners (range 60–85 %); central = 0.75.
    // Returns disputes: agent reduces dispute escalations by ~22 % observed at
    //   design partners (range 18–28 %); central = 0.22.
    // Both reductions are documented in docs/methodology/retailer-roi.md.
    const workdays = 22;
    const buyerSavings =
      inputs.buyers * inputs.buyerHoursPerDay * 0.75 * inputs.buyerHourlyCost * workdays;
    const disputeSavings = inputs.returnsPerMonth * 0.22 * inputs.disputeCost;
    return buyerSavings + disputeSavings;
  }, [inputs]);

  const lower = central * 0.6;
  const upper = central * 1.4;

  return (
    <section data-testid={testId} data-roi-calculator data-maturity={maturity} style={SECTION_STYLE}>
      <header style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.75rem' }}>
        <h2 style={HEADLINE_STYLE}>Illustrative monthly savings</h2>
        <MaturityBadge level={maturity} />
        <span data-illustrative-label style={CAPTION_STYLE}>
          Illustrative — coefficients calibrated against design partners; will be re-baselined with reference customers.
        </span>
      </header>

      <form
        aria-label="ROI calculator inputs"
        style={FORM_GRID}
        onSubmit={(e) => e.preventDefault()}
      >
        <Field
          label="Buyers / merchandisers"
          hint="Headcount across replenishment + assortment teams"
          value={inputs.buyers}
          step="1"
          onChange={(v) => setInputs((s) => ({ ...s, buyers: clampNumber(v, DEFAULTS.buyers) }))}
        />
        <Field
          label="Hours per buyer per day"
          hint="Time spent on replenishment review today"
          value={inputs.buyerHoursPerDay}
          step="0.25"
          onChange={(v) =>
            setInputs((s) => ({ ...s, buyerHoursPerDay: clampNumber(v, DEFAULTS.buyerHoursPerDay) }))
          }
        />
        <Field
          label="Buyer loaded hourly cost (USD)"
          hint="Salary + benefits + overhead"
          value={inputs.buyerHourlyCost}
          step="1"
          onChange={(v) =>
            setInputs((s) => ({ ...s, buyerHourlyCost: clampNumber(v, DEFAULTS.buyerHourlyCost) }))
          }
        />
        <Field
          label="Returns per month"
          hint="Units returned that go through your triage queue"
          value={inputs.returnsPerMonth}
          step="100"
          onChange={(v) =>
            setInputs((s) => ({ ...s, returnsPerMonth: clampNumber(v, DEFAULTS.returnsPerMonth) }))
          }
        />
        <Field
          label="Dispute cost (USD)"
          hint="Loaded cost of an escalated dispute"
          value={inputs.disputeCost}
          step="1"
          onChange={(v) =>
            setInputs((s) => ({ ...s, disputeCost: clampNumber(v, DEFAULTS.disputeCost) }))
          }
        />
      </form>

      <div role="region" aria-live="polite" style={RESULTS_STYLE} data-roi-output>
        <span style={BAND_STYLE}>
          {formatUsd(central)}{' '}
          <span style={{ fontWeight: 500, fontSize: '0.6em' }}>/ month</span>
        </span>
        <span style={CAPTION_STYLE}>
          Range {formatUsd(lower)} – {formatUsd(upper)} (±40 % confidence interval).
        </span>
        <span style={CAPTION_STYLE}>
          Built from buyer-time savings (75 % reduction observed at design partners) and dispute reduction (22 %).{' '}
          <a href={methodologyHref}>Read the methodology and coefficients.</a>
        </span>
      </div>

      <p style={CAPTION_STYLE}>
        No data is sent anywhere. Calculations run in your browser only. Every input keeps the same
        confidence interval applied to the central estimate.
      </p>
    </section>
  );
}

function Field({
  label,
  hint,
  value,
  step,
  onChange,
}: {
  label: string;
  hint: string;
  value: number;
  step: string;
  onChange: (v: string) => void;
}): ReactElement {
  return (
    <label style={FIELD_STYLE}>
      <span style={LABEL_STYLE}>{label}</span>
      <input
        type="number"
        min="0"
        step={step}
        value={value}
        style={INPUT_STYLE}
        onChange={(e: ChangeEvent<HTMLInputElement>) => onChange(e.target.value)}
      />
      <span style={HINT_STYLE}>{hint}</span>
    </label>
  );
}
