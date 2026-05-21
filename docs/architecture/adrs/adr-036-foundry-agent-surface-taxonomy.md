# ADR-036: Foundry Agent Surface Taxonomy

**Status**: Accepted
**Date**: 2026-05
**Deciders**: Architecture Team, Ricardo Cataldi
**Tags**: foundry, agents, hosted-agents, custom-agents, aks, governance

## Context

Holiday Peak Hub is both a framework and a product. Operators need one simple rule for Foundry exposure without changing the product runtime:

- Public or human-facing agents should be easy to test and evaluate in Microsoft Foundry as Hosted Agents.
- Non-public internal agents should stay behind the existing product edge and be represented as Custom Agents that proxy the AKS/APIM endpoint.

Microsoft Foundry Hosted Agents are code-based, containerized agents that run on Foundry Agent Service managed compute and can expose the Responses protocol. That is useful for public Playground, telemetry, and evaluation surfaces. It is not, by itself, a decision to move Holiday Peak Hub product traffic away from AKS.

## Decision

Adopt a two-track Foundry surface taxonomy:

| Surface | Applies To | Repo Artifact | Runtime Meaning |
|---|---|---|---|
| Hosted Agent | Public or human-facing agents | `apps/<service>/agent.hosted.yaml` | Foundry-managed Hosted Agent exposure over the same FastAPI app and `/responses` adapter. |
| Custom Agent | Non-public or internal agents | `apps/<service>/.foundry/agent-metadata.yaml` with `surface.type: custom` | Proxy surface for the existing APIM -> AGC -> AKS product endpoint; no Foundry-managed compute. |

The central policy registry is `apps/foundry-surfaces.yaml`. Tests must fail when a listed Hosted Agent lacks `agent.hosted.yaml`, when a Custom Agent has a hosted manifest, or when the registry no longer covers all 26 active agent services exactly once.

## Hosted Agent Surface Contract

Hosted manifests must use:

- `template.kind: hosted`
- `responses` protocol version `1.0.0`
- the existing service module entry point, for example `python -m uvicorn ecommerce_catalog_search.main:app --host 0.0.0.0 --port 8088`
- `HOLIDAY_PEAK_FOUNDRY_HOSTED=1`
- `UVICORN_PORT=8088`
- hosted-safe agent identity aliases such as `HPH_AGENT_ID_FAST` and `HPH_AGENT_ID_RICH`
- no declared environment variable names starting with reserved `FOUNDRY_` or `AGENT_` prefixes

The framework mounts `/responses` from the existing FastAPI app when `HOLIDAY_PEAK_FOUNDRY_HOSTED=1`. This keeps Hosted Agent manifests executable without introducing per-service `hosted_main.py` files. The mount is idempotent, so a service such as `inventory-health-check` that also enables the AKS Responses adapter cannot double-mount the host server.

Hosted surfaces are approved for these public or human-facing agents:

- `ecommerce-catalog-search`
- `ecommerce-cart-intelligence`
- `ecommerce-checkout-support`
- `ecommerce-order-status`
- `ecommerce-product-detail-enrichment`
- `crm-support-assistance`
- `inventory-health-check`
- `logistics-eta-computation`
- `logistics-returns-support`
- `truth-hitl`

## Custom Agent Surface Contract

Custom surfaces must declare in `.foundry/agent-metadata.yaml`:

- `surface.type: custom`
- `surface.classification: Custom Agent`
- `surface.foundryManagedCompute: false`
- `surface.proxy.target: existing-aks-apim-endpoint`
- `surface.productRuntime: aks`
- `surface.productTrafficPath: APIM -> AGC -> AKS`

Custom surfaces are approved for these internal agents:

- `crm-campaign-intelligence`
- `crm-profile-aggregation`
- `crm-segmentation-personalization`
- `inventory-alerts-triggers`
- `inventory-jit-replenishment`
- `inventory-reservation-validation`
- `logistics-carrier-selection`
- `logistics-route-issue-detection`
- `product-management-acp-transformation`
- `product-management-assortment-optimization`
- `product-management-consistency-validation`
- `product-management-normalization-classification`
- `search-enrichment-agent`
- `truth-enrichment`
- `truth-export`
- `truth-ingestion`

## Guardrail Alignment

This ADR does not weaken existing architecture guardrails:

- ADR-005 remains in force: MAF direct-model invocation runs in the existing FastAPI app; no duplicate `hosted_main.py`, duplicate FastAPI app, or second product traffic path.
- ADR-017 remains in force: azd + Flux + HelmRelease remain the current AKS deployment model for product traffic.
- ADR-021 remains in force: APIM -> AGC -> AKS is the canonical product edge.
- ADR-024 and ADR-030 remain in force: agent-to-agent communication stays MCP-only, with approved REST/Event Hubs paths only.
- ADR-032 remains in force: Responses paths keep Redis, Cosmos DB, Blob Storage, Event Hub, Key Vault, and Application Insights parity with `/invoke`.

Moving product traffic ownership from AKS to Foundry-managed hosted containers would require a future ADR that explicitly supersedes the relevant runtime and edge decisions.

## Consequences

**Positive**: Operators get a simple exposure taxonomy; public agents gain a Foundry Hosted Agent Playground/evaluation surface; internal agents remain private and reuse the existing AKS/APIM operational path.

**Negative**: Hosted Agent surfaces create Foundry-managed compute and can incur additional Hosted Agents runtime charges when deployed or active. Custom Agent surfaces do not create Foundry-managed compute, but their health depends on the existing AKS/APIM path.

**Operational**: Tests become the enforcement point for taxonomy drift. Registry, hosted manifests, and custom metadata must be updated together when an agent changes exposure class.

## Related ADRs

- [ADR-005: Microsoft Agent Framework + Foundry](adr-005-agent-framework.md)
- [ADR-017: Deployment Strategy - azd Provisioning + Flux CD GitOps](adr-017-deployment-strategy.md)
- [ADR-021: APIM + Application Gateway for Containers as Canonical AKS Edge](adr-021-apim-agc-edge.md)
- [ADR-024: Agent Communication Policy, Isolation, and Async Contracts](adr-024-agent-communication-policy.md)
- [ADR-030: MCP-Only Agent-to-Agent Communication with Hop Counter](adr-030-mcp-only-a2a.md)
- [ADR-032: Three-Tier Memory Contract Pinning](adr-032-three-tier-memory-contract.md)