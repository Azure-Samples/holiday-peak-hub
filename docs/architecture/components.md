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
