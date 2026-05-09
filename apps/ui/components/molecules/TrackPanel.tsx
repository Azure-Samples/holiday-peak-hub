import type { ReactElement } from 'react';
import { MaturityBadge, type MaturityLevel } from '../atoms/MaturityBadge';

/**
 * TrackPanel — running-deployment status panel (Issue #1032 / Epic #1039).
 *
 * v1: server-rendered snapshot panel. The actual real-time refresh ships
 * with the SignalR client wiring once the deploy-portal API publishes the
 * status hub.
 *
 * Hard rules from Epic #1039:
 *   - "Clean up now" is the PRIMARY action even on a successful deployment
 *     so the user always has an exit path (#1036).
 *   - "Delete this deployment" requires type-the-RG confirmation (#1036).
 *   - 30-day audit retention surfaced in the panel.
 */

export type TrackPhase = 'queued' | 'preflight' | 'provisioning' | 'configuring' | 'verifying' | 'success' | 'failed' | 'rolling-back';

export type TrackStep = {
  id: string;
  label: string;
  phase: TrackPhase;
  startedAt?: string;
  durationSeconds?: number;
  detail?: string;
};

export type TrackPanelProps = {
  deploymentId: string;
  resourceGroup: string;
  region: string;
  subscriptionAlias: string;
  steps: TrackStep[];
  currentPhase: TrackPhase;
  retentionDays: number;
  cleanupHref: string;
  deleteHref: string;
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
  maxWidth: '78rem',
  margin: '0 auto',
  width: '100%',
};

const HEADLINE_STYLE = {
  fontSize: 'clamp(1.25rem, 2.4vw, 1.75rem)',
  fontWeight: 700,
  color: 'var(--sys-text, var(--hp-text))',
};

const META_STYLE = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(11rem, 1fr))',
  gap: '0.5rem',
  fontSize: '0.875rem',
  color: 'var(--sys-text-muted, var(--hp-text-muted))',
};

const META_KEY_STYLE = {
  display: 'block',
  fontSize: '0.6875rem',
  textTransform: 'uppercase' as const,
  letterSpacing: '0.05em',
  color: 'var(--sys-text-muted, var(--hp-text-muted))',
};

const STEP_STYLE = {
  display: 'grid',
  gridTemplateColumns: '2.25rem 1fr auto',
  gap: '0.75rem',
  alignItems: 'center',
  padding: '0.625rem 0',
  borderBottom: '1px solid var(--sys-border, var(--hp-border))',
};

const STEP_BUBBLE_STYLE = {
  width: '1.875rem',
  height: '1.875rem',
  borderRadius: '999px',
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  background: 'var(--sys-surface-base, var(--hp-bg))',
  border: '1px solid var(--sys-border, var(--hp-border))',
  fontWeight: 600,
};

const ACTIONS_STYLE = {
  display: 'flex',
  flexWrap: 'wrap' as const,
  gap: '0.75rem',
  marginTop: '0.5rem',
};

const PRIMARY_BTN_STYLE = {
  padding: '0.5rem 1rem',
  borderRadius: 'var(--radius-md, 0.5rem)',
  background: 'var(--sys-primary, var(--hp-primary))',
  color: 'var(--sys-on-primary, var(--hp-on-primary))',
  fontWeight: 600,
  fontSize: '0.875rem',
  textDecoration: 'none',
  border: 'none',
};

const SECONDARY_BTN_STYLE = {
  padding: '0.5rem 1rem',
  borderRadius: 'var(--radius-md, 0.5rem)',
  background: 'transparent',
  border: '1px solid var(--sys-border, var(--hp-border))',
  color: 'var(--sys-text, var(--hp-text))',
  fontWeight: 600,
  fontSize: '0.875rem',
  textDecoration: 'none',
};

export function TrackPanel({
  deploymentId,
  resourceGroup,
  region,
  subscriptionAlias,
  steps,
  currentPhase,
  retentionDays,
  cleanupHref,
  deleteHref,
  maturity,
  testId,
}: TrackPanelProps): ReactElement {
  return (
    <section data-testid={testId} data-track-panel data-current-phase={currentPhase} style={SECTION_STYLE}>
      <header style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.75rem' }}>
        <h2 style={HEADLINE_STYLE}>Deployment {deploymentId}</h2>
        <MaturityBadge level={maturity} />
      </header>
      <div style={META_STYLE}>
        <div>
          <span style={META_KEY_STYLE}>Resource group</span>
          <span>{resourceGroup}</span>
        </div>
        <div>
          <span style={META_KEY_STYLE}>Region</span>
          <span>{region}</span>
        </div>
        <div>
          <span style={META_KEY_STYLE}>Subscription</span>
          <span>{subscriptionAlias}</span>
        </div>
        <div>
          <span style={META_KEY_STYLE}>Retention</span>
          <span>{retentionDays} d (then purged)</span>
        </div>
      </div>
      <div data-track-steps>
        {steps.map((s, i) => (
          <div key={s.id} data-step-id={s.id} data-step-phase={s.phase} style={STEP_STYLE}>
            <span style={STEP_BUBBLE_STYLE}>{i + 1}</span>
            <div>
              <span style={{ fontWeight: 600 }}>{s.label}</span>
              {s.detail ? <span style={{ display: 'block', fontSize: '0.8125rem', color: 'var(--sys-text-muted, var(--hp-text-muted))' }}>{s.detail}</span> : null}
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--sys-text-muted, var(--hp-text-muted))' }}>
              {s.startedAt ? `started ${s.startedAt}` : '—'}
              {s.durationSeconds !== undefined ? ` · ${s.durationSeconds}s` : ''}
            </span>
          </div>
        ))}
      </div>
      <div style={ACTIONS_STYLE}>
        <a href={cleanupHref} style={PRIMARY_BTN_STYLE} data-track-cleanup>
          Clean up now
        </a>
        <a href={deleteHref} style={SECONDARY_BTN_STYLE} data-track-delete>
          Delete this deployment (type-the-RG)
        </a>
      </div>
    </section>
  );
}
