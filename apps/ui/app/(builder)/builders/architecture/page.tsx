import type { Metadata } from 'next';
import fs from 'node:fs';
import path from 'node:path';

import { CallToAction } from '@/components/molecules/CallToAction';
import { Hero } from '@/components/molecules/Hero';
import { RegistryTable, type RegistryTableRow } from '@/components/molecules/RegistryTable';
import { buildMetadata } from '@/lib/seo';

export const metadata: Metadata = buildMetadata({
  section: 'builder',
  description:
    'Architecture diagrams auto-built from docs/architecture. Mermaid sources downloadable; deep-link to Mermaid Live Editor for in-browser viewing. No proprietary diagram tools required.',
  path: '/builders/architecture',
});

type DiagramEntry = {
  slug: string;
  doc_title: string;
  doc_filename: string;
  block_index: number;
  mermaid_path: string;
  source_doc: string;
  mermaid_live_url: string;
};

type DiagramRegistry = {
  schema_version: number;
  generated_at: string;
  source_dir: string;
  stale: boolean;
  parse_errors: string[];
  diagrams: DiagramEntry[];
};

const REGISTRY_PATH = path.join(
  process.cwd(),
  'public',
  'architecture',
  'registry.json',
);

function loadRegistry(): DiagramRegistry {
  try {
    const raw = fs.readFileSync(REGISTRY_PATH, 'utf-8');
    return JSON.parse(raw) as DiagramRegistry;
  } catch {
    return {
      schema_version: 1,
      generated_at: '',
      source_dir: 'docs/architecture',
      stale: true,
      parse_errors: [
        'registry not yet built — run scripts/ops/build_architecture_registry.py',
      ],
      diagrams: [],
    };
  }
}

function diagramToRow(entry: DiagramEntry): RegistryTableRow {
  const githubHref = `https://github.com/Azure-Samples/holiday-peak-hub/blob/main/${entry.source_doc}`;
  return {
    key: entry.slug,
    cells: [
      { kind: 'text', value: entry.doc_title },
      { kind: 'text', value: `Block ${entry.block_index}` },
      { kind: 'link', value: 'View source', href: githubHref },
      { kind: 'link', value: 'Download .mmd', href: entry.mermaid_path },
      { kind: 'link', value: 'Open in Mermaid Live', href: entry.mermaid_live_url },
    ],
  };
}

/**
 * `/builders/architecture` — auto-built architecture-diagram catalog
 * (Issue #1047 / Epic #1053).
 *
 * Each row links to the GitHub source document, the raw .mmd file (so the
 * builder can paste it into their own tool), and a deterministic Mermaid
 * Live Editor deep link (so the browser-side experience is "click and see"
 * without bundling mermaid.js).
 *
 * No client-side renderer. No proprietary diagram format. The contract is
 * "the source is markdown; we never lose the source."
 */
export default function BuilderArchitecturePage() {
  const registry = loadRegistry();
  const rows = registry.diagrams.map(diagramToRow);

  return (
    <>
      <Hero
        kind="audience-page"
        headline="The architecture, on the page."
        sub={`${registry.diagrams.length} diagrams auto-extracted from docs/architecture. Every diagram is downloadable as Mermaid source and deep-linkable into the Mermaid Live Editor.`}
        primaryCta={{ label: 'See ADR registry', href: '/builders/adrs' }}
        secondaryCta={{ label: 'Browse pattern catalog', href: '/builders/patterns' }}
        testId="builder-architecture-hero"
      />
      <RegistryTable
        testId="builder-architecture-table"
        headline="Architecture diagrams"
        description="Mermaid sources extracted from docs/architecture markdown by scripts/ops/build_architecture_registry.py. We do not bundle a client-side mermaid renderer; the deep link opens the source in the public Mermaid Live Editor."
        columns={['Document', 'Block', 'Source', 'Mermaid', 'Render']}
        rows={rows}
        banner={
          registry.stale
            ? {
                tone: 'warn',
                text: `Registry stale — ${registry.parse_errors.length} parse warning(s).`,
              }
            : registry.generated_at
              ? { tone: 'info', text: `Last generated ${registry.generated_at}.` }
              : undefined
        }
        emptyState={{
          headline: 'No diagrams found.',
          body: 'Add Mermaid blocks to docs/architecture/*.md and re-run the build.',
        }}
      />
      <CallToAction
        tone="audience-pair"
        headline="Want the decisions behind the diagrams?"
        primary={{ label: 'See ADR registry', href: '/builders/adrs' }}
        secondary={{ label: 'See live telemetry workbook', href: '/builders/telemetry' }}
        testId="builder-architecture-cta-pair"
      />
    </>
  );
}
