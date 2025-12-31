# ADR-003: Adapter Pattern for Retail Integrations

**Status**: Accepted  
**Date**: 2024-12  
**Deciders**: Architecture Team, Ricardo Cataldi

## Context

Retailers have diverse legacy systems for inventory, pricing, CRM, and logistics. Each system exposes data differently:
- REST APIs with custom schemas
- SOAP services
- Direct database access
- File-based exports (CSV, XML)
- GraphQL endpoints

The accelerator must support pluggable integrations without modifying agent or app logic.

## Decision

**Implement Adapter Pattern for all retail system integrations.**

### Structure
```python
# lib/src/holiday_peak_lib/adapters/base.py
class RetailAdapter(ABC):
    @abstractmethod
    async def fetch_inventory(self, sku: str) -> InventoryStatus:
        pass
    
    @abstractmethod
    async def get_price(self, sku: str, customer_id: str) -> PriceInfo:
        pass

# Retailer implements adapter
class LevisInventoryAdapter(RetailAdapter):
    async def fetch_inventory(self, sku: str) -> InventoryStatus:
        # Call Levis API
        ...
```

### Adapter Types
1. **Inventory Adapter**: Stock levels, reservations
2. **Pricing Adapter**: Dynamic pricing, promotions
3. **CRM Adapter**: Customer profiles, segments
4. **Logistics Adapter**: Shipping rates, ETAs
5. **Catalog Adapter**: Product metadata, taxonomy

## Consequences

### Positive
- **Decoupling**: Agent code never calls retailer APIs directly
- **Testability**: Mock adapters for unit tests
- **Swappability**: Change backend without changing app logic
- **Consistency**: Standardized return types (Pydantic models)

### Negative
- **Indirection**: One extra hop per call (mitigated by async)
- **Schema Mapping**: Each adapter must normalize to lib schemas
- **Maintenance**: Adapters need updates when retailer APIs change

## Alternatives Considered

### Direct API Calls
- **Pros**: Fewer abstractions, simpler stack traces
- **Cons**: Agent code tightly coupled to retailer; impossible to test without real APIs

### GraphQL Stitching
- **Pros**: Single query language across systems
- **Cons**: Requires GraphQL servers on all retailers; adds translation layer

### API Gateway Transformation
- **Pros**: Centralized schema mapping
- **Cons**: APIM complexity; still need adapters for non-HTTP sources

## Implementation Guidelines

### Adapter Location
- **Library**: `lib/src/holiday_peak_lib/adapters/<domain>/`
- **Examples**: `inventory_adapter.py`, `pricing_adapter.py`

### Adapter Registration
- Dependency injection via app_factory
- Override in app config:
```python
# apps/inventory-health-check/src/config.py
from holiday_peak_lib.adapters.inventory import DefaultInventoryAdapter

INVENTORY_ADAPTER = DefaultInventoryAdapter(api_url=os.getenv("INVENTORY_API_URL"))
```

### Error Handling
- Adapters raise `AdapterException` subclasses
- Apps catch and map to HTTP 502/503
- Timeouts enforced at adapter level (default 5s)

### Testing
- Mock adapters in `lib/tests/mocks/`
- Integration tests use Docker Compose with stub APIs

## Related ADRs

- [ADR-004: Builder Pattern](adr-004-builder-pattern-memory.md) — Memory adapter construction
- [ADR-010: REST + MCP](adr-010-rest-and-mcp-exposition.md) — Adapter consumption by agents
