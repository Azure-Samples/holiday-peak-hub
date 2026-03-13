# Holiday Peak Hub

Agent-driven retail accelerator for building and operating intelligent, cloud-native retail services with a shared framework and domain-focused apps.

[![Release](https://img.shields.io/github/v/release/Azure-Samples/holiday-peak-hub?display_name=tag&include_prereleases&sort=semver)](https://github.com/Azure-Samples/holiday-peak-hub/releases)
[![Pre-release](https://img.shields.io/badge/channel-unstable-orange)](https://github.com/Azure-Samples/holiday-peak-hub/releases/tag/v2.1.0-unstable.0)
[![CI](https://img.shields.io/github/actions/workflow/status/Azure-Samples/holiday-peak-hub/ci.yml?branch=main&label=ci)](https://github.com/Azure-Samples/holiday-peak-hub/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-89.39%25-brightgreen)](htmlcov/index.html)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Python](https://img.shields.io/badge/python-3.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/typescript-5.x-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![License](https://img.shields.io/github/license/Azure-Samples/holiday-peak-hub)](LICENSE)

## Quick links

- [Documentation hub](docs/README.md)
- [Architecture](docs/architecture/README.md)
- [Provisioning & deployment (azd)](.infra/README.md)
- [Implementation roadmap](docs/IMPLEMENTATION_ROADMAP.md)
- [Changelog](CHANGELOG.md)

## Fast start (local)

### Prerequisites

- Python 3.13+
- Node.js 20+
- Yarn
- Docker (recommended)
- Azure CLI and Azure Developer CLI (`azd`)

### Run locally

```bash
# From repo root
python -m pip install --upgrade pip
pip install -e lib

# Install one service (example)
pip install -e apps/crud-service/src

# Run CRUD service
uvicorn crud_service.main:app --reload --port 8000 --app-dir apps/crud-service/src

# Run UI (separate terminal)
cd apps/ui
yarn install
yarn dev
```

For complete local setup across services, see [apps/README.md](apps/README.md) and [docs/backend_plan.md](docs/backend_plan.md).

## Provision to Azure (azd)

This is the primary path for provisioning and deployment.

```bash
# 1) Sign in
az login
azd auth login

# 2) Create/select environment
azd env new <env-name>

# 3) Provision infrastructure
azd provision -e <env-name>

# 4) Deploy services
azd deploy -e <env-name>
```

For environment flags, service-scoped deploys, shared/static topology options, and CI/CD entry workflows, see [.infra/README.md](.infra/README.md) and [docs/governance/README.md](docs/governance/README.md).

## Where to find everything else

- Framework library: [lib/README.md](lib/README.md)
- Service catalog and app guidance: [apps/README.md](apps/README.md)
- Architecture decisions (ADRs): [docs/architecture/ADRs.md](docs/architecture/ADRs.md)
- Governance and release policy: [docs/governance/README.md](docs/governance/README.md)
- Security: [SECURITY.MD](SECURITY.MD)

## Contributing and license

- Contributing guide: [CONTRIBUTING.md](CONTRIBUTING.md)
- License: [LICENSE](LICENSE)
