# Components Documentation

This document indexes all component documentation for Holiday Peak Hub, organized by libs (framework) and apps (domain services).

## Libs (Framework Components)

Core micro-framework providing reusable patterns for retail AI agents.

| Component | Path | Description | Pattern |
|-----------|------|-------------|---------|
| [Adapters](components/libs/adapters.md) | `lib/src/holiday_peak_lib/adapters/` | Pluggable retail system integrations | Adapter Pattern |
| [Agents](components/libs/agents.md) | `lib/src/holiday_peak_lib/agents/` | Agent orchestration and MCP wrappers | Builder Pattern (memory) |
| [Memory](components/libs/memory.md) | `lib/src/holiday_peak_lib/memory/` | Three-tier memory management | Tiered Caching |
| [Orchestration](components/libs/orchestration.md) | `lib/src/holiday_peak_lib/orchestration/` | SAGA choreography helpers | Event-driven |
| [Schemas](components/libs/schemas.md) | `lib/src/holiday_peak_lib/schemas/` | Pydantic models for data contracts | Domain Models |
| [Utils](components/libs/utils.md) | `lib/src/holiday_peak_lib/utils/` | Logging, config, retry logic | Utilities |

## Apps (Domain Services)

Runnable services built on the framework, one per retail process.

**App Index**: [components/apps/README.md](components/apps/README.md)

### E-commerce Domain

| Service | Path | Purpose |
|---------|------|---------|
| [Catalog Search](components/apps/ecommerce-catalog-search.md) | `apps/ecommerce-catalog-search/` | Product discovery with AI Search |
| [Product Detail Enrichment](components/apps/ecommerce-product-detail-enrichment.md) | `apps/ecommerce-product-detail-enrichment/` | ACP metadata augmentation |
| [Cart Intelligence](components/apps/ecommerce-cart-intelligence.md) | `apps/ecommerce-cart-intelligence/` | Personalized cart recommendations |
| [Checkout Support](components/apps/ecommerce-checkout-support.md) | `apps/ecommerce-checkout-support/` | Allocation validation, dynamic pricing |
| [Order Status](components/apps/ecommerce-order-status.md) | `apps/ecommerce-order-status/` | Proactive order tracking |

### Product Management Domain

| Service | Path | Purpose |
|---------|------|---------|
| [Normalization/Classification](components/apps/product-management-normalization-classification.md) | `apps/product-management-normalization-classification/` | Automated taxonomy alignment |
| [ACP Transformation](components/apps/product-management-acp-transformation.md) | `apps/product-management-acp-transformation/` | Standards-compliant catalog export |
| [Consistency Validation](components/apps/product-management-consistency-validation.md) | `apps/product-management-consistency-validation/` | Real-time data quality checks |
| [Assortment Optimization](components/apps/product-management-assortment-optimization.md) | `apps/product-management-assortment-optimization/` | ML-driven SKU mix recommendations |

### CRM Domain

| Service | Path | Purpose |
|---------|------|---------|
| [Profile Aggregation](components/apps/crm-profile-aggregation.md) | `apps/crm-profile-aggregation/` | Unified customer view |
| [Segmentation/Personalization](components/apps/crm-segmentation-personalization.md) | `apps/crm-segmentation-personalization/` | Dynamic cohort building |
| [Campaign Intelligence](components/apps/crm-campaign-intelligence.md) | `apps/crm-campaign-intelligence/` | ROI-optimized marketing automation |
| [Support Assistance](components/apps/crm-support-assistance.md) | `apps/crm-support-assistance/` | Agent-augmented customer service |

### Inventory Domain

| Service | Path | Purpose |
|---------|------|---------|
| [Health Check](components/apps/inventory-health-check.md) | `apps/inventory-health-check/` | Predictive stock-out alerts |
| [JIT Replenishment](components/apps/inventory-jit-replenishment.md) | `apps/inventory-jit-replenishment/` | Demand-sensing reorder triggers |
| [Reservation Validation](components/apps/inventory-reservation-validation.md) | `apps/inventory-reservation-validation/` | Real-time allocation locking |
| [Alerts/Triggers](components/apps/inventory-alerts-triggers.md) | `apps/inventory-alerts-triggers/` | Exception-based notifications |

### Logistics Domain

| Service | Path | Purpose |
|---------|------|---------|
| [ETA Computation](components/apps/logistics-eta-computation.md) | `apps/logistics-eta-computation/` | Real-time delivery predictions |
| [Carrier Selection](components/apps/logistics-carrier-selection.md) | `apps/logistics-carrier-selection/` | Cost/speed trade-off optimization |
| [Returns Support](components/apps/logistics-returns-support.md) | `apps/logistics-returns-support/` | Reverse logistics automation |
| [Route Issue Detection](components/apps/logistics-route-issue-detection.md) | `apps/logistics-route-issue-detection/` | Proactive delay mitigation |

## Frontend Components

Next.js 15 application with atomic design component library connecting to all backend services.

**Frontend Stack**: Next.js 15.1.6, React 19.0.0, TypeScript 5.7.2, Tailwind CSS 4.0.0

### Component Library

**52 production-ready components** organized by atomic design principles:

| Category | Count | Location | Description |
|----------|-------|----------|-------------|
| **Atoms** | 19 | `ui/components/atoms/` | Basic building blocks (Button, Input, Icon, etc.) |
| **Molecules** | 20 | `ui/components/molecules/` | Simple composed components (Card, FormField, etc.) |
| **Organisms** | 9 | `ui/components/organisms/` | Complex composed components (Navigation, ProductGrid, etc.) |
| **Templates** | 4 | `ui/components/templates/` | Page-level layouts (MainLayout, ShopLayout, etc.) |

See [Component Library Documentation](../../ui/components/COMPONENT_README.md) for details.

### Page Structure

**15 pages total**: Organized by user role (anonymous, customer, staff, admin)

#### Anonymous Pages (5 pages - Public Access)

| Page | Route | Services Used | Purpose |
|------|-------|---------------|---------|
| Homepage | `/` | catalog-search, segmentation-personalization, assortment-optimization | Landing with featured products |
| Category | `/category/[slug]` | catalog-search, inventory-health-check, assortment-optimization | Product browsing by category |
| Product | `/product/[id]` | product-detail-enrichment, inventory-health-check, eta-computation, cart-intelligence | Detailed product view |
| Reviews | `/product/[id]/reviews` | product-detail-enrichment, profile-aggregation | Product reviews and ratings |
| Order | `/order/[id]` | order-status, eta-computation, route-issue-detection | Order status lookup |

#### Customer Pages (4 pages - Role: `customer`)

| Page | Route | Services Used | Purpose |
|------|-------|---------------|---------|
| Checkout | `/checkout` | cart-intelligence, checkout-support, inventory-reservation-validation, carrier-selection | Complete purchase |
| Order Tracking | `/my-orders` | order-status, eta-computation, returns-support | View customer orders |
| Dashboard | `/dashboard` | profile-aggregation, segmentation-personalization, order-status, inventory-health-check | Customer overview |
| Profile | `/profile` | profile-aggregation, segmentation-personalization | User profile and preferences |

#### Staff Pages (5 pages - Role: `staff`)

| Page | Route | Services Used | Purpose |
|------|-------|---------------|---------|
| Sales Analytics | `/staff/sales` | campaign-intelligence, catalog-search, inventory-health-check | Sales metrics (page views, per product, per category) |
| Requests | `/staff/requests` | support-assistance, profile-aggregation, returns-support | Customer support requests |
| Shippings | `/staff/shippings` | eta-computation, carrier-selection, route-issue-detection | Shipping management |
| Logistic Tracking | `/staff/logistics` | eta-computation, route-issue-detection, carrier-selection | Real-time logistics tracking |
| Customer Profiles | `/staff/customers` | profile-aggregation, segmentation-personalization, order-status | Customer information and history |

#### Admin Pages (1 page - Role: `admin`)

| Page | Route | Services Used | Purpose |
|------|-------|---------------|---------|
| Admin Portal | `/admin` | All backend services | Gateway to all sensitive backend capabilities |

### Protocol Compliance

**AG-UI Protocol**: All interactive elements annotated with `data-ag-*` attributes for agent interoperability
- **Specification**: https://docs.ag-ui.com/concepts/generative-ui-specs
- **Implementation**: Action registry, state exposure, agent communication layer

**Agentic Commerce Protocol (ACP)**: Product data standardized for agent consumption
- **Specification**: https://github.com/agentic-commerce-protocol/agentic-commerce-protocol
- **Implementation**: Zod schemas, validators, transformers

### Authentication & Security

- **JWT tokens** in httpOnly cookies
- **Role-Based Access Control (RBAC)** with 4 roles: `anonymous`, `customer`, `staff`, `admin`
- **Next.js middleware** for route protection
- **Session management** with automatic refresh

### Design System

**Color Palette**:
- Ocean Blue (#0077BE) - Primary actions
- Lime Green (#32CD32) - Success states
- Cyan (#00CED1) - Accents
- White (#FFFFFF) - Backgrounds
- Dark Grey (#2D3748) - Text

**Dark Mode**: Full support with inverted color palette

### Related ADRs

- [ADR-015](adrs/adr-015-nextjs-app-router.md) - Next.js 15 with App Router
- [ADR-016](adrs/adr-016-atomic-design-system.md) - Atomic Design System
- [ADR-017](adrs/adr-017-ag-ui-protocol.md) - AG-UI Protocol Integration
- [ADR-018](adrs/adr-018-acp-frontend.md) - ACP Frontend Integration
- [ADR-019](adrs/adr-019-authentication-rbac.md) - Authentication & RBAC
- [ADR-020](adrs/adr-020-api-client-architecture.md) - API Client Architecture

## Operational Playbooks

Operational response guides for common incidents and runtime issues.

- [Playbooks Index](playbooks/README.md)

## Component Interaction Matrix

| Component | Depends On | Consumed By |
|-----------|------------|-------------|
| Adapters | - | All apps (via DI) |
| Memory Builder | Redis, Cosmos, Blob SDKs | Agents |
| Agents | Memory, Adapters | All apps |
| Orchestration | Event Hubs SDK | Apps (SAGA participants) |
| Schemas | Pydantic | Adapters, Agents, Apps |
| Utils | Azure Monitor SDK | All apps |

## Extension Points

### For Retailers

1. **Custom Adapters**: Implement `RetailAdapter` interface for your APIs
2. **Memory Policies**: Override tier promotion rules in `MemoryBuilder`
3. **Agent Tools**: Register custom MCP tools in app `main.py`
4. **Event Handlers**: Subscribe to Event Hubs topics for SAGA participation

### For Microsoft Partners

1. **ISV Adapters**: Package adapters for common retail platforms (Shopify, SAP, Oracle)
2. **Model Tuning**: Fine-tune Foundry models on retailer catalogs
3. **Evaluation Harnesses**: Build scenario-based quality tests
4. **UI Components**: Foundry-based React components for common flows

## Documentation Standards

Each component README includes:
- **Purpose**: What problem does it solve?
- **Patterns**: Which design patterns are used?
- **ADRs**: Links to relevant architectural decisions
- **API Reference**: Key classes and methods
- **Usage Examples**: Code snippets for common scenarios
- **Testing**: How to run unit/integration tests
- **Extension**: How retailers customize this component

## Next Steps

- Explore lib components: [libs/](components/libs/)
- Review app components: [apps/](components/apps/)
- Understand patterns: [ADRs](ADRs.md)
