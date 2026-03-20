# Holiday Peak Hub - Architecture Documentation

**Last Updated**: March 11, 2026  
**Version**: [v2.0.0](https://github.com/Azure-Samples/holiday-peak-hub/releases/tag/v2.0.0)  
**Status**: Active Development

## Overview

Holiday Peak Hub is a **cloud-native, agent-driven retail accelerator** with complete frontend implementation and comprehensive backend architecture plan. This documentation covers all architectural decisions, implementation plans, and operational procedures.

## Developer Scripts

Per-app run and test scripts are available under [scripts](scripts). These scripts create per-app virtual environments under each app src folder and run tests with coverage outputs per app directory.

Python package management in this repository is uv-first. In CI, dependency installs use `uv pip --system`; use pip only as a compatibility bootstrap path to install uv.

- Run an app: [scripts/run-app.sh](scripts/run-app.sh) with a per-app wrapper like [scripts/run-ecommerce-checkout-support.sh](scripts/run-ecommerce-checkout-support.sh)
- Run all tests with coverage per app: [scripts/run-all-tests.sh](scripts/run-all-tests.sh)

## Infrastructure CLI

Provisioning and deployment use the azd project defined in `azure.yaml`.
The Python CLI in `.infra/cli.py` is scaffolding-only (`generate-bicep`, `generate-dockerfile`).

### Deployment Runbook (GitHub Actions + azd)

Use environment-specific entry workflows:

- `.github/workflows/deploy-azd-dev.yml` as the default development path (auto-runs on `main` changes and supports manual dispatch).
- `.github/workflows/deploy-azd-prod.yml` for production deployments triggered only by stable release tags (`v*.*.*` without pre-release suffixes) that also have a published GitHub Release and point to a commit reachable from `main`.
- `.github/workflows/deploy-azd.yml` remains the shared core workflow invoked by both entry workflows.
- `.github/workflows/ci.yml` publishes GHCR images automatically for stable tags (`v*.*.*`) and can still be run manually for build/optional publish.

> Provisioning is mandatory before frontend/backend consumption in any environment. Always run `azd provision` (and then `azd deploy`) before validating APIs or UI integration.

**Required repository/environment secrets**:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`

**Entry workflow inputs**:

- Dev entrypoint (`deploy-azd-dev.yml`): `location`, `projectName`, `imageTag`, `deployStatic`, `uiOnly`, `apiBaseUrl`, `forceApimSync`, `autoAllowAcrRunnerIp`.
- Prod entrypoint (`deploy-azd-prod.yml`): no manual inputs; runs only from stable release tags and deploys using the tag name as `imageTag`.

**Manual trigger examples**:

- Day-to-day development rollout (recommended default):

```bash
gh workflow run deploy-azd-dev.yml -f location=eastus2 -f projectName=holidaypeakhub405 -f imageTag=latest -f deployStatic=true -f autoAllowAcrRunnerIp=true
```

- Fast development rerun without APIM sync:

```bash
gh workflow run deploy-azd-dev.yml -f location=eastus2 -f projectName=holidaypeakhub405 -f imageTag=latest -f deployStatic=true -f forceApimSync=false -f autoAllowAcrRunnerIp=true
```

- Production rollout (stable release tag + published GitHub Release):

```bash
git tag v1.2.3
git push origin v1.2.3
```

Then publish a GitHub Release for `v1.2.3`. The production workflow validates release existence before deploying.

Core workflow note: `.github/workflows/deploy-azd.yml` is reusable-only and not intended for direct manual dispatch.

**Execution order**:

1. `provision` job: sets azd env values and runs `azd provision`.
2. `deploy-crud` job: deploys `crud-service` when CRUD/lib changes are detected.
3. `deploy-foundry-models` and `deploy-agents` jobs: run after provision; `deploy-agents` deploys changed agent services (and can proceed when `deploy-crud` is skipped for agent-only changes).
4. `sync-apim` and `smoke-apim` jobs: run when CRUD/agent changes are present or `forceApimSync=true`.
5. `deploy-ui` job (when `deployStatic=true`): runs after APIM sync/smoke gates, resolves APIM URL with fail-fast validation, fetches the SWA deployment token from Azure, and deploys `apps/ui` via `Azure/static-web-apps-deploy@v1` (framework-aware build for dynamic Next.js routes).
6. Demo data seeding is operator-driven and must be run locally (outside CI) when needed.

**Operational notes**:

- Keep `deployShared=true` for all shared-environment rollouts.
- UI deployment intentionally uses the SWA GitHub Action path (not `azd deploy --service ui`) so App Router dynamic segments (`[id]`, `[slug]`) are built in the same mode as standard SWA workflows.
- Frontend API calls must always use APIM via validated runtime env aliases (`NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_CRUD_API_URL` are set together in deployment workflows).
- Demo seeding uses a curated catalog of 10 categories and 100 products with realistic retail data. Re-runs are idempotent by item ID (`cat-*`, `prd-*`): existing seeded records are updated instead of duplicated.
- Use environment approvals in GitHub Environments for `staging`/`prod`.
- Keep image tags immutable for reproducible rollback.

**Local demo seeding (manual)**:

```bash
python -m crud_service.scripts.seed_demo_data
```

Run this locally from the CRUD service environment with `POSTGRES_*` variables configured for your target environment.

**CRUD write-path validation via API POST endpoints (recommended)**:

Use this to validate CRUD liveness and write behavior through HTTP endpoints (instead of direct DB scripts):

```powershell
./scripts/ops/crud-post-write-check.ps1 -AzdEnvironment dev
```

By default this runs against APIM (`APIM_GATEWAY_URL` from the selected azd environment).

To run against the live CRUD service directly using AKS port-forward (`svc/crud-service`):

```powershell
./scripts/ops/crud-post-write-check.ps1 -AzdEnvironment dev -UsePortForward
```

If you have a bearer token for authenticated endpoints, pass it via `CRUD_BEARER_TOKEN`:

```powershell
$env:CRUD_BEARER_TOKEN = "<token>"
./scripts/ops/crud-post-write-check.ps1 -AzdEnvironment dev
```

The script exercises all CRUD `POST` routes and reports `PASS` / `SKIPPED` / `FAIL` per endpoint.

### Governance Compliance Checklist

- Use environment entrypoint workflows only (`deploy-azd-dev.yml`, `deploy-azd-prod.yml`).
- Apply production gates: stable tag, published release, and commit lineage from `main`.
- Enforce OIDC authentication and Key Vault secret management.
- Preserve changed-service deployment and APIM sync/smoke behavior per environment defaults.
- Run lint/test quality gates before deployment (repo minimum 75% coverage).
- Update governance docs when workflow behavior or runtime controls change:
  - `docs/governance/README.md`
  - `docs/governance/backend-governance.md`
  - `docs/governance/frontend-governance.md`
  - `docs/governance/infrastructure-governance.md`

### Reproducible Deployment Operations (Non-Bicep)

The following steps were used to deploy and validate services without changing Bicep infrastructure definitions. These commands are intended for operators reproducing the same workflow in another subscription.

1. **Resolve active environment and resource names**

```bash
azd env get-values -e dev
```

2. **Verify current public egress IP (for ACR firewall allowlist)**

```powershell
$ip = Invoke-RestMethod -Uri 'https://api.ipify.org'
Write-Output "PUBLIC_IP=$ip"
```

3. **Inspect ACR network posture and firewall rules**

```bash
az acr show -n <acrName> --query "{publicNetworkAccess:publicNetworkAccess,defaultAction:networkRuleSet.defaultAction,bypass:networkRuleBypassOptions,exportPolicy:policies.exportPolicy.status}" -o json
az acr network-rule list -n <acrName> -o table
```

4. **Temporarily unblock ACR publish from operator IP (if `azd deploy` fails with DENIED/IP blocked)**

```bash
az acr update -n <acrName> --allow-exports true
az acr update -n <acrName> --public-network-enabled true --default-action Deny
az acr network-rule add -n <acrName> --ip-address <PUBLIC_IP>/32
```

5. **Deploy CRUD service through azd (Helm-driven AKS deploy)**

```bash
azd deploy --service crud-service --no-prompt -e dev
```

For Entra-only PostgreSQL authentication in CRUD, set these `azd` environment values before deploy:

```bash
azd env set POSTGRES_AUTH_MODE entra
azd env set POSTGRES_USER <aks-managed-identity-name>
azd env set POSTGRES_PASSWORD ""
```

6. **Deploy UI through azd**

```bash
azd deploy --service ui --no-prompt -e dev
```

7. **Validate AKS health and CRUD runtime**

```bash
az aks show -g <resourceGroup> -n <aksName> --query "{powerState:powerState.code,provisioningState:provisioningState}" -o json
az aks get-credentials -g <resourceGroup> -n <aksName> --overwrite-existing
kubectl get svc,pods -n holiday-peak
```

8. **Validate Helm-rendered desired state before applying manual fixes**

```bash
apps/crud-service/src/../../../.infra/azd/hooks/render-helm.sh crud-service
kubectl apply --dry-run=server -f .kubernetes/rendered/crud-service/all.yaml -n holiday-peak
```

9. **Manual recovery only (if probes cause crash loops)**

```powershell
$patch = '{"spec":{"template":{"spec":{"containers":[{"name":"crud-service","readinessProbe":{"initialDelaySeconds":45,"failureThreshold":10},"livenessProbe":{"initialDelaySeconds":90,"failureThreshold":10}}]}}}}'
kubectl patch deployment crud-service-crud-service -n holiday-peak -p $patch
kubectl rollout status deployment/crud-service-crud-service -n holiday-peak --timeout=300s
```

10. **APIM operational checks and bootstrap (when APIs are missing)**

```bash
az apim show -g <resourceGroup> -n <apimName> --query "{gatewayUrl:gatewayUrl,publicNetworkAccess:publicNetworkAccess,virtualNetworkType:virtualNetworkType}" -o json
az apim api list -g <resourceGroup> --service-name <apimName> -o table
./.infra/azd/hooks/sync-apim-agents.sh
```

This sync script is also executed automatically by the global `postdeploy` hook in `azure.yaml`.
It discovers all AKS services from `azure.yaml` (excluding `crud-service`) and upserts APIM APIs with this path contract:

- API path: `/agents/<service-name>`
- Operations: `GET /health`, `POST /invoke`, `POST /mcp/{tool}`
- Backend URL template: `http://<service-name>-<service-name>.<namespace>.svc.cluster.local`

Examples:

- `https://<apimName>.azure-api.net/agents/ecommerce-cart-intelligence/invoke`
- `https://<apimName>.azure-api.net/agents/inventory-health-check/health`

12. **Postdeploy Foundry ensure hook (`azd deploy` / `azd up`)**

- `ensure-foundry-agents` postdeploy hook now resolves Kubernetes service names by `app=<service>` label and uses the actual Service port, avoiding false failures from chart-generated service names and non-8000 service ports.
- Foundry ensure runs in non-blocking mode by default for `azd` hooks (`FailOnError=false` / `--non-blocking`) so transient per-service ensure failures do not fail the deployment.
- Demo data seeding is now local/manual only and is not executed by `azd` postdeploy hooks.

13. **End-to-end smoke checks (APIM and SWA)**

14. **Post-deploy hardening (recommended)**

```powershell
$apim = "https://<apimName>.azure-api.net"
$ui = "https://<swaHost>.azurestaticapps.net"
Invoke-WebRequest "$apim/api/products" -UseBasicParsing
Invoke-WebRequest "$apim/api/categories" -UseBasicParsing
Invoke-WebRequest "$ui/api/products" -UseBasicParsing
Invoke-WebRequest "$ui/api/categories" -UseBasicParsing
```


After deployment succeeds, remove temporary ACR public ingress:

```bash
az acr network-rule remove -n <acrName> --ip-address <PUBLIC_IP>/32
az acr update -n <acrName> --public-network-enabled false
```

> Notes:
> - Use Microsoft VPN only if it provides a stable egress IP that you can consistently allowlist on ACR.
> - Keep manual `kubectl patch` usage as recovery-only; normal deployments should remain `azd deploy` + Helm-rendered manifests.
> - Demo data seeding runs inside AKS (not from the GitHub runner) to support private PostgreSQL networking.

---

## 📚 Documentation Index

### Implementation Plans
- **[Implementation Roadmap](IMPLEMENTATION_ROADMAP.md)** - Current progress and pending tasks
  - Phase 1 Complete: CRUD service, frontend integration, infrastructure modules
  - Phases 2-7 Pending: Deployment, testing, monitoring, optimization
  - Estimated 29-46 hours to complete
- **[CRUD Service Documentation](architecture/crud-service-implementation.md)** - Complete implementation details
  - 31 REST endpoints, authentication, event publishing
  - Database schemas, deployment guides
  - Frontend integration examples
- **[Single RG Deployment Runbook](implementation/single-rg-deployment-runbook.md)** - Fast provision/recover/deprovision operations for `holidaypeakhub405-dev-rg`

### Architecture Documentation

**Frontend Architecture**: The production-ready frontend (13 pages, 52 components) is fully documented in the [Components Documentation](architecture/components.md) and governed by 6 frontend-specific ADRs ([ADR-015](architecture/adrs/adr-015-nextjs-app-router.md) through [ADR-020](architecture/adrs/adr-020-api-client-architecture.md)).

### Core Documentation
- **[Architecture Overview](architecture/architecture.md)** - System context and high-level design
- **[Business Summary](architecture/business-summary.md)** - Business requirements and use cases
- **[Components Documentation](architecture/components.md)** - All framework and service components
- **[ADRs (Architecture Decision Records)](architecture/ADRs.md)** - Index of architectural decisions

---

## 🏗️ System Architecture

### Frontend Layer
**Technology**: Next.js 16.2.0-canary.17, React 19, TypeScript 5.7.2, Tailwind CSS 3.4.0  
**Location**: `apps/ui/`  
**Status**: ✅ Complete (13 pages, 52 components)

**Pages by Role**:
- **Anonymous** (6): Homepage, Category, Product Detail, Order Tracking, Login, Signup
- **Customer** (3): Checkout, Dashboard, Profile
- **Staff** (3): Sales Analytics, Customer Requests, Logistics Tracking
- **Admin** (1): Admin Portal

### API Management Layer
**Technology**: Azure API Management  
**Status**: 📋 Planned (detailed in backend plan)

**Features**:
- Entra ID token validation
- Rate limiting and caching
- CORS policies
- Request routing
- WAF integration

**Networking posture**:
- Non-prod environments run APIM in VNET `External` mode (public gateway, private backend reachability to AKS).
- This supports the APIM-in-front pattern while keeping AKS services as `ClusterIP` behind private network paths.

### Application Layer
**Technology**: FastAPI (Python 3.13)  
**Status**: ✅ CRUD Service Complete, ✅ 21 Agent Services Complete

**CRUD Service** ✅ **IMPLEMENTED**:
- **31 REST endpoints** across 15 route modules
- **Authentication**: Entra ID JWT validation, RBAC (anonymous, customer, staff, admin)
- **Repositories**: Base + specialized (User, Product, Order, Cart)
- **Routes**: health, auth, users, products, categories, cart, orders, checkout, payments, reviews
- **Staff Routes**: analytics, tickets, returns, shipments
- **Integrations**: Event Hubs publisher (5 topics), MCP agent client
- **Testing**: Unit, integration, and e2e test structure
- **Location**: `apps/crud-service/`
- **Documentation**: [CRUD Service Implementation](architecture/crud-service-implementation.md)

**Agent Services** (21):
- E-Commerce (5): catalog-search, product-detail-enrichment, cart-intelligence, checkout-support, order-status
- Product Management (4): normalization-classification, acp-transformation, consistency-validation, assortment-optimization
- CRM (4): profile-aggregation, segmentation-personalization, campaign-intelligence, support-assistance
- Inventory (4): health-check, jit-replenishment, reservation-validation, alerts-triggers
- Logistics (4): eta-computation, carrier-selection, returns-support, route-issue-detection

**CRUD Service** ✅ **IMPLEMENTED**:
- **31 REST endpoints** across 15 route modules
- **Authentication**: Entra ID JWT validation, RBAC (anonymous, customer, staff, admin)
- **Repositories**: Base + specialized (User, Product, Order, Cart)
- **Routes**: health, auth, users, products, categories, cart, orders, checkout, payments, reviews
- **Staff Routes**: analytics, tickets, returns, shipments
- **Integrations**: Event Hubs publisher (5 topics), MCP agent client
- **Testing**: Unit, integration, and e2e test structure
- **Location**: `apps/crud-service/`

### Data Layer
**Technology**: Cosmos DB, Redis, Blob Storage  
**Status**: ✅ Agent memory implemented, 📋 Operational data planned

**Databases**:
- **Cosmos DB (Operational)**: Users, Products, Orders, Reviews, Cart, Addresses, Payments, Tickets, Shipments, Audit Logs
- **Cosmos DB (Agent Memory)**: Conversation history, context
- **Redis**: Hot memory, caching
- **Blob Storage**: Cold storage, product images

### Integration Layer
**Technology**: Azure Event Hubs  
**Status**: ✅ Infrastructure ready

**Event Topics**: user-events, product-events, order-events, inventory-events, payment-events, shipping-events, support-events

---

## 🔒 Cloud-Native Architecture

### Security & Identity
- **Azure Key Vault**: All secrets centralized, no hardcoded credentials
- **Managed Identity**: Passwordless authentication to all Azure services
- **Microsoft Entra ID**: OAuth 2.0 / OpenID Connect for user authentication
- **RBAC**: 4 roles (anonymous, customer, staff, admin)

### Networking
- **Virtual Network**: Complete network isolation
- **Private Endpoints**: All Azure PaaS services accessible only via private IPs
- **NSGs**: Network Security Groups on all subnets
- **Zero Public Endpoints**: Only Azure Front Door and APIM exposed

### Container Management
- **Azure Container Registry**: Premium SKU with geo-replication
- **ACR Tasks**: Automated image builds on commit
- **Managed Identity**: AKS pulls images without passwords

### Content Delivery
- **Azure Front Door Premium**: Global CDN and WAF
- **OWASP Core Rule Set 3.2**: Web application firewall
- **Bot Protection**: Automated threat detection

### Observability
- **Application Insights**: Distributed tracing with correlation IDs
- **Log Analytics**: Centralized logging with KQL queries
- **Azure Monitor**: Alerts and dashboards

---

## 📋 Architecture Decision Records (ADRs)

### Language & Tooling
- ✅ [ADR-001: Python 3.13 as Primary Language](architecture/adrs/adr-001-python-3.13.md)
- ✅ [ADR-005: FastAPI + MCP for API Exposition](architecture/adrs/adr-005-fastapi-mcp.md)
- ✅ [ADR-015: Next.js 15 with App Router for Frontend](architecture/adrs/adr-015-nextjs-app-router.md)

### Frontend Architecture
- ✅ [ADR-016: Atomic Design System for Component Library](architecture/adrs/adr-016-atomic-design-system.md)
- ✅ [ADR-017: AG-UI Protocol Integration](architecture/adrs/adr-017-ag-ui-protocol.md)
- ✅ [ADR-018: Agentic Commerce Protocol (ACP) Frontend](architecture/adrs/adr-018-acp-frontend.md)
- ✅ [ADR-019: Authentication and RBAC](architecture/adrs/adr-019-authentication-rbac.md)
- ✅ [ADR-020: API Client Architecture](architecture/adrs/adr-020-api-client-architecture.md)

### Backend Architecture
- ✅ [ADR-002: Azure Service Stack Selection](architecture/adrs/adr-002-azure-services.md)
- ✅ [ADR-003: Adapter Pattern for Retail Integrations](architecture/adrs/adr-003-adapter-pattern.md)
- ✅ [ADR-006: Microsoft Agent Framework + Foundry](architecture/adrs/adr-006-agent-framework.md)
- ✅ [ADR-007: SAGA Choreography with Event Hubs](architecture/adrs/adr-007-saga-choreography.md)

### Memory & State
- ✅ [ADR-004: Builder Pattern for Agent Memory](architecture/adrs/adr-004-builder-pattern-memory.md)
- ✅ [ADR-008: Three-Tier Memory Architecture](architecture/adrs/adr-008-memory-tiers.md)
- ✅ [ADR-014: Memory Partitioning and Data Placement](architecture/adrs/adr-014-memory-partitioning.md)

### Infrastructure
- ✅ [ADR-009: AKS with Helm, KEDA, and Canary Deployments](architecture/adrs/adr-009-aks-deployment.md)
- ✅ [ADR-010: Dual Exposition: REST + MCP Servers](architecture/adrs/adr-010-rest-and-mcp-exposition.md)

### Agent & AI
- ✅ [ADR-012: Adapter Boundaries and Composition](architecture/adrs/adr-012-adapter-boundaries.md)
- ✅ [ADR-013: SLM-First Model Routing Strategy](architecture/adrs/adr-013-model-routing.md)

**[View all 20 ADRs](architecture/ADRs.md)**

---

## 🔄 Implementation Status

### ✅ Completed
- Frontend implementation (13 pages, 52 components)
- 21 AI agent services
- Backend implementation plan (140+ pages)
- Cloud-native architecture design
- CI/CD pipeline design
- Complete documentation

### ⏳ In Progress
- Phase 1: Foundation (cloud infrastructure, authentication, CRUD service)

### 📋 Planned (Phases 2-8)
- Product & Category pages backend
- Cart & Checkout backend
- Customer dashboard & profile backend
- Reviews & wishlist backend
- Staff pages backend
- Admin portal backend
- Optimization & monitoring

**Timeline**: 1-2 weeks remaining (see [Implementation Roadmap](IMPLEMENTATION_ROADMAP.md))

---

## 🎯 Key Features

### Production-Ready Frontend
- Fully responsive design (mobile-first)
- Dark mode support with theme toggle
- Accessible components (WCAG 2.1 AA)
- SEO optimized
- Performance optimized (lazy loading, code splitting)

### Cloud-Native Backend
- Zero hardcoded secrets
- Private networking (no public endpoints)
- Managed Identity everywhere
- Automated CI/CD
- Blue-green and canary deployments
- Distributed tracing
- Multi-region disaster recovery

### Agent-Driven Intelligence
- AI-powered product search
- Personalized recommendations
- Intelligent cart optimization
- Automated inventory management
- Predictive logistics
- Smart campaign optimization

---

## 🛠️ Development & Testing

### Framework Layers
- **lib/**: adapters, agent builder, FastAPI/MCP helpers, and memory layers
  - Hot memory: Redis for fast context/state
  - Warm memory: Azure Cosmos DB for structured session/profile data (prefer high-cardinality keys and hierarchical partition keys to minimize cross-partition scans)
  - Cold memory: Azure Blob Storage for long-lived artifacts
  - Search: Azure AI Search for hybrid/vector retrieval
  - Messaging: Event Hubs hooks for SAGA-style flows
- **apps/**: domain services (ecommerce, product, CRM, inventory, logistics) using the framework via app_factory
- **utils/config**: shared logging, retry, settings wiring

### Installation
```bash
# Install framework
pip install -e lib

# Install specific service
pip install -e apps/<service>/src
```

### Local Development
```bash
# Run a service locally
uvicorn main:app --app-dir apps/<service>/src --reload

# Check health
curl http://localhost:8000/health
```

### Testing
```bash
# Run tests with coverage
pytest

# Minimum coverage: 75%
pytest --cov=lib --cov=apps --cov-report=html
```

### Code Quality
```bash
# Format code
black lib apps
isort lib apps

# Lint code
pylint lib/src apps/**/src
```

---

## 🚀 Infrastructure & Deployment

### Infrastructure as Code
- Bicep modules in `.infra/modules`
- Per-service entrypoints in `.infra/*.bicep`
- Typer CLI for deployments:

```bash
# Deploy single service
python -m .infra.cli deploy <service> --location <region> --version <release> \
  [--subscription-id <sub>] [--resource-group <rg>]

# Deploy all services
python -m .infra.cli deploy_all --location <region> --version <release>
```

**Note**: RG defaults to `<service>-rg`. Deployments are subscription-scoped and resources are named `appname-azureservicename-version` (storage accounts strip hyphens).

### Kubernetes
- Helm chart in `.kubernetes/chart` for AKS + KEDA
- Fill in image names, env vars, autoscaling triggers in `values.yaml`

### CI/CD
- **GitHub Actions**: Automated build, test, security scanning, and deployment
- **Develop Branch**: Auto-deploy to dev environment
- **Tags**: Canary deployment to production with gradual traffic shift
- **Security Scanning**: Trivy image scans (HIGH/CRITICAL) before GHCR push and weekly scan of published images with SARIF upload

---

## 🔗 Quick Links

### For Developers
- [Implementation Roadmap](IMPLEMENTATION_ROADMAP.md) - Current status and next steps
- [CRUD Service Documentation](architecture/crud-service-implementation.md) - Backend implementation details
- [Components Documentation](architecture/components.md) - All framework and service components
- [Frontend Component Library](../apps/ui/components/COMPONENT_README.md) - Component API reference
- [Playbooks](architecture/playbooks/) - Operational procedures

### For Architects
- [ADRs Index](architecture/ADRs.md) - All 20 architectural decisions
- [Architecture Overview](architecture/architecture.md) - System design and context
- [Sequence Diagrams](architecture/diagrams/) - Key flows
- [Test Plans](architecture/test-plans/) - Load and resilience testing

### For Product Managers
- [Business Summary](architecture/business-summary.md) - Requirements and use cases

---

## 📊 Metrics & Goals

### Code Quality
- **Test Coverage**: 75% minimum (current: varies by service)
- **Linting**: Passing (black, isort, pylint, ESLint)
- **Type Safety**: 100% (mypy for Python, TypeScript for frontend)

### Performance
- **API Response Time (p95)**: < 500ms
- **Frontend Load Time**: < 2s
- **Cosmos DB RU**: < 10,000 RU/s per container
- **Availability**: 99.9% SLA

### Security
- **Zero Secrets in Code**: 100% compliance
- **Security Vulnerabilities**: None critical/high
- **Private Endpoints**: 100% backend services
- **WAF Protection**: Enabled on all public endpoints

---

## 🆘 Support & Resources

- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Documentation**: This repository
- **Azure Support**: [Azure Portal](https://portal.azure.com)

---

**Note**: This is a living document. Architecture evolves based on learnings and requirements. All major changes are documented via ADRs.
