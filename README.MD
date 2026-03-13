# Holiday Peak Hub

Agent-driven retail accelerator for building and operating intelligent, cloud-native retail services with a shared framework and domain-focused apps.

![Release](https://img.shields.io/badge/release-v2.1.0--unstable.0-blue)
![Tests](https://img.shields.io/badge/tests-1410%20passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)

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
