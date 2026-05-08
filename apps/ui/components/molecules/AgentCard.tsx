import type { ReactElement } from 'react';
import Link from 'next/link';

/**
 * AgentCard — agent surface card (ADR-035 §54 / Issue #1059).
 *
 * Used as a cluster of 6 cards on `/retailers` to surface representative
 * retail agents with a one-line description and a deep link into the
 * builder lane (`/builders/agents/<slug>`).
 *
 * Honesty enforcement: every agent card carries a `domain` (e.g.,
 * "Inventory", "Catalog", "Logistics") so a procurement-minded reader can
 * map the agent to a retail bounded context without guessing.
 */
export type AgentCardProps = {
  name: string;
  /** One-sentence summary. */
  description: string;
  /** Bounded-context label (e.g., "Inventory"). */
  domain: string;
  /** Deep link into the builder lane agent doc. */
  href: string;
  testId?: string;
};

const CARD_STYLE = {
  display: 'flex',
  flexDirection: 'column' as const,
  gap: '0.5rem',
  padding: '1.25rem',
  borderRadius: 'var(--radius-lg, 1rem)',
  border: '1px solid var(--sys-border, var(--hp-border))',
  background: 'var(--sys-surface, var(--hp-surface))',
  textDecoration: 'none' as const,
  color: 'var(--sys-text, var(--hp-text))',
};

const DOMAIN_STYLE = {
  fontSize: '0.75rem',
  fontWeight: 600,
  textTransform: 'uppercase' as const,
  letterSpacing: '0.08em',
  color: 'var(--sys-text-muted, var(--hp-text-muted))',
};

const NAME_STYLE = {
  fontSize: '1.0625rem',
  fontWeight: 600,
  lineHeight: 1.3,
};

const DESCRIPTION_STYLE = {
  fontSize: '0.9375rem',
  lineHeight: 1.5,
  color: 'var(--sys-text-muted, var(--hp-text-muted))',
};

export function AgentCard({ name, description, domain, href, testId }: AgentCardProps): ReactElement {
  return (
    <Link href={href} data-testid={testId} data-agent-card="" style={CARD_STYLE}>
      <span style={DOMAIN_STYLE}>{domain}</span>
      <span style={NAME_STYLE}>{name}</span>
      <span style={DESCRIPTION_STYLE}>{description}</span>
    </Link>
  );
}
