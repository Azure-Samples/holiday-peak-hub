import type { ReactElement } from 'react';
import { MaturityBadge, type MaturityLevel } from '../atoms/MaturityBadge';

/**
 * PreflightPanel — green / red panel for /deploy/preflight (Issue #1030 /
 * Epic #1039).
 *
 * Each row carries a check id, a verdict, and a reason. Reasons are
 * mandatory on red so the user knows what to fix without contacting
 * support.
 */

export type PreflightVerdict = 'pass' | 'warn' | 'fail';

export type PreflightCheck = {
  id: string;
  label: string;
  verdict: PreflightVerdict;
  reason: string;
  remediationHref?: string;
};

export type PreflightPanelProps = {
  headline: string;
  description?: string;
  checks: PreflightCheck[];
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
  color: 'var(--sys-text, var(--hp-text))',
};

const DESC_STYLE = {
  fontSize: '0.9375rem',
  lineHeight: 1.55,
  color: 'var(--sys-text-muted, var(--hp-text-muted))',
};

const ROW_STYLE = {
  display: 'grid',
  gridTemplateColumns: '2.5rem 1fr auto',
  gap: '0.75rem',
  alignItems: 'start',
  padding: '0.75rem 0',
  borderBottom: '1px solid var(--sys-border, var(--hp-border))',
};

const VERDICT_PASS_STYLE = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  width: '2rem',
  height: '2rem',
  borderRadius: '999px',
  background: 'var(--sys-success-bg, var(--hp-success-bg))',
  color: 'var(--sys-success-text, var(--hp-success-text))',
  fontWeight: 700,
};

const VERDICT_WARN_STYLE = {
  ...VERDICT_PASS_STYLE,
  background: 'var(--sys-warning-bg, var(--hp-warning-bg))',
  color: 'var(--sys-warning-text, var(--hp-warning-text))',
};

const VERDICT_FAIL_STYLE = {
  ...VERDICT_PASS_STYLE,
  background: 'var(--sys-error-bg, var(--hp-error-bg))',
  color: 'var(--sys-error-text, var(--hp-error-text))',
};

const LABEL_STYLE = {
  fontWeight: 600,
  color: 'var(--sys-text, var(--hp-text))',
};

const REASON_STYLE = {
  fontSize: '0.8125rem',
  color: 'var(--sys-text-muted, var(--hp-text-muted))',
  marginTop: '0.125rem',
};

function verdictGlyph(v: PreflightVerdict): { glyph: string; style: typeof VERDICT_PASS_STYLE; label: string } {
  switch (v) {
    case 'pass':
      return { glyph: '✓', style: VERDICT_PASS_STYLE, label: 'Pass' };
    case 'warn':
      return { glyph: '!', style: VERDICT_WARN_STYLE, label: 'Warn' };
    case 'fail':
      return { glyph: '✕', style: VERDICT_FAIL_STYLE, label: 'Fail' };
  }
}

export function PreflightPanel({
  headline,
  description,
  checks,
  maturity,
  testId,
}: PreflightPanelProps): ReactElement {
  return (
    <section data-testid={testId} data-preflight-panel data-maturity={maturity} style={SECTION_STYLE}>
      <header style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.75rem' }}>
        <h2 style={HEADLINE_STYLE}>{headline}</h2>
        <MaturityBadge level={maturity} />
      </header>
      {description ? <p style={DESC_STYLE}>{description}</p> : null}
      {checks.map((c) => {
        const v = verdictGlyph(c.verdict);
        return (
          <div key={c.id} data-check-id={c.id} data-verdict={c.verdict} style={ROW_STYLE}>
            <span style={v.style} aria-label={v.label} title={v.label}>
              {v.glyph}
            </span>
            <div>
              <span style={LABEL_STYLE}>{c.label}</span>
              <p style={REASON_STYLE}>{c.reason}</p>
            </div>
            {c.remediationHref ? (
              <a
                href={c.remediationHref}
                style={{ fontSize: '0.8125rem', color: 'var(--sys-link, var(--hp-link))' }}
              >
                Remediate
              </a>
            ) : (
              <span />
            )}
          </div>
        );
      })}
    </section>
  );
}
