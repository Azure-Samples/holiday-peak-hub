# Backend Development Governance and Compliance Guidelines

**Version**: 1.0  
**Last Updated**: 2026-01-30  
**Owner**: Backend Team

## Overview

This document defines the coding standards, architectural patterns, and compliance requirements for backend development in the Holiday Peak Hub project. All Python backend code must adhere to these guidelines to ensure consistency, maintainability, security, and scalability.

## Table of Contents

1. [Tech Stack](#tech-stack)
2. [Code Style and Standards](#code-style-and-standards)
3. [Architecture Patterns](#architecture-patterns)
4. [Agent Development](#agent-development)
5. [Adapter Implementation](#adapter-implementation)
6. [Memory Management](#memory-management)
7. [API Design](#api-design)
8. [ACP Compliance](#acp-compliance)
9. [Security Requirements](#security-requirements)
10. [Testing Requirements](#testing-requirements)
11. [Performance Guidelines](#performance-guidelines)
12. [Observability Standards](#observability-standards)

---

## Tech Stack

### Mandatory Stack

**Language**:
- Python 3.13+ (required)
- Async/await for all I/O operations

**Framework**:
- FastAPI 0.115+ for REST APIs
- FastAPI MCP Server for MCP tool exposition
- Pydantic 2.0+ for data validation

**AI Framework**:
- Microsoft Agent Framework
- Azure AI Foundry for model endpoints

**Data Stores**:
- Redis 7+ (hot memory tier)
- Azure Cosmos DB (warm memory tier)
- Azure Blob Storage (cold memory tier)

**Messaging**:
- Azure Event Hubs (event choreography)

**Testing**:
- pytest with pytest-asyncio
- pytest-cov for coverage
- pytest-mock for mocking

**Utilities**:
- uv for package management
- pyproject.toml for dependency management
- Azure Monitor SDK for logging/telemetry

### Prohibited Libraries

❌ **DO NOT USE**:
- Synchronous blocking libraries (requests, use httpx async instead)
- Threading or multiprocessing (use asyncio)
- Global mutable state
- eval() or exec()

---

## Code Style and Standards

### PEP 8 Compliance

**Mandatory**: Strictly follow PEP 8 and all PEP guidelines.

**Key Rules**:
- Indentation: 4 spaces (no tabs)
- Line length: 100 characters maximum
- Imports: grouped and sorted (stdlib, third-party, local)
- Naming: snake_case for functions/variables, PascalCase for classes
- Docstrings: Google style for all public APIs

### Type Hints

✅ **DO**:
- Use type hints for all function parameters and return types
- Use `typing` module for complex types (List, Dict, Optional, Union)
- Use Pydantic models for structured data
- Enable mypy strict mode

```python
from typing import Optional, List
from pydantic import BaseModel

async def get_product(product_id: str) -> Optional[Product]:
    """Fetch product by ID from adapter.
    
    Args:
        product_id: Unique product identifier
        
    Returns:
        Product if found, None otherwise
        
    Raises:
        AdapterError: If external system fails
    """
    pass
```

❌ **DO NOT**:
- Skip type hints
- Use `Any` type without justification
- Mix typed and untyped code

### Import Organization

**Standard Order**:
```python
# Standard library
import asyncio
import logging
from typing import Optional, List

# Third-party
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Local framework
from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.adapters import ProductAdapter
from holiday_peak_lib.memory import HotMemory, WarmMemory

# Local app
from .models import ProductResponse
from .config import settings
```

### Linting and Formatting

**Tools**:
- **pylint**: Code quality checks
- **black**: Code formatting
- **isort**: Import sorting
- **mypy**: Type checking

**Configuration** (pyproject.toml):
```toml
[tool.black]
line-length = 100
target-version = ['py313']

[tool.isort]
profile = "black"
line_length = 100

[tool.mypy]
python_version = "3.13"
strict = true
warn_return_any = true
warn_unused_configs = true

[tool.pylint]
max-line-length = 100
disable = ["C0111", "R0903"]
```

---

## Architecture Patterns

### Adapter Pattern

**Reference**: [ADR-003: Adapter Pattern](../architecture/adrs/adr-003-adapter-pattern.md)

**Purpose**: Pluggable integrations with external retail systems

**Base Interface**:
```python
from abc import ABC, abstractmethod
from typing import Any, Dict

class RetailAdapter(ABC):
    """Base adapter for retail system integrations."""
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to external system."""
        pass
    
    @abstractmethod
    async def fetch_data(self, query: Dict[str, Any]) -> Any:
        """Fetch data from external system."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Clean up connection resources."""
        pass
```

**Implementation Rules**:
- All adapters extend `RetailAdapter`
- Use async/await for all I/O operations
- Implement retry logic with exponential backoff
- Log all external calls
- Handle errors gracefully

### Builder Pattern

**Reference**: [ADR-004: Builder Pattern](../architecture/adrs/adr-004-builder-pattern-memory.md)

**Purpose**: Flexible agent and memory configuration

**Usage**:
```python
from holiday_peak_lib.agents import AgentBuilder
from holiday_peak_lib.memory import MemorySettings

# Build agent with memory tiers
agent = (
    AgentBuilder()
    .with_memory(MemorySettings(
        redis_url=settings.REDIS_URL,
        cosmos_account_uri=settings.COSMOS_URI,
        blob_account_url=settings.BLOB_URL,
    ))
    .with_slm_config(slm_config)
    .with_llm_config(llm_config)
    .build()
)
```

### SAGA Choreography

**Reference**: [ADR-007: SAGA Choreography](../architecture/adrs/adr-007-saga-choreography.md)

**Purpose**: Distributed transaction coordination

**Pattern**:
```python
from azure.eventhub.aio import EventHubProducerClient
from holiday_peak_lib.orchestration import SagaEvent

async def publish_order_created(order_id: str, user_id: str):
    """Publish order created event for saga participants."""
    event = SagaEvent(
        saga_id=order_id,
        event_type="order.created",
        payload={"order_id": order_id, "user_id": user_id},
        timestamp=datetime.utcnow(),
    )
    
    async with EventHubProducerClient.from_connection_string(
        settings.EVENT_HUB_CONNECTION_STRING
    ) as producer:
        await producer.send_event(event.to_event_data())
```

---

## Agent Development

### Base Agent Structure

**Reference**: [ADR-006: Agent Framework](../architecture/adrs/adr-006-agent-framework.md)

**Standard Template**:
```python
from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.memory import HotMemory, WarmMemory, ColdMemory
from .adapters import ProductAdapter

class ProductAgent(BaseRetailAgent):
    """Agent for product management operations."""
    
    def __init__(
        self,
        product_adapter: ProductAdapter,
        hot_memory: HotMemory,
        warm_memory: WarmMemory,
        cold_memory: ColdMemory,
    ):
        super().__init__(
            name="product-agent",
            hot_memory=hot_memory,
            warm_memory=warm_memory,
            cold_memory=cold_memory,
        )
        self.product_adapter = product_adapter
    
    async def handle_query(self, query: str, context: Dict[str, Any]) -> str:
        """Process product-related query."""
        # 1. Check hot memory
        cached = await self.hot_memory.get(query)
        if cached:
            return cached
        
        # 2. Fetch from adapter
        result = await self.product_adapter.fetch_data({"query": query})
        
        # 3. Store in memory tiers
        await self.hot_memory.set(query, result, ttl=300)
        await self.warm_memory.set(query, result)
        
        return result
```

### Model Routing

**Reference**: [ADR-013: SLM-First Routing](../architecture/adrs/adr-013-model-routing.md)

**Strategy**: Route simple queries to SLM, complex to LLM

```python
from holiday_peak_lib.agents import FoundryAgentConfig

# Configure both models
slm_config = FoundryAgentConfig(
    endpoint=settings.FOUNDRY_ENDPOINT,
    agent_id=settings.FOUNDRY_AGENT_ID_FAST,
    deployment_name=settings.MODEL_DEPLOYMENT_NAME_FAST,
)

llm_config = FoundryAgentConfig(
    endpoint=settings.FOUNDRY_ENDPOINT,
    agent_id=settings.FOUNDRY_AGENT_ID_RICH,
    deployment_name=settings.MODEL_DEPLOYMENT_NAME_RICH,
)

# Agent will route automatically based on complexity
agent = AgentBuilder().with_slm_config(slm_config).with_llm_config(llm_config).build()
```

---

## Adapter Implementation

### Adapter Boundaries

**Reference**: [ADR-012: Adapter Boundaries](../architecture/adrs/adr-012-adapter-boundaries.md)

**Rules**:
- One adapter per external system
- Adapters are stateless
- No business logic in adapters (only translation)
- Use circuit breaker pattern for fault tolerance

**Example**:
```python
from typing import Optional, Dict, Any
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

class CRMAdapter(RetailAdapter):
    """Adapter for CRM system integration."""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.client: Optional[httpx.AsyncClient] = None
    
    async def connect(self) -> None:
        """Initialize HTTP client."""
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=30.0,
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def fetch_customer_profile(self, customer_id: str) -> Dict[str, Any]:
        """Fetch customer profile from CRM."""
        if not self.client:
            raise RuntimeError("Adapter not connected")
        
        response = await self.client.get(f"/customers/{customer_id}")
        response.raise_for_status()
        
        return response.json()
    
    async def disconnect(self) -> None:
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
```

---

## Memory Management

### Three-Tier Architecture

**Reference**: [ADR-008: Memory Tiers](../architecture/adrs/adr-008-memory-tiers.md)

**Hot Tier (Redis)**:
- TTL: 5-30 minutes
- Use for: Session data, cart state, real-time inventory
- Size limit: 100KB per key

**Warm Tier (Cosmos DB)**:
- TTL: 30 days
- Use for: Customer profiles, order history, product catalog
- Partition key: User ID or Product ID

**Cold Tier (Blob Storage)**:
- TTL: 7 years (compliance)
- Use for: Historical data, analytics, audit logs

**Memory Partitioning**:
**Reference**: [ADR-014: Memory Partitioning](../architecture/adrs/adr-014-memory-partitioning.md)

```python
from holiday_peak_lib.memory import MemorySettings, HotMemory, WarmMemory, ColdMemory

# Configure memory tiers
memory_settings = MemorySettings(
    redis_url=settings.REDIS_URL,
    cosmos_account_uri=settings.COSMOS_ACCOUNT_URI,
    cosmos_database=settings.COSMOS_DATABASE,
    cosmos_container=settings.COSMOS_CONTAINER,
    blob_account_url=settings.BLOB_ACCOUNT_URL,
    blob_container=settings.BLOB_CONTAINER,
)

# Initialize tiers
hot_memory = HotMemory(memory_settings)
warm_memory = WarmMemory(memory_settings)
cold_memory = ColdMemory(memory_settings)

# Usage
await hot_memory.set("cart:user123", cart_data, ttl=1800)  # 30 min
await warm_memory.set("profile:user123", profile_data)     # 30 days
await cold_memory.set("audit:order123", audit_log)          # 7 years
```

---

## API Design

### FastAPI Standards

**Reference**: [ADR-005: FastAPI + MCP](../architecture/adrs/adr-005-fastapi-mcp.md)

**Endpoint Pattern**:
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Product Service", version="1.0.0")

class ProductRequest(BaseModel):
    product_id: str
    enrich: bool = True

class ProductResponse(BaseModel):
    product_id: str
    name: str
    price: float
    inventory: int

@app.post("/invoke", response_model=ProductResponse)
async def invoke_agent(request: ProductRequest) -> ProductResponse:
    """Main agent invocation endpoint."""
    try:
        result = await agent.handle_query(
            query=f"Get product {request.product_id}",
            context={"enrich": request.enrich},
        )
        return ProductResponse(**result)
    except Exception as e:
        logger.error(f"Agent invocation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "product-service"}
```

### MCP Tool Exposition

**Reference**: [ADR-010: REST + MCP](../architecture/adrs/adr-010-rest-and-mcp-exposition.md)

```python
from fastapi_mcp import FastAPIMCPServer

mcp_server = FastAPIMCPServer(app)

@mcp_server.tool()
async def get_product_context(product_id: str) -> Dict[str, Any]:
    """MCP tool: Get product context for agents.
    
    Args:
        product_id: Product identifier
        
    Returns:
        Product context dictionary
    """
    return await product_adapter.fetch_data({"product_id": product_id})

# Register at endpoint
app.add_route("/product/context", mcp_server.create_handler())
```

---

## ACP Compliance

**Reference**: [ADR-014: ACP Alignment](../architecture/adrs/adr-014-acp-alignment.md)

### Schema Validation

```python
from pydantic import BaseModel, Field
from typing import List, Optional

class ACPPrice(BaseModel):
    """ACP-compliant price model."""
    amount: float
    currency: str = Field(..., min_length=3, max_length=3)
    compare_at: Optional[float] = None

class ACPAvailability(BaseModel):
    """ACP-compliant availability model."""
    in_stock: bool
    quantity: Optional[int] = None
    estimated_delivery: Optional[str] = None

class ACPProduct(BaseModel):
    """ACP-compliant product model."""
    id: str
    name: str
    description: str
    brand: Optional[str] = None
    category: List[str]
    price: ACPPrice
    availability: ACPAvailability
    images: List[str]
    attributes: Optional[Dict[str, Any]] = None
```

### Transformation

```python
async def transform_to_acp(raw_product: Dict[str, Any]) -> ACPProduct:
    """Transform raw product data to ACP format."""
    return ACPProduct(
        id=raw_product["product_id"],
        name=raw_product["product_name"],
        description=raw_product.get("description", ""),
        brand=raw_product.get("brand_name"),
        category=raw_product.get("categories", []),
        price=ACPPrice(
            amount=raw_product["price"],
            currency=raw_product.get("currency", "USD"),
            compare_at=raw_product.get("compare_at_price"),
        ),
        availability=ACPAvailability(
            in_stock=raw_product["stock_quantity"] > 0,
            quantity=raw_product["stock_quantity"],
        ),
        images=raw_product.get("images", []),
    )
```

---

## Security Requirements

### Authentication

✅ **DO**:
- Validate all incoming requests
- Use Azure AD or OAuth 2.0 for authentication
- Store credentials in Azure Key Vault
- Rotate secrets regularly

❌ **DO NOT**:
- Store credentials in code or config files
- Use hardcoded API keys
- Log sensitive data
- Expose internal error details to clients

### Authorization

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def verify_token(credentials: HTTPBearer = Depends(security)) -> Dict[str, Any]:
    """Verify JWT token and extract claims."""
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET,
            algorithms=["HS256"],
        )
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/admin/data")
async def get_admin_data(user: Dict = Depends(verify_token)) -> Dict:
    """Protected endpoint requiring authentication."""
    if "admin" not in user.get("roles", []):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    return {"data": "sensitive admin data"}
```

### Input Validation

```python
from pydantic import BaseModel, validator, Field

class ProductQuery(BaseModel):
    """Validated product query model."""
    
    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(10, ge=1, le=100)
    offset: int = Field(0, ge=0)
    
    @validator("query")
    def validate_query(cls, v: str) -> str:
        """Sanitize query string."""
        # Remove SQL injection patterns
        dangerous = ["--", "/*", "*/", "xp_", "sp_"]
        for pattern in dangerous:
            if pattern in v.lower():
                raise ValueError(f"Invalid pattern in query: {pattern}")
        return v.strip()
```

---

## Testing Requirements

### Test Coverage Requirements

**Minimum Coverage**:
- Unit tests: 80% coverage
- Integration tests: 60% coverage
- Critical paths: 100% coverage

### Unit Testing

**Test Every**:
- Adapter methods
- Agent handlers
- Memory operations
- Validators and transformers
- Utility functions

**Example**:
```python
# tests/test_product_adapter.py
import pytest
from unittest.mock import AsyncMock, patch
from adapters.product_adapter import ProductAdapter

@pytest.mark.asyncio
async def test_fetch_product_success():
    """Test successful product fetch."""
    adapter = ProductAdapter(base_url="http://test", api_key="test")
    adapter.client = AsyncMock()
    adapter.client.get.return_value.json.return_value = {
        "product_id": "123",
        "product_name": "Test Product",
        "price": 99.99,
    }
    
    result = await adapter.fetch_product("123")
    
    assert result["product_id"] == "123"
    assert result["product_name"] == "Test Product"
    adapter.client.get.assert_called_once_with("/products/123")

@pytest.mark.asyncio
async def test_fetch_product_retry():
    """Test retry logic on failure."""
    adapter = ProductAdapter(base_url="http://test", api_key="test")
    adapter.client = AsyncMock()
    adapter.client.get.side_effect = [
        Exception("Network error"),
        Exception("Network error"),
        AsyncMock(json=lambda: {"product_id": "123"}),
    ]
    
    result = await adapter.fetch_product("123")
    
    assert result["product_id"] == "123"
    assert adapter.client.get.call_count == 3
```

### Integration Testing

```python
# tests/integration/test_agent_flow.py
import pytest
from fastapi.testclient import TestClient
from main import app

@pytest.mark.asyncio
async def test_full_agent_invocation():
    """Test complete agent invocation flow."""
    client = TestClient(app)
    
    response = client.post(
        "/invoke",
        json={"product_id": "123", "enrich": True},
        headers={"Authorization": "Bearer test_token"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "product_id" in data
    assert "name" in data
    assert "price" in data
```

---

## Performance Guidelines

### Async/Await Best Practices

✅ **DO**:
- Use async/await for all I/O operations
- Use `asyncio.gather()` for parallel operations
- Use `asyncio.create_task()` for fire-and-forget
- Set timeouts for external calls

```python
import asyncio

async def fetch_product_details(product_id: str) -> Dict[str, Any]:
    """Fetch product details from multiple sources in parallel."""
    # Parallel fetch from multiple adapters
    product_task = product_adapter.fetch_product(product_id)
    inventory_task = inventory_adapter.fetch_stock(product_id)
    pricing_task = pricing_adapter.fetch_price(product_id)
    
    product, inventory, pricing = await asyncio.gather(
        product_task,
        inventory_task,
        pricing_task,
        return_exceptions=True,  # Don't fail if one fails
    )
    
    return {
        "product": product if not isinstance(product, Exception) else None,
        "inventory": inventory if not isinstance(inventory, Exception) else None,
        "pricing": pricing if not isinstance(pricing, Exception) else None,
    }
```

### Caching Strategy

```python
from functools import lru_cache
from typing import Optional

# In-memory cache for config
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()

# Redis cache with TTL
async def get_product_with_cache(product_id: str) -> Optional[ACPProduct]:
    """Get product with Redis caching."""
    # Check cache
    cached = await hot_memory.get(f"product:{product_id}")
    if cached:
        logger.info(f"Cache hit for product {product_id}")
        return ACPProduct(**cached)
    
    # Fetch from adapter
    raw_product = await product_adapter.fetch_product(product_id)
    acp_product = await transform_to_acp(raw_product)
    
    # Store in cache
    await hot_memory.set(
        f"product:{product_id}",
        acp_product.dict(),
        ttl=300,  # 5 minutes
    )
    
    return acp_product
```

### Performance Targets

- **API Response Time**: < 200ms (p95)
- **Memory Usage**: < 512MB per service
- **CPU Usage**: < 70% average
- **Database Queries**: < 50ms (p95)

---

## Observability Standards

### Structured Logging

```python
import logging
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()

# Usage
logger.info(
    "product.fetched",
    product_id=product_id,
    source="adapter",
    duration_ms=duration,
    cache_hit=cache_hit,
)

logger.error(
    "adapter.error",
    adapter="product",
    error=str(e),
    product_id=product_id,
    retry_count=retry_count,
)
```

### Telemetry

```python
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace

# Configure Azure Monitor
configure_azure_monitor(
    connection_string=settings.APPLICATIONINSIGHTS_CONNECTION_STRING
)

tracer = trace.get_tracer(__name__)

async def fetch_with_telemetry(product_id: str) -> Dict[str, Any]:
    """Fetch product with distributed tracing."""
    with tracer.start_as_current_span("fetch_product") as span:
        span.set_attribute("product.id", product_id)
        span.set_attribute("service.name", "product-service")
        
        try:
            result = await product_adapter.fetch_product(product_id)
            span.set_attribute("result.status", "success")
            return result
        except Exception as e:
            span.set_attribute("result.status", "error")
            span.record_exception(e)
            raise
```

### Metrics

```python
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
request_count = Counter(
    "product_requests_total",
    "Total product requests",
    ["endpoint", "status"],
)

request_duration = Histogram(
    "product_request_duration_seconds",
    "Product request duration",
    ["endpoint"],
)

cache_hit_rate = Gauge(
    "cache_hit_rate",
    "Cache hit rate",
    ["cache_tier"],
)

# Usage
@app.post("/invoke")
async def invoke_agent(request: ProductRequest):
    with request_duration.labels(endpoint="/invoke").time():
        try:
            result = await agent.handle_query(...)
            request_count.labels(endpoint="/invoke", status="success").inc()
            return result
        except Exception:
            request_count.labels(endpoint="/invoke", status="error").inc()
            raise
```

---

## Documentation Requirements

### Function Documentation

```python
def calculate_shipping_cost(
    weight_kg: float,
    distance_km: float,
    carrier: str,
) -> float:
    """Calculate shipping cost based on weight, distance, and carrier.
    
    Uses carrier-specific rate tables and applies volume discounts
    for weights over 10kg.
    
    Args:
        weight_kg: Package weight in kilograms
        distance_km: Shipping distance in kilometers
        carrier: Carrier code (e.g., 'ups', 'fedex', 'usps')
        
    Returns:
        Shipping cost in USD
        
    Raises:
        ValueError: If weight or distance is negative
        KeyError: If carrier is not supported
        
    Examples:
        >>> calculate_shipping_cost(5.0, 100.0, 'ups')
        12.50
        >>> calculate_shipping_cost(15.0, 500.0, 'fedex')
        45.75
    """
    pass
```

### Module Documentation

Every module must have a docstring:

```python
"""Product management service.

This module provides the core product management functionality including:
- Product catalog search
- Product detail enrichment with ACP
- Inventory validation
- Price computation

The service integrates with:
- Product Management Adapter
- Inventory Service
- Pricing Service
- AI Search

Example:
    >>> from product_service import ProductAgent
    >>> agent = ProductAgent(product_adapter, memory)
    >>> result = await agent.fetch_product("prod-123")
"""
```

---

## References

### Architecture Decision Records

- [ADR-001: Python 3.13](../architecture/adrs/adr-001-python-3.13.md)
- [ADR-002: Azure Services](../architecture/adrs/adr-002-azure-services.md)
- [ADR-003: Adapter Pattern](../architecture/adrs/adr-003-adapter-pattern.md)
- [ADR-004: Builder Pattern](../architecture/adrs/adr-004-builder-pattern-memory.md)
- [ADR-005: FastAPI + MCP](../architecture/adrs/adr-005-fastapi-mcp.md)
- [ADR-006: Agent Framework](../architecture/adrs/adr-006-agent-framework.md)
- [ADR-007: SAGA Choreography](../architecture/adrs/adr-007-saga-choreography.md)
- [ADR-008: Memory Tiers](../architecture/adrs/adr-008-memory-tiers.md)
- [ADR-012: Adapter Boundaries](../architecture/adrs/adr-012-adapter-boundaries.md)
- [ADR-013: Model Routing](../architecture/adrs/adr-013-model-routing.md)
- [ADR-014: Memory Partitioning](../architecture/adrs/adr-014-memory-partitioning.md)

### Component Documentation

- [Lib Components](../architecture/components.md#libs-framework-components)
- [App Components](../architecture/components.md#apps-domain-services)

---

## Revision History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-01-30 | Initial documentation | Backend Team |
