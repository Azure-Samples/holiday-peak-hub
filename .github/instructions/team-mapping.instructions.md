---
applyTo: '**'
description: Delegation bootstrap that binds agent handoffs to team mapping and available workspace agents.
---
# Delegation Bootstrap

Before delegating to any agent:

1. Read `.github/agents/data/team-mapping.md` as the canonical agent registry.
2. Restrict delegation to agents whose `.agent.md` files exist under `.github/agents/`.
3. If a mapped agent is not available in `.github/agents/`, fall back to the current agent and continue with available tools.
4. Do not invent agent names that are absent from team mapping or unavailable in the workspace.

## Shared Agents Enabled By Control Plane

The following shared agent files are currently enabled for export by `repos/asset-map.yaml`:

- `azure-aks.agent.md`
- `azure-apim.agent.md`
- `azure-blob.agent.md`
- `azure-container-apps.agent.md`
- `azure-cosmos.agent.md`
- `azure-foundry.agent.md`
- `azure-postgres.agent.md`
- `azure-redis.agent.md`
- `azure-swa.agent.md`
- `business-strategy-agent.agent.md`
- `cataldi-librarian.agent.md`
- `code-guidelines-agent.agent.md`
- `competitive-intelligence-agent.agent.md`
- `enterprise-connectors.agent.md`
- `financial-modeling-agent.agent.md`
- `platform-quality.agent.md`
- `pr-evaluator.agent.md`
- `process-management-agent.agent.md`
- `python-specialist.agent.md`
- `report-generator.agent.md`
- `risk-analysis-agent.agent.md`
- `rust-specialist.agent.md`
- `system-architect.agent.md`
- `tech-manager.agent.md`
- `typescript-specialist.agent.md`
- `ui-agent.agent.md`
