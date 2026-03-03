# Implementation Roadmap

**Last Updated**: March 3, 2026  
**Version**: [v1.1.0](https://github.com/Azure-Samples/holiday-peak-hub/releases/tag/v1.1.0)  
**Status**: Phase 1 Complete | Phase 2 Complete | Truth Layer Phase 1-2 Complete | Enterprise Connectors Active

---

## Overview

This document tracks the implementation progress of the Holiday Peak Hub platform. The CRUD service, frontend integration, 21 AI agents, and shared infrastructure (Bicep) are complete. v1.1.0 adds enterprise system connectors (Oracle, Salesforce, SAP, Dynamics 365), the Product Truth Layer foundation, HITL review system, and enterprise hardening patterns (circuit breaker, bulkhead, rate limiter).

> **Known Issues**: See [docs/roadmap/](roadmap/) for tracked corrections and gaps discovered during deployment validation.
> 
> **Enterprise Integration**: See [docs/roadmap/011-retail-system-integration-strategy.md](roadmap/011-retail-system-integration-strategy.md) for the comprehensive connector strategy based on retail capabilities research.

---

## Completed Work ✅

### v1.1.0 Features (March 2026)

#### Product Truth Layer (Foundation)
- ✅ **Phase 1**: Pydantic v2 data models (`TruthAttribute`, `ProposedAttribute`, `GapReport`, `AuditEvent`, `ProductStyle`, `ProductVariant`)
- ✅ **Phase 2**: Truth Ingestion service with Cosmos DB integration
- ✅ Sample data, category schemas, and seeding scripts
- ✅ Cosmos DB container population for Truth Layer

#### Enterprise System Connectors
- ✅ **Oracle Fusion Cloud SCM** (`lib/connectors/inventory_scm/oracle_scm/`)
  - OAuth 2.0 authentication with JWKS
  - Inventory, Purchase Orders, Shipments endpoints
  - Canonical model field mappings
- ✅ **Salesforce CRM & Marketing Cloud** (`lib/connectors/crm_loyalty/salesforce/`)
  - OAuth 2.0 + refresh token authentication
  - Contacts, Accounts, Leads, Campaigns endpoints
  - Bi-directional sync capabilities
- ✅ **SAP S/4HANA Inventory & SCM**
  - OData v4 with SAP authentication
  - Material master, inventory positions, purchase orders
- ✅ **Dynamics 365 Customer Engagement**
  - Dataverse Web API integration
  - Contact, Account, Opportunity, Case entities
- ✅ **Generic REST DAM** (`lib/integrations/dam_generic.py`)
  - Configurable endpoint mapping
  - OAuth/API key authentication

#### Enterprise Hardening (PR #110)
- ✅ **Circuit Breaker** (`lib/utils/circuit_breaker.py`) — Failure isolation with recovery
- ✅ **Bulkhead Pattern** (`lib/utils/bulkhead.py`) — Resource isolation
- ✅ **Rate Limiter** (`lib/utils/rate_limiter.py`) — Token bucket algorithm
- ✅ **Telemetry** (`lib/utils/telemetry.py`) — OpenTelemetry integration
- ✅ **Health Probes** — Kubernetes liveness/readiness enhanced

#### PIM Writeback Module (PR #107)
- ✅ Opt-in tenant configuration (`TenantConfig`)
- ✅ Circuit breaker protection for PIM APIs
- ✅ Conflict detection with version comparison
- ✅ Audit trail for all writeback operations

#### HITL Staff Review UI (PR #103)
- ✅ Review queue page (`/staff/review`) with filtering and pagination
- ✅ Entity detail review (`/staff/review/[entityId]`) with side-by-side comparison
- ✅ UI components: `ReviewQueueTable`, `ProposalCard`, `ConfidenceBadge`, `CompletenessBar`, `AuditTimeline`
- ✅ React hooks: `useReviewQueue`, `useProductReview`, `useReviewActions`

#### Admin UI for Truth Layer
- ✅ Schema management (`/admin/schemas`)
- ✅ Tenant configuration (`/admin/config`)
- ✅ Analytics dashboard (`/admin/analytics`)

#### Frontend Enhancements
- ✅ Stripe checkout integration (real payments)
- ✅ Dashboard and profile pages with live API hooks
- ✅ Server-side route protection (Next.js middleware)
- ✅ Entra ID configuration documentation

#### Testing & Quality
- ✅ **508 tests passing** (↑343 from v1.0.0)
- ✅ Connector test suites (Oracle: 48 tests, Salesforce: 48 tests)
- ✅ Enterprise hardening tests (circuit breaker, bulkhead, rate limiter, telemetry)
- ✅ PIM writeback tests (25 tests)

---

### Phase 1: Foundation & Core Services (v1.0.0)

#### 1.1 Shared Infrastructure (Bicep Modules)
- ✅ Created `.infra/modules/shared-infrastructure/`
  - Single AKS cluster (3 node pools: system, agents, crud)
  - Azure Container Registry (Premium, geo-replication)
  - Cosmos DB account (10 operational containers + agent memory)
  - Event Hubs namespace (5 topics)
  - Redis Cache Premium (6GB)
  - Azure Storage Account
  - Azure Key Vault
  - Azure API Management (Consumption/StandardV2)
  - Application Insights + Log Analytics
  - Virtual Network with Private Endpoints
  - Network Security Groups
  - RBAC role assignments (Managed Identity)
- ✅ Created `.infra/modules/static-web-app/`
  - Azure Static Web Apps configuration
  - GitHub Actions integration
  - Custom domain support
  - Environment variables

#### 1.2 CRUD Service (Backend)
- ✅ **Complete**: 31 REST endpoints across 15 route modules
- ✅ FastAPI application with lifespan management
- ✅ Microsoft Entra ID JWT validation + RBAC (4 roles)
- ✅ Repositories: Base + User, Product, Order, Cart
- ✅ Routes: health, auth, users, products, categories, cart, orders, checkout, payments, reviews
- ✅ Staff routes: analytics, tickets, returns, shipments
- ✅ Event Hubs publisher (5 topics)
- ✅ MCP agent client integration
- ✅ Test structure (unit, integration, e2e)
- ✅ Dockerfile with Python 3.13
- ✅ Environment configuration

**Endpoints**:
- Anonymous (7): Health checks, product browsing, categories
- Customer (18): Cart, orders, reviews, profile, checkout, payments
- Staff (4): Analytics, tickets, shipments
- Admin (2): Returns processing

**Database Containers** (Cosmos DB):
1. Users - User profiles, addresses, payment methods
2. Products - Product catalog (ACP-compliant)
3. Orders - Order headers
4. OrderItems - Order line items
5. Cart - Shopping carts
6. Reviews - Product reviews
7. PaymentMethods - Saved payment methods
8. Tickets - Support tickets
9. Shipments - Shipment tracking
10. AuditLogs - Audit trail

**Event Topics** (Event Hubs):
1. user-events - Registration, profile updates
2. product-events - CRUD operations
3. order-events - Placed, status changed, cancelled
4. inventory-events - Stock updates
5. payment-events - Success, failure

#### 1.3 Frontend API Integration
- ✅ TypeScript API client (Axios with JWT interceptors)
- ✅ 6 service modules: product, cart, order, auth, user, checkout
- ✅ 5 React Query hooks with cache invalidation
- ✅ Microsoft Entra ID authentication (MSAL, SSR-safe)
- ✅ Type definitions matching backend Pydantic models
- ✅ Environment configuration
- ✅ Next.js 16.2.0-canary configuration
- ✅ Tailwind CSS 3.4.0 setup
- ✅ PostCSS configuration
- ✅ Complete integration documentation

#### 1.4 Agent Services
- ✅ 21 AI agent services implemented
- ✅ Agent framework (`holiday_peak_lib`)
- ✅ Three-tier memory (hot/warm/cold)
- ✅ MCP exposition for inter-agent communication
- ✅ Dockerfiles for each agent

**Agent Categories**:
- E-Commerce (5): catalog-search, product-detail-enrichment, cart-intelligence, checkout-support, order-status
- Product Management (4): normalization-classification, acp-transformation, consistency-validation, assortment-optimization
- CRM (4): profile-aggregation, segmentation-personalization, campaign-intelligence, support-assistance
- Inventory (4): health-check, jit-replenishment, reservation-validation, alerts-triggers
- Logistics (4): eta-computation, carrier-selection, returns-support, route-issue-detection

---

## Pending Work 📋

### Phase 2: Infrastructure Deployment

#### 2.1 Deploy Shared Infrastructure
**Priority**: CRITICAL  
**Estimated Time**: 2-4 hours

**Tasks**:
- [ ] Create Azure resource group
- [ ] Deploy shared infrastructure Bicep module:
  ```bash
  az deployment sub create \
    --location eastus \
    --template-file .infra/modules/shared-infrastructure/shared-infrastructure-main.bicep \
    --parameters environment=dev
  ```
- [ ] Verify all resources created successfully
- [ ] Test connectivity (Private Endpoints)
- [ ] Validate RBAC assignments (Managed Identity permissions)

**Expected Resources**:
- AKS cluster (3 node pools, 6 nodes total)
- Cosmos DB account (10 containers)
- Event Hubs namespace (5 topics)
- Redis Cache Premium
- Storage Account
- Key Vault
- ACR
- APIM
- VNet + NSGs
- Application Insights

#### 2.2 Microsoft Entra ID Configuration
**Priority**: CRITICAL  
**Estimated Time**: 1-2 hours

**Tasks**:
- [ ] Create Entra ID app registration for backend
- [ ] Configure redirect URIs
- [ ] Create app roles (anonymous, customer, staff, admin)
- [ ] Assign users to roles for testing
- [ ] Update backend `.env` with client ID, tenant ID
- [ ] Update frontend `.env.local` with client ID, tenant ID
- [ ] Test authentication flow (login → token → API call)

#### 2.3 Deploy CRUD Service to AKS
**Priority**: HIGH  
**Estimated Time**: 2-3 hours

**Tasks**:
- [ ] Build Docker image:
  ```bash
  docker build -t crud-service:latest apps/crud-service
  ```
- [ ] Tag and push to ACR:
  ```bash
  docker tag crud-service:latest <acr-name>.azurecr.io/crud-service:latest
  docker push <acr-name>.azurecr.io/crud-service:latest
  ```
- [ ] Create Kubernetes deployment manifest
- [ ] Create Kubernetes service (ClusterIP)
- [ ] Create HPA (3-20 replicas)
- [ ] Deploy to AKS:
  ```bash
  kubectl apply -f .kubernetes/crud-service/
  ```
- [ ] Verify pods running: `kubectl get pods -n default`
- [ ] Test health endpoint: `kubectl port-forward svc/crud-service 8000:8000`

#### 2.4 Deploy Static Web App
**Priority**: HIGH  
**Estimated Time**: 1-2 hours

**Tasks**:
- [ ] Deploy Static Web App Bicep module:
  ```bash
  az deployment sub create \
    --location eastus2 \
    --template-file .infra/modules/static-web-app/static-web-app-main.bicep \
    --parameters environment=dev
  ```
- [ ] Configure GitHub Actions workflow
- [ ] Add deployment token to GitHub secrets
- [ ] Update `next.config.js` for static export
- [ ] Trigger deployment via git push
- [ ] Verify deployment successful
- [ ] Test frontend: `https://<swa-name>.azurestaticapps.net`

#### 2.5 Deploy Agent Services to AKS
**Priority**: MEDIUM  
**Estimated Time**: 4-6 hours

**Tasks**:
- [ ] Build Docker images for all 21 agents
- [ ] Push images to ACR
- [ ] Create Kubernetes deployment manifests
- [ ] Deploy agents to AKS (agents node pool)
- [ ] Configure KEDA autoscaling (Event Hubs triggers)
- [ ] Verify agents receiving events
- [ ] Test agent MCP endpoints

### Phase 3: Event-Driven Integration

#### 3.1 Complete Event Subscriptions
**Priority**: HIGH  
**Estimated Time**: 2-3 hours

**Tasks**:
- [ ] Configure Event Hubs consumer groups for each agent
- [ ] Implement event handlers in agents:
  - CRM agents → Subscribe to `user-events`, `order-events`
  - Inventory agents → Subscribe to `order-events`, `inventory-events`
  - Logistics agents → Subscribe to `order-events`
  - Product agents → Subscribe to `product-events`
- [ ] Add error handling and retry logic
- [ ] Implement dead-letter queue processing
- [ ] Test end-to-end event flow

#### 3.2 Agent MCP Integration
**Priority**: MEDIUM  
**Estimated Time**: 2-3 hours

**Tasks**:
- [ ] Update CRUD service to call agent MCP endpoints:
  - Product enrichment → `product-detail-enrichment` agent
  - Cart intelligence → `cart-intelligence` agent
  - Checkout validation → `checkout-support` agent
- [ ] Implement fallback logic (if agent unavailable)
- [ ] Add circuit breaker pattern
- [ ] Test agent calls with timeouts
- [ ] Monitor agent latency in Application Insights

### Phase 4: Testing & Validation

#### 4.1 Complete Test Implementation
**Priority**: MEDIUM  
**Estimated Time**: 3-4 hours

**Tasks**:
- [ ] Implement Cosmos DB test mocks in `conftest.py`
- [ ] Implement Event Hubs test mocks
- [ ] Complete unit tests for all repositories
- [ ] Complete integration tests for all API routes
- [ ] Run full test suite: `pytest --cov=crud_service`
- [ ] Achieve 75%+ code coverage
- [ ] Fix failing tests

#### 4.2 E2E Testing
**Priority**: MEDIUM  
**Estimated Time**: 2-3 hours

**Tasks**:
- [ ] Set up Playwright or Cypress
- [ ] Create E2E test scenarios:
  - User registration → login → browse → add to cart → checkout
  - Staff login → view analytics → manage tickets
  - Admin login → process returns
- [ ] Run E2E tests against deployed environment
- [ ] Document test results

### Phase 5: Monitoring & Observability

#### 5.1 Application Insights Configuration
**Priority**: MEDIUM  
**Estimated Time**: 1-2 hours

**Tasks**:
- [ ] Verify telemetry flowing to Application Insights
- [ ] Create custom dashboards:
  - CRUD service: Request rate, latency, errors
  - Agents: Event processing rate, MCP call latency
  - Frontend: Page load times, API errors
- [ ] Set up alerts:
  - Error rate > 5% for 5 minutes
  - p99 latency > 1 second
  - RU consumption > 80%
- [ ] Configure availability tests

#### 5.2 Grafana Dashboards
**Priority**: LOW  
**Estimated Time**: 2-3 hours

**Tasks**:
- [ ] Deploy Grafana to AKS
- [ ] Connect to Application Insights
- [ ] Create dashboards for each service
- [ ] Add Cosmos DB RU metrics
- [ ] Add Event Hubs throughput metrics

### Phase 6: Performance Optimization

#### 6.1 Load Testing
**Priority**: MEDIUM  
**Estimated Time**: 2-3 hours

**Tasks**:
- [ ] Set up k6 or Locust
- [ ] Create load test scenarios:
  - Product browsing (100 RPS)
  - Cart operations (50 RPS)
  - Checkout flow (25 RPS)
- [ ] Run load tests against dev environment
- [ ] Identify bottlenecks
- [ ] Optimize queries, indexes, caching

#### 6.2 Cosmos DB Optimization
**Priority**: MEDIUM  
**Estimated Time**: 1-2 hours

**Tasks**:
- [ ] Review indexing policies
- [ ] Optimize partition keys
- [ ] Implement query result caching (Redis)
- [ ] Tune RU provisioning
- [ ] Add retry logic for 429 errors

### Phase 7: Security Hardening

#### 7.1 Network Security
**Priority**: HIGH  
**Estimated Time**: 1-2 hours

**Tasks**:
- [ ] Verify Private Endpoints for all PaaS services
- [ ] Verify no public IPs exposed
- [ ] Test NSG rules
- [ ] Enable Azure DDoS Protection (optional)

#### 7.2 Secrets Management
**Priority**: CRITICAL  
**Estimated Time**: 1 hour

**Tasks**:
- [ ] Migrate all secrets to Key Vault
- [ ] Remove hardcoded credentials
- [ ] Test Managed Identity access
- [ ] Rotate Stripe API keys

#### 7.3 APIM Policies
**Priority**: HIGH  
**Estimated Time**: 2-3 hours

**Tasks**:
- [ ] Configure JWT validation policy
- [ ] Add rate limiting (100 req/min per user)
- [ ] Add IP filtering (optional)
- [ ] Configure CORS policies
- [ ] Test APIM policies

---

## TODO Items in Existing Code

### CRUD Service Routes

#### payments.py
- [ ] Complete Stripe PaymentIntent retrieval
- [ ] Add webhook handler for payment confirmation
- [ ] Test payment flow with test card

#### staff/analytics.py
- [ ] Implement aggregation queries for sales metrics
- [ ] Add time-series data (daily/weekly/monthly)
- [ ] Cache analytics results (Redis, 5 min TTL)

#### checkout.py
- [ ] Add inventory validation (call inventory agents)
- [ ] Add address validation (geocoding API)
- [ ] Implement fraud detection (optional)

### Frontend Pages

#### app/page.tsx (Homepage)
- [ ] Replace mock data with API calls
- [ ] Use `useProducts({ category: 'featured' })`
- [ ] Add loading skeletons

#### app/product/[id]/page.tsx
- [ ] Use `useProduct(id)` hook
- [ ] Add error boundary
- [ ] Add breadcrumbs

#### app/checkout/page.tsx
- [ ] Integrate with `useCheckout()` hook
- [ ] Add Stripe Elements
- [ ] Test payment flow

#### app/order/[id]/page.tsx
- [ ] Use `useOrder(id)` and `useTrackOrder(id)` hooks
- [ ] Add shipment tracking map (optional)

---

### Phase 8: Enterprise Connector Integration

> **Reference**: See [docs/roadmap/011-retail-system-integration-strategy.md](roadmap/011-retail-system-integration-strategy.md) for full details.

#### 8.1 Connector Registry Implementation
**Priority**: HIGH  
**Estimated Time**: 3-4 hours  
**Issue**: [#79](https://github.com/Azure-Samples/holiday-peak-hub/issues/79)

**Tasks**:
- [ ] Implement ConnectorRegistry in `lib/src/holiday_peak_lib/integrations/`
- [ ] Add connector health monitoring with circuit breakers
- [ ] Create configuration loader for connector settings
- [ ] Integrate with CRUD service as central hub
- [ ] Write unit and integration tests

#### 8.2 Core Connector Development (Phase 2a)
**Priority**: HIGH  
**Estimated Time**: 8-12 hours

**Recommended Default Connectors** (for greenfield deployments):
- Azure Synapse Analytics (#60) - Analytics/Data warehouse
- Azure Cosmos DB - Already integrated via CRUD service
- Azure Event Hubs - Already integrated for events

**Customer-Specific Connector Priority**:
1. PIM connector (choose based on customer: Salsify, Akeneo, or Pimcore)
2. DAM connector (choose based on customer: Cloudinary, Bynder, or AEM)
3. Inventory/WMS connector (choose based on customer: SAP, Oracle, Manhattan)
4. CRM connector (choose based on customer: Salesforce, D365 CE)

#### 8.3 Event-Driven Connector Sync
**Priority**: MEDIUM  
**Estimated Time**: 4-6 hours  
**Issue**: [#80](https://github.com/Azure-Samples/holiday-peak-hub/issues/80)

**Tasks**:
- [ ] Define event schemas for each domain (ProductChanged, InventoryUpdated, etc.)
- [ ] Implement webhook receivers in CRUD service
- [ ] Create Event Hub consumers for connector events
- [ ] Add idempotency and dead-letter handling
- [ ] Test end-to-end event flow

#### 8.4 Multi-Tenant Connector Configuration
**Priority**: MEDIUM  
**Estimated Time**: 3-4 hours  
**Issue**: [#81](https://github.com/Azure-Samples/holiday-peak-hub/issues/81)

**Tasks**:
- [ ] Design tenant configuration schema
- [ ] Implement TenantResolver middleware
- [ ] Add Azure Key Vault integration for secrets
- [ ] Create connector instance caching
- [ ] Document multi-tenant setup

#### 8.5 Internal Data Guardrails
**Priority**: CRITICAL  
**Estimated Time**: 2-3 hours  
**Issue**: [#83](https://github.com/Azure-Samples/holiday-peak-hub/issues/83)

**Tasks**:
- [ ] Create GuardrailMiddleware for enrichment agents
- [ ] Implement source data validation (no AI generation without source)
- [ ] Add audit logging for data lineage
- [ ] Create rejection handlers for missing sources
- [ ] Test guardrail enforcement

---

## Enterprise Connector Summary

| Domain | Connectors | Issues |
|--------|------------|--------|
| Inventory/SCM | SAP S/4HANA, Oracle SCM, Manhattan, Blue Yonder, D365 SCM, Infor | #36-40, #77 |
| CRM/Loyalty | Salesforce, D365 CE, Adobe AEP, Braze, Segment, Oracle CX | #41-45, #78 |
| PIM | Salsify, inRiver, Akeneo, Pimcore, SAP Hybris, Informatica | #46-49, #74-75 |
| DAM | Cloudinary, Adobe AEM, Bynder, Sitecore | #50-52, #76 |
| Commerce/Order | Shopify, commercetools, SFCC, Magento, SAP Commerce, Manhattan OMS, VTEX | #53-59 |
| Data/Analytics | Azure Synapse, Snowflake, Databricks, GA4, Adobe Analytics | #60-64 |
| Integration | MuleSoft, Confluent, Boomi, IBM Sterling | #65-68 |
| Identity | Okta/Auth0, OneTrust | #69-70 |
| Workforce | UKG/Kronos, Zebra Reflexis, WorkJam | #71-73 |
| Architecture | Registry, Events, Multi-tenant, Guardrails, Reference Patterns | #79-84 |

**Total Connector Issues**: 49 issues (#36-#84)

---

## Timeline Estimate

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| Phase 2: Infrastructure Deployment | 8 | 10-17 hours |
| Phase 3: Event-Driven Integration | 2 | 4-6 hours |
| Phase 4: Testing & Validation | 2 | 5-7 hours |
| Phase 5: Monitoring & Observability | 2 | 3-5 hours |
| Phase 6: Performance Optimization | 2 | 3-5 hours |
| Phase 7: Security Hardening | 3 | 4-6 hours |
| Phase 8: Enterprise Connectors | 5 | 20-29 hours |
| **Total** | **24** | **49-75 hours** |

**Estimated completion**: 2-3 weeks (full-time work)

---

## Success Criteria

### Infrastructure
- ✅ All Azure resources deployed
- ✅ Private Endpoints configured
- ✅ Managed Identity working
- ✅ No public IPs exposed

### Services
- ✅ CRUD service running on AKS (3+ pods)
- ✅ All 21 agents deployed and responding
- ✅ Frontend deployed to Static Web Apps
- ✅ APIM routing traffic correctly

### Functionality
- ✅ User can register and login
- ✅ User can browse products
- ✅ User can add to cart and checkout
- ✅ Staff can view analytics
- ✅ Events flowing to agents

### Enterprise Connectors (Phase 8)
- ✅ Connector Registry operational
- ✅ At least one PIM connector integrated
- ✅ At least one DAM connector integrated
- ✅ Data guardrails enforced (no AI generation without source)
- ✅ Multi-tenant configuration working

### Performance
- ✅ API p99 latency < 1 second
- ✅ No 429 errors under normal load
- ✅ Frontend load time < 2 seconds

### Security
- ✅ All secrets in Key Vault
- ✅ JWT validation working
- ✅ RBAC enforced
- ✅ No public endpoints

---

## Related Documentation

- [Architecture Documentation](README.md)
- [CRUD Service Implementation](architecture/crud-service-implementation.md)
- [Frontend Integration Guide](../apps/ui/INTEGRATION.md)
- [Shared Infrastructure README](.infra/modules/shared-infrastructure/README.md)
- [Static Web App README](.infra/modules/static-web-app/README.md)
- [Enterprise Integration Strategy](roadmap/011-retail-system-integration-strategy.md)
- [Connector Contracts and Registry](../lib/src/holiday_peak_lib/integrations/)
- [CHANGELOG](../CHANGELOG.md)
