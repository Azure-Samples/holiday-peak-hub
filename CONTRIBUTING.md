# Contributing

Thanks for helping improve Holiday Peak Hub. This repo is a Python 3.13 monorepo with a shared micro-framework (`lib/`) plus multiple FastAPI agent services (`apps/`) and a Next.js frontend (`apps/ui/`). Keep changes small, tested, and focused.

## Prerequisites

### Required

| Tool | Version | Notes |
|------|---------|-------|
| **Python** | ≥ 3.13 | Runtime for all backend services and scripts |
| **uv** | Latest | Canonical Python package manager (`pip install uv`) |
| **Node.js** | 20 | Required for the UI app; CI pins `node-version: '20'` |
| **Yarn** | 1.22 | Pinned in `apps/ui/package.json` `packageManager` field |
| **Docker** | Latest | Image builds for all services |
| **Git** | Latest | Hooks, CI diffing |

### Azure tooling (for infra & deployment)

| Tool | Version | Install |
|------|---------|---------|
| **Azure CLI (az)** | ≥ 2.67 | [Install guide](https://learn.microsoft.com/cli/azure/install-azure-cli) |
| **Azure Developer CLI (azd)** | Latest | [Install guide](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd) — used by `azure.yaml` hooks and `scripts/ops/demo-provision.ps1` |
| **Azure CLI `alb` extension** | Latest | `az extension add --name alb` — required for Application Gateway for Containers (AGC) operations |

### Kubernetes tooling (for AKS deployment)

| Tool | Version | Notes |
|------|---------|-------|
| **Helm** | 3.x | Predeploy hooks run `helm template` via `.infra/azd/hooks/render-helm.*` |
| **kubectl** | Matching AKS cluster | Required after `az aks get-credentials`; used by deploy hooks and `scripts/ops/demo-preflight-validate.ps1` |
| **kubelogin** | Latest | `az aks install-cli --kubelogin-version latest` — required for Entra ID-based AKS auth |

### Azure services (for end-to-end testing)

When exercising memory/adapters end-to-end, you need access to:

- **Redis** (hot memory tier)
- **Azure Cosmos DB** (warm memory tier)
- **Azure Blob Storage** (cold memory tier)
- **Azure AI Search** (semantic search / vector indexing)
- **Azure Event Hubs** (agent event processing)
- **Azure Key Vault** (secret management)
- **Azure PostgreSQL Flexible Server** (CRUD service data store)
- **Azure AI Foundry / AI Services** (agent model endpoints)
- **Azure API Management** (API gateway — deploy workflows use `az apim` commands)

> **Tip**: Use `scripts/start-dev-environment.ps1` to start stopped dev resources (PostgreSQL, AKS) that may have been paused by cost-saving automation.

## Backend setup (Python)

```pwsh
python -m pip install --upgrade pip
python -m pip install uv

# Install shared library
uv pip install --system -e ./lib/src

# Install all app packages
Get-ChildItem apps | ForEach-Object {
    $srcPath = Join-Path $_.FullName 'src'
    if (Test-Path (Join-Path $srcPath 'pyproject.toml')) {
        uv pip install --system -e $srcPath
    }
}

# Install dev/lint/test extras
uv pip install --system -e "./lib/src[dev,test,lint]"
```

`uv` is the canonical package manager for this repo. `pip` is compatibility-only for bootstrapping `uv`.

## Frontend setup (Next.js)

```pwsh
cd apps/ui
yarn install --frozen-lockfile
yarn dev          # Start dev server
yarn test         # Run Jest unit tests
yarn test:e2e     # Run Playwright E2E tests (requires: npx playwright install)
yarn lint         # ESLint + Prettier
yarn type-check   # TypeScript type check
```

Copy `apps/ui/.env.example` to `apps/ui/.env.local` and fill in your environment values.

## Lockfile policy

CI enforces that lockfiles are committed and up-to-date:
- **Python apps**: Each `apps/*/src/` must have a `uv.lock` file. CI runs `uv lock --check` to verify.
- **Frontend**: `apps/ui/yarn.lock` must be committed. CI runs `yarn install --frozen-lockfile`.

When updating dependencies, regenerate lockfiles (`uv lock` / `yarn install`) and commit them.

## Development workflow

### Lint & format
```bash
python -m isort --check lib apps
python -m black --check lib apps
python -m pylint --fail-on=E,F lib/src apps/*/src
python -m mypy --config-file pyproject.toml --ignore-missing-imports --follow-imports=skip \
    lib/src/holiday_peak_lib/agents/service_agent.py \
    lib/src/holiday_peak_lib/agents/memory/builder.py
```
- Lint policy: any pylint `E` or `F` diagnostic is blocking in both CI and the local push gate.
- `mypy` type-checks selected modules (see `lint.yml` for the current target list).

### Tests
```bash
# Lib tests (coverage floor: 80%)
pytest lib/tests --maxfail=1 --cov=lib/src --cov-fail-under=80

# App tests (coverage floor: 60% in CI, 75% overall)
pytest apps/*/tests --ignore=apps/ui/tests --cov=apps --cov-fail-under=60

# E2E tests
pytest tests/e2e -m e2e --maxfail=1

# Dependency vulnerability audit
python -m pip_audit --skip-editable
```

### Push gate (recommended)
```bash
git config core.hooksPath .githooks
```
With push gate enabled, every push runs `scripts/ops/pre_push_gate.py`, which mirrors the CI lint/test gate commands used by `.github/workflows/lint.yml` and `.github/workflows/test.yml`.

### Run a service locally
```bash
uvicorn main:app --reload --app-dir apps/ecommerce-catalog-search/src --port 8000
```

### Documentation site
```bash
uv pip install --system mkdocs mkdocs-material
mkdocs serve -f mkdocs/mkdocs.yml
```

### Keep README and docs in sync when adding adapters, agents, or services.

## Infra contributions
- Bicep modules live under `.infra/modules`; entrypoints under `.infra/azd/`. Deploy with `azd up` after `az login`, or use `python -m .infra.cli deploy <service> --resource-group <rg> --location <region>`.
- Helm chart scaffolding is in `.kubernetes/chart`. Prefer values-driven configuration; avoid hardcoding secrets.
- Predeploy hooks (`.infra/azd/hooks/render-helm.*`) convert the Helm chart into rendered YAML under `.kubernetes/rendered/<service>/`.

## Pull requests
- Describe the change, risk, and how to validate.
- Add or update tests alongside code changes.
- Avoid unrelated formatting churn; keep commits cohesive.
- Ensure CI is green before requesting review.

## Repository hygiene maintenance (maintainers)
- Use the governance runbook in `docs/governance/repository-hygiene-cleanup.md` for backlog reset operations (Issues/PRs) and branch pruning to `main` only.
- Run hygiene operations only with explicit maintainer approval because they can close work items and delete branches.

## Reporting issues
- Include reproduction steps, expected vs actual behavior, and environment details (OS, Python, cloud resources used).
