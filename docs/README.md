# Holiday Peak Hub - Architecture Documentation

**Last Updated**: January 30, 2026  
**Status**: Active Development

## Overview

Holiday Peak Hub is a **cloud-native, agent-driven retail accelerator** with complete frontend implementation and comprehensive backend architecture plan. This documentation covers all architectural decisions, implementation plans, and operational procedures.

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

### Architecture Documentation

**Frontend Architecture**: The production-ready frontend (13 pages, 52 components) is fully documented in the [Components Documentation](architecture/components.md) and governed by 6 frontend-specific ADRs ([ADR-015](architecture/adrs/adr-015-nextjs-app-router.md) through [ADR-020](architecture/adrs/adr-020-api-client-architecture.md)).

### Core Documentation
- **[Architecture Overview](architecture/architecture.md)** - System context and high-level design
- **[Business Summary](architecture/business-summary.md)** - Business requirements and use cases
- **[Components Documentation](architecture/components.md)** - All framework and service components
- **[ADRs (Architecture Decision Records)](architecture/ADRs.md)** - Index of all 20 ADRs

---

## 🏗️ System Architecture

### Frontend Layer
**Technology**: Next.js 15.1.6, React 19, TypeScript 5.7.2, Tailwind CSS 4.0  
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
- **Security Scanning**: Trivy for container image vulnerabilities

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
