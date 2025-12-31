
# Holiday Peak Hub

Agent-driven retail accelerator with a reusable micro-framework, multi-tier memory (Redis/Cosmos/Blob), FastAPI + MCP surfaces, and per-domain services for commerce, product, CRM, inventory, and logistics.

## Monorepo layout

- lib/ — core micro-framework (adapters, agents, memory, orchestration, schemas, utils, config, app factory)
- apps/ — runnable FastAPI services built on the framework (one folder per domain process)
- .infra/ — Bicep modules and Typer CLI for Azure provisioning
- .kubernetes/ — Helm chart with deployment/service/KEDA templates
- .github/workflows/ — CI for linting, testing, and container publishing
- .vscode/ — local tasks and launch configs

## Quickstart

Requirements: Python 3.13, pip, Docker (for images), Azure CLI (for Bicep deploys), and access to Redis, Azure Cosmos DB, Azure Storage, and Azure AI Search when exercising the memory/adapters end-to-end.

Environment: a shared .env at repo root carries per-service endpoints keyed off `RELEASE_VERSION`; adjust values to match your release and secrets before running locally or deploying.

Install the framework and all apps:

```pwsh
python -m pip install --upgrade pip
pip install -e lib
Get-ChildItem apps | ForEach-Object { pip install -e (Join-Path $_.FullName 'src') }
```

Run any service locally (example: ecommerce catalog search):

```pwsh
uvicorn main:app --reload --app-dir apps/ecommerce-catalog-search/src --port 8000
```

Each service exposes a simple health endpoint at `/health`. Set environment variables for your backing services (Redis, Cosmos DB, Storage, Search, Event Hub) before exercising end-to-end flows. Prefer high-cardinality partition keys and hierarchical partition keys for Cosmos DB to balance throughput and minimize cross-partition scans.

## Testing and linting

Commands align with CI gates (coverage floor 75%):

```pwsh
python -m isort --check lib apps
python -m black --check lib apps
python -m pylint lib/src apps/*/src
pytest lib/tests apps/**/tests --maxfail=1 --cov=. --cov-report=term-missing --cov-fail-under=75
```

## CI

The workflow in .github/workflows/ci.yml runs lint, format, and tests on pushes/PRs and, on main, builds and pushes every app image to GHCR (`ghcr.io/<owner>/<app>:latest`).

## Infrastructure and deployment

- Bicep modules live in .infra/modules; per-service entry points are in .infra/*.bicep.
- A Typer CLI wraps deployment: `python -m .infra.cli deploy <service> --location <region> --version <release> [--subscription-id <sub>] [--resource-group <rg>]` or `deploy_all` to iterate every service (defaults RG to `<service>-rg`). Each deployment is subscription-scoped, creates the RG, and names resources as `appname-azureservicename-version` (storage accounts use a hyphen-stripped variant).
- Helm chart scaffolding lives in .kubernetes/chart for AKS + KEDA; supply your image names, environment, and HPA/KEDA triggers via values.yaml.

## Services catalog

- Ecommerce: catalog-search, product-detail-enrichment, cart-intelligence, checkout-support, order-status
- Product management: normalization-classification, acp-transformation, consistency-validation, assortment-optimization
- CRM: profile-aggregation, segmentation-personalization, campaign-intelligence, support-assistance
- Inventory: health-check, jit-replenishment, reservation-validation, alerts-triggers
- Logistics: eta-computation, carrier-selection, returns-support, route-issue-detection

## Configuration notes

- Memory stack: Redis (hot), Cosmos DB (warm), Blob Storage (cold). Use diagnostics from the Cosmos DB SDK to monitor RU/latency and handle 429 with retry-after.
- Agent orchestration and MCP helpers live in lib/agents; app_factory wires FastAPI apps with shared logging and settings.
- Use .vscode/tasks.json for local lint/test shortcuts and launch.json for debugging via uvicorn.

