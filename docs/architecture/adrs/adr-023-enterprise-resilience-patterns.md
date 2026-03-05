# ADR-023: Enterprise Resilience Patterns

**Status**: Accepted  
**Date**: 2026-03  
**Deciders**: Architecture Team

## Context

As the accelerator integrates with enterprise systems (ERP, PIM, CRM), resilience becomes critical. External systems may:
- Experience high latency during peak loads
- Become temporarily unavailable
- Throttle requests based on rate limits
- Return partial failures in batch operations

Without proper resilience patterns, a single slow or unavailable backend can cascade failures across the entire platform, impacting customer experience during critical retail periods (Black Friday, holiday peaks).

Key questions addressed:
- How do we prevent slow backends from consuming all connection resources?
- How do we handle rate-limited APIs gracefully?
- How do we isolate failures to prevent cascading outages?
- How do we balance fast failure with retry logic?

## Decision

**Implement a layered resilience strategy using Circuit Breaker, Bulkhead, and Rate Limiter patterns at the connector level.**

### Pattern 1: Circuit Breaker

Prevents repeated calls to failing services, allowing them time to recover.

```python
from holiday_peak_lib.resilience import CircuitBreaker, CircuitState

class OracleFusionConnector:
    def __init__(self, config: OracleFusionConfig):
        self.circuit_breaker = CircuitBreaker(
            name="oracle-fusion",
            failure_threshold=5,          # Open after 5 failures
            recovery_timeout_seconds=30,  # Half-open after 30s
            success_threshold=3,          # Close after 3 successes
        )
    
    async def fetch_inventory(self, sku: str) -> InventoryData:
        if self.circuit_breaker.state == CircuitState.OPEN:
            raise CircuitOpenError("Oracle Fusion circuit is open")
        
        try:
            result = await self._api_call(sku)
            self.circuit_breaker.record_success()
            return result
        except Exception as e:
            self.circuit_breaker.record_failure()
            raise
```

**State Transitions**:
```
CLOSED → (failures >= threshold) → OPEN
OPEN → (timeout elapsed) → HALF_OPEN
HALF_OPEN → (success) → CLOSED
HALF_OPEN → (failure) → OPEN
```

### Pattern 2: Bulkhead

Isolates resources to prevent a single slow dependency from consuming all capacity.

```python
from holiday_peak_lib.resilience import Bulkhead

class SAPConnector:
    def __init__(self, config: SAPConfig):
        # Limit concurrent SAP connections to 10
        self.bulkhead = Bulkhead(
            name="sap-bulkhead",
            max_concurrent=10,
            max_wait_seconds=5,
        )
    
    async def sync_product(self, product: Product) -> SyncResult:
        async with self.bulkhead.acquire():
            # Only 10 concurrent SAP calls allowed
            return await self._sync_impl(product)
```

**Bulkhead Sizing by System Type**:
| System Type | Max Concurrent | Max Wait |
|------------|----------------|----------|
| ERP (SAP, Oracle) | 10 | 5s |
| CRM (Salesforce, Dynamics) | 20 | 3s |
| PIM | 15 | 4s |
| External APIs | 5 | 2s |

### Pattern 3: Rate Limiter

Enforces API rate limits to prevent throttling errors.

```python
from holiday_peak_lib.resilience import RateLimiter

class SalesforceConnector:
    def __init__(self, config: SalesforceConfig):
        # Salesforce: 100K requests/day ≈ 70/min with buffer
        self.rate_limiter = RateLimiter(
            name="salesforce",
            requests_per_minute=60,
            burst_allowance=10,
        )
    
    async def update_customer(self, customer_id: str, data: dict):
        async with self.rate_limiter.acquire():
            return await self._api_call(customer_id, data)
```

### Layered Application

All three patterns are applied together in the recommended order:

```python
class EnterpriseConnector:
    """Base class demonstrating layered resilience."""
    
    async def execute_with_resilience(self, operation: Callable):
        # Layer 1: Rate Limiter (prevent throttling)
        async with self.rate_limiter.acquire():
            # Layer 2: Bulkhead (isolate resources)
            async with self.bulkhead.acquire():
                # Layer 3: Circuit Breaker (fail fast)
                if self.circuit_breaker.state == CircuitState.OPEN:
                    raise CircuitOpenError(f"{self.name} is unavailable")
                
                try:
                    result = await operation()
                    self.circuit_breaker.record_success()
                    return result
                except Exception as e:
                    self.circuit_breaker.record_failure()
                    raise
```

### Fallback Strategies

When resilience patterns trigger, provide graceful degradation:

```python
class InventoryAdapter:
    async def get_stock(self, sku: str) -> StockLevel:
        try:
            return await self.connector.fetch_inventory(sku)
        except CircuitOpenError:
            # Fallback: Return cached data with staleness indicator
            cached = await self.cache.get(f"stock:{sku}")
            if cached:
                return StockLevel(
                    quantity=cached.quantity,
                    is_stale=True,
                    staleness_seconds=cached.age_seconds,
                )
            # No cache available
            raise StockUnavailableError(sku)
```

### Observability Integration

All resilience events are emitted as structured telemetry:

```python
@dataclass
class ResilienceEvent:
    pattern: str           # "circuit_breaker", "bulkhead", "rate_limiter"
    action: str            # "opened", "closed", "rejected", "throttled"
    connector: str         # "oracle-fusion", "salesforce"
    duration_ms: int
    timestamp: datetime

# Integration with Azure Monitor
await telemetry.emit(ResilienceEvent(
    pattern="circuit_breaker",
    action="opened",
    connector="oracle-fusion",
    duration_ms=0,
    timestamp=datetime.utcnow(),
))
```

## Consequences

### Positive
- **Fault isolation**: Single backend failure doesn't cascade
- **Graceful degradation**: Users see stale data instead of errors
- **Cost protection**: Rate limiting prevents overage charges
- **Observability**: Clear metrics for capacity planning

### Negative
- **Complexity**: Three patterns to configure and tune
- **Testing difficulty**: Resilience behavior hard to test without chaos engineering
- **Cache staleness**: Fallbacks may serve outdated data

### Risks Mitigated
- **Cascading failures**: Bulkhead isolates blast radius
- **Thundering herd**: Rate limiter smooths burst traffic
- **Repeated timeouts**: Circuit breaker fails fast

## Alternatives Considered

### 1. Retry-Only Approach
**Rejected**: Retries without circuit breaker can overwhelm recovering systems.

### 2. Infrastructure-Level Resilience (Service Mesh)
**Deferred**: Adds operational complexity; connector-level gives finer control for v1.x.

### 3. Amazon/Netflix Libraries (Hystrix, Resilience4j)
**Rejected**: Not Python-native; custom implementation allows protocol integration (AG-UI, ACP).

## Implementation Notes

- See `lib/src/holiday_peak_lib/resilience/` for implementation
- Circuit breaker state persisted in Redis for distributed consistency
- Bulkhead limits are per-instance; scale horizontally for more capacity
- Rate limiter uses sliding window algorithm

## References

- [Circuit Breaker Pattern](https://docs.microsoft.com/en-us/azure/architecture/patterns/circuit-breaker)
- [Bulkhead Pattern](https://docs.microsoft.com/en-us/azure/architecture/patterns/bulkhead)
- [Rate Limiting Pattern](https://docs.microsoft.com/en-us/azure/architecture/patterns/rate-limiting-pattern)
- ADR-012: Adapter Boundaries (composition rules for resilience)
- ADR-013: Protocol Resilience (AG-UI/ACP retry semantics)
