import type { ReactElement } from 'react';
import Link from 'next/link';

import type { AgentCatalogDomain } from '@/lib/agents/catalog';
import { ConfidenceInterval } from '../atoms/ConfidenceInterval';
import { MaturityBadge } from '../atoms/MaturityBadge';

/**
 * AgentCatalog — the 26-agent catalog (Issue #1041 / Epic #1046).
 *
 * Renders agents grouped by bounded context. Each agent row carries:
 *   - Name + maturity badge (compile-time required)
 *   - One-line description
 *   - Cost-per-1k-requests as a `ConfidenceInterval` (lower/upper/methodology)
 *
 * Honesty enforcement:
 *   - `maturity` is required per agent at the type level.
 *   - Cost lower/upper are required strings (not numbers) so consumers
 *     match the `ConfidenceInterval` contract.
 */

export type AgentCatalogProps = {
  domains: readonly AgentCatalogDomain[];
  /** Population descriptor passed to every `ConfidenceInterval`. */
  costPopulation: string;
  /** Methodology descriptor passed to every `ConfidenceInterval`. */
  costMethodology: string;
  /** Sample size passed to every `ConfidenceInterval`. */
  costSampleSize: number;
  /** Optional detail-link builder used by the builder-side catalog. */
  agentHref?: (slug: string) => string;
  testId?: string;
};

const DOMAIN_SECTION_STYLE = {
  display: 'flex',
  flexDirection: 'column' as const,
  gap: '1rem',
  padding: 'clamp(1.5rem, 4vw, 2.5rem) 1.5rem',
  maxWidth: '64rem',
  margin: '0 auto',
  width: '100%',
};

const DOMAIN_LABEL_STYLE = {
  fontSize: 'clamp(1.25rem, 2.4vw, 1.75rem)',
  fontWeight: 700,
  color: 'var(--sys-text, var(--hp-text))',
};

const DOMAIN_BLURB_STYLE = {
  fontSize: '0.9375rem',
  color: 'var(--sys-text-muted, var(--hp-text-muted))',
};

const GRID_STYLE = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
  gap: '1rem',
  listStyle: 'none' as const,
  padding: 0,
  margin: 0,
};

const CARD_STYLE = {
  display: 'flex',
  flexDirection: 'column' as const,
  gap: '0.5rem',
  padding: '1rem 1.125rem',
  borderRadius: 'var(--radius-md, 0.75rem)',
  border: '1px solid var(--sys-border, var(--hp-border))',
  background: 'var(--sys-surface-base, var(--hp-bg))',
};

const CARD_HEADER_STYLE = {
  display: 'flex',
  alignItems: 'center',
  gap: '0.5rem',
  flexWrap: 'wrap' as const,
};

const CARD_TITLE_STYLE = {
  fontSize: '1.0625rem',
  fontWeight: 700,
  margin: 0,
  color: 'var(--sys-text, var(--hp-text))',
};

const CARD_BODY_STYLE = {
  fontSize: '0.9375rem',
  lineHeight: 1.5,
  margin: 0,
  color: 'var(--sys-text-muted, var(--hp-text-muted))',
};

const CARD_LINK_STYLE = {
  alignSelf: 'flex-start' as const,
  color: 'var(--sys-link, var(--hp-link))',
  fontSize: '0.875rem',
  fontWeight: 600,
  textDecoration: 'underline',
  textUnderlineOffset: '0.18em',
};

export function AgentCatalog({
  domains,
  costPopulation,
  costMethodology,
  costSampleSize,
  agentHref,
  testId,
}: AgentCatalogProps): ReactElement {
  return (
    <div data-testid={testId} data-agent-catalog>
      {domains.map((domain) => (
        <section
          key={domain.key}
          data-testid={`retailer-agents-domain-${domain.key}`}
          data-domain={domain.key}
          style={DOMAIN_SECTION_STYLE}
        >
          <header
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '0.25rem',
            }}
          >
            <h2 style={DOMAIN_LABEL_STYLE}>{domain.label}</h2>
            <p style={DOMAIN_BLURB_STYLE}>{domain.blurb}</p>
          </header>
          <ul style={GRID_STYLE}>
            {domain.agents.map((agent) => {
              const href = agentHref?.(agent.slug);
              return (
                <li key={agent.slug} data-agent-slug={agent.slug} style={CARD_STYLE}>
                  <header style={CARD_HEADER_STYLE}>
                    <h3 style={CARD_TITLE_STYLE}>{agent.name}</h3>
                    <MaturityBadge level={agent.maturity} />
                  </header>
                  <p style={CARD_BODY_STYLE}>{agent.oneLine}</p>
                  <ConfidenceInterval
                    lower={agent.costLower}
                    upper={agent.costUpper}
                    unit="USD per 1,000 requests"
                    sampleSize={costSampleSize}
                    population={costPopulation}
                    methodology={costMethodology}
                  />
                  {href ? (
                    <Link href={href} style={CARD_LINK_STYLE}>
                      Open builder detail
                    </Link>
                  ) : null}
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
}
