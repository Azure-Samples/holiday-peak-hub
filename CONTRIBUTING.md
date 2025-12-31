# Contributing

Thanks for helping improve Holiday Peak Hub. This repo is a Python 3.13 monorepo with a shared micro-framework plus multiple FastAPI services. Keep changes small, tested, and focused.

## Prerequisites
- Python 3.13 with pip
- Docker (for image builds)
- Azure CLI if you plan to run Bicep deploys
- Access to Redis, Azure Cosmos DB, Azure Storage, and Azure AI Search when exercising memory/adapters end-to-end

## Setup
```pwsh
python -m pip install --upgrade pip
pip install -e lib
Get-ChildItem apps | ForEach-Object { pip install -e (Join-Path $_.FullName 'src') }
```

## Development workflow
- Format/lint: `python -m isort --check lib apps` then `python -m black --check lib apps` and `python -m pylint lib/src apps/*/src`
- Tests: `pytest lib/tests apps/**/tests --maxfail=1 --cov=. --cov-report=term-missing --cov-fail-under=75`
- Coverage floor is 75% to match CI.
- Run a service locally (example): `uvicorn main:app --reload --app-dir apps/ecommerce-catalog-search/src --port 8000`
- Keep README and docs in sync when adding adapters, agents, or services.

## Infra contributions
- Bicep modules live under .infra/modules; entrypoints under .infra/*.bicep. Deploy with `python -m .infra.cli deploy <service> --resource-group <rg> --location <region>` after `az login`.
- Helm chart scaffolding is in .kubernetes/chart. Prefer values-driven configuration; avoid hardcoding secrets.

## Pull requests
- Describe the change, risk, and how to validate.
- Add or update tests alongside code changes.
- Avoid unrelated formatting churn; keep commits cohesive.
- Ensure CI is green before requesting review.

## Reporting issues
- Include reproduction steps, expected vs actual behavior, and environment details (OS, Python, cloud resources used).
