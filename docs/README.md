# Holiday Peak Hub - Architecture Documentation

**Last Updated**: April 12, 2026
**Version**: main (post PR #802)  
**Status**: Active Development

## Latest Update Snapshot (April 12, 2026)

- **FoundryAgentInvoker** replaces legacy `FoundryInvoker` (PR #802 / Issue #801): agent tools are now properly forwarded through the Microsoft Agent Framework `FoundryAgent` runtime. `agent-framework` upgraded to `>=1.0.1` GA across all 27 Python services.
- Memory tier reads/writes parallelized via `asyncio.gather` (PR #800): concurrent hot/warm/cold I/O reduces agent memory latency. New memory tools (`get_memory`, `set_memory`, `search_memory`) and `gather_adapters` helper added.
- Catalog-search I/O parallelized and duplicate keyword search eliminated (PR #796).
- CRUD_SERVICE_URL port corrected from 8000 to 80 for all agent deployments in AKS (PR #794).
- Flux CD Phase B complete (PR #792): kubectl-apply removed, full GitOps reconciliation via Flux.
- API Center governance, sync pipeline, and APIM MCP strategy added (PR #789 / ADR-035).
- Namespace isolation (PR #788 / ADR-034): CRUD and agent services now run in separate Kubernetes namespaces.
- AKS deployments migrated to Flux CD GitOps (PR #785 / ADR-033).
- Self-healing epic complete (PR #771): incident lifecycle kernel, remediation policy, and audit trail across all agent surfaces.
- CRUD Entra ID auth rollout contracts hardened (PR #776).
- Validation status: **1796 tests passed** (1136 lib + 660 app), 0 failures.
- 35 Architecture Decision Records (ADR-001 through ADR-035).

## Overview

Holiday Peak Hub is a **cloud-native, agent-driven retail accelerator** with complete frontend implementation and comprehensive backend architecture plan. This documentation covers all architectural decisions, implementation plans, and operational procedures.

## Developer Tooling

Repository-maintained automation scripts are available under [../scripts/ops](../scripts/ops) and [../scripts/ci](../scripts/ci).

Per-app local run/test commands are documented in each service README under [../apps](../apps) (for example [../apps/ecommerce-catalog-search/README.md](../apps/ecommerce-catalog-search/README.md)).

Python package management in this repository is uv-first. In CI, dependency installs use `uv pip --system`; use pip only as a compatibility bootstrap path to install uv.

- Run tests: `python -m pytest`
- Run lint: `python -m pylint lib/src apps/**/src`
- Run format: `python -m black lib apps && python -m isort lib apps`
- App smoke tests under `apps/**/tests/test_app.py` can use the shared fixture in `apps/conftest.py` to satisfy Foundry readiness when exercising local business-route behavior for services that set `require_foundry_readiness=True`.

## Infrastructure CLI

Provisioning and deployment use the azd project defined in `azure.yaml`.
The Python CLI in `.infra/cli.py` is scaffolding-only (`generate-bicep`, `generate-dockerfile`).

### Service-scoped deployment wrappers

In addition to the shared environment entrypoints, the repository supports thin service-scoped GitHub workflow wrappers for agent-by-agent deployment operations. These wrappers forward to the reusable azd deployment engine and can target an explicit branch or commit SHA without first merging to `main`.

Push-triggered service and UI wrapper runs now use GitHub Environment `branch` as the non-protected deployment context while still targeting the selected Azure environment. Azure federated credentials for these preview paths must trust the environment-scoped OIDC subject for `branch`, not only `ref:refs/heads/*` subjects. This keeps feature-branch validation unblocked without weakening the protected `dev` live-validation boundary or the protected production release path.

When a non-prod wrapper run targets a non-default `refs/heads/*` source, the reusable workflow temporarily repoints `GitRepository/holiday-peak-gitops` in `flux-system` to that branch, verifies Flux fetched the preview revision, waits only for the AGC-relevant Flux kustomization to record that preview revision while honoring that live kustomization's configured Flux timeout window, evaluates AGC readiness against the live gateway, and then restores the repository default branch in an always-run cleanup job. This preview-preparation step is intentionally decoupled from unrelated CRUD workload readiness in the wider kustomization; the later AGC readiness gate remains strict.
When that AGC readiness gate runs, it validates the live shared `ApplicationLoadBalancer/holiday-peak-agc`, confirms Azure traffic-controller health in the AKS node resource group, checks the CRUD-owned `Gateway/holiday-peak-agc` binding contract in `holiday-peak-crud`, verifies shared-Gateway parent attachment for CRUD plus changed-agent `HTTPRoute` resources, and only then enters the direct frontend health loop against the approved AGC hostname.

Examples:

```bash
gh workflow run deploy-azd-ecommerce-catalog-search.yml -f environment=dev -f testedSourceRef=refs/heads/feature/123-catalog-update
gh workflow run deploy-azd-truth-enrichment.yml -f environment=dev -f testedSourceSha=<commit-sha>
gh workflow run deploy-ui-swa.yml -f environment=dev -f sourceRef=refs/heads/feature/123-ui-update
```

### Deployment Runbook (GitHub Actions + azd)

Use environment-specific entry workflows:

- `.github/workflows/deploy-azd-dev.yml` as the default development path (auto-runs after successful `test` workflow completion for a push to `main` and supports manual dispatch).
- `.github/workflows/deploy-azd-prod.yml` for production deployments triggered only by stable release tags (`v*.*.*` without pre-release suffixes) that also have a published GitHub Release and point to a commit reachable from `main`.
- `.github/workflows/deploy-azd.yml` remains the shared core workflow invoked by both entry workflows.
- `.github/workflows/protected-dev-live-agent-readiness.yml` runs protected live validation against dev after successful `deploy-azd-dev` runs on `main`, or by explicit manual/scheduled execution through the `dev` environment boundary.
- `.github/workflows/ci.yml` publishes GHCR images automatically for stable tags (`v*.*.*`) and can still be run manually for build/optional publish.

> Provisioning remains the default path for all automatic deploys and normal manual rollouts. The only approved exception is a manual dev emergency redeploy through `deploy-azd-dev.yml` with `skipProvision=true`, which reuses the current azd environment values and already-provisioned infrastructure while still running the reusable workflow's auth, guard, build, deploy, and smoke paths.

**Required repository/environment secrets**:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`

The OIDC deploy principal behind `AZURE_CLIENT_ID` must be allowed to manage the environment-scoped RBAC assignments used by the reusable deployment workflow. `deploy-azd.yml` now idempotently verifies `Azure Kubernetes Service RBAC Cluster Admin` on the environment resource group and `AcrPush` on the environment ACR before tested-image builds start.

For the protected live suite, store these values in the GitHub Environment `dev` and keep Azure authentication OIDC-only. Do not add client secrets, connection strings, or API keys for live validation.

Repository code establishes this environment-scoped secret boundary. The `dev` environment must remain configured with selected-branch deployment protection on `main`.

**Entry workflow inputs**:

- Dev entrypoint (`deploy-azd-dev.yml`): `location`, `projectName`, `imageTag`, `testedSourceSha`, `testedSourceRef`, `skipProvision`, `serviceFilter`, `deployStatic`, `uiOnly`, `apiBaseUrl`, `forceApimSync`, `autoAllowAcrRunnerIp`, `skipApiSmokeChecks`.
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

- Manual dev emergency redeploy on already-provisioned infrastructure, scoped to a subset of AKS services:

```bash
gh workflow run deploy-azd-dev.yml -f location=eastus2 -f projectName=holidaypeakhub405 -f imageTag=latest -f skipProvision=true -f serviceFilter=ecommerce-catalog-search -f forceApimSync=true -f autoAllowAcrRunnerIp=true
```

Use this only when dev infrastructure already exists and the immediate goal is to redeploy specific runtime changes without reconciling shared infrastructure.

- Production rollout (stable release tag + published GitHub Release):

```bash
git tag v1.2.3
git push origin v1.2.3
```

Then publish a GitHub Release for `v1.2.3`. The production workflow validates release existence before deploying.

Core workflow note: `.github/workflows/deploy-azd.yml` is reusable-only and not intended for direct manual dispatch.

**Execution order**:

1. `provision` job: sets azd env values, runs `azd provision`, and idempotently ensures the OIDC deploy principal has `Azure Kubernetes Service RBAC Cluster Admin` on the environment resource group plus `AcrPush` on the environment ACR.
2. `build-aks-images` job: builds changed AKS workloads from the tested source SHA into the existing ACR (or reuses an existing per-SHA image), retries `az acr login` with bounded backoff to absorb RBAC propagation delay, and then records immutable digest refs for downstream deploy jobs. When `autoAllowAcrRunnerIp=true`, the workflow also reuses the existing runner-IP allowlist path; if the ACR public endpoint is disabled, it first enables public access with `defaultAction=Deny`, adds only the active GitHub-hosted runner IP, and restores the original public-access setting after the build phase. This is required because disabling ACR public network access overrides firewall rules, and GitHub-hosted runners do not have private network line of sight to a private-only registry.
3. `deploy-crud` job: renders and applies the `crud-service` Helm manifest pinned to the tested image digest when CRUD/lib changes are detected.
4. `deploy-foundry-models` and `deploy-agents` jobs: run after provision; `deploy-agents` deploys changed agent services from prebuilt digest-pinned manifests (and can proceed when `deploy-crud` is skipped for agent-only changes).
5. `ensure-foundry-agents` job: re-renders changed agent manifests with the workflow's strict/auto-ensure contract, compares rendered env values against live AKS Deployments, then validates `POST /foundry/agents/ensure` plus `/ready` for each changed agent service.
6. `commit-rendered-manifests` job: republishes rendered GitOps manifests back to the tested branch when wrapper-driven AKS deployments change Flux-managed services.
7. `wait-flux-reconciliation` and `validate-agc-readiness` jobs: branch-preview validation first reconciles Flux against the published preview branch, then confirms the preview source plus the AGC-relevant Flux kustomization have recorded the tested revision without coupling that preparation step to unrelated CRUD workload readiness, resolves the approved AGC hostname from azd outputs, the ALB frontend in the environment RG or AKS node RG, or the live shared Gateway status address after AKS credentials are available, validates the live shared `ApplicationLoadBalancer` contract plus Azure traffic-controller health, checks the live shared Gateway binding contract (`alb.networking.azure.io/alb-name`, `alb.networking.azure.io/alb-namespace`) plus `Accepted=True`, `Programmed=True`, and an assigned status address, requires shared-Gateway parent attachment for CRUD and changed-agent `HTTPRoute` resources, and only then probes direct AGC CRUD plus changed-agent health before APIM sync.
8. `sync-apim` and `smoke-apim` jobs: run when CRUD/agent changes are present or `forceApimSync=true`.
9. `deploy-ui` job (when `deployStatic=true`): runs after APIM sync/smoke gates, resolves APIM URL with fail-fast validation, fetches the SWA deployment token from Azure, and deploys `apps/ui` via `Azure/static-web-apps-deploy@v1` (framework-aware build for dynamic Next.js routes).
10. Demo data seeding is operator-driven and must be run locally (outside CI) when needed.

**Operational notes**:

- Keep `deployShared=true` for all shared-environment rollouts.
- Dev AKS rollouts must use the tested source checkout plus immutable image digests (`repo@sha256:...`); deploy jobs render/apply Kubernetes manifests directly and must not rebuild service images inline.
- `skipProvision=true` is a manual dev-only emergency path for already-provisioned infrastructure. It skips only the `azd provision` step; Azure login, azd environment setup, AKS/ACR/Key Vault guards, output export, image build, deploy, Foundry ensure, and downstream smoke/deploy gates remain active.
- For GitHub-hosted tested-image builds, `autoAllowAcrRunnerIp=true` preserves OIDC-only auth and the existing ACR IP allowlist flow. If the environment registry is private-only (`publicNetworkAccess=Disabled`), the workflow temporarily reopens the public endpoint with `defaultAction=Deny`, scopes access to the current runner IP, and restores the original ACR public-access state immediately after the build phase.
- For changed AKS agent services, treat the Foundry runtime contract as a blocking gate: expected `FOUNDRY_STRICT_ENFORCEMENT=true` and `FOUNDRY_AUTO_ENSURE_ON_STARTUP=true` must survive render and rollout, and `/ready` is only accepted when it matches successful Foundry ensure results.
- UI deployment intentionally uses the SWA GitHub Action path (not `azd deploy --service ui`) so App Router dynamic segments (`[id]`, `[slug]`) are built in the same mode as standard SWA workflows.
- Frontend API calls must always use APIM via validated runtime env aliases (`NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_CRUD_API_URL` are set together in deployment workflows).
- Demo seeding uses a curated catalog of 10 categories and 100 products with realistic retail data. Re-runs are idempotent by item ID (`cat-*`, `prd-*`): existing seeded records are updated instead of duplicated.
- Use GitHub Environment protection rules for privileged `dev` validation and for `staging`/`prod` deployment paths; for `dev`, selected-branch deployment protection on `main` is required.
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
- Keep `protected-dev-live-agent-readiness.yml` limited to trusted triggers and the `dev` environment boundary; do not add it as a required PR check.
- Preserve changed-service deployment and APIM sync/smoke behavior per environment defaults.
- Run lint/test quality gates before deployment (repo minimum 75% coverage).
- Verify canonical event schema compatibility before rollout whenever governed retail or connector event contracts change (`python scripts/ops/check_event_schema_contracts.py`).
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

When ACR `publicNetworkAccess` is disabled, firewall rules are ignored until the public endpoint is re-enabled. GitHub-hosted runners and local operators without private network line of sight must temporarily reopen the registry before an IP allowlist can take effect.

```bash
az acr update -n <acrName> --allow-exports true
az acr update -n <acrName> --public-network-enabled true --default-action Deny
az acr network-rule add -n <acrName> --ip-address <PUBLIC_IP>/32
```

5. **Deploy CRUD service through azd (Helm-driven AKS deploy)**

```bash
azd deploy --service crud-service --no-prompt -e dev
```

For Entra-only PostgreSQL authentication in CRUD, set these `azd` environment values before `azd provision` or `azd deploy`. `POSTGRES_AUTH_MODE` now drives both the shared-infrastructure PostgreSQL auth policy and the CRUD runtime outputs used by Helm rendering:

```bash
azd env set POSTGRES_AUTH_MODE entra
azd env set POSTGRES_USER <crud-workload-identity-name>
azd env set POSTGRES_PASSWORD ""
```

6. **Deploy UI through the azd dev entry workflow (SWA action path)**

```bash
gh workflow run deploy-azd-dev.yml -f location=eastus2 -f projectName=holidaypeakhub405 -f imageTag=latest -f deployStatic=true -f uiOnly=true -f forceApimSync=false -f autoAllowAcrRunnerIp=true
```

This preserves the current governance path for UI rollout and avoids direct `azd deploy --service ui` usage.

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
- **[Per-Agent azd Deployment Guide](implementation/per-agent-azd-deployment.md)** - Dependency-aware deployment flow for one specific agent service using shared IaC.
- **[Single RG Deployment Runbook](implementation/single-rg-deployment-runbook.md)** - Fast provision/recover/deprovision operations for `holidaypeakhub405-dev-rg`

### Governance

- **[Repository Hygiene Cleanup Runbook](governance/repository-hygiene-cleanup.md)** - Procedure to clean Issues/PRs and enforce main-only local and remote branches.

### Architecture Documentation

**Frontend Architecture**: The production-ready frontend (13 pages, 52 components) is fully documented in the [Components Documentation](architecture/components.md) and governed by 6 frontend-specific ADRs ([ADR-015](architecture/adrs/adr-015-nextjs-app-router.md) through [ADR-020](architecture/adrs/adr-020-api-client-architecture.md)).

### Core Documentation

- **[Architecture Overview](architecture/architecture.md)** - System context and high-level design
- **[Business Summary](architecture/business-summary.md)** - Business requirements and use cases
- **[Components Documentation](architecture/components.md)** - All framework and service components
- **[ADRs (Architecture Decision Records)](architecture/ADRs.md)** - Index of architectural decisions
- **[Agentic Microservices Reference](agentic-microservices-reference.md)** - Why this is a reference architecture for agentic microservices on Azure
- **[MAF Integration Rationale](architecture/maf-integration-rationale.md)** - Why Microsoft Agent Framework is wrapped inside the lib
- **[Solution Architecture Diagrams](architecture/solution-architecture-diagrams.md)** - Per-domain Mermaid diagrams (system context, container, 7 domains, data flow)
- **[Standalone Deployment Guide](architecture/standalone-deployment-guide.md)** - How to deploy a single agent service to AKS
- **[Test Coverage Gap Analysis](architecture/test-coverage-gap-analysis.md)** - Coverage gaps, patterns, and remediation plan

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
**Status**: ✅ CRUD Service Complete, ✅ 26 Agent Services Complete

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

**Agent Services** (26):
- E-Commerce (5): catalog-search, product-detail-enrichment, cart-intelligence, checkout-support, order-status
- Product Management (4): normalization-classification, acp-transformation, consistency-validation, assortment-optimization
- CRM (4): profile-aggregation, segmentation-personalization, campaign-intelligence, support-assistance
- Inventory (4): health-check, jit-replenishment, reservation-validation, alerts-triggers
- Logistics (4): eta-computation, carrier-selection, returns-support, route-issue-detection
- Search (1): search-enrichment-agent
- Truth Layer (4): truth-ingestion, truth-enrichment, truth-hitl, truth-export

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
