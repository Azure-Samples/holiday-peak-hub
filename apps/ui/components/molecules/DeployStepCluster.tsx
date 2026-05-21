import type { ReactElement } from 'react';
import { DeployStep, type DeployStepProps } from './DeployStep';

/**
 * DeployStepCluster — labelled stack of `DeployStep`s (ADR-035 §54 / Issue #1059).
 *
 * Used on `/deploy` to surface the 5-step flow (sign in, pick subscription,
 * name deployment, review estimated cost, launch). The cluster owns the
 * heading and stack layout so the audience-route page-level code stays free
 * of inline layout (per ADR-035 §49 / Issue #1058 L-3).
 *
 * Steps are passed as a flat list. The cluster numbers them automatically
 * (callers do NOT supply `ordinal` — that property on `DeployStep` is set
 * here from the array index).
 */
export type DeployStepClusterProps = {
  headline: string;
  description?: string;
  steps: ReadonlyArray<Omit<DeployStepProps, 'ordinal'>>;
  testId?: string;
};

const SECTION_STYLE = {
  display: 'flex',
  flexDirection: 'column' as const,
  gap: '1rem',
  padding: 'clamp(2rem, 5vw, 3rem) 1.5rem',
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

const STACK_STYLE = {
  display: 'flex',
  flexDirection: 'column' as const,
  gap: '0.75rem',
};

export function DeployStepCluster({
  headline,
  description,
  steps,
  testId,
}: DeployStepClusterProps): ReactElement {
  const headingId = `${testId ?? 'deploy-step-cluster'}-heading`;
  return (
    <section
      data-testid={testId}
      data-deploy-step-cluster=""
      aria-labelledby={headingId}
      style={SECTION_STYLE}
    >
      <h2 id={headingId} style={HEADLINE_STYLE}>
        {headline}
      </h2>
      {description ? <p style={DESCRIPTION_STYLE}>{description}</p> : null}
      <ol style={{ ...STACK_STYLE, listStyle: 'none', padding: 0, margin: 0 }}>
        {steps.map((step, index) => (
          <li key={step.headline}>
            <DeployStep {...step} ordinal={index + 1} />
          </li>
        ))}
      </ol>
    </section>
  );
}
