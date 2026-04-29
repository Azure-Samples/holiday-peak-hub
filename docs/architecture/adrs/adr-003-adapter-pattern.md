# ADR-003: Adapter Pattern, Boundaries, and Connector Registry

**Status**: Accepted (Revised 2026-04-28 — consolidated adapter boundaries and connector registry)  
**Date**: 2024-12  
**Deciders**: Architecture Team, Ricardo Cataldi  
**Supersedes**: prior separate decisions on Adapter Boundaries and Composition, and Connector Registry Pattern (now absorbed into this ADR)

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

## Implementation Status (2026-03-20)

- **Implemented and expanded**: Runtime adapter taxonomy now includes `BaseAdapter`, `BaseMCPAdapter`, `BaseExternalAPIAdapter`, and `BaseCRUDAdapter` in `lib/src/holiday_peak_lib/adapters/`.
- **Connector-aligned execution**: Adapter contracts are used alongside connector registration and routing (see Part 3 below).
- **Legacy snippet note**: The decision example below is historical and intentionally simplified; current implementation favors composable adapter specializations over domain-specific abstract methods in the base contract.

### Structure
```python
# lib/src/holiday_peak_lib/adapters/base.py
class BaseAdapter(ABC):
    @abstractmethod
    async def fetch_inventory(self, sku: str) -> InventoryStatus:
        pass
    
    @abstractmethod
    async def get_price(self, sku: str, customer_id: str) -> PriceInfo:
        pass

# Retailer implements adapter
class LevisInventoryAdapter(BaseAdapter):
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

- [ADR-007: Memory Architecture](adr-007-memory-tiers.md) — Memory adapter construction
- [ADR-004: FastAPI with Dual REST + MCP](adr-004-fastapi-mcp.md) — Adapter consumption by agents
- [ADR-019: Enterprise Resilience](adr-019-enterprise-resilience-patterns.md) — Resilience patterns applied at connector level

---

## Part 2: Adapter Boundaries and Composition

### Boundary Guiding Principles

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
```python
# ✅ GOOD: Composition
class CheckoutAdapter:
    def __init__(self, inventory: InventoryAdapter, pricing: PricingAdapter):
        self.inventory = inventory
        self.pricing = pricing
    
    async def validate_cart(self, cart: Cart) -> CartValidation:
        stock = await self.inventory.check_availability(cart.items)
        prices = await self.pricing.get_cart_total(cart)
        return CartValidation(stock=stock, prices=prices)

# ❌ BAD: Inheritance creates tight coupling
class CheckoutAdapter(InventoryAdapter, PricingAdapter):
    pass
```

#### 4. Adapter-to-Adapter Calls
**Prohibited**: Adapters MUST NOT call other adapters directly.

**Solution**: Agents orchestrate multiple adapters:
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
```

### Adapter Sizing Guidelines

| Condition | Action |
|-----------|--------|
| > 500 LOC | Consider splitting by responsibility |
| Multiple backend systems | One adapter per system |
| Different error handling | Separate adapters for different failure modes |
| < 200 LOC | Keep together (premature split) |
| Shared authentication | Keep together (single OAuth flow) |
| Atomic transactions | Keep together (must succeed/fail together) |

### Cross-Cutting Concerns (Handled by `BaseAdapter`)
- Circuit breaker, retry logic, caching, rate limiting, logging/tracing, connection pooling

---

## Part 3: Connector Registry Pattern (from former ADR-024)

### Registry Architecture

The accelerator connects to diverse enterprise systems. Each connector requires different authentication mechanisms, unique configuration parameters, and resilience settings tuned to vendor SLAs.

**Implement a Connector Registry using the Factory pattern with environment-driven configuration.**

### Factory Implementation

```python
from holiday_peak_lib.connectors import ConnectorRegistry, ConnectorType

class InventorySCMFactory:
    _registry: dict[str, type] = {
        "oracle-fusion": OracleFusionConnector,
        "sap-s4hana": SAPConnector,
        "manhattan-wms": ManhattanConnector,
    }
    
    @classmethod
    def create(cls, connector_name: str, config: ConnectorConfig) -> BaseConnector:
        connector_class = cls._registry.get(connector_name)
        if not connector_class:
            raise UnknownConnectorError(f"Unknown inventory connector: {connector_name}")
        return connector_class(config)
    
    @classmethod
    def register(cls, name: str, connector_class: type):
        cls._registry[name] = connector_class
```

### Environment-Driven Configuration

```bash
# Pattern: CONNECTOR_{DOMAIN}_{SYSTEM}_{SETTING}
CONNECTOR_INVENTORY_PROVIDER=oracle-fusion
CONNECTOR_INVENTORY_ORACLE_ENDPOINT=https://xxx.oraclecloud.com
CONNECTOR_INVENTORY_ORACLE_CLIENT_SECRET=@Microsoft.KeyVault(SecretUri=...)

CONNECTOR_CRM_PROVIDER=salesforce
CONNECTOR_PIM_PROVIDER=akeneo
```

### Credential Resolution Order
1. Azure Key Vault reference (production)
2. Managed Identity token (Azure services)
3. Environment variable (development)
4. DefaultAzureCredential fallback

### Connector Interface Contract

All connectors implement domain-specific interfaces:

```python
class InventorySCMConnector(ABC):
    @abstractmethod
    async def fetch_inventory(self, sku: str) -> InventoryData: ...
    @abstractmethod
    async def reserve_stock(self, sku: str, quantity: int, order_id: str) -> Reservation: ...
    @abstractmethod
    async def release_reservation(self, reservation_id: str) -> bool: ...

class CRMLoyaltyConnector(ABC):
    @abstractmethod
    async def get_customer_profile(self, customer_id: str) -> CustomerProfile: ...
    @abstractmethod
    async def update_loyalty_points(self, customer_id: str, delta: int) -> LoyaltyStatus: ...

class PIMConnector(ABC):
    @abstractmethod
    async def get_product(self, sku: str) -> ProductData: ...
    @abstractmethod
    async def update_product(self, sku: str, data: ProductData) -> WritebackResult: ...
```

### Service Integration

```python
class InventoryAdapter:
    def __init__(self):
        self.connector = ConnectorRegistry.get_inventory_connector()
    
    async def check_availability(self, sku: str) -> StockLevel:
        return await self.connector.fetch_inventory(sku)
```

### Feature Flags for Gradual Rollout

New connectors can be rolled out gradually with traffic splitting:
```python
CONNECTOR_INVENTORY_EXPERIMENTAL_SAP=true
CONNECTOR_INVENTORY_SAP_ROLLOUT_PERCENT=10
```

---

## Migration Notes

This ADR consolidates three formerly separate decisions:
- Base Adapter Pattern for retail integrations
- Adapter Boundaries and Composition — boundary rules, sizing, composition-over-inheritance
- Connector Registry Pattern — factory, env config, credential management, feature flags

The boundary and registry decisions are now superseded and absorbed into this ADR.

## References
- [Factory Pattern](https://refactoring.guru/design-patterns/factory-method)
- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)
- [Circuit Breaker Pattern](https://learn.microsoft.com/azure/architecture/patterns/circuit-breaker)
- [Azure Key Vault References](https://docs.microsoft.com/en-us/azure/app-service/app-service-key-vault-references)
