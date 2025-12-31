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

## Roadmap placeholders
- Add ADRs for adapter boundaries, model/tool routing, and memory partitioning choices.
- Add sequence diagrams for key flows (search, inventory health, returns).
- Add load and resilience test plans for Cosmos DB (429 handling) and Event Hubs backpressure.
