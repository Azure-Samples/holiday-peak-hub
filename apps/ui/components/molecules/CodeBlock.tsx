import type { ReactElement } from 'react';

/**
 * CodeBlock — code snippet card (ADR-035 §54 / Issue #1059).
 *
 * Used on `/builders` to surface 3 representative snippets (call-an-agent,
 * register-MCP-tool, read-three-tier-memory). Per the issue spec the cluster
 * is **collapsed by default with a "Show snippet" affordance**; expansion is
 * lazy and links out to the canonical docs page that owns the snippet (no
 * duplication on the marketing route).
 *
 * This composite uses native `<details>` / `<summary>` for the
 * collapse / expand interaction so the whole block is server-renderable
 * and works without JS. No client component is needed.
 */
export type CodeBlockProps = {
  /** Snippet label (e.g., "Call an agent over MCP"). */
  label: string;
  /** Programming language hint (e.g., "python"). */
  language: string;
  /** Code body (kept short — under ~10 lines on the marketing route). */
  code: string;
  /** Canonical docs page that owns the full example. */
  canonical: { label: string; href: string };
  testId?: string;
};

const CARD_STYLE = {
  display: 'flex',
  flexDirection: 'column' as const,
  gap: '0.5rem',
  padding: '1rem 1.25rem',
  borderRadius: 'var(--radius-lg, 1rem)',
  border: '1px solid var(--sys-border, var(--hp-border))',
  background: 'var(--sys-surface, var(--hp-surface))',
};

const SUMMARY_STYLE = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: '0.75rem',
  cursor: 'pointer',
  fontWeight: 600,
  color: 'var(--sys-text, var(--hp-text))',
};

const LANGUAGE_STYLE = {
  fontSize: '0.75rem',
  textTransform: 'uppercase' as const,
  letterSpacing: '0.08em',
  color: 'var(--sys-text-muted, var(--hp-text-muted))',
};

const CODE_STYLE = {
  background: 'var(--sys-surface-muted, var(--hp-surface-muted, #0b1220))',
  color: 'var(--sys-text-on-muted, var(--hp-text-on-muted, #e2e8f0))',
  padding: '1rem',
  borderRadius: 'var(--radius-md, 0.75rem)',
  fontFamily: 'var(--font-mono, ui-monospace, SFMono-Regular, Menlo, Consolas, monospace)',
  fontSize: '0.8125rem',
  lineHeight: 1.5,
  overflowX: 'auto' as const,
};

const CANONICAL_STYLE = {
  fontSize: '0.8125rem',
  color: 'var(--sys-text-muted, var(--hp-text-muted))',
};

export function CodeBlock({ label, language, code, canonical, testId }: CodeBlockProps): ReactElement {
  return (
    <details data-testid={testId} data-code-block="" style={CARD_STYLE}>
      <summary style={SUMMARY_STYLE}>
        <span>{label}</span>
        <span style={LANGUAGE_STYLE}>{language}</span>
      </summary>
      <pre style={CODE_STYLE}>
        <code>{code}</code>
      </pre>
      <p style={CANONICAL_STYLE}>
        Canonical:{' '}
        <a href={canonical.href} style={{ color: 'inherit', textDecoration: 'underline' }}>
          {canonical.label}
        </a>
      </p>
    </details>
  );
}
