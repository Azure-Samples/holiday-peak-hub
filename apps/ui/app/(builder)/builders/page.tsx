import type { Metadata } from 'next';

import { CallToAction } from '@/components/molecules/CallToAction';
import { CodeBlockCluster } from '@/components/molecules/CodeBlockCluster';
import { DocsCardCluster } from '@/components/molecules/DocsCardCluster';
import { FeatureMatrix } from '@/components/molecules/FeatureMatrix';
import { Hero } from '@/components/molecules/Hero';
import { ValuePropGrid } from '@/components/molecules/ValuePropGrid';
import { buildMetadata } from '@/lib/seo';

export const metadata: Metadata = buildMetadata({
  section: 'builder',
  description:
    'Architecture, ADRs, MCP-only A2A, three-tier memory, AGC blue-green rollback, and the reference implementation for engineers building on the platform.',
  path: '/builders',
});

const CALL_AGENT_SNIPPET = `# Call an agent over MCP from another agent.
from holiday_peak_lib.mcp import MCPClient

mcp = MCPClient(endpoint="https://mcp.example/eta-computation")
eta = await mcp.call("compute_eta", order_id="O-1234")
print(eta.window_lower, eta.window_upper, eta.confidence)`;

const REGISTER_TOOL_SNIPPET = `# Register an MCP tool on a FastAPI agent service.
from holiday_peak_lib.mcp import FastAPIMCPServer

mcp = FastAPIMCPServer(app)

@mcp.tool("get_profile_context")
async def get_profile_context(customer_id: str) -> dict:
    return await profile_aggregation.fetch(customer_id)`;

const READ_MEMORY_SNIPPET = `# Three-tier memory: hot (Redis) → warm (Cosmos) → cold (Blob).
from holiday_peak_lib.memory import ThreeTierMemory

memory = ThreeTierMemory(settings)
ctx = await memory.read(customer_id, scope="cart")
# ctx auto-promoted from warm/cold to hot on read.`;

/**
 * `/builders` — cool-cognitive-model audience page (ADR-034 §1 / ADR-035 §54 / Issue #1059).
 *
 * Composition order (locked at v1, see `docs/ui/ux-patterns.md`):
 *
 *   1. `<Hero kind="audience-page">` — capability-led headline, dual CTA.
 *   2. `<ValuePropGrid cardinality="three-to-five">` — 5 technical capability cards, all qualitative.
 *   3. `<CodeBlockCluster>` — 3 representative snippets, collapsed by default.
 *   4. `<FeatureMatrix>` — capabilities shipped vs. roadmap, every row carries `<MaturityBadge>`.
 *   5. `<DocsCardCluster>` — direct links into mkdocs sections.
 *   6. `<CallToAction tone="audience-pair">` — switch lane / try deploy.
 */
export default function BuildersIndexPage() {
  return (
    <>
      <Hero
        kind="audience-page"
        headline="The architecture, the contracts, the receipts."
        sub="26 agents across 7 bounded contexts on Azure Foundry. MCP-only agent-to-agent. Three-tier memory. AGC 90-second blue-green rollback."
        primaryCta={{ label: 'See architecture →', href: '/builders/architecture' }}
        secondaryCta={{ label: 'Browse agent catalog →', href: '/builders/agents' }}
        testId="builders-hero"
      />
      <ValuePropGrid
        testId="builders-value-props"
        cardinality="three-to-five"
        items={[
          {
            kind: 'qualitative',
            headline: 'MCP-only agent-to-agent.',
            body: 'Agents communicate exclusively over the Model Context Protocol. No bespoke RPC. No shared database. Every cross-agent call is a typed tool invocation with a discoverable contract.',
            maturity: 'design-partner',
          },
          {
            kind: 'qualitative',
            headline: 'Three-tier memory: hot / warm / cold.',
            body: 'Hot in Redis (sub-millisecond), warm in Cosmos DB (durable, queryable), cold in Blob (cheap, replayable). Promotion and demotion are first-class.',
            maturity: 'design-partner',
          },
          {
            kind: 'qualitative',
            headline: 'AGC blue-green with 90-second rollback.',
            body: 'Application Gateway for Containers routes weighted traffic between blue and green slots. An unhealthy slot rolls back in 90 seconds without operator intervention.',
            maturity: 'preview',
          },
          {
            kind: 'qualitative',
            headline: 'Foundry SLM-first routing.',
            body: 'Every agent ships an SLM and an LLM target. Requests route to the SLM first; complexity gates upgrade to the LLM. Cost and latency follow the routing decision.',
            maturity: 'design-partner',
          },
          {
            kind: 'qualitative',
            headline: 'Eventing via Event Hubs.',
            body: 'Async work flows over Event Hubs. The CRUD service publishes domain events; agents subscribe and process out-of-band. No tight coupling, no synchronous fan-out.',
            maturity: 'design-partner',
          },
        ]}
      />
      <CodeBlockCluster
        testId="builders-code-blocks"
        headline="Three things you'll do on day one"
        description="Snippets are collapsed by default and link to the canonical docs page that owns the full example. We do not duplicate the docs on the marketing route."
        blocks={[
          {
            label: 'Call an agent over MCP',
            language: 'python',
            code: CALL_AGENT_SNIPPET,
            canonical: { label: 'lib/holiday_peak_lib/mcp/README.md', href: '/docs/lib/mcp' },
          },
          {
            label: 'Register an MCP tool',
            language: 'python',
            code: REGISTER_TOOL_SNIPPET,
            canonical: { label: 'lib/holiday_peak_lib/mcp/README.md', href: '/docs/lib/mcp' },
          },
          {
            label: 'Read three-tier memory',
            language: 'python',
            code: READ_MEMORY_SNIPPET,
            canonical: { label: 'lib/holiday_peak_lib/memory/README.md', href: '/docs/lib/memory' },
          },
        ]}
      />
      <FeatureMatrix
        testId="builders-feature-matrix"
        headline="Capabilities shipped vs. roadmap"
        description="Every row carries a maturity badge. We don't list roadmap items as available."
        rows={[
          {
            capability: 'MCP-only agent-to-agent',
            summary: 'All cross-agent calls go through MCP tools with discoverable schemas.',
            availability: 'available',
            maturity: 'design-partner',
          },
          {
            capability: 'Three-tier memory',
            summary: 'Hot (Redis), warm (Cosmos), cold (Blob), with auto-promotion on read.',
            availability: 'available',
            maturity: 'design-partner',
          },
          {
            capability: 'SLM-first routing',
            summary: 'Foundry agent config exposes fast + rich targets; complexity gates pick.',
            availability: 'available',
            maturity: 'design-partner',
          },
          {
            capability: 'AGC blue-green rollback',
            summary: 'Application Gateway for Containers, weighted canary, 90-second rollback SLO.',
            availability: 'preview',
            maturity: 'preview',
          },
          {
            capability: 'Continuous evaluation',
            summary: 'Per-agent eval baselines + drift checks on PR.',
            availability: 'preview',
            maturity: 'preview',
          },
          {
            capability: 'Multi-region active/active',
            summary: 'Two regions writing simultaneously with conflict resolution.',
            availability: 'roadmap',
            maturity: 'internal',
          },
        ]}
      />
      <DocsCardCluster
        testId="builders-docs"
        headline="Read the docs"
        cards={[
          {
            kicker: 'Architecture',
            title: 'System overview & ADRs',
            description: 'How the agents, CRUD service, frontend, and Azure stack fit together.',
            href: '/docs/architecture',
          },
          {
            kicker: 'Governance',
            title: 'Branching, releases, quality gates',
            description: 'How code reaches main, how main reaches prod, and how prod rolls back.',
            href: '/docs/governance',
          },
          {
            kicker: 'Ops',
            title: 'Runbooks & SLOs',
            description: 'On-call playbooks, SLO catalog, incident response patterns.',
            href: '/docs/ops',
          },
        ]}
      />
      <CallToAction
        tone="audience-pair"
        headline="Want to try it on your tenant?"
        primary={{ label: 'Deploy to Azure', href: '/deploy' }}
        secondary={{ label: 'Talk to the team', href: '/contact' }}
        testId="builders-cta-pair"
      />
    </>
  );
}
