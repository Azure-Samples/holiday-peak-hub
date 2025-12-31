# Utils Component

**Path**: `lib/src/holiday_peak_lib/utils/`  
**Design Pattern**: Utility Functions & Helper Classes  
**Purpose**: Reusable cross-cutting concerns (logging, config, retry, validation, telemetry)

## Overview

Provides common utilities used across all libs and apps to avoid code duplication and enforce consistency. Utilities are stateless, composable, and framework-agnostic where possible.

**Key Categories**:
- **Logging**: Structured JSON logging with correlation IDs
- **Config**: Environment variable loading with validation
- **Retry**: Exponential backoff for transient failures
- **Telemetry**: OpenTelemetry instrumentation helpers
- **Validation**: Input sanitization and business rule checks
- **DateTime**: Timezone-aware datetime utilities

## Core Utilities

### 1. Structured Logging

```python
from holiday_peak_lib.utils.logging import get_logger

logger = get_logger(__name__)

# Structured logging with context
logger.info("Order created", extra={
    "order_id": "order-123",
    "customer_id": "customer-456",
    "total": 199.99
})

# Automatic correlation ID propagation
with logger.correlation_context(correlation_id="trace-789"):
    logger.info("Processing payment")  # Includes correlation_id
    await payment_service.charge(...)
    logger.info("Payment completed")  # Same correlation_id
```

**Features**:
- JSON output for Azure Monitor ingestion
- Correlation ID propagation across async calls
- Log level filtering per module
- Sensitive field masking (email, card numbers)

### 2. Configuration Management

```python
from holiday_peak_lib.utils.config import Config, Field

class AppConfig(Config):
    """Application configuration with validation."""
    redis_host: str = Field(..., env="REDIS_HOST")
    redis_port: int = Field(6379, env="REDIS_PORT")
    redis_password: str = Field(..., env="REDIS_PASSWORD")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    
    @validator("log_level")
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}")
        return v.upper()

# Load from environment
config = AppConfig()

# Access with type safety
assert isinstance(config.redis_port, int)
```

**Features**:
- Load from `.env` files, environment variables, or Azure App Configuration
- Type validation with Pydantic
- Required vs optional with defaults
- Fail-fast on missing required vars

### 3. Retry Logic

```python
from holiday_peak_lib.utils.retry import retry, RetryConfig

@retry(
    max_attempts=3,
    backoff_base=2.0,  # 1s, 2s, 4s
    exceptions=[ConnectionError, TimeoutError]
)
async def fetch_inventory(sku: str) -> int:
    """Fetch inventory with automatic retry."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api/inventory/{sku}")
        response.raise_for_status()
        return response.json()["quantity"]

# Custom retry config
config = RetryConfig(
    max_attempts=5,
    backoff_base=1.5,
    max_backoff=30.0,  # Cap at 30s
    jitter=True  # Add randomness to avoid thundering herd
)

@retry(config=config)
async def critical_operation():
    ...
```

**Features**:
- Exponential backoff with optional jitter
- Configurable exceptions to retry
- Max backoff cap to prevent infinite delays
- Async and sync function support

### 4. Telemetry Helpers

```python
from holiday_peak_lib.utils.telemetry import traced, track_metric, track_event

@traced(name="search.catalog", attributes={"index": "products"})
async def search_catalog(query: str) -> list[Product]:
    """Search catalog with automatic tracing."""
    track_metric("search.query_length", len(query))
    
    results = await search_adapter.search(query)
    
    track_metric("search.result_count", len(results))
    track_event("search.completed", {"query": query, "results": len(results)})
    
    return results

# Spans automatically include:
# - Duration
# - Success/failure status
# - Exception details
# - Custom attributes
```

**Features**:
- OpenTelemetry integration for Azure Monitor
- Automatic span creation with decorators
- Metric tracking (counters, gauges, histograms)
- Event logging for business metrics

### 5. Input Validation

```python
from holiday_peak_lib.utils.validation import (
    validate_email,
    validate_sku,
    sanitize_input,
    validate_url
)

# Email validation
try:
    validate_email("user@example.com")  # OK
    validate_email("invalid")  # Raises ValidationError
except ValidationError as e:
    print(e.message)

# SKU validation (format: PREFIX-NUMBER)
validate_sku("NIKE-001")  # OK
validate_sku("invalid")  # Raises ValidationError

# Sanitize user input (prevent XSS, SQL injection)
safe_query = sanitize_input("<script>alert('xss')</script>")
# Returns: "&lt;script&gt;alert('xss')&lt;/script&gt;"

# URL validation
validate_url("https://example.com")  # OK
validate_url("javascript:alert('xss')")  # Raises ValidationError
```

**Features**:
- Common validation patterns (email, URL, phone)
- Business-specific validators (SKU format, order ID)
- XSS/SQL injection prevention
- Configurable regex patterns

### 6. DateTime Utilities

```python
from holiday_peak_lib.utils.datetime import (
    now_utc,
    parse_iso8601,
    format_iso8601,
    is_business_hours,
    next_business_day
)

# Always use UTC internally
timestamp = now_utc()  # datetime(2025, 12, 30, 10, 30, 0, tzinfo=UTC)

# Parse ISO8601 strings
dt = parse_iso8601("2025-12-30T10:30:00Z")

# Format for API responses
iso_str = format_iso8601(dt)  # "2025-12-30T10:30:00Z"

# Business logic helpers
if is_business_hours(dt, timezone="America/New_York"):
    print("Contact support during business hours")

# Calculate next business day (skip weekends, holidays)
next_day = next_business_day(dt, holidays=["2025-12-25", "2026-01-01"])
```

**Features**:
- UTC-first to avoid timezone bugs
- Holiday calendar support
- Business hours calculation
- Timezone conversion helpers

## What's Implemented

✅ **Structured Logger**: JSON output with correlation IDs  
✅ **Config Loader**: Pydantic-based env var loading  
✅ **Retry Decorator**: Exponential backoff with jitter  
✅ **Telemetry Decorators**: `@traced`, `track_metric`, `track_event`  
✅ **Basic Validators**: email, SKU, URL regex patterns  
✅ **DateTime Helpers**: UTC now, ISO8601 parsing/formatting  

## What's NOT Implemented

### Azure App Configuration Integration

❌ **No Centralized Config**: Apps load from `.env`, not Azure App Configuration  
❌ **No Dynamic Refresh**: Config changes require app restart  

**To Implement**:
```python
from azure.appconfiguration import AzureAppConfigurationClient
from azure.identity import DefaultAzureCredential

class AzureAppConfig(Config):
    def __init__(self, connection_string: Optional[str] = None):
        if connection_string:
            self.client = AzureAppConfigurationClient.from_connection_string(connection_string)
        else:
            # Use Managed Identity
            endpoint = os.getenv("AZURE_APP_CONFIG_ENDPOINT")
            self.client = AzureAppConfigurationClient(endpoint, DefaultAzureCredential())
    
    def get(self, key: str) -> str:
        """Fetch config value from Azure App Configuration."""
        setting = self.client.get_configuration_setting(key)
        return setting.value
    
    def watch(self, key: str, callback):
        """Watch for config changes and invoke callback."""
        # Poll for changes every 30s
        # Invoke callback when value changes
        ...
```

### Feature Flags

❌ **No Feature Toggle Support**: Can't enable/disable features without deployment  
❌ **No A/B Testing**: Can't route % of traffic to new feature  

**To Implement**:
```python
from azure.appconfiguration.provider import load_feature_flags

feature_flags = load_feature_flags(connection_string="...")

def is_feature_enabled(feature_name: str, user_id: Optional[str] = None) -> bool:
    """Check if feature enabled for user."""
    flag = feature_flags.get(feature_name)
    
    if not flag:
        return False
    
    # Simple on/off
    if not flag.get("targeting"):
        return flag.get("enabled", False)
    
    # Percentage rollout
    if user_id:
        user_hash = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
        rollout_pct = flag["targeting"].get("percentage", 100)
        return (user_hash % 100) < rollout_pct
    
    return False

# Usage
if is_feature_enabled("new_search_algorithm", user_id="user-123"):
    results = await new_search(query)
else:
    results = await old_search(query)
```

### Circuit Breaker

❌ **No Circuit Breaker Util**: Retry decorator doesn't track failure rates  
❌ **Risk**: Retry storm when downstream service down  

**To Implement**:
```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
async def call_external_api():
    """Call with circuit breaker."""
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api/endpoint")
        response.raise_for_status()
        return response.json()

# Circuit opens after 5 consecutive failures
# Stays open for 60s before half-open (test single request)
```

### Rate Limiting

❌ **No Rate Limiter**: No util to throttle API calls per user/IP  
❌ **Apps must implement from scratch**  

**To Implement**:
```python
from redis.asyncio import Redis
from datetime import timedelta

class RateLimiter:
    def __init__(self, redis: Redis):
        self.redis = redis
    
    async def is_allowed(self, key: str, limit: int, window: timedelta) -> bool:
        """Check if request allowed under rate limit."""
        current = await self.redis.incr(f"ratelimit:{key}")
        
        if current == 1:
            # First request in window, set expiration
            await self.redis.expire(f"ratelimit:{key}", window.total_seconds())
        
        return current <= limit

# Usage in FastAPI
@app.get("/search")
async def search(request: Request):
    user_id = request.state.user_id
    
    if not await rate_limiter.is_allowed(user_id, limit=100, window=timedelta(minutes=1)):
        raise HTTPException(429, "Rate limit exceeded")
    
    ...
```

### Secrets Management

❌ **No Key Vault Helper**: Each app manually integrates with Key Vault  
❌ **No Secret Caching**: Secrets fetched on every access (slow)  

**To Implement**:
```python
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
from functools import lru_cache

class SecretManager:
    def __init__(self, vault_url: str):
        self.client = SecretClient(vault_url=vault_url, credential=DefaultAzureCredential())
        self._cache = {}
    
    async def get_secret(self, name: str, cache_ttl: int = 300) -> str:
        """Get secret with caching."""
        # Check cache
        if name in self._cache:
            cached_value, cached_at = self._cache[name]
            if time.time() - cached_at < cache_ttl:
                return cached_value
        
        # Fetch from Key Vault
        secret = await self.client.get_secret(name)
        
        # Cache
        self._cache[name] = (secret.value, time.time())
        
        return secret.value

# Usage
secrets = SecretManager(vault_url="https://vault.vault.azure.net")
redis_password = await secrets.get_secret("redis-password")
```

### Health Check Utilities

❌ **No Health Check Helpers**: Each app implements `/health` from scratch  
❌ **No Dependency Checks**: Health endpoints don't check Redis/Cosmos/etc.  

**To Implement**:
```python
from typing import Callable

class HealthCheck:
    def __init__(self):
        self.checks: dict[str, Callable] = {}
    
    def register(self, name: str, check: Callable[[], bool]):
        """Register dependency health check."""
        self.checks[name] = check
    
    async def run(self) -> dict[str, bool]:
        """Run all health checks."""
        results = {}
        for name, check in self.checks.items():
            try:
                results[name] = await check()
            except Exception:
                results[name] = False
        return results

# Usage
health = HealthCheck()

health.register("redis", lambda: redis.ping())
health.register("cosmos", lambda: cosmos.get_database_properties() is not None)

@app.get("/health")
async def health_check():
    results = await health.run()
    status = "healthy" if all(results.values()) else "unhealthy"
    return {"status": status, "checks": results}
```

### Distributed Lock

❌ **No Distributed Lock Util**: No way to coordinate exclusive access across pods  
❌ **Use Case**: Prevent duplicate SAGA execution, ensure single cron job  

**To Implement**:
```python
from redis.asyncio import Redis
import asyncio

class DistributedLock:
    def __init__(self, redis: Redis, key: str, ttl: int = 30):
        self.redis = redis
        self.key = f"lock:{key}"
        self.ttl = ttl
        self.lock_id = str(uuid.uuid4())
    
    async def __aenter__(self):
        """Acquire lock."""
        while True:
            # Try to set lock with NX (only if not exists)
            acquired = await self.redis.set(
                self.key,
                self.lock_id,
                nx=True,
                ex=self.ttl
            )
            
            if acquired:
                return self
            
            # Wait before retry
            await asyncio.sleep(0.1)
    
    async def __aexit__(self, *args):
        """Release lock."""
        # Only delete if we own the lock
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        await self.redis.eval(script, 1, self.key, self.lock_id)

# Usage
async with DistributedLock(redis, "order-123-payment"):
    # Only one pod can execute this block
    await process_payment(order_id="order-123")
```

### Pagination Helpers

❌ **No Pagination Util**: Each app implements offset/cursor pagination manually  

**To Implement**:
```python
from typing import Generic, TypeVar

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    has_next: bool
    
    @classmethod
    def paginate(cls, items: list[T], page: int, page_size: int, total: int):
        start = (page - 1) * page_size
        end = start + page_size
        
        return cls(
            items=items[start:end],
            total=total,
            page=page,
            page_size=page_size,
            has_next=end < total
        )

# Usage
@app.get("/products", response_model=PaginatedResponse[Product])
async def list_products(page: int = 1, page_size: int = 20):
    all_products = await db.fetch_all_products()
    return PaginatedResponse.paginate(all_products, page, page_size, len(all_products))
```

## Extension Guide

### Adding a Custom Validator

**Step 1**: Implement validator function
```python
# lib/src/holiday_peak_lib/utils/validation.py
def validate_phone(phone: str, country: str = "US") -> None:
    """Validate phone number format."""
    patterns = {
        "US": r"^\+1\d{10}$",  # +1XXXXXXXXXX
        "UK": r"^\+44\d{10}$"
    }
    
    pattern = patterns.get(country)
    if not pattern:
        raise ValueError(f"No validation for country: {country}")
    
    if not re.match(pattern, phone):
        raise ValidationError(f"Invalid {country} phone: {phone}")
```

**Step 2**: Use in schemas
```python
from holiday_peak_lib.utils.validation import validate_phone

class Customer(BaseModel):
    phone: str
    
    @validator("phone")
    def validate_phone_format(cls, v):
        validate_phone(v, country="US")
        return v
```

### Creating Custom Telemetry Metric

**Step 1**: Register metric
```python
from opencensus.stats import measure, view, aggregation

cart_value = measure.MeasureFloat("cart/value", "Cart total value", "$")

cart_value_view = view.View(
    "cart_value_distribution",
    "Distribution of cart values",
    ["customer_tier"],
    cart_value,
    aggregation.DistributionAggregation([0, 50, 100, 200, 500, 1000])
)
```

**Step 2**: Track in code
```python
from holiday_peak_lib.utils.telemetry import track_metric

@app.post("/cart/add")
async def add_to_cart(item: CartItem):
    cart = await cart_service.add_item(item)
    
    # Track cart value
    track_metric("cart/value", cart.total, tags={"customer_tier": cart.customer.tier})
```

## Security Considerations

### Current State

⚠️ **Partial Security**:
- ✅ Input sanitization (XSS prevention)
- ✅ URL validation (no javascript: protocol)
- ❌ **No Secrets Encryption**: Secrets in memory as plaintext
- ❌ **No Audit Logging**: No util to log security events

### Recommendations

**Add Audit Logger**:
```python
class AuditLogger:
    def __init__(self, logger):
        self.logger = logger
    
    def log_access(self, user_id: str, resource: str, action: str, result: str):
        """Log access attempt."""
        self.logger.info("audit.access", extra={
            "user_id": user_id,
            "resource": resource,
            "action": action,
            "result": result,  # "allowed" or "denied"
            "timestamp": datetime.utcnow().isoformat()
        })

# Usage
audit = AuditLogger(logger)
audit.log_access("user-123", "order-456", "view", "allowed")
```

**Encrypt Secrets in Memory**:
```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class EncryptedSecret:
    def __init__(self, value: str, key: bytes):
        self.cipher = AESGCM(key)
        self.nonce = os.urandom(12)
        self.ciphertext = self.cipher.encrypt(self.nonce, value.encode(), None)
    
    def decrypt(self) -> str:
        return self.cipher.decrypt(self.nonce, self.ciphertext, None).decode()
```

## Testing

### Current State

⚠️ **Good Unit Test Coverage**:
- ✅ Validator tests (~30 tests)
- ✅ Retry logic tests (~15 tests)
- ✅ Config loader tests (~20 tests)
- ✅ DateTime helper tests (~25 tests)
- ❌ **No Integration Tests**: Telemetry/logging not tested with real Azure Monitor

### Recommendations

**Test Telemetry Integration**:
```python
@pytest.mark.integration
def test_telemetry_exports_to_azure_monitor():
    """Verify spans exported to Azure Monitor."""
    with traced(name="test.span"):
        time.sleep(0.1)
    
    # Check span exported (requires real App Insights)
    # Query Application Insights API for span
    ...
```

## Documentation

### Current State

✅ **Good Docstrings**: All public functions documented  
❌ **No Examples**: No cookbook/recipes for common patterns  

### Recommendation

Add `docs/utils-cookbook.md` with examples:
- How to set up structured logging
- How to integrate feature flags
- How to implement distributed locks
- How to add custom validators

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `LOG_LEVEL` | Logging level | `INFO` | ❌ |
| `LOG_FORMAT` | Log format | `json` | ❌ |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Azure Monitor | - | ⚠️ (for telemetry) |
| `AZURE_APP_CONFIG_ENDPOINT` | App Configuration | - | ⚠️ (for centralized config) |

## Related Components

- **All Components** — Utils used across all libs and apps

## Related ADRs

- [ADR-001: Python 3.13](../../adrs/adr-001-python-3.13.md) — Async support in retry/telemetry

---

**License**: MIT + Microsoft | **Author**: Ricardo Cataldi | **Last Updated**: December 30, 2025
