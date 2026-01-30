# Implementation Roadmap

**Last Updated**: January 29, 2026  
**Status**: Phase 1 Complete | Phases 2-3 Pending

---

## Overview

This document tracks the implementation progress of the Holiday Peak Hub platform. The CRUD service and frontend integration are complete. Remaining work focuses on infrastructure deployment and agent event handlers.

---

## Completed Work ✅

### Phase 1: Foundation & Core Services

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

## Timeline Estimate

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| Phase 2: Infrastructure Deployment | 8 | 10-17 hours |
| Phase 3: Event-Driven Integration | 2 | 4-6 hours |
| Phase 4: Testing & Validation | 2 | 5-7 hours |
| Phase 5: Monitoring & Observability | 2 | 3-5 hours |
| Phase 6: Performance Optimization | 2 | 3-5 hours |
| Phase 7: Security Hardening | 3 | 4-6 hours |
| **Total** | **19** | **29-46 hours** |

**Estimated completion**: 1-2 weeks (full-time work)

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
- [CHANGELOG](../CHANGELOG.md)
