import type { Metadata } from 'next';
import { notFound } from 'next/navigation';

import { CallToAction } from '@/components/molecules/CallToAction';
import { CodeBlockCluster } from '@/components/molecules/CodeBlockCluster';
import { DocsCardCluster } from '@/components/molecules/DocsCardCluster';
import { Hero } from '@/components/molecules/Hero';
import { RegistryTable, type RegistryTableRow } from '@/components/molecules/RegistryTable';
import { getAgentCatalogAgent } from '@/lib/agents/catalog';
import {
  AGENT_PROFILE_SLUGS,
  getAgentProfile,
  type AgentProfile,
  type AgentProfileSlug,
} from '@/lib/agents/profiles';
import { buildMetadata } from '@/lib/seo';

type BuilderAgentPageProps = {
  params: Promise<{ slug: string }>;
};

export const dynamicParams = false;

export function generateStaticParams(): Array<{ slug: AgentProfileSlug }> {
  return AGENT_PROFILE_SLUGS.map((slug) => ({ slug }));
}

export async function generateMetadata({ params }: BuilderAgentPageProps): Promise<Metadata> {
  const { slug } = await params;
  const profile = getAgentProfile(slug);

  if (!profile) {
    notFound();
  }

  return buildMetadata({
    section: 'builder',
    title: profile.displayName,
    description: `${profile.oneLiner} Runtime contract, KPIs, schemas, and collaborators.`,
    path: `/builders/agents/${profile.slug}`,
  });
}

function formatJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

function buildRuntimeRows(profile: AgentProfile): RegistryTableRow[] {
  const catalogAgent = getAgentCatalogAgent(profile.slug);

  return [
    {
      key: 'domain',
      cells: [
        { kind: 'text', value: 'Bounded context' },
        { kind: 'text', value: profile.domainLabel },
      ],
    },
    {
      key: 'mode',
      cells: [
        { kind: 'text', value: 'Primary mode' },
        { kind: 'badge', value: profile.primaryMode === 'sync' ? 'Synchronous' : 'Event-driven async' },
      ],
    },
    {
      key: 'maturity',
      cells: [
        { kind: 'text', value: 'Maturity' },
        { kind: 'maturity', level: catalogAgent?.maturity ?? 'internal' },
      ],
    },
    {
      key: 'trace-explorer',
      cells: [
        { kind: 'text', value: 'Trace entry point' },
        { kind: 'link', value: profile.traceExplorerHref, href: profile.traceExplorerHref },
      ],
    },
    {
      key: 'collaborators',
      cells: [
        { kind: 'text', value: 'Collaborators' },
        { kind: 'tags', values: profile.collaborates },
      ],
    },
  ];
}

function buildFitRows(profile: AgentProfile): RegistryTableRow[] {
  return [
    {
      key: 'problem',
      cells: [
        { kind: 'text', value: 'Retail problem' },
        { kind: 'text', value: profile.retailProblem },
      ],
    },
    {
      key: 'fit-for',
      cells: [
        { kind: 'text', value: 'Fit for' },
        { kind: 'tags', values: profile.fitFor },
      ],
    },
    {
      key: 'latency',
      cells: [
        { kind: 'text', value: 'Latency signal' },
        { kind: 'text', value: profile.productivityGain.latency },
      ],
    },
    {
      key: 'quality',
      cells: [
        { kind: 'text', value: 'Quality signal' },
        { kind: 'text', value: profile.productivityGain.quality },
      ],
    },
    {
      key: 'cost',
      cells: [
        { kind: 'text', value: 'Cost signal' },
        { kind: 'text', value: profile.productivityGain.cost },
      ],
    },
    {
      key: 'revenue-impact',
      cells: [
        { kind: 'text', value: 'Revenue impact' },
        { kind: 'text', value: profile.productivityGain.revenueImpact ?? 'Not claimed for this agent.' },
      ],
    },
  ];
}

function buildKpiRows(profile: AgentProfile): RegistryTableRow[] {
  return profile.kpisToTrack.map((kpi) => ({
    key: kpi.id,
    cells: [
      { kind: 'text', value: kpi.label },
      { kind: 'badge', value: kpi.target },
      { kind: 'text', value: kpi.why },
      { kind: 'text', value: kpi.source },
    ],
  }));
}

export default async function BuilderAgentDetailPage({ params }: BuilderAgentPageProps) {
  const { slug } = await params;
  const profile = getAgentProfile(slug);

  if (!profile) {
    notFound();
  }

  return (
    <>
      <Hero
        kind="audience-page"
        headline={profile.displayName}
        sub={profile.oneLiner}
        primaryCta={{ label: 'Open trace entry point', href: profile.traceExplorerHref }}
        secondaryCta={{ label: 'Back to agent catalog', href: '/builders/agents' }}
        testId="builder-agent-detail-hero"
      />
      <RegistryTable
        testId="builder-agent-runtime"
        headline="Runtime contract"
        description="The builder-facing ownership summary for mode, maturity, traceability, and agent-to-agent collaboration."
        columns={['Signal', 'Value']}
        rows={buildRuntimeRows(profile)}
      />
      <RegistryTable
        testId="builder-agent-fit"
        headline="Operational fit"
        description="The retail problem and observed operating signals that explain why this agent exists in the product."
        columns={['Facet', 'Detail']}
        rows={buildFitRows(profile)}
      />
      <RegistryTable
        testId="builder-agent-kpis"
        headline="KPIs to track"
        description="Each KPI is tied to a source so operators can validate whether the agent is improving a real workflow."
        columns={['KPI', 'Target', 'Why it matters', 'Source']}
        rows={buildKpiRows(profile)}
      />
      <CodeBlockCluster
        testId="builder-agent-contract-json"
        headline="Interface contract"
        description="Schemas and a curated sample payload from the shared profile data. The full service contract remains owned by the agent service."
        blocks={[
          {
            label: 'Input schema',
            language: 'json',
            code: formatJson(profile.inputSchema),
            canonical: { label: 'Agent profile contract', href: '/docs/agentic-microservices-reference' },
          },
          {
            label: 'Sample input',
            language: 'json',
            code: formatJson(profile.sampleInput),
            canonical: { label: 'Agent profile contract', href: '/docs/agentic-microservices-reference' },
          },
          {
            label: 'Output schema',
            language: 'json',
            code: formatJson(profile.outputSchema),
            canonical: { label: 'Agent profile contract', href: '/docs/agentic-microservices-reference' },
          },
        ]}
      />
      <DocsCardCluster
        testId="builder-agent-next-steps"
        headline="Next builder steps"
        cards={[
          {
            kicker: 'Telemetry',
            title: 'Inspect live seams',
            description: 'Open the builder telemetry surface to inspect spans, canaries, and runtime health.',
            href: '/builders/telemetry',
          },
          {
            kicker: 'Architecture',
            title: 'Place this agent in the system',
            description: 'Review diagrams and ADRs that pin the agent, CRUD, MCP, and eventing boundaries.',
            href: '/builders/architecture',
          },
          {
            kicker: 'Patterns',
            title: 'Review implementation patterns',
            description: 'Trace MCP-only A2A, three-tier memory, and routing decisions back to their source docs.',
            href: '/builders/patterns',
          },
        ]}
      />
      <CallToAction
        tone="audience-pair"
        headline="Need another agent contract?"
        primary={{ label: 'Browse agent catalog', href: '/builders/agents' }}
        secondary={{ label: 'Switch to retailer view', href: '/retailers/agents' }}
        testId="builder-agent-detail-cta-pair"
      />
    </>
  );
}