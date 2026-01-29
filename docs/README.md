# Architecture overview

Holiday Peak Hub is an agent-first retail accelerator. It ships a reusable micro-framework plus multiple FastAPI services that exercise adapters and a multi-tier memory stack.

## Layers
- lib/: adapters, agent builder, FastAPI/MCP helpers, and memory layers
  - Hot memory: Redis for fast context/state
  - Warm memory: Azure Cosmos DB for structured session/profile data (prefer high-cardinality keys and hierarchical partition keys to minimize cross-partition scans)
  - Cold memory: Azure Blob Storage for long-lived artifacts
  - Search: Azure AI Search for hybrid/vector retrieval
  - Messaging: Event Hubs hooks for SAGA-style flows
- apps/: domain services (ecommerce, product, CRM, inventory, logistics) using the framework via app_factory
- utils/config: shared logging, retry, settings wiring

## Infrastructure
- Bicep modules in .infra/modules; per-service entrypoints in .infra/*.bicep.
- Typer CLI: `python -m .infra.cli deploy <service> --location <region> --version <release> [--subscription-id <sub>] [--resource-group <rg>]` or `deploy_all` (RG defaults to `<service>-rg`). Deployments are subscription-scoped and resources are named `appname-azureservicename-version` (storage accounts strip hyphens).
- Root `.env` carries per-service endpoints and uses `RELEASE_VERSION` substitutions; update it before local runs or deployments.
- Typer CLI: `python -m .infra.cli deploy <service> --location <region> --version <release> [--subscription-id <sub>] [--resource-group <rg>]` or `deploy_all` (RG defaults to `<service>-rg`). Deployments are subscription-scoped and resources are named `appname-azureservicename-version` (storage accounts strip hyphens).
- Helm chart in .kubernetes/chart for AKS + KEDA; fill in image names, env vars, autoscaling triggers in values.yaml.

## Development and testing
- Install: `pip install -e lib` and `pip install -e apps/<service>/src` for each app.
- Lint/format: isort, black, pylint (see contributing).
- Tests: pytest with coverage floor 75% (lib/tests and apps/**/tests).
- Local run: `uvicorn main:app --app-dir apps/<service>/src --reload` and hit `/health`.

## Architecture Documentation

### ADRs
All architectural decisions are documented in [architecture/ADRs.md](architecture/ADRs.md):
- ✅ [ADR-012: Adapter Boundaries and Composition](architecture/adrs/adr-012-adapter-boundaries.md)
- ✅ [ADR-013: SLM-First Model Routing Strategy](architecture/adrs/adr-013-model-routing.md)
- ✅ [ADR-014: Memory Partitioning and Data Placement](architecture/adrs/adr-014-memory-partitioning.md)

### Sequence Diagrams
Key flows are documented in [architecture/diagrams/](architecture/diagrams/):
- ✅ [E-commerce Catalog Search](architecture/diagrams/sequence-catalog-search.md)
- ✅ [Inventory Health Check](architecture/diagrams/sequence-inventory-health.md)
- ✅ [Logistics Returns Support](architecture/diagrams/sequence-returns-support.md)

### Test Plans
Load and resilience testing documented in [architecture/test-plans/](architecture/test-plans/):
- ✅ [Cosmos DB Load and Resilience](architecture/test-plans/cosmos-db-load-resilience.md)
- ✅ [Event Hubs Load and Resilience](architecture/test-plans/eventhub-load-resilience.md)

## Roadmap Status

**All planned documentation items completed!** ✅

The architecture documentation is now comprehensive with:
- 14 ADRs covering all major architectural decisions
- 3 detailed sequence diagrams for key flows
- 2 comprehensive load and resilience test plans
- Complete playbooks for operational scenarios
