# ADR-027: API Center Governance and APIM MCP Server Strategy

**Status**: Accepted
**Date**: 2026-04-11
**Deciders**: Architecture Team, Ricardo Cataldi
**Tags**: api-governance, api-center, apim, mcp, api-discovery
**References**: [ADR-021](adr-021-apim-agc-edge.md), [ADR-024](adr-024-agent-communication-policy.md), [ADR-026](adr-026-namespace-isolation-strategy.md)

## Context

The holiday-peak-hub platform exposes 29 APIs through Azure API Management (APIM): 26 agent APIs, 1 CRUD API, 1 Azure OpenAI gateway, and 1 echo-api. Each agent API already registers a `POST /mcp/{tool}` operation for MCP tool invocation through APIM (managed by `sync-apim-agents.ps1`).

Two governance gaps remain after namespace isolation (ADR-026):

1. **API Discovery and Catalog** — No centralized API registry exists. Consumers (frontend, agents, external) must know exact APIM paths. There is no metadata layer for domain classification, lifecycle status, or compliance tracking.

2. **APIM MCP Server Registration** — APIM portal shows an MCP Servers feature (currently 0 registered), but the ARM API does not expose a `mcpServers` resource type in any available API version (tested: `2024-06-01-preview`, `2024-10-01-preview`, `2025-03-01-preview`). The `configurationApi` property is null and cannot be enabled via ARM REST API.

### Investigation Results — APIM MCP Servers

| API Version | Endpoint | Result |
|-------------|----------|--------|
| `2024-06-01-preview` | `/mcpServers` | 404 Not Found |
| `2024-10-01-preview` | `/mcpServers` | 404 Not Found |
| `2025-03-01-preview` | `/mcpServers` | 404 Not Found |
| `2025-01-01` | `/mcpServers` | Invalid API version |
| Gateway `/mcp` | Direct HTTP | 404 Not Found |
| `configurationApi` PATCH | Enable via ARM | Deserialization error |

**Conclusion**: APIM MCP Server registration is currently a portal-only feature or requires an API version not yet publicly available. It cannot be automated via ARM, Bicep, or Azure CLI as of April 2026.

## Decision

### 1. Provision Azure API Center

Deploy `Microsoft.ApiCenter/services` via Bicep as the centralized API governance layer. API Center provides:

- **API discovery** — Searchable catalog of all platform APIs
- **Domain classification** — APIs tagged by business domain (CRM, eCommerce, Inventory, Logistics, Product Management, Truth Layer, Search)
- **Lifecycle tracking** — API versions, deprecation status, and compliance metadata
- **APIM integration** — Bulk import from APIM via `az apic import-from-apim`

### 2. Automated API Center Sync

Create `sync-apic-apis.ps1` (with `.sh` wrapper) that runs after APIM sync in CI/CD:

1. Import all APIs from APIM into API Center using `az apic import-from-apim`
2. Fallback to individual `az apic api register` if bulk import fails

### 3. APIM MCP Server — Deferred to Portal

Per-agent `POST /mcp/{tool}` operations are already registered in APIM and functional. Full APIM MCP Server registration (the portal feature that aggregates MCP endpoints) is deferred until:

- ARM API exposes `mcpServers` resource type, OR
- Azure CLI adds `az apim mcp-server` commands, OR
- Bicep/AVM modules support MCP Server configuration

**Workaround**: Each agent's `/mcp/{tool}` endpoint is already accessible through APIM. Consumers can invoke MCP tools via `POST https://{apim-gateway}/agents/{service-name}/mcp/{tool}`.

### 4. Communication Path Topology

APIM serves a dual role in the platform's communication architecture:

1. **Public facade** — Frontend → CRUD and Frontend → Agent REST calls are routed through APIM for authentication, rate limiting, and observability (ADR-021).
2. **Internal MCP gateway** — CRUD → Agent enrichment/decision-assist calls use APIM-routed MCP tool invocations, maintaining governance and telemetry (ADR-024).
3. **Agents do NOT use APIM for CRUD reads** — Agent → CRUD transactional reads use cross-namespace Kubernetes DNS (ADR-026 Option A). Agents are forbidden from invoking CRUD REST endpoints directly for general API consumption (ADR-024).

## Consequences

### Positive

- Centralized API catalog for all 29 platform APIs
- Domain-based API discovery for internal and external consumers
- Automated sync keeps API Center in sync with APIM on every deployment
- No manual intervention needed — API Center syncs via CI/CD pipeline

### Negative

- APIM MCP Server aggregation requires manual portal setup until ARM API support arrives
- API Center adds a minor infrastructure cost (~$0/mo for Free tier, ~$750/mo for Standard)

### Risks

| Risk | Mitigation |
|------|------------|
| API Center import-from-apim fails | Fallback to individual API registration in sync script |
| APIM MCP Server ARM API changes | Monitor Azure updates; automate when available |
| API Center metadata drift | Sync runs on every deployment via CI/CD |

## Implementation

| Component | File | Change |
|-----------|------|--------|
| Bicep resource | `shared-infrastructure.bicep` | Add `Microsoft.ApiCenter/services@2024-03-01` |
| Sync script | `sync-apic-apis.ps1` + `.sh` | Import APIs from APIM into API Center |
| CI/CD | `deploy-azd.yml` | Add `sync-apic` job after `sync-apim` |
| Namespace fix | `sync-apim-agents.sh` | Update default namespace to `holiday-peak-agents` |
