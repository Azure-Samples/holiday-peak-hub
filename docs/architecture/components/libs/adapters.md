# Adapters Component

**Path**: `lib/src/holiday_peak_lib/adapters/`  
**Pattern**: Adapter Pattern + Connector utilities  
**Related ADRs**: [ADR-003](../../adrs/adr-003-adapter-pattern.md)

## Purpose

Provides pluggable interfaces for integrating with diverse retailer systems (inventory, pricing, CRM, logistics, catalog) and connector helpers that normalize upstream payloads into agent-ready context. Decouples agent/app logic from external API specifics, enabling retailers to swap implementations without code changes.

## Design Pattern: Adapter

Adapters translate retailer-specific APIs into a standardized interface (`BaseAdapter.connect/fetch/upsert/delete`). Connectors consume any `BaseAdapter` and map results to canonical schemas (CRM, product, inventory, pricing, logistics, funnel) for agent prompts. A set of mock adapters provides deterministic data for local testing and doctests. Resilience (rate limiting, caching, retries, timeouts, circuit breaking) is built into `BaseAdapter` and applies to all child adapters.

## What's Implemented

✅ **Base interfaces**: `BaseAdapter` and `AdapterError` in `base.py`

✅ **Connector utilities**: `BaseConnector` adds bounded async mapping, adapter accessors, and validation

✅ **Domain connectors**: CRM, product, inventory, pricing, logistics, funnel connectors normalize adapter payloads into canonical schemas

✅ **Mock adapters**: `mock_adapters.py` provides deterministic stubs for all domains
✅ **App-level composition**: Domain services define their own `adapters.py` modules to assemble connectors and domain-specific helpers

✅ **Resilience defaults**: `BaseAdapter` includes rate limiting, caching, retries, timeouts, and circuit breaking around all adapter operations

## What's NOT Implemented (Retailer Responsibility)

❌ **Real API Clients**: No actual HTTP/gRPC/database calls to retailer systems  
❌ **Authentication**: No OAuth, API key rotation, or token refresh logic  
❌ **Rate Limiting**: Provided via `BaseAdapter` but not tuned per retailer  
❌ **Caching**: Provided via `BaseAdapter` but currently in-memory only  
❌ **Circuit Breakers / Retries / Timeouts**: Provided via `BaseAdapter` but defaults may need tuning  

**Current Status**: Connectors and mock adapters are available. Retailers must implement concrete adapters by:
1. Subclassing `BaseAdapter`
2. Implementing async methods with real API calls
3. Mapping retailer schemas to lib Pydantic models (consumed by connectors)
4. Tuning `BaseAdapter` resilience parameters per retailer workload
5. Registering the adapter in app config via dependency injection

## Extension Guide

### Step 1: Implement Adapter

```python
# apps/inventory-health-check/src/adapters/custom_inventory.py
from holiday_peak_lib.adapters.base import AdapterError, BaseAdapter
import aiohttp


class CustomInventoryAdapter(BaseAdapter):
    def __init__(self, api_url: str, api_key: str):
        super().__init__(max_calls=20, per_seconds=1.0, retries=4, timeout=6.0)
        self.api_url = api_url
        self.api_key = api_key

    async def _connect_impl(self, **kwargs):
        return None

    async def _fetch_impl(self, query: dict[str, object]):
        sku = query.get("sku")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_url}/api/v1/stock/{sku}",
                    headers={"X-API-Key": self.api_key},
                    timeout=5,
                ) as resp:
                    if resp.status != 200:
                        raise AdapterError(f"API error: {resp.status}")
                    data = await resp.json()
                    return [{"sku": sku, "available": data["qty_available"], "reserved": data.get("qty_reserved", 0)}]
        except Exception as exc:
            raise AdapterError("Failed to fetch inventory") from exc

    async def _upsert_impl(self, payload: dict[str, object]):
        return payload

    async def _delete_impl(self, identifier: str) -> bool:
        return True
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

- Use **Managed Identity + Key Vault** for API keys and secrets in production (not implemented in mocks)
- Add OAuth/mTLS/HMAC per retailer requirements

### Authentication Patterns

**Options to implement**:
1. **OAuth 2.0**: For partner APIs requiring token exchange
2. **mTLS**: For high-security B2B integrations
3. **HMAC Signing**: For request integrity verification

## Observability (NOT IMPLEMENTED)

- Add structured logging, tracing, and metrics when implementing real adapters

## Testing

### Unit Tests

✅ **Implemented**: Doctest coverage in connector modules and import validation in `lib/tests/test_lib_imports.py`

```python
# lib/tests/test_lib_imports.py
import pytest


def test_imports():
    import holiday_peak_lib.adapters  # noqa: F401
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
