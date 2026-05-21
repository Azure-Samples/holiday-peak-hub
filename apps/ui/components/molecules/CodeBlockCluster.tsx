import type { ReactElement } from 'react';
import { CodeBlock, type CodeBlockProps } from './CodeBlock';

/**
 * CodeBlockCluster — labelled stack of collapsed `CodeBlock`s (ADR-035 §54 / Issue #1059).
 *
 * Used on `/builders` to surface 3 representative snippets (call-an-agent,
 * register-MCP-tool, read-three-tier-memory). Each snippet stays collapsed
 * by default; the cluster owns the heading and stack layout so the
 * audience-route page-level code stays free of inline layout.
 */
export type CodeBlockClusterProps = {
  headline: string;
  description?: string;
  blocks: ReadonlyArray<CodeBlockProps>;
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

export function CodeBlockCluster({
  headline,
  description,
  blocks,
  testId,
}: CodeBlockClusterProps): ReactElement {
  const headingId = `${testId ?? 'code-block-cluster'}-heading`;
  return (
    <section
      data-testid={testId}
      data-code-block-cluster=""
      aria-labelledby={headingId}
      style={SECTION_STYLE}
    >
      <h2 id={headingId} style={HEADLINE_STYLE}>
        {headline}
      </h2>
      {description ? <p style={DESCRIPTION_STYLE}>{description}</p> : null}
      <div style={STACK_STYLE}>
        {blocks.map((block) => (
          <CodeBlock key={block.label} {...block} />
        ))}
      </div>
    </section>
  );
}
