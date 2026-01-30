# Holiday Peak Hub

**Agent-driven retail accelerator** with cloud-native architecture, complete frontend implementation, and comprehensive backend plan.

![Status](https://img.shields.io/badge/Status-Active%20Development-green)
![Frontend](https://img.shields.io/badge/Frontend-Complete-brightgreen)
![Backend](https://img.shields.io/badge/Backend-Complete-brightgreen)
![Architecture](https://img.shields.io/badge/Architecture-Cloud--Native-orange)
![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)
![Coverage](https://img.shields.io/badge/coverage-91%25-brightgreen)

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2FAzure-Samples%2Fholiday-peak-hub%2Fmain%2F.infra%2Fmodules%2Fshared-infrastructure%2Fshared-infrastructure-main.bicep)

## 🎉 Recent Updates (January 2026)

### ✅ Frontend Implementation Complete
- **13 production-ready pages** across 4 user roles (anonymous, customer, staff, admin)
- **52-component library** following atomic design principles
- **Ocean Blue/Lime Green/Cyan color system** with dark mode support
- **Full responsive design** with Tailwind CSS 4.0
- See [Components Documentation](docs/architecture/components.md) for complete details

### ✅ Backend Implementation Progress
- **CRUD Service**: Fully implemented with 31 endpoints across 15 route modules
- **Cloud-native architecture** with Azure best practices
- **10 database schemas** for operational data (Cosmos DB)
- **Event-driven integration** with Azure Event Hubs (5 topics)
- **Authentication**: Microsoft Entra ID JWT validation with RBAC
- **Zero-trust networking** with Private Endpoints and Managed Identity
- See [Implementation Roadmap](docs/IMPLEMENTATION_ROADMAP.md) and [CRUD Service Documentation](docs/architecture/crud-service-implementation.md)

### ✅ Architecture Documentation
- **20 ADRs** covering all major decisions
- **Cloud-native patterns**: Key Vault, Managed Identity, APIM, Front Door
- **Event-driven choreography** with Azure Event Hubs
- **Complete observability** with Application Insights

---

## Overview

Agent-driven retail accelerator with a reusable micro-framework, multi-tier memory (Redis/Cosmos/Blob), FastAPI + MCP surfaces, and per-domain services for commerce, product, CRM, inventory, and logistics.

---

## 📚 Documentation

### Core Documentation
- **[Implementation Roadmap](docs/IMPLEMENTATION_ROADMAP.md)** - Completed work and pending tasks with timelines
- **[Architecture Documentation](docs/architecture/)** - ADRs, components, system design, diagrams, playbooks
- **[Components Documentation](docs/architecture/components.md)** - Framework libraries, 21 agent services, and complete frontend component library (52 components, 15 pages)
- **[CRUD Service Documentation](docs/architecture/crud-service-implementation.md)** - Complete CRUD service implementation details
- **[Business Summary](docs/architecture/business-summary.md)** - Business context and requirements

### Architecture Decision Records (ADRs)
- [ADR-001](docs/architecture/adrs/adr-001-python-3.13.md) - Python 3.13 as Primary Language
- [ADR-002](docs/architecture/adrs/adr-002-azure-services.md) - Azure Service Stack Selection
- [ADR-007](docs/architecture/adrs/adr-007-saga-choreography.md) - SAGA Choreography with Event Hubs
- [ADR-009](docs/architecture/adrs/adr-009-aks-deployment.md) - AKS with Helm, KEDA, and Canary Deployments
- [ADR-015](docs/architecture/adrs/adr-015-nextjs-app-router.md) - Next.js 15 with App Router for Frontend
- [ADR-019](docs/architecture/adrs/adr-019-authentication-rbac.md) - Microsoft Entra ID Authentication and RBAC
- **[View all 20 ADRs](docs/architecture/ADRs.md)**

### Key Documents
- **[Components Documentation](docs/architecture/components.md)** - Library components, service components, and frontend component library
- **[Playbooks](docs/architecture/playbooks/)** - Operational runbooks for common scenarios
- **[Test Plans](docs/architecture/test-plans/)** - Load and resilience testing documentation

---

## 🏗️ Architecture Highlights

### Frontend (Production-Ready)
- **Framework**: Next.js 16.2.0 (canary) with App Router, React 19, TypeScript 5.7.2
- **Styling**: Tailwind CSS 3.4.0 with ocean/lime/cyan color system
- **Components**: 52 components (19 atoms, 20 molecules, 9 organisms, 4 templates)
- **Pages**: 13 pages across 4 user roles
- **Authentication**: Microsoft Entra ID via @azure/msal-browser & @azure/msal-react
- **Data Fetching**: TanStack Query 5.90.20 with Axios 1.7.9
- **API Integration**: Complete TypeScript client layer (6 services, 5 hooks)
- **Location**: `apps/ui/` | **Setup**: See [INTEGRATION.md](apps/ui/INTEGRATION.md)

### Backend (CRUD Service Complete, Agents Ready)
- **API Gateway**: Azure API Management with Entra ID policies (planned)
- **Services**: FastAPI (Python 3.13) with 21 AI agent services + 1 CRUD service ✅
- **CRUD Service**: 31 endpoints, 15 route modules, event publishing, managed identity auth
- **Database**: Azure Cosmos DB (10 containers with optimized partitioning)
- **Authentication**: Microsoft Entra ID JWT validation with RBAC ✅
- **Messaging**: Azure Event Hubs (5 topics: user, product, order, inventory, payment) ✅
- **Memory**: Redis (hot), Cosmos DB (warm), Blob Storage (cold)

### Cloud-Native Infrastructure
- **Networking**: Virtual Network, Private Endpoints, NSGs, zero public endpoints
- **Security**: Azure Key Vault, Managed Identity, no hardcoded secrets
- **CDN & WAF**: Azure Front Door Premium with OWASP rules
- **Container Registry**: Azure Container Registry with geo-replication
- **Observability**: Application Insights, Log Analytics, distributed tracing
- **CI/CD**: GitHub Actions (automated build, test, deploy)
- **IaC**: Bicep for all infrastructure

---

## Monorepo layout

- lib/ — core micro-framework (adapters, agents, memory, orchestration, schemas, utils, config, app factory)
- apps/ — runnable FastAPI services built on the framework (one folder per domain process)
- .infra/ — Bicep modules and Typer CLI for Azure provisioning
- .kubernetes/ — Helm chart with deployment/service/KEDA templates
- .github/workflows/ — CI for linting, testing, and container publishing
- .vscode/ — local tasks and launch configs

## Quickstart

### Prerequisites
- **Python 3.13+** for backend services
- **Node.js 20+ and Yarn** for frontend
- **Docker** for container images
- **Azure CLI** for Bicep deployments
- **Access to Azure services**: Redis, Cosmos DB, Storage, AI Search, Event Hubs

### 1. Setup Backend (CRUD Service + Agents)

```bash
# Install framework and all services
python -m pip install --upgrade pip
pip install -e lib
Get-ChildItem apps | ForEach-Object { pip install -e (Join-Path $_.FullName 'src') }

# Run CRUD Service
cd apps/crud-service/src
cp .env.example .env  # Configure your Azure resources
uvicorn crud_service.main:app --reload --port 8000

# Run an Agent Service (example: catalog search)
cd apps/ecommerce-catalog-search/src
uvicorn main:app --reload --port 8001
```

### 2. Setup Frontend

```bash
cd apps/ui
cp .env.example .env.local  # Configure API URL and Entra ID
yarn install
yarn dev
# Open http://localhost:3000
```

### 3. Configure Environment Variables

**Backend** (`.env`):
```bash
COSMOS_ACCOUNT_URI=https://your-account.documents.azure.com:443/
COSMOS_DATABASE=holiday-peak-hub
EVENTHUB_NAMESPACE=your-namespace.servicebus.windows.net
REDIS_URL=redis://your-redis.redis.cache.windows.net:6380
KEYVAULT_URL=https://your-keyvault.vault.azure.net/
ENTRA_TENANT_ID=your-tenant-id
ENTRA_CLIENT_ID=your-client-id
```

**Frontend** (`.env.local`):
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_ENTRA_CLIENT_ID=your-client-id
NEXT_PUBLIC_ENTRA_TENANT_ID=your-tenant-id
```

### 4. Verify Health

```bash
# CRUD Service
curl http://localhost:8000/health

# Frontend
curl http://localhost:3000/api/health
```

**See [Implementation Roadmap](docs/IMPLEMENTATION_ROADMAP.md) for deployment to Azure.**

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

### AI Agent Services (21 services)
- **E-commerce** (5): catalog-search, product-detail-enrichment, cart-intelligence, checkout-support, order-status
- **Product management** (4): normalization-classification, acp-transformation, consistency-validation, assortment-optimization
- **CRM** (4): profile-aggregation, segmentation-personalization, campaign-intelligence, support-assistance
- **Inventory** (4): health-check, jit-replenishment, reservation-validation, alerts-triggers
- **Logistics** (4): eta-computation, carrier-selection, returns-support, route-issue-detection

### Backend Services
- **CRUD Service** ✅ (`apps/crud-service/`): FastAPI REST API with 31 endpoints
  - Authentication: Microsoft Entra ID JWT validation + RBAC
  - Routes: health, auth, users, products, categories, cart, orders, checkout, payments, reviews
  - Staff routes: analytics, tickets, returns, shipments
  - Event publishing: 5 Event Hubs topics (user, product, order, inventory, payment)
  - Integration: MCP agent client, Cosmos DB repositories

### Frontend Application
- **Next.js UI** ✅ (`apps/ui/`): Complete e-commerce frontend
  - 13 production-ready pages across 4 user roles
  - 52 components following atomic design (19 atoms, 20 molecules, 9 organisms, 4 templates)
  - Complete API integration: 6 services, 5 React Query hooks
  - Authentication: MSAL integration (SSR-safe)
  - Ocean/lime/cyan color system with dark mode support

## Configuration notes

### Current (Agent Services)
- Memory stack: Redis (hot), Cosmos DB (warm), Blob Storage (cold). Use diagnostics from the Cosmos DB SDK to monitor RU/latency and handle 429 with retry-after.
- Agent orchestration and MCP helpers live in lib/agents; app_factory wires FastAPI apps with shared logging and settings.
- Use .vscode/tasks.json for local lint/test shortcuts and launch.json for debugging via uvicorn.

### Planned (Backend Implementation)
- **Authentication**: Microsoft Entra ID (OAuth 2.0) - no local password storage
- **Secrets**: Azure Key Vault with Managed Identity - zero hardcoded secrets
- **Networking**: Private Endpoints for all Azure services - zero public backend endpoints
- **API Gateway**: Azure API Management with JWT validation policies
- **Deployment**: AKS with Helm, KEDA autoscaling, canary deployments
- **Monitoring**: Application Insights with distributed tracing, Log Analytics
- See [Implementation Roadmap](docs/IMPLEMENTATION_ROADMAP.md) for deployment steps

---

## 🚀 Quick Start

### Prerequisites
- Python 3.13+
- Node.js 20+ and Yarn (for frontend)
- Docker (for container images)
- Azure CLI (for Bicep deployments)
- Access to Azure services: Redis, Cosmos DB, Storage, AI Search, Event Hubs

### Frontend Development

```bash
# Navigate to UI app
cd apps/ui

# Install dependencies
yarn install

# Run development server
yarn dev

# Open http://localhost:3000
```

### Backend Development

```bash
# Install framework and services
pip install -e lib
Get-ChildItem apps | ForEach-Object { pip install -e (Join-Path $_.FullName 'src') }

# Run a service (example: catalog search)
uvicorn main:app --reload --app-dir apps/ecommerce-catalog-search/src --port 8000
```

---

## 🧪 Testing and Linting

### Backend (Python)
```pwsh
# Format and lint
python -m isort --check lib apps
python -m black --check lib apps
python -m pylint lib/src apps/*/src

# Run tests (75% coverage floor)
pytest lib/tests apps/**/tests --maxfail=1 --cov=. --cov-report=term-missing --cov-fail-under=75
```

### Frontend (TypeScript/React)
```bash
cd apps/ui

# Lint
yarn lint

# Type check
yarn type-check

# Run unit tests
yarn test:unit

# Run E2E tests
yarn test:e2e
```

---

## 📦 Deployment

### Infrastructure (Bicep)

```bash
# Deploy a single service
python -m .infra.cli deploy <service> --location <region> --version <release>

# Deploy all services
python -m .infra.cli deploy_all --location eastus --version 1.0.0
```

### CI/CD (GitHub Actions)

- **Push to `develop`**: Automatic deployment to dev environment
- **Tag with `v*`**: Production deployment with canary strategy
- **PR**: Automated linting, testing, security scanning

See [Implementation Roadmap](docs/IMPLEMENTATION_ROADMAP.md) for deployment details.

---

## 🎯 Implementation Status

| Component | Status | Documentation |
|-----------|--------|---------------|
| **Frontend** | ✅ Complete | [Frontend Plan](docs/architecture/FRONTEND_IMPLEMENTATION_PLAN.md) |
| **21 AI Agent Services** | ✅ Complete | [Components](docs/architecture/components.md) |
| **CRUD Service** | ✅ Complete | [CRUD Service Docs](docs/architecture/crud-service-implementation.md) |
| **Frontend Integration** | ✅ Complete | [Integration Guide](apps/ui/INTEGRATION.md) |
| **Cloud Architecture** | ✅ Designed | [Shared Infrastructure](.infra/modules/shared-infrastructure/README.md) |
| **Infrastructure (Bicep)** | ⏳ Pending Deployment | [Implementation Roadmap](docs/IMPLEMENTATION_ROADMAP.md) |
| **Agent Deployment** | ⏳ Pending | [Implementation Roadmap](docs/IMPLEMENTATION_ROADMAP.md) |
| **E2E Integration** | ⏳ Pending | Phases 2-8 |

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📄 License

See [LICENSE](LICENSE) for details.

---

## 🔗 Related Resources

- [Azure Well-Architected Framework](https://learn.microsoft.com/azure/well-architected/)
- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)
- [Next.js Documentation](https://nextjs.org/docs)
- [Azure API Management](https://learn.microsoft.com/azure/api-management/)
- [Azure Cosmos DB](https://learn.microsoft.com/azure/cosmos-db/)