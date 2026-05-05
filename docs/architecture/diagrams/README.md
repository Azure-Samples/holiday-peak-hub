# Architecture Diagrams

> Last Updated: 2026-04-30

Canonical diagram index for Holiday Peak Hub. Diagrams follow the C4 model hierarchy: **Context → Container → Component → Code**.

## Visual Hierarchy

| Level | Scope | Artifact Type |
|-------|-------|---------------|
| **Context** | System boundary, external actors (shoppers, operators, 3rd-party APIs) | `.drawio` |
| **Container** | Azure runtime (AKS, APIM, AGC, SWA, Event Hubs, AI Search, Foundry) | `.drawio` |
| **Component** | Service internals (agents, adapters, MCP tools, memory tiers) | `.drawio` |
| **Code** | Runtime interaction flows (invocation, memory I/O, deployment) | Mermaid sequence `.md` |

## Color Palette & Style Guide

All Mermaid diagrams in this repository use the following theme to ensure visual consistency:

```
%%{init: {'theme':'base', 'themeVariables': {
  'primaryColor':'#FFB3BA',
  'primaryTextColor':'#000',
  'primaryBorderColor':'#FF8B94',
  'lineColor':'#BAE1FF',
  'secondaryColor':'#BAE1FF',
  'tertiaryColor':'#FFFFFF'
}}}%%
```

| Token | Hex | Usage |
|-------|-----|-------|
| `primaryColor` | `#FFB3BA` | Actor/participant boxes |
| `primaryTextColor` | `#000` | All label text |
| `primaryBorderColor` | `#FF8B94` | Box borders |
| `lineColor` | `#BAE1FF` | Arrows and message lines |
| `secondaryColor` | `#BAE1FF` | Alternate lanes and highlights |
| `tertiaryColor` | `#FFFFFF` | Background/notes |

## C4 Draw.io Diagrams

| Diagram | Viewpoint | Purpose |
|---|---|---|
| `c4-system-context.drawio` | C4 Context | External actors, channels, and system boundary |
| `c4-container-azure-runtime.drawio` | C4 Container | Azure runtime composition across edge, AKS, and platform services |
| `c4-component-summary.drawio` | C4 Component | Service grouping and high-level internal composition |
| `c4-component-detailed.drawio` | C4 Component | Detailed component/service relationships |

> **TODO (.drawio review)**: Verify that `c4-container-azure-runtime.drawio` reflects the current topology: 26 agent services in `agents` namespace, 1 CRUD service in `crud` namespace, APIM + AGC edge, Flux CD GitOps deployment model, and 8 Event Hub topics. Verify `c4-system-context.drawio` shows Azure AI Foundry (GPT-5-nano SLM + GPT-4o LLM) and MAF >=1.0.1 GA as the agent runtime. Update `c4-component-detailed.drawio` to include MCP tool exposition on all 26 agents and FoundryAgentInvoker as the invocation wrapper.

## Sequence Diagrams (Mermaid)

| Diagram | Domain | Caption |
|---|---|---|
| [sequence-catalog-search.md](./sequence-catalog-search.md) | E-commerce | End-to-end product search: SLM-first routing, embedding generation, AI Search hybrid query, parallel inventory checks, and personalization — constrained to a strict 4s pipeline. Reference when working on catalog-search agent or AI Search integration. |
| [sequence-inventory-health.md](./sequence-inventory-health.md) | Inventory | Scheduled and on-demand health validation: rule-based checks (negative stock, stale data, reservation integrity), Z-score anomaly detection, alert generation, and SAGA remediation. Reference when modifying health-check rules or alert thresholds. |
| [sequence-returns-support.md](./sequence-returns-support.md) | Logistics/CRM | Full returns lifecycle: eligibility validation, LLM-guided instructions, label generation, SAGA choreography (WMS → Carrier → Refund), and VIP fast-track. Reference when changing returns policies or carrier integrations. |
| [sequence-foundry-agent-invocation.md](./sequence-foundry-agent-invocation.md) | Agent Runtime | FoundryAgentInvoker → MAF FoundryAgent tool-forwarding flow with SLM-first routing, parallel memory I/O, and MCP tool execution. Reference when modifying agent invocation, model routing, or tool registration. |
| [sequence-memory-parallel-io.md](./sequence-memory-parallel-io.md) | Memory | Three-tier parallel read/write (Redis hot → Cosmos DB warm → Blob cold) via `asyncio.gather`. Reference when modifying memory adapters, TTL policies, or tier promotion/demotion logic. |
| [sequence-flux-gitops-deployment.md](./sequence-flux-gitops-deployment.md) | Infrastructure | Flux CD GitOps reconciliation: Phase 2 HelmRelease (pilot) and Phase 1 rendered YAML (legacy), namespace-isolated deployment to `agents` and `crud` namespaces, drift detection, and self-healing. Reference when changing deployment strategy or namespace policies. |

## Usage Guidelines

- Keep C4 diagrams in `.drawio` format as the architecture source of truth.
- Keep runtime interaction flows in Mermaid sequence files.
- Update this index whenever diagram files are added, removed, or renamed.
- Keep diagram naming stable to avoid broken links in architecture docs.
- All new Mermaid diagrams must include the standard theme init block documented above.
- Cross-reference diagrams using relative paths (e.g., `./sequence-catalog-search.md`).

## Related Docs

- [Architecture Overview](../architecture.md)
- [ADR Index](../ADRs.md)
- [Components](../components.md)
- [Playbooks](../playbooks/README.md)
