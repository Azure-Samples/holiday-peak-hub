import type { ReactElement } from 'react';
import { MaturityBadge, type MaturityLevel } from '../atoms/MaturityBadge';

/**
 * AgentPicker — checkbox-list of agents grouped by domain (Issue #1028 /
 * Epic #1039).
 *
 * v1 ships as a server-rendered checklist with per-agent cost band; the
 * actual selection state and live cost roll-up land with the
 * client-side configure flow (#1029).
 */

export type AgentPickerAgent = {
  slug: string;
  name: string;
  oneLine: string;
  costLower: string;
  costUpper: string;
  maturity: MaturityLevel;
};

export type AgentPickerDomain = {
  key: string;
  label: string;
  agents: AgentPickerAgent[];
};

export type AgentPickerProps = {
  headline: string;
  description?: string;
  domains: AgentPickerDomain[];
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

const DOMAIN_HEADER_STYLE = {
  fontSize: '1.0625rem',
  fontWeight: 700,
  color: 'var(--sys-text, var(--hp-text))',
  marginTop: '1.25rem',
};

const AGENT_ROW_STYLE = {
  display: 'grid',
  gridTemplateColumns: 'auto 1fr auto auto',
  gap: '0.75rem',
  alignItems: 'center',
  padding: '0.625rem 0',
  borderBottom: '1px solid var(--sys-border, var(--hp-border))',
};

const AGENT_NAME_STYLE = {
  fontWeight: 600,
  color: 'var(--sys-text, var(--hp-text))',
};

const AGENT_DESC_STYLE = {
  fontSize: '0.8125rem',
  color: 'var(--sys-text-muted, var(--hp-text-muted))',
};

const COST_STYLE = {
  fontSize: '0.8125rem',
  color: 'var(--sys-text-muted, var(--hp-text-muted))',
  whiteSpace: 'nowrap' as const,
};

export function AgentPicker({
  headline,
  description,
  domains,
  testId,
}: AgentPickerProps): ReactElement {
  return (
    <section data-testid={testId} data-agent-picker style={SECTION_STYLE}>
      <header>
        <h2 style={HEADLINE_STYLE}>{headline}</h2>
      </header>
      {description ? <p style={DESCRIPTION_STYLE}>{description}</p> : null}
      <form data-agent-picker-form>
        {domains.map((d) => (
          <fieldset
            key={d.key}
            data-domain-key={d.key}
            style={{ border: 0, padding: 0, margin: 0 }}
          >
            <legend style={DOMAIN_HEADER_STYLE}>{d.label}</legend>
            {d.agents.map((a) => (
              <label
                key={a.slug}
                data-agent-slug={a.slug}
                style={AGENT_ROW_STYLE}
              >
                <input
                  type="checkbox"
                  name="agents"
                  value={a.slug}
                  defaultChecked
                  aria-describedby={`${a.slug}-desc`}
                />
                <span>
                  <span style={AGENT_NAME_STYLE}>{a.name}</span>
                  <span id={`${a.slug}-desc`} style={{ display: 'block', ...AGENT_DESC_STYLE }}>
                    {a.oneLine}
                  </span>
                </span>
                <span style={COST_STYLE}>
                  ${a.costLower}–${a.costUpper} / 1k
                </span>
                <MaturityBadge level={a.maturity} />
              </label>
            ))}
          </fieldset>
        ))}
      </form>
    </section>
  );
}
