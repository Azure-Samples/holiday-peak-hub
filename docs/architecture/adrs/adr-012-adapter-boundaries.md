# ADR-012: Adapter Boundaries and Composition

**Status**: Accepted  
**Date**: 2026-01  
**Deciders**: Architecture Team

## Context

As the accelerator grows, determining when to split adapters versus composing them becomes critical. Overly granular adapters increase complexity, while monolithic adapters create tight coupling and maintenance challenges.

Key questions:
- Should inventory and pricing be separate adapters or combined?
- When should an adapter call another adapter versus duplicating logic?
- How do we prevent circular dependencies between adapters?
- What's the boundary between adapters and agents?

## Decision

**Define clear adapter boundaries based on domain boundaries and rate of change.**

### Guiding Principles

#### 1. Domain-Driven Boundaries
Adapters align with retail domains:
- **CRM Adapter**: Customer profiles, segments, preferences
- **Inventory Adapter**: Stock levels, reservations, warehouse locations
- **Pricing Adapter**: Base prices, promotions, dynamic pricing rules
- **Logistics Adapter**: Shipping rates, ETAs, carrier selection, tracking
- **Product Adapter**: Catalog, attributes, taxonomy, media

#### 2. Rate of Change
Split adapters when:
- **Different SLA requirements** (pricing updates hourly vs inventory real-time)
- **Different source systems** (SAP for inventory, custom API for pricing)
- **Different scaling patterns** (high-volume inventory vs low-volume logistics)
- **Different teams own the backend** (separate vendor contracts)

#### 3. Composition Over Inheritance
Adapters should compose, not extend:

```python
# ✅ GOOD: Composition
class CheckoutAdapter:
    def __init__(self, inventory: InventoryAdapter, pricing: PricingAdapter):
        self.inventory = inventory
        self.pricing = pricing
    
    async def validate_cart(self, cart: Cart) -> CartValidation:
        # Orchestrate calls to inventory and pricing
        stock = await self.inventory.check_availability(cart.items)
        prices = await self.pricing.get_cart_total(cart)
        return CartValidation(stock=stock, prices=prices)

# ❌ BAD: Inheritance creates tight coupling
class CheckoutAdapter(InventoryAdapter, PricingAdapter):
    pass
```

#### 4. Adapter-to-Adapter Calls
**Prohibited**: Adapters MUST NOT call other adapters directly.

**Rationale**:
- Creates hidden dependencies
- Prevents independent testing
- Complicates error handling
- Makes tracing difficult

**Solution**: Agents orchestrate multiple adapters.

```python
# ✅ GOOD: Agent orchestrates
class CartIntelligenceAgent:
    def __init__(self, inventory_adapter, pricing_adapter):
        self.inventory = inventory_adapter
        self.pricing = pricing_adapter
    
    async def analyze_cart(self, cart: Cart):
        stock = await self.inventory.fetch_inventory(cart.items)
        prices = await self.pricing.get_prices(cart.items)
        return self._merge_results(stock, prices)

# ❌ BAD: Adapter calling adapter
class InventoryAdapter:
    def __init__(self, pricing_adapter):
        self.pricing = pricing_adapter  # ← Creates coupling
    
    async def fetch_with_price(self, sku):
        stock = await self._fetch_impl(sku)
        price = await self.pricing.get_price(sku)  # ← Hidden dependency
        return {**stock, "price": price}
```

### Adapter Sizing Guidelines

#### When to Split
- **> 500 LOC**: Consider splitting by responsibility
- **Multiple backend systems**: One adapter per system
- **Different error handling**: Separate adapters for different failure modes
- **Independent versioning**: Split when backends evolve independently

#### When to Keep Together
- **Shared authentication**: Single OAuth flow for multiple operations
- **Atomic transactions**: Operations that must succeed/fail together
- **< 200 LOC**: Premature optimization
- **Same source system**: Single API with multiple endpoints

### Cross-Cutting Concerns

Handled by `BaseAdapter` (not per-adapter):
- **Circuit breaker**: Fail fast on repeated errors
- **Retry logic**: Exponential backoff
- **Caching**: TTL-based response cache
- **Rate limiting**: Token bucket per adapter
- **Logging/tracing**: Correlation IDs
- **Connection pooling**: Shared HTTP client

## Consequences

### Positive
- **Clear ownership**: Each adapter has single responsibility
- **Independent testing**: Mock one adapter without affecting others
- **Parallel development**: Teams can work on different adapters
- **Explicit orchestration**: Agents make dependencies visible
- **Resilience isolation**: One adapter failure doesn't cascade

### Negative
- **More files**: More adapters = more boilerplate
- **Coordination overhead**: Agents must orchestrate multiple calls
- **Potential latency**: Sequential adapter calls (mitigated by async)
- **Duplicate code**: Common patterns may appear across adapters

### Risk Mitigation
- **Starter templates**: CLI generator for new adapters
- **Shared base class**: `BaseAdapter` provides common functionality
- **Async by default**: Parallel adapter calls in agents
- **Code review guidelines**: Enforce boundaries during PR reviews

## Implementation Guidelines

### File Structure
```
lib/src/holiday_peak_lib/adapters/
├── __init__.py
├── base.py                    # BaseAdapter with resilience
├── inventory_adapter.py       # Domain adapter
├── pricing_adapter.py
├── crm_adapter.py
├── logistics_adapter.py
└── product_adapter.py
```

### Adapter Interface
```python
from holiday_peak_lib.adapters.base import BaseAdapter

class InventoryAdapter(BaseAdapter):
    """Adapter for inventory system integration."""
    
    async def _connect_impl(self, **kwargs) -> Any:
        """Initialize connection to inventory backend."""
        pass
    
    async def _fetch_impl(self, query: InventoryQuery) -> InventoryResponse:
        """Fetch inventory data."""
        pass
    
    async def _upsert_impl(self, payload: InventoryUpdate) -> bool:
        """Update inventory levels."""
        pass
    
    async def _delete_impl(self, identifier: str) -> bool:
        """Delete inventory record."""
        pass
```

### Testing Strategy
- **Unit tests**: Mock backend, test adapter logic
- **Integration tests**: Docker Compose with stub APIs
- **Contract tests**: Validate schema against real backend
- **Chaos tests**: Simulate backend failures (circuit breaker, retries)

## Alternatives Considered

### Microservices per Adapter
**Pros**: Ultimate isolation, independent scaling  
**Cons**: Network overhead, operational complexity, latency  
**Decision**: Adapters are libraries, not services. Apps compose adapters.

### Adapter Registry Pattern
**Pros**: Dynamic adapter discovery, runtime swapping  
**Cons**: Hidden dependencies, harder to trace, type safety loss  
**Decision**: Dependency injection via app constructor is explicit and type-safe.

### Unified Retail Adapter
**Pros**: Single interface for all operations  
**Cons**: God object, tight coupling, impossible to mock partially  
**Decision**: Domain-specific adapters are more maintainable.

## Related ADRs
- [ADR-003: Adapter Pattern for Retail Integrations](adr-003-adapter-pattern.md)
- [ADR-006: Microsoft Agent Framework + Foundry](adr-006-agent-framework.md)
- [ADR-010: Dual Exposition: REST + MCP Servers](adr-010-rest-and-mcp-exposition.md)

## References
- [Domain-Driven Design](https://martinfowler.com/bliki/DomainDrivenDesign.html)
- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)
- [Circuit Breaker Pattern](https://learn.microsoft.com/azure/architecture/patterns/circuit-breaker)
