# Adapters Component

**Path**: `lib/src/holiday_peak_lib/adapters/`  
**Pattern**: Adapter Pattern  
**Related ADRs**: [ADR-003](../../adrs/adr-003-adapter-pattern.md)

## Purpose

Provides pluggable interfaces for integrating with diverse retailer systems (inventory, pricing, CRM, logistics, catalog). Decouples agent/app logic from external API specifics, enabling retailers to swap implementations without code changes.

## Design Pattern: Adapter

Adapters translate retailer-specific APIs into standardized interfaces consumed by agents. Each adapter type defines an abstract base class with methods agents expect; retailers implement concrete adapters for their systems.

```python
# Base adapter interface
class InventoryAdapter(ABC):
    @abstractmethod
    async def fetch_stock(self, sku: str) -> InventoryStatus:
        """Get current stock level for SKU."""
        pass
    
    @abstractmethod
    async def reserve_stock(self, sku: str, quantity: int, order_id: str) -> ReservationResult:
        """Reserve inventory for order."""
        pass

# Mock implementation (stubbed in current codebase)
class MockInventoryAdapter(InventoryAdapter):
    async def fetch_stock(self, sku: str) -> InventoryStatus:
        return InventoryStatus(sku=sku, available=100, reserved=0, status="in_stock")
    
    async def reserve_stock(self, sku: str, quantity: int, order_id: str) -> ReservationResult:
        return ReservationResult(success=True, reservation_id=f"RES-{order_id}")

# Retailer implementation (to be provided by retailer)
class LevisInventoryAdapter(InventoryAdapter):
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key
        self.session = aiohttp.ClientSession()
    
    async def fetch_stock(self, sku: str) -> InventoryStatus:
        async with self.session.get(
            f"{self.api_url}/inventory/{sku}",
            headers={"Authorization": f"Bearer {self.api_key}"}
        ) as resp:
            data = await resp.json()
            return InventoryStatus(
                sku=sku,
                available=data["available"],
                reserved=data["reserved"],
                status=data["status"]
            )
```

## What's Implemented

✅ **Base Adapter Interfaces**:
- `InventoryAdapter`: Stock queries, reservations
- `PricingAdapter`: Price lookups, promotions
- `CRMAdapter`: Customer profiles, segments
- `LogisticsAdapter`: Shipping rates, ETAs
- `CatalogAdapter`: Product metadata, search

✅ **Mock Adapters**: Stub implementations returning hardcoded data for all interfaces

✅ **Retry Logic**: Exponential backoff with jitter for transient failures

✅ **Timeout Handling**: Default 5-second timeout per call, configurable

✅ **Error Mapping**: `AdapterException` hierarchy for consistent error handling

## What's NOT Implemented (Retailer Responsibility)

❌ **Real API Clients**: No actual HTTP/gRPC/database calls to retailer systems  
❌ **Authentication**: No OAuth, API key rotation, or token refresh logic  
❌ **Schema Mapping**: No transformation from retailer schemas to lib schemas  
❌ **Rate Limiting**: No backpressure or quota management  
❌ **Caching**: No adapter-level caching (apps use memory tiers)  
❌ **Circuit Breakers**: No fault isolation when downstream systems fail  

**Current Status**: All adapters are **stubs**. Apps use `MockInventoryAdapter`, `MockPricingAdapter`, etc. Retailers must implement concrete adapters by:
1. Subclassing base adapter interface
2. Implementing async methods with real API calls
3. Mapping retailer schemas to lib Pydantic models
4. Registering adapter in app config via dependency injection

## Extension Guide

### Step 1: Implement Adapter

```python
# apps/inventory-health-check/src/adapters/custom_inventory.py
from holiday_peak_lib.adapters.inventory import InventoryAdapter
from holiday_peak_lib.schemas.inventory import InventoryStatus
import aiohttp

class CustomInventoryAdapter(InventoryAdapter):
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key
    
    async def fetch_stock(self, sku: str) -> InventoryStatus:
        # Call your API
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.api_url}/api/v1/stock/{sku}",
                headers={"X-API-Key": self.api_key}
            ) as resp:
                if resp.status != 200:
                    raise AdapterException(f"API error: {resp.status}")
                data = await resp.json()
                
                # Map your schema to lib schema
                return InventoryStatus(
                    sku=sku,
                    available=data["qty_available"],
                    reserved=data["qty_reserved"],
                    status="in_stock" if data["qty_available"] > 0 else "out_of_stock"
                )
```

### Step 2: Register in App

```python
# apps/inventory-health-check/src/config.py
from adapters.custom_inventory import CustomInventoryAdapter
import os

# Override mock adapter
INVENTORY_ADAPTER = CustomInventoryAdapter(
    api_url=os.getenv("INVENTORY_API_URL"),
    api_key=os.getenv("INVENTORY_API_KEY")
)
```

### Step 3: Inject via DI

```python
# apps/inventory-health-check/src/main.py
from config import INVENTORY_ADAPTER

app = FastAPI()

@app.get("/inventory/{sku}")
async def get_inventory(sku: str):
    status = await INVENTORY_ADAPTER.fetch_stock(sku)
    return status.model_dump()
```

## Security Considerations

### Secrets Management (NOT IMPLEMENTED)

**Current State**: Adapters read secrets from environment variables (`.env` file with placeholders).

**Production Requirements**:
- Use **Azure Key Vault** for API keys, connection strings
- Implement **Managed Identity** for passwordless access
- Rotate secrets automatically via Key Vault rotation policies
- Never commit secrets to git; use CI/CD secret injection

Example with Key Vault:
```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

credential = DefaultAzureCredential()
client = SecretClient(vault_url="https://<vault>.vault.azure.net", credential=credential)
api_key = client.get_secret("inventory-api-key").value

adapter = CustomInventoryAdapter(api_url="...", api_key=api_key)
```

### Authentication Patterns

**Options to implement**:
1. **OAuth 2.0**: For partner APIs requiring token exchange
2. **mTLS**: For high-security B2B integrations
3. **HMAC Signing**: For request integrity verification

## Observability (PARTIALLY IMPLEMENTED)

### Logging

✅ **Implemented**: Basic logging via `holiday_peak_lib.utils.logging`
- Adapter calls logged at INFO level
- Errors logged at ERROR level with stack traces

❌ **NOT Implemented**:
- No structured logging with adapter-specific tags
- No correlation IDs for distributed tracing
- No sampling for high-volume calls

**Add Distributed Tracing**:
```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

class CustomInventoryAdapter(InventoryAdapter):
    async def fetch_stock(self, sku: str) -> InventoryStatus:
        with tracer.start_as_current_span("inventory.fetch_stock") as span:
            span.set_attribute("sku", sku)
            try:
                result = await self._api_call(sku)
                span.set_attribute("status", result.status)
                return result
            except Exception as e:
                span.record_exception(e)
                raise
```

### Metrics

❌ **NOT Implemented**:
- No adapter call latency histograms
- No error rate counters
- No retry/timeout metrics

**Add Azure Monitor Metrics**:
```python
from azure.monitor.opentelemetry import configure_azure_monitor

configure_azure_monitor(connection_string="...")

# Track adapter latency
start = time.time()
result = await adapter.fetch_stock(sku)
duration_ms = (time.time() - start) * 1000
logger.info("adapter.call", extra={"duration_ms": duration_ms, "adapter": "inventory"})
```

## Testing

### Unit Tests

✅ **Implemented**: Basic tests for mock adapters in `lib/tests/adapters/`

```python
# lib/tests/adapters/test_inventory_adapter.py
import pytest
from holiday_peak_lib.adapters.inventory import MockInventoryAdapter

@pytest.mark.asyncio
async def test_fetch_stock():
    adapter = MockInventoryAdapter()
    status = await adapter.fetch_stock("SKU-123")
    assert status.sku == "SKU-123"
    assert status.available > 0
```

### Integration Tests (NOT IMPLEMENTED)

❌ **Missing**:
- No Docker Compose setup with stub API servers
- No contract tests verifying adapter schemas match retailer APIs
- No resilience tests (timeout, retry, circuit breaker)

**Add Integration Tests**:
```python
# apps/inventory-health-check/tests/integration/test_adapter.py
import pytest
from testcontainers.core.container import DockerContainer

@pytest.fixture
async def stub_api():
    # Spin up stub API container
    with DockerContainer("stub-inventory-api:latest").with_exposed_ports(8080) as container:
        yield f"http://localhost:{container.get_exposed_port(8080)}"

@pytest.mark.asyncio
async def test_real_adapter_call(stub_api):
    adapter = CustomInventoryAdapter(api_url=stub_api, api_key="test-key")
    status = await adapter.fetch_stock("SKU-123")
    assert status.sku == "SKU-123"
```

## Performance Tuning

### Connection Pooling

❌ **NOT Implemented**: Each adapter call creates new HTTP session

**Recommendation**: Reuse `aiohttp.ClientSession` per adapter instance:
```python
class CustomInventoryAdapter:
    def __init__(self, ...):
        self.session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=100),  # Max 100 concurrent connections
            timeout=aiohttp.ClientTimeout(total=5)
        )
    
    async def close(self):
        await self.session.close()
```

### Parallel Calls

For batch operations, use `asyncio.gather`:
```python
skus = ["SKU-1", "SKU-2", "SKU-3"]
results = await asyncio.gather(*[adapter.fetch_stock(sku) for sku in skus])
```

## Runbooks (NOT PROVIDED)

**Operational playbooks needed**:
- **Adapter Failure**: How to detect, diagnose, and fallback when retailer API is down
- **Latency Spikes**: Tuning timeouts, retry policies, circuit breaker thresholds
- **Schema Changes**: Versioning strategy when retailer updates API contract

## Related Components

- [Agents](agents.md) — Consume adapters for tool calls
- [Schemas](schemas.md) — Define adapter return types
- [Utils](utils.md) — Provide retry/timeout helpers

## Related ADRs

- [ADR-003: Adapter Pattern](../../adrs/adr-003-adapter-pattern.md)
- [ADR-002: Azure Services](../../adrs/adr-002-azure-services.md)
