# Architecture Implementation Plan

**Date**: January 30, 2026  
**Version**: 1.0  
**Status**: Ready for Implementation  
**Target Completion**: Q1 2026

---

## Overview

This document provides a comprehensive implementation plan to achieve 100% compliance with Agentic Architecture Patterns and deploy a production-ready Holiday Peak Hub solution.

**Current Compliance**: 65%  
**Target Compliance**: 100%  
**Implementation Phases**: 4 phases over 16 weeks

**Critical Gap**: MCP adapter layer not implemented - agents cannot execute CRUD operations or call 3rd party APIs

---

## Current Status Update (January 30, 2026)

**Completed**:
- CRUD service now calls agent REST endpoints with circuit breaker + retries.
- Frontend semantic search integration (agent API client + search page) with CRUD fallback.

**Pending / Not Yet Implemented**:
- API Gateway (APIM) configuration for `/agents/catalog-search/semantic` and `/agents/campaign-intelligence/analytics`.
- RBAC enforcement and rate limits in APIM policies.
- Load testing and Helm-based agent deployment scripts.
- Monitoring dashboards validation and production smoke tests.

---

## Phase 1: MCP Adapter Layer Implementation (Weeks 1-4)

### Objective
Implement MCP adapter layer in all 21 agent services to enable agents to execute CRUD operations and call 3rd party APIs via MCP tools.

**Critical**: This is the highest priority gap (P0) from compliance analysis. Agents currently cannot perform CRUD operations or call external APIs.

### Architecture Pattern
- **CRUD → Agent**: REST (for fast enrichment) - unchanged
- **Agent → CRUD**: MCP tools in adapter layer (not REST)
- **Agent → 3rd Party APIs**: MCP tools in adapter layer
- **Agent → Agent**: MCP for contextual communication

### 1.1 Base Adapter Framework (Week 1)

#### 1.1.1 Create Base CRUD Adapter

```python
# lib/src/holiday_peak_lib/adapters/crud_adapter.py

from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer
import httpx
import structlog

logger = structlog.get_logger()

class BaseCRUDAdapter:
    """Base adapter exposing MCP tools for CRUD operations."""
    
    def __init__(self, crud_base_url: str, name: str = "crud-adapter"):
        self.crud_base_url = crud_base_url
        self.mcp_server = FastAPIMCPServer(
            name=name,
            version="1.0.0"
        )
        self._register_base_tools()
    
    def _register_base_tools(self):
        """Register common CRUD operation MCP tools."""
        
        @self.mcp_server.tool()
        async def get_product(product_id: str) -> dict:
            """Get product details from CRUD service."""
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.crud_base_url}/products/{product_id}"
                )
                response.raise_for_status()
                return response.json()
        
        @self.mcp_server.tool()
        async def update_order_status(
            order_id: str,
            status: str,
            metadata: dict | None = None
        ) -> dict:
            """Update order status in CRUD service."""
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.crud_base_url}/orders/{order_id}",
                    json={"status": status, "metadata": metadata}
                )
                response.raise_for_status()
                return response.json()
        
        @self.mcp_server.tool()
        async def get_inventory_level(sku: str) -> dict:
            """Get current inventory level from CRUD service."""
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.crud_base_url}/inventory/{sku}"
                )
                response.raise_for_status()
                return response.json()
        
        @self.mcp_server.tool()
        async def create_customer_ticket(
            user_id: str,
            subject: str,
            description: str
        ) -> dict:
            """Create support ticket in CRUD service."""
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.crud_base_url}/tickets",
                    json={
                        "user_id": user_id,
                        "subject": subject,
                        "description": description
                    }
                )
                response.raise_for_status()
                return response.json()
```

#### 1.1.2 Create Base 3rd Party Adapter Template

```python
# lib/src/holiday_peak_lib/adapters/external_api_adapter.py

from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer
import httpx

class BaseExternalAPIAdapter:
    """Base adapter for exposing MCP tools for 3rd party APIs."""
    
    def __init__(self, api_name: str):
        self.mcp_server = FastAPIMCPServer(
            name=f"{api_name}-adapter",
            version="1.0.0"
        )
        self.api_key = None  # Set in child class
        self.base_url = None  # Set in child class
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> dict:
        """Make authenticated request to 3rd party API."""
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                f"{self.base_url}{endpoint}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                **kwargs
            )
            response.raise_for_status()
            return response.json()
```

**Deliverables (Week 1)**:
- ✅ Base CRUD adapter framework
- ✅ Base external API adapter template
- ✅ MCP tool registration patterns
- ✅ Unit tests for base adapters

---

### 1.2 E-commerce Domain Adapters (Week 2)

#### 1.2.1 Catalog Search Agent - CRUD Adapter

```python
# apps/ecommerce-catalog-search/src/catalog_search_service/event_handlers.py

from azure.eventhub.aio import EventHubConsumerClient
from .indexer import update_search_index

async def handle_product_event(partition_context, event):
    """Handle product CRUD events and update search index"""
    data = json.loads(event.body_as_str())
    event_type = data["event_type"]
    product_data = data["data"]
    
    if event_type == "product.created":
        await update_search_index("add", product_data)
    elif event_type == "product.updated":
        await update_search_index("update", product_data)
    elif event_type == "product.deleted":
        await update_search_index("delete", product_data)
    
    await partition_context.update_checkpoint(event)

async def start_consumer():
    consumer = EventHubConsumerClient.from_connection_string(
        conn_str=settings.EVENTHUB_CONNECTION_STRING,
        consumer_group="catalog-search-group",
        eventhub_name="product-events"
    )
    
    async with consumer:
        await consumer.receive(
            on_event=handle_product_event,
            starting_position="-1"
        )
```

**Deployment**:
```yaml
# apps/ecommerce-catalog-search/k8s/deployment.yaml
containers:
- name: catalog-search
  image: catalog-search:latest
  env:
  - name: CRUD_SERVICE_URL
    value: "http://crud-service:8080"
  - name: EVENTHUB_CONNECTION_STRING
    valueFrom:
      secretKeyRef:
        name: eventhub-secret
        key: connection-string
```

```python
# apps/ecommerce-catalog-search/src/catalog_search_service/adapters.py

from holiday_peak_lib.adapters.crud_adapter import BaseCRUDAdapter
import httpx

class CatalogSearchCRUDAdapter(BaseCRUDAdapter):
    """CRUD adapter for catalog search agent."""
    
    def __init__(self, crud_base_url: str):
        super().__init__(crud_base_url, name="catalog-search-crud-adapter")
        self._register_search_tools()
    
    def _register_search_tools(self):
        """Register search-specific MCP tools."""
        
        @self.mcp_server.tool()
        async def get_products_batch(product_ids: list[str]) -> list[dict]:
            """Get multiple products for indexing."""
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.crud_base_url}/products/batch",
                    json={"ids": product_ids}
                )
                response.raise_for_status()
                return response.json()

# Agent Integration
from .adapters import CatalogSearchCRUDAdapter

crud_adapter = CatalogSearchCRUDAdapter(settings.CRUD_SERVICE_URL)

# Agent uses MCP tool to fetch products
async def index_product(product_id: str):
    """Agent calls CRUD via MCP tool."""
    product = await agent.call_tool("get_product", product_id=product_id)
    await search_index.add(product)
```

#### 1.2.2 Product Detail Enrichment Agent - CRUD Adapter

```python
# apps/ecommerce-product-detail-enrichment/src/enrichment_service/adapters.py

from holiday_peak_lib.adapters.crud_adapter import BaseCRUDAdapter

class EnrichmentCRUDAdapter(BaseCRUDAdapter):
    """CRUD adapter for product enrichment agent."""
    
    def __init__(self, crud_base_url: str):
        super().__init__(crud_base_url, name="enrichment-crud-adapter")
        # Inherits get_product tool from base

# Agent uses adapter to fetch products
crud_adapter = EnrichmentCRUDAdapter(settings.CRUD_SERVICE_URL)

async def enrich_product(product_id: str):
    """Agent enriches product by calling CRUD via MCP."""
    product = await agent.call_tool("get_product", product_id=product_id)
    acp_metadata = await generate_acp_metadata(product)
    return acp_metadata
```

#### 1.2.3 Cart Intelligence Agent - CRUD Adapter

```python
# apps/ecommerce-cart-intelligence/src/cart_service/adapters.py

from holiday_peak_lib.adapters.crud_adapter import BaseCRUDAdapter
import httpx

class CartCRUDAdapter(BaseCRUDAdapter):
    """CRUD adapter for cart intelligence agent."""
    
    def __init__(self, crud_base_url: str):
        super().__init__(crud_base_url, name="cart-crud-adapter")
        self._register_cart_tools()
    
    def _register_cart_tools(self):
        @self.mcp_server.tool()
        async def get_user_order_history(user_id: str, limit: int = 10) -> list[dict]:
            """Get user order history for recommendations."""
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.crud_base_url}/users/{user_id}/orders",
                    params={"limit": limit}
                )
                return response.json()

# Agent uses adapter
crud_adapter = CartCRUDAdapter(settings.CRUD_SERVICE_URL)

async def get_recommendations(user_id: str):
    """Get personalized recommendations using MCP tool."""
    order_history = await agent.call_tool("get_user_order_history", user_id=user_id, limit=10)
    recommendations = await generate_recommendations(order_history)
    return recommendations
```

#### 1.2.4-1.2.5 Checkout Support & Order Status Agents

[Similar CRUD adapter implementations]

**Deliverables (Week 2)**:
- ✅ 5 E-commerce domain adapters implemented
- ✅ MCP tools registered for CRUD operations
- ✅ Unit tests for all adapter tools
- ✅ Integration tests with CRUD service
- ✅ Deployment manifests updated

---

### 1.3 CRM & Inventory Domain Adapters (Week 3)

#### 1.3.1 Profile Aggregation Agent - CRUD Adapter

```python
# apps/crm-profile-aggregation/src/profile_service/adapters.py

class ProfileCRUDAdapter(BaseCRUDAdapter):
    def __init__(self, crud_base_url: str):
        super().__init__(crud_base_url, name="profile-crud-adapter")
        self._register_profile_tools()
    
    def _register_profile_tools(self):
        @self.mcp_server.tool()
        async def get_user_profile(user_id: str) -> dict:
            """Get user profile from CRUD."""
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.crud_base_url}/users/{user_id}")
                return response.json()
        
        @self.mcp_server.tool()
        async def update_user_profile(user_id: str, profile_data: dict) -> dict:
            """Update user profile in CRUD."""
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.crud_base_url}/users/{user_id}",
                    json=profile_data
                )
                return response.json()
```

#### 1.3.2-1.3.4 Segmentation, Campaign Intelligence, Support Agents

[Similar CRUD adapter implementations]

#### 1.3.5 Inventory Health Check Agent - CRUD Adapter

```python
# apps/inventory-health-check/src/health_service/adapters.py

class InventoryCRUDAdapter(BaseCRUDAdapter):
    def __init__(self, crud_base_url: str):
        super().__init__(crud_base_url, name="inventory-crud-adapter")
        self._register_inventory_tools()
    
    def _register_inventory_tools(self):
        @self.mcp_server.tool()
        async def update_inventory_alert(
            sku: str,
            alert_type: str,
            threshold: int
        ) -> dict:
            """Create inventory alert in CRUD."""
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.crud_base_url}/inventory/alerts",
                    json={
                        "sku": sku,
                        "alert_type": alert_type,
                        "threshold": threshold
                    }
                )
                return response.json()
```

**Deliverables (Week 3)**:
- ✅ 8 CRM & Inventory adapters implemented
- ✅ MCP tools for profile updates, inventory alerts
- ✅ Unit tests passing

---

### 1.4 Logistics & Product Management Domain Adapters (Week 4)

#### 1.4.1 Carrier Selection Agent - 3rd Party API Adapter (Example)
        # Invalidate cached recommendations
        await memory.delete(f"recommendations:{user_id}")
    
    await partition_context.update_checkpoint(event)
```

#### 1.1.4 Checkout Support Agent
**Event Topics**: `order-events`, `inventory-events`

```python
# apps/ecommerce-checkout-support/src/checkout_service/event_handlers.py

async def handle_inventory_event(partition_context, event):
    """Adjust checkout validation rules based on inventory changes"""
    data = json.loads(event.body_as_str())
    event_type = data["event_type"]
    
    if event_type == "inventory.low_stock":
        sku = data["data"]["sku"]
        # Enable scarcity messaging
        await memory.store(f"scarcity:{sku}", {"enabled": True, "stock": data["data"]["quantity"]})
    
    await partition_context.update_checkpoint(event)
```

#### 1.1.5 Order Status Agent
**Event Topics**: `order-events`

```python
# apps/ecommerce-order-status/src/order_status_service/event_handlers.py

async def handle_order_event(partition_context, event):
    """Track order lifecycle and proactive notifications"""
    data = json.loads(event.body_as_str())
    event_type = data["event_type"]
    order_data = data["data"]
    
    if event_type == "order.status_changed":
        # Update order tracking cache
        await memory.store(f"order_status:{order_data['id']}", order_data)
        
        # Trigger proactive notification if needed
        if order_data["status"] in ["shipped", "delivered"]:
            await send_notification(order_data)
    
    await partition_context.update_checkpoint(event)
```

**Deliverables (Week 2)**:
- ✅ 5 E-commerce domain adapters implemented:
  - Catalog Search (CRUD adapter)
  - Product Detail Enrichment (CRUD adapter)
  - Cart Intelligence (CRUD adapter)
  - Checkout Support (CRUD adapter)
  - Order Status (CRUD adapter)
- ✅ MCP tools registered for all adapters
- ✅ Unit tests for adapter tools
- ✅ Integration tests with CRUD service
- ✅ Deployment manifests updated with adapter initialization

---

### 1.3 CRM & Inventory Domain Adapters (Week 3)

#### 1.2.1 Profile Aggregation Agent
**Event Topics**: `user-events`, `order-events`

```python
# apps/crm-profile-aggregation/src/profile_service/event_handlers.py

async def handle_user_event(partition_context, event):
    """Aggregate user profile data from multiple sources"""
    data = json.loads(event.body_as_str())
    event_type = data["event_type"]
    user_data = data["data"]
    
    if event_type == "user.registered":
        # Create initial profile
        profile = await create_profile(user_data)
        await store_profile(profile)
    elif event_type == "user.updated":
        # Update profile
        await update_profile(user_data)
    
    await partition_context.update_checkpoint(event)

async def handle_order_event(partition_context, event):
    """Enrich profile with order history"""
    data = json.loads(event.body_as_str())
    event_type = data["event_type"]
    
    if event_type == "order.placed":
        order_data = data["data"]
        user_id = order_data["user_id"]
        
        # Update purchase history
        await append_order_to_profile(user_id, order_data)
        
        # Recalculate LTV
        await recalculate_lifetime_value(user_id)
    
    await partition_context.update_checkpoint(event)
```

#### 1.2.2 Segmentation/Personalization Agent
**Event Topics**: `order-events`

```python
# apps/crm-segmentation-personalization/src/segmentation_service/event_handlers.py

async def handle_order_event(partition_context, event):
    """Update customer segments based on purchase behavior"""
    data = json.loads(event.body_as_str())
    event_type = data["event_type"]
    
    if event_type == "order.placed":
        order_data = data["data"]
        user_id = order_data["user_id"]
        
        # Re-evaluate segment membership
        new_segments = await recalculate_segments(user_id, order_data)
        
        # Update segment assignments
        await update_user_segments(user_id, new_segments)
        
        # Trigger personalization rules update
        await refresh_personalization_rules(user_id)
    
    await partition_context.update_checkpoint(event)
```

#### 1.2.3 Campaign Intelligence Agent
**Event Topics**: `order-events`, `user-events`

```python
# apps/crm-campaign-intelligence/src/campaign_service/event_handlers.py

async def handle_order_event(partition_context, event):
    """Update campaign effectiveness metrics"""
    data = json.loads(event.body_as_str())
    event_type = data["event_type"]
    
    if event_type == "order.placed":
        order_data = data["data"]
        
        # Check if order attributed to campaign
        if "campaign_id" in order_data:
            await update_campaign_metrics(
                campaign_id=order_data["campaign_id"],
                order_value=order_data["total"]
            )
    
    await partition_context.update_checkpoint(event)
```

#### 1.2.4 Support Assistance Agent
**Event Topics**: `order-events`

```python
# apps/crm-support-assistance/src/support_service/event_handlers.py

async def handle_order_event(partition_context, event):
    """Update support knowledge base with order context"""
    data = json.loads(event.body_as_str())
    event_type = data["event_type"]
    
    if event_type == "order.cancelled":
        order_data = data["data"]
        
        # Flag potential support issue
        await flag_for_support_review(order_data)
        
        # Update FAQs if pattern detected
        if await detect_common_issue(order_data):
            await update_knowledge_base(order_data)
    
    await partition_context.update_checkpoint(event)
```

**Deliverables (Week 4)**:
- ✅ 4 CRM event handlers implemented
- ✅ Multi-topic subscription patterns
- ✅ Profile aggregation logic tested
- ✅ Deployment manifests updated

---

### 1.3 Inventory Domain (Week 5)

#### 1.3.1 Health Check Agent
**Event Topics**: `order-events`, `inventory-events`

```python
# apps/inventory-health-check/src/health_service/event_handlers.py

async def handle_order_event(partition_context, event):
    """Monitor inventory levels after orders"""
    data = json.loads(event.body_as_str())
    event_type = data["event_type"]
    
    if event_type == "order.placed":
        order_data = data["data"]
        
        for item in order_data["items"]:
            sku = item["sku"]
            quantity = item["quantity"]
            
            # Check if stock level requires attention
            current_stock = await get_current_stock(sku)
            if current_stock - quantity < settings.LOW_STOCK_THRESHOLD:
                await trigger_low_stock_alert(sku, current_stock - quantity)
    
    await partition_context.update_checkpoint(event)
```

#### 1.3.2 JIT Replenishment Agent
**Event Topics**: `inventory-events`

```python
# apps/inventory-jit-replenishment/src/replenishment_service/event_handlers.py

async def handle_inventory_event(partition_context, event):
    """Trigger replenishment when low stock detected"""
    data = json.loads(event.body_as_str())
    event_type = data["event_type"]
    
    if event_type == "inventory.low_stock":
        inventory_data = data["data"]
        sku = inventory_data["sku"]
        current_stock = inventory_data["quantity"]
        
        # Calculate reorder quantity
        reorder_qty = await calculate_reorder_quantity(sku, current_stock)
        
        # Generate purchase order
        po = await create_purchase_order(sku, reorder_qty)
        
        # Store PO in Cosmos DB
        await store_po(po)
    
    await partition_context.update_checkpoint(event)
```

#### 1.3.3 Reservation Validation Agent
**Event Topics**: `order-events`

```python
# apps/inventory-reservation-validation/src/reservation_service/event_handlers.py

import httpx

async def handle_order_event(partition_context, event):
    """Validate and reserve inventory for orders"""
    data = json.loads(event.body_as_str())
    event_type = data["event_type"]
    
    if event_type == "order.created":
        order_data = data["data"]
        
        # Attempt reservation
        reservations = []
        for item in order_data["items"]:
            reserved = await reserve_inventory(item["sku"], item["quantity"])
            if not reserved:
                # Compensation: release previous reservations
                await release_reservations(reservations)
                
                # Agent calls CRUD REST endpoint to update order status
                async with httpx.AsyncClient() as client:
                    await client.patch(
                        f"{settings.CRUD_API_URL}/orders/{order_data['id']}",
                        json={"status": "reservation_failed"},
                        headers={"Authorization": f"Bearer {settings.SERVICE_TOKEN}"}
                    )
                return
            reservations.append(reserved)
        
        # Update order in CRUD
        async with httpx.AsyncClient() as client:
            await client.patch(
                f"{settings.CRUD_API_URL}/orders/{order_data['id']}",
                json={"status": "reserved", "reservations": reservations},
                headers={"Authorization": f"Bearer {settings.SERVICE_TOKEN}"}
            )
    
    await partition_context.update_checkpoint(event)
```

#### 1.3.4 Alerts/Triggers Agent
**Event Topics**: `inventory-events`

```python
# apps/inventory-alerts-triggers/src/alerts_service/event_handlers.py

async def handle_inventory_event(partition_context, event):
    """Send alerts based on inventory events"""
    data = json.loads(event.body_as_str())
    event_type = data["event_type"]
    
    if event_type == "inventory.critical_stock":
        inventory_data = data["data"]
        
        # Send email/SMS to operations team
        await send_alert(
            recipients=settings.OPS_TEAM_EMAILS,
            subject=f"CRITICAL: Low stock for {inventory_data['sku']}",
            body=f"Current stock: {inventory_data['quantity']} units"
        )
    
    await partition_context.update_checkpoint(event)
```

**Deliverables (Week 5)**:
- ✅ 4 inventory event handlers implemented
- ✅ SAGA compensation logic (reservation validation)
- ✅ Alert delivery mechanisms configured
- ✅ Deployment manifests updated

---

### 1.4 Logistics Domain (Week 5)

#### 1.4.1 ETA Computation Agent
**Event Topics**: `order-events`

```python
# apps/logistics-eta-computation/src/eta_service/event_handlers.py

async def handle_order_event(partition_context, event):
    """Compute and update ETA when orders are shipped"""
    data = json.loads(event.body_as_str())
    event_type = data["event_type"]
    
    if event_type == "order.shipped":
        order_data = data["data"]
        
        # Compute ETA
        eta = await compute_eta(
            origin=order_data["warehouse_location"],
            destination=order_data["shipping_address"],
            carrier=order_data["carrier"]
        )
        
        # Store ETA in cache
        await memory.store(f"eta:{order_data['id']}", eta)
        
        # Publish ETA computed event
        await publish_event("logistics.eta_computed", {
            "order_id": order_data["id"],
            "eta": eta
        })
    
    await partition_context.update_checkpoint(event)
```

#### 1.4.2 Carrier Selection Agent
**Event Topics**: `order-events`

```python
# apps/logistics-carrier-selection/src/carrier_service/event_handlers.py

async def handle_order_event(partition_context, event):
    """Select optimal carrier when order is ready to ship"""
    data = json.loads(event.body_as_str())
    event_type = data["event_type"]
    
    if event_type == "order.ready_to_ship":
        order_data = data["data"]
        
        # Get carrier options
        carriers = await get_carrier_options(order_data)
        
        # Select optimal carrier (cost vs speed)
        selected_carrier = await select_carrier(carriers, order_data["shipping_preference"])
        
        # Store selection
        await memory.store(f"carrier:{order_data['id']}", selected_carrier)
        
        # Publish carrier selected event
        await publish_event("logistics.carrier_selected", {
            "order_id": order_data["id"],
            "carrier": selected_carrier
        })
    
    await partition_context.update_checkpoint(event)
```

#### 1.4.3 Returns Support Agent
**Event Topics**: `order-events`

```python
# apps/logistics-returns-support/src/returns_service/event_handlers.py

async def handle_order_event(partition_context, event):
    """Handle return requests and generate return labels"""
    data = json.loads(event.body_as_str())
    event_type = data["event_type"]
    
    if event_type == "order.return_requested":
        order_data = data["data"]
        
        # Generate return label
        label = await generate_return_label(order_data)
        
        # Store return info
        await store_return_info(order_data["id"], label)
        
        # Publish return label generated event
        await publish_event("logistics.return_label_generated", {
            "order_id": order_data["id"],
            "label_url": label["url"]
        })
    
    await partition_context.update_checkpoint(event)
```

#### 1.4.4 Route Issue Detection Agent
**Event Topics**: `order-events`

```python
# apps/logistics-route-issue-detection/src/route_service/event_handlers.py

async def handle_order_event(partition_context, event):
    """Detect delays and route issues"""
    data = json.loads(event.body_as_str())
    event_type = data["event_type"]
    
    if event_type == "order.in_transit":
        order_data = data["data"]
        
        # Check current location vs expected
        tracking = await get_tracking_info(order_data["tracking_number"])
        expected_eta = await memory.get(f"eta:{order_data['id']}")
        
        if await detect_delay(tracking, expected_eta):
            # Publish delay detected event
            await publish_event("logistics.delay_detected", {
                "order_id": order_data["id"],
                "expected_eta": expected_eta,
                "new_eta": tracking["estimated_delivery"]
            })
    
    await partition_context.update_checkpoint(event)
```

**Deliverables (Week 5)**:
- ✅ 4 logistics event handlers implemented
- ✅ Carrier API integrations tested
- ✅ Deployment manifests updated

---

### 1.5 Product Management Domain (Week 6)

#### 1.5.1 Normalization/Classification Agent
**Event Topics**: `product-events`

```python
# apps/product-management-normalization-classification/src/normalization_service/event_handlers.py

async def handle_product_event(partition_context, event):
    """Normalize and classify products when created"""
    data = json.loads(event.body_as_str())
    event_type = data["event_type"]
    
    if event_type == "product.created":
        product_data = data["data"]
        
        # Auto-classify category
        category = await classify_product(product_data)
        
        # Normalize attributes
        normalized = await normalize_product(product_data)
        
        # Store normalized version
        await store_normalized_product(normalized)
    
    await partition_context.update_checkpoint(event)
```

#### 1.5.2 ACP Transformation Agent
**Event Topics**: `product-events`

```python
# apps/product-management-acp-transformation/src/acp_service/event_handlers.py

async def handle_product_event(partition_context, event):
    """Transform products to ACP schema"""
    data = json.loads(event.body_as_str())
    event_type = data["event_type"]
    
    if event_type in ["product.created", "product.updated"]:
        product_data = data["data"]
        
        # Transform to ACP
        acp_product = await transform_to_acp(product_data)
        
        # Validate ACP compliance
        if await validate_acp(acp_product):
            await store_acp_product(acp_product)
    
    await partition_context.update_checkpoint(event)
```

#### 1.5.3 Consistency Validation Agent
**Event Topics**: `product-events`

```python
# apps/product-management-consistency-validation/src/validation_service/event_handlers.py

async def handle_product_event(partition_context, event):
    """Validate product data consistency"""
    data = json.loads(event.body_as_str())
    event_type = data["event_type"]
    
    if event_type in ["product.created", "product.updated"]:
        product_data = data["data"]
        
        # Run validation rules
        violations = await validate_product(product_data)
        
        if violations:
            # Store violations
            await store_violations(product_data["id"], violations)
            
            # Publish validation failed event
            await publish_event("product.validation_failed", {
                "product_id": product_data["id"],
                "violations": violations
            })
    
    await partition_context.update_checkpoint(event)
```

#### 1.5.4 Assortment Optimization Agent
**Event Topics**: `order-events`, `product-events`

```python
# apps/product-management-assortment-optimization/src/assortment_service/event_handlers.py

async def handle_order_event(partition_context, event):
    """Update assortment recommendations based on sales"""
    data = json.loads(event.body_as_str())
    event_type = data["event_type"]
    
    if event_type == "order.placed":
        order_data = data["data"]
        
        # Update sales metrics
        await update_sales_metrics(order_data["items"])
        
        # Re-run assortment optimization model
        await trigger_assortment_optimization()
    
    await partition_context.update_checkpoint(event)
```

**Deliverables (Week 6)**:
- ✅ 4 product management event handlers implemented
- ✅ ACP transformation validated
- ✅ Deployment manifests updated

---

### 1.4 Logistics & Product Management Domain Adapters (Week 4)

[Similar adapter implementations for remaining 12 agents]

---

### Phase 1 Summary

**Total Deliverables**:
- ✅ MCP adapter layer implemented in all 21 agents:
  - Base CRUD adapter framework
  - Base external API adapter template
  - 21 domain-specific CRUD adapters
  - 5+ 3rd party API adapters (carrier, payment, warehouse, etc.)
- ✅ Library modules added in lib/src/holiday_peak_lib/adapters:
  - mcp_adapter.py
  - crud_adapter.py
  - external_api_adapter.py
- ✅ MCP tool registration for all adapters
- ✅ Agent integration with adapters
- ✅ Unit tests for adapter tools (75% coverage)
- ✅ Integration tests with CRUD service and 3rd party APIs
- ✅ Deployment manifests updated (Kubernetes)
- ✅ Documentation for adapter patterns

**Deployment Architecture**:
```
Event Hubs (5 topics)
    │
    ├─→ user-events
    │     ├─→ profile-aggregation (consumer group: profile-agg-group)
    │     └─→ campaign-intelligence (consumer group: campaign-intel-group)
    │
    ├─→ product-events
    │     ├─→ catalog-search (consumer group: catalog-search-group)
    │     ├─→ product-detail-enrichment (consumer group: enrichment-group)
    │     ├─→ normalization-classification (consumer group: normalization-group)
    │     ├─→ acp-transformation (consumer group: acp-transform-group)
    │     └─→ consistency-validation (consumer group: validation-group)
    │
    ├─→ order-events
    │     ├─→ profile-aggregation (consumer group: profile-agg-group)
    │     ├─→ segmentation-personalization (consumer group: segmentation-group)
    │     ├─→ cart-intelligence (consumer group: cart-intel-group)
    │     ├─→ order-status (consumer group: order-status-group)
    │     ├─→ health-check (consumer group: health-check-group)
    │     ├─→ reservation-validation (consumer group: reservation-group)
    │     ├─→ eta-computation (consumer group: eta-group)
    │     ├─→ carrier-selection (consumer group: carrier-group)
    │     └─→ assortment-optimization (consumer group: assortment-group)
    │
    ├─→ inventory-events
    │     ├─→ checkout-support (consumer group: checkout-group)
    │     ├─→ health-check (consumer group: health-check-group)
    │     ├─→ jit-replenishment (consumer group: replenishment-group)
    │     └─→ alerts-triggers (consumer group: alerts-group)
    │
    └─→ payment-events
          └─→ campaign-intelligence (consumer group: campaign-intel-group)
```

---

## Phase 2: Event Handler Implementation (Weeks 5-10)

### Objective
Implement event subscription and processing in all 21 agent services to enable async communication from CRUD service.

**Note**: Now that agents have MCP adapter layer, they can execute CRUD operations when processing events.

**Library Support**:
- Use `EventHubSubscriber` from [lib/src/holiday_peak_lib/utils/event_hub.py](lib/src/holiday_peak_lib/utils/event_hub.py) as the abstract subscription layer.
- Configure `EventHubSubscriberConfig` per agent to standardize consumer setup and checkpointing.

### 2.1 Circuit Breaker Implementation (Week 7)

#### 2.1.1 Install Dependencies

```bash
# apps/crud-service/src/pyproject.toml
[project.dependencies]
circuitbreaker = "^2.0.0"
tenacity = "^8.2.3"
httpx = "^0.25.0"
```

#### 2.1.2 Update Agent Client

**Important**: ⚠️ **MCP is exclusively for agent-to-agent communication**. CRUD service calls agent **REST endpoints**, not MCP tools.

```python
# apps/crud-service/src/crud_service/integrations/agent_client.py

import httpx
from circuitbreaker import circuit
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog

logger = structlog.get_logger()

class AgentClient:
    """
    Client for invoking agent REST endpoints with resilience patterns.
    
    Note: MCP protocol is for agent-to-agent communication only.
    CRUD service uses regular REST endpoints exposed by agents.
    """
    
    def __init__(self):
        self.timeout = httpx.Timeout(0.5, connect=1.0)  # 500ms timeout
        
    @circuit(failure_threshold=5, recovery_timeout=60, expected_exception=httpx.HTTPError)
    @retry(
        stop=stop_after_attempt(2), 
        wait=wait_exponential(multiplier=0.5, min=0.5, max=2),
        reraise=True
    )
    async def call_endpoint(
        self, 
        agent_url: str, 
        endpoint: str, 
        data: dict,
        fallback: dict | None = None
    ) -> dict:
        """
        Call agent REST endpoint with circuit breaker and retry logic.
        
        Args:
            agent_url: Base URL of agent service
            endpoint: REST endpoint path (e.g., '/enrich', '/recommendations')
            data: Request body
            fallback: Fallback response if agent fails
            
        Returns:
            API response or fallback
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{agent_url}{endpoint}",
                    json=data,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                
                result = response.json()
                logger.info(
                    "agent_call_success",
                    agent=agent_url,
                    endpoint=endpoint,
                    duration_ms=response.elapsed.total_seconds() * 1000
                )
                return result
                
        except httpx.TimeoutException as e:
            logger.warning(
                "agent_call_timeout",
                agent=agent_url,
                tool=tool_name,
                error=str(e)
            )
            return fallback or {"status": "timeout", "data": None}
            
        except httpx.HTTPError as e:
            logger.error(
                "agent_call_failed",
                agent=agent_url,
                tool=tool_name,
                error=str(e),
                status_code=getattr(e.response, "status_code", None)
            )
            return fallback or {"status": "error", "data": None}

# Singleton instance
agent_client = AgentClient()
```

#### 2.1.3 Update Product Routes

```python
# apps/crud-service/src/crud_service/routes/products.py

from ..integrations.agent_client import agent_client

@router.get("/{product_id}")
async def get_product(product_id: str):
    """Get product with optional enrichment"""
    # Get base product from Cosmos DB
    product = await product_repository.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Try to enrich with ACP metadata (with fallback)
    # Note: Using REST endpoint, not MCP (MCP is for agent-to-agent only)
    enrichment = await agent_client.call_endpoint(
        agent_url=settings.ENRICHMENT_AGENT_URL,
        endpoint="/enrich",  # REST endpoint
        data={"product_id": product_id},
        fallback={"acp_metadata": None}  # Fallback: return product without enrichment
    )
    
    if enrichment["status"] != "timeout":
        product["acp_metadata"] = enrichment.get("data", {})
    
    return product
```

#### 2.1.4 Update Cart Routes

```python
# apps/crud-service/src/crud_service/routes/cart.py

@router.get("/recommendations")
async def get_cart_recommendations(user_id: str = Depends(get_current_user)):
    """Get cart recommendations with fallback to trending products"""
    
    # Try to get AI-powered recommendations via REST endpoint
    recommendations = await agent_client.call_endpoint(
        agent_url=settings.CART_INTELLIGENCE_AGENT_URL,
        endpoint="/recommendations",  # REST endpoint
        data={"user_id": user_id},
        fallback=None
    )
    
    if recommendations and recommendations["status"] != "timeout":
        return recommendations["data"]
    
    # Fallback: Return trending products
    trending = await product_repository.get_trending(limit=5)
    return {"items": trending, "source": "trending"}
```

### 2.2 Fallback Strategy Documentation (Week 7)

#### 2.2.1 Communication Patterns

**Bidirectional REST Communication**:

```python
# Pattern 1: CRUD calls Agent REST endpoint
# Use case: Product enrichment, cart recommendations

# In CRUD Service:
result = await agent_client.call_endpoint(
    agent_url="http://enrichment:8080",
    endpoint="/enrich",
    data={"product_id": product_id},
    fallback={"acp_metadata": None}
)

# Pattern 2: Agent calls CRUD REST endpoint
# Use case: Update order status, create tickets, inventory updates

# In Agent Service:
async with httpx.AsyncClient() as client:
    await client.post(
        f"{settings.CRUD_API_URL}/orders/{order_id}/status",
        json={"status": "reserved"},
        headers={"Authorization": f"Bearer {settings.SERVICE_TOKEN}"}
    )

# Pattern 3: Agent calls another Agent's MCP tool
# Use case: Inventory agent needs pricing from pricing agent

# In Agent Service:
from agent_framework import MCPClient

mcp_client = MCPClient()
price = await mcp_client.call_tool(
    agent="pricing-agent",
    tool="get_dynamic_price",
    arguments={"sku": "SKU-123"}
)
```

**Architecture Note**: Agents no longer need service-to-service authentication for CRUD calls because they use MCP tools from the adapter layer. The adapter handles HTTP communication internally.

#### 2.2.2 Agent Architecture with MCP Adapters

**Communication Patterns**:
1. **CRUD → Agent**: REST calls (for fast enrichment)
2. **Agent → CRUD**: MCP tools in adapter layer (for transactional operations)
3. **Agent → 3rd Party APIs**: MCP tools in adapter layer (for external integrations)
4. **Agent → Agent**: MCP tools (for contextual communication)

**Implementation Note (CRUD Service)**:
- Agent REST calls currently use the shared `/invoke` endpoint created by `build_service_app`.
- Payloads follow each agent's `handle()` contract (e.g., `{ "sku": "..." }` for enrichment, `{ "items": [...] }` for checkout/cart).

**Implementation Note (Frontend)**:
- Semantic search is wired in the UI via `NEXT_PUBLIC_AGENT_API_URL` and calls `/catalog-search/semantic`.
- UI falls back to CRUD `/products?search=` when agent APIs are unavailable.

**Agent Implementation Pattern**:
```python
# apps/ecommerce-product-detail-enrichment/src/enrichment_service/main.py

from fastapi import FastAPI
from holiday_peak_lib.agents import AgentBuilder
from .adapters import EnrichmentCRUDAdapter

app = FastAPI()

# Initialize CRUD adapter with MCP tools
crud_adapter = EnrichmentCRUDAdapter(
    crud_base_url=settings.CRUD_SERVICE_URL
)

# Build agent with adapter
agent = AgentBuilder() \
    .with_adapter(crud_adapter) \
    .with_memory(memory_settings) \
    .build()

# REST endpoint for CRUD service and Frontend to call
@app.post("/enrich")
async def enrich_product(request: EnrichRequest):
    """REST endpoint for external services (CRUD, Frontend) to call."""
    # Agent uses MCP tool from adapter to fetch product
    product = await agent.call_tool("get_product", product_id=request.product_id)
    acp_metadata = await generate_acp_metadata(product)
    return {"acp_metadata": acp_metadata}

# MCP tool for agent-to-agent communication
@agent.mcp_server.tool()
async def get_product_enrichment(product_id: str) -> dict:
    """MCP tool for other agents to call - indexed and discoverable."""
    product = await agent.call_tool("get_product", product_id=product_id)
    return await generate_acp_metadata(product)
```

**Key Architecture Points**:
- **Adapter Layer**: Agents use MCP tools from adapters to call CRUD and 3rd party APIs
- **No Direct REST**: Agents never make direct REST calls to CRUD; they use MCP tools
- **Inbound REST**: Agents expose REST endpoints for CRUD/Frontend to call
- **Agent-to-Agent MCP**: Agents expose MCP tools for other agents to discover and call

#### 2.2.3 Create ADR for Fallback Strategies

```markdown
# ADR-020: Agent Fallback Strategies

**Status**: Accepted  
**Date**: 2026-01-30

## Context
Sync calls to agents may fail due to timeouts, errors, or circuit breakers.

## Decision
Define explicit fallback strategies for each agent call:

| Agent Call | Primary | Fallback |
|------------|---------|----------|
| Product Enrichment | ACP metadata | Basic product data only |
| Cart Recommendations | AI-powered | Trending products |
| Checkout Validation | Agent validation | Basic inventory check |
| ETA Computation | Real-time ETA | Default shipping estimate |

## Implementation
Configure fallback in `agent_client.invoke_tool()` calls.
```

### 2.3 Monitoring & Alerting (Week 8)

#### Configure Azure Monitor Alerts

```bicep
// .infra/modules/monitoring/alerts.bicep

resource circuitBreakerAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: 'circuit-breaker-open'
  location: location
  properties: {
    severity: 2
    evaluationFrequency: 'PT1M'
    windowSize: 'PT5M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'circuit-breaker-open'
          metricName: 'agent_circuit_breaker_open'
          operator: 'GreaterThan'
          threshold: 0
          timeAggregation: 'Maximum'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}
```

**Deliverables (Week 8)**:
- ✅ Circuit breaker implemented in CRUD service
- ✅ Timeout configuration (500ms)
- ✅ Retry logic with exponential backoff
- ✅ Fallback strategies documented
- ✅ Monitoring alerts configured
- ✅ ADR-020 created

---

## Phase 3: Resilience Patterns (Weeks 11-12)

### Objective
Add circuit breakers, timeouts, and fallback strategies to CRUD service for synchronous agent REST calls.

### 3.1 API Gateway Configuration (Week 9)

#### 3.1.1 Update API Management

```bicep
// .infra/modules/apim/apis.bicep

// Agent APIs
resource agentApi 'Microsoft.ApiManagement/service/apis@2022-08-01' = {
  name: 'agents-api'
  parent: apimService
  properties: {
    displayName: 'Agents API'
    path: 'agents'
    protocols: ['https']
    subscriptionRequired: true
    authenticationSettings: {
      oAuth2: {
        authorizationServerId: 'entra-id'
        scope: 'api://agents/read'
      }
    }
  }
}

// Semantic search operation
resource semanticSearchOp 'Microsoft.ApiManagement/service/apis/operations@2022-08-01' = {
  name: 'semantic-search'
  parent: agentApi
  properties: {
    displayName: 'Semantic Product Search'
    method: 'POST'
    urlTemplate: '/catalog-search/semantic'
    request: {
      queryParameters: []
      representations: [
        {
          contentType: 'application/json'
          schemaId: 'semantic-search-request'
        }
      ]
    }
  }
}

// Policy: Rate limiting + auth
resource semanticSearchPolicy 'Microsoft.ApiManagement/service/apis/operations/policies@2022-08-01' = {
  name: 'policy'
  parent: semanticSearchOp
  properties: {
    value: '''
      <policies>
        <inbound>
          <base />
          <validate-jwt header-name="Authorization">
            <openid-config url="https://login.microsoftonline.com/{tenant-id}/v2.0/.well-known/openid-configuration" />
            <audiences>
              <audience>api://agents</audience>
            </audiences>
          </validate-jwt>
          <rate-limit-by-key calls="100" renewal-period="60" counter-key="@(context.Request.IpAddress)" />
        </inbound>
        <backend>
          <forward-request timeout="5" />
        </backend>
        <outbound>
          <base />
        </outbound>
      </policies>
    '''
  }
}
```

### 3.2 Frontend Integration (Week 9)

#### 3.2.1 Create Agent API Client

```typescript
// apps/ui/lib/api/agentClient.ts

import axios from 'axios';

const agentApiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_AGENT_API_URL || 'https://api.holidaypeakhub.com/agents',
  timeout: 5000,
});

// Request interceptor: Attach JWT token
agentApiClient.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('accessToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default agentApiClient;
```

#### 3.2.2 Create Semantic Search Service

```typescript
// apps/ui/lib/services/semanticSearchService.ts

import agentApiClient from '../api/agentClient';

export interface SemanticSearchRequest {
  query: string;
  filters?: {
    category?: string;
    priceRange?: { min: number; max: number };
  };
  limit?: number;
}

export const semanticSearchService = {
  search: async (request: SemanticSearchRequest) => {
    try {
      const response = await agentApiClient.post('/catalog-search/semantic', request);
      return response.data;
    } catch (error) {
      console.error('Semantic search failed:', error);
      // Fallback to basic search via CRUD API
      return crudApiClient.get('/products', { params: { search: request.query } });
    }
  },
};
```

#### 3.2.3 Create React Hook

```typescript
// apps/ui/lib/hooks/useSemanticSearch.ts

import { useQuery } from '@tanstack/react-query';
import { semanticSearchService } from '../services/semanticSearchService';

export function useSemanticSearch(query: string, enabled: boolean = true) {
  return useQuery({
    queryKey: ['semantic-search', query],
    queryFn: () => semanticSearchService.search({ query }),
    enabled: enabled && query.length > 2,
    staleTime: 60 * 1000, // 1 minute
  });
}
```

#### 3.2.4 Update Search Component

```tsx
// apps/ui/components/organisms/ProductSearch.tsx

import { useSemanticSearch } from '@/lib/hooks/useSemanticSearch';

export function ProductSearch() {
  const [query, setQuery] = useState('');
  const { data: results, isLoading } = useSemanticSearch(query);

  return (
    <div>
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Try: 'winter jackets for hiking'"
      />
      {isLoading && <Spinner />}
      {results && <ProductGrid products={results.items} />}
    </div>
  );
}
```

### 3.3 Campaign Analytics Agent (Week 10)

#### 3.3.1 Expose via API Gateway

```bicep
// Campaign analytics operation
resource campaignAnalyticsOp 'Microsoft.ApiManagement/service/apis/operations@2022-08-01' = {
  name: 'campaign-analytics'
  parent: agentApi
  properties: {
    displayName: 'Campaign Analytics'
    method: 'POST'
    urlTemplate: '/campaign-intelligence/analytics'
    request: {
      representations: [
        {
          contentType: 'application/json'
        }
      ]
    }
  }
}

// Policy: Staff role required
resource campaignAnalyticsPolicy 'Microsoft.ApiManagement/service/apis/operations/policies@2022-08-01' = {
  name: 'policy'
  parent: campaignAnalyticsOp
  properties: {
    value: '''
      <policies>
        <inbound>
          <base />
          <validate-jwt header-name="Authorization">
            <openid-config url="https://login.microsoftonline.com/{tenant-id}/v2.0/.well-known/openid-configuration" />
            <required-claims>
              <claim name="roles" match="any">
                <value>staff</value>
                <value>admin</value>
              </claim>
            </required-claims>
          </validate-jwt>
        </inbound>
      </policies>
    '''
  }
}
```

#### 3.3.2 Frontend Service

```typescript
// apps/ui/lib/services/campaignAnalyticsService.ts

export const campaignAnalyticsService = {
  getAnalytics: async (campaignId: string) => {
    const response = await agentApiClient.post('/campaign-intelligence/analytics', {
      campaign_id: campaignId,
    });
    return response.data;
  },
};
```

**Deliverables (Week 10)**:
- ✅ API Gateway configured
- ✅ Semantic search exposed via `/agents/catalog-search/semantic`
- ✅ Campaign analytics exposed via `/agents/campaign-intelligence/analytics`
- ✅ Rate limiting configured (100 req/min)
- ✅ RBAC enforced (staff role for analytics)
- ✅ Frontend integration complete
- ✅ Fallback to CRUD API implemented

---

## Phase 4: API Gateway & Testing (Weeks 13-16)

### Objective
Expose semantic search and analytics agents via API Gateway for direct frontend access, and complete integration testing.

### 4.1 Integration Testing (Week 11)

#### 4.1.1 Event Handler Tests

```python
# tests/integration/test_event_handlers.py

import pytest
from azure.eventhub import EventData
from apps.crm_profile_aggregation.src.profile_service.event_handlers import handle_order_event

@pytest.mark.asyncio
async def test_order_placed_updates_profile():
    """Test that order.placed event updates user profile"""
    # Arrange
    event_data = {
        "event_type": "order.placed",
        "data": {
            "order_id": "order-123",
            "user_id": "user-456",
            "total": 199.99,
            "items": [{"sku": "SKU-789", "quantity": 2}]
        }
    }
    event = EventData(json.dumps(event_data))
    
    # Act
    await handle_order_event(mock_partition_context, event)
    
    # Assert
    profile = await profile_repository.get("user-456")
    assert profile["order_count"] == 1
    assert profile["lifetime_value"] == 199.99
```

#### 4.1.2 Circuit Breaker Tests

```python
# tests/integration/test_circuit_breaker.py

@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_failures():
    """Test circuit breaker opens after 5 failures"""
    # Arrange: Mock agent to always fail
    mock_agent.return_value = httpx.TimeoutException()
    
    # Act: Call agent 5 times
    for _ in range(5):
        result = await agent_client.invoke_tool(
            "http://agent:8080",
            "test_tool",
            {}
        )
    
    # Assert: Circuit breaker is open
    assert agent_client.invoke_tool.circuit_breaker.opened
    
    # Next call should fail immediately without hitting agent
    with pytest.raises(CircuitBreakerError):
        await agent_client.invoke_tool("http://agent:8080", "test_tool", {})
```

### 4.2 Load Testing (Week 11)

#### 4.2.1 Locust Test

```python
# tests/load/locustfile.py

from locust import HttpUser, task, between

class HolidayPeakUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login and get token"""
        response = self.client.post("/auth/login", json={
            "username": "testuser",
            "password": "testpass"
        })
        self.token = response.json()["access_token"]
    
    @task(3)
    def browse_products(self):
        """Browse products (most common)"""
        self.client.get("/products", headers={"Authorization": f"Bearer {self.token}"})
    
    @task(2)
    def search_products(self):
        """Semantic search"""
        self.client.post("/agents/catalog-search/semantic", 
            json={"query": "winter jackets"},
            headers={"Authorization": f"Bearer {self.token}"}
        )
    
    @task(1)
    def add_to_cart(self):
        """Add to cart"""
        self.client.post("/cart/items",
            json={"product_id": "prod-123", "quantity": 1},
            headers={"Authorization": f"Bearer {self.token}"}
        )
```

Run test:
```bash
locust -f tests/load/locustfile.py --host=https://api.holidaypeakhub.com --users=1000 --spawn-rate=10
```

### 4.3 Deployment (Week 12)

#### 4.3.1 Helm Chart for Agents

```yaml
# charts/agents/values.yaml

global:
  eventHub:
    connectionString: ""  # From Key Vault
  cosmosDb:
    uri: ""
  redis:
    url: ""

agents:
  - name: catalog-search
    image: holidaypeakhub.azurecr.io/catalog-search:latest
    replicas: 3
    resources:
      requests:
        cpu: 500m
        memory: 1Gi
      limits:
        cpu: 1000m
        memory: 2Gi
    eventTopics:
      - product-events
    consumerGroup: catalog-search-group
    
  - name: profile-aggregation
    image: holidaypeakhub.azurecr.io/profile-aggregation:latest
    replicas: 2
    eventTopics:
      - user-events
      - order-events
    consumerGroup: profile-agg-group
    
  # ... repeat for all 21 agents
```

#### 4.3.2 Deployment Script

```bash
#!/bin/bash
# scripts/deploy-agents.sh

set -e

NAMESPACE="agents"
HELM_RELEASE="holiday-peak-agents"

# Create namespace
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Create secrets from Key Vault
az keyvault secret show --vault-name holiday-peak-kv --name eventhub-connection-string --query value -o tsv | \
  kubectl create secret generic eventhub-secret --from-file=connection-string=/dev/stdin -n $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Deploy agents via Helm
helm upgrade --install $HELM_RELEASE ./charts/agents \
  --namespace $NAMESPACE \
  --set global.eventHub.connectionString="$(kubectl get secret eventhub-secret -n $NAMESPACE -o jsonpath='{.data.connection-string}' | base64 -d)" \
  --wait

# Verify deployment
kubectl rollout status deployment -n $NAMESPACE
kubectl get pods -n $NAMESPACE
```

**Deliverables (Week 12)**:
- ✅ Integration tests passing (75% coverage)
- ✅ Load tests completed (1000 concurrent users, P99 < 500ms)
- ✅ Helm charts created
- ✅ Deployment scripts automated
- ✅ Production deployment successful
- ✅ Monitoring dashboards live

---

## C4 Component Diagram (Level 3)

### Production Architecture

```mermaid
C4Component
    title Component Diagram - Holiday Peak Hub (Production)

    Container_Boundary(frontend, "Frontend Layer") {
        Component(nextjs, "Next.js App", "React 19, TypeScript", "User interface")
    }

    Container_Boundary(gateway, "API Gateway") {
        Component(apim, "Azure API Management", "API Gateway", "Rate limiting, auth, routing")
    }

    Container_Boundary(crud, "CRUD Service") {
        Component(crud_api, "FastAPI App", "Python 3.13", "REST API for transactions")
        Component(crud_repos, "Repositories", "Python", "Data access layer")
        Component(event_pub, "Event Publisher", "Python", "Publishes to Event Hubs")
        Component(agent_client, "Agent Client", "Python", "Sync agent calls with circuit breaker")
    }

    Container_Boundary(agents_ecom, "E-commerce Agents") {
        Component(catalog_search, "Catalog Search", "Agent", "Semantic product search")
        Component(enrichment, "Product Enrichment", "Agent", "ACP metadata")
        Component(cart_intel, "Cart Intelligence", "Agent", "Recommendations")
        Component(checkout, "Checkout Support", "Agent", "Validation")
        Component(order_status, "Order Status", "Agent", "Tracking")
    }

    Container_Boundary(agents_crm, "CRM Agents") {
        Component(profile_agg, "Profile Aggregation", "Agent", "Customer profiles")
        Component(segmentation, "Segmentation", "Agent", "Customer segments")
        Component(campaign, "Campaign Intelligence", "Agent", "Marketing analytics")
        Component(support, "Support Assistance", "Agent", "Customer support")
    }

    Container_Boundary(agents_inv, "Inventory Agents") {
        Component(health, "Health Check", "Agent", "Stock monitoring")
        Component(replenish, "JIT Replenishment", "Agent", "Auto-reorder")
        Component(reservation, "Reservation", "Agent", "Inventory locking")
        Component(alerts, "Alerts/Triggers", "Agent", "Notifications")
    }

    Container_Boundary(agents_log, "Logistics Agents") {
        Component(eta, "ETA Computation", "Agent", "Delivery estimates")
        Component(carrier, "Carrier Selection", "Agent", "Shipping optimization")
        Component(returns, "Returns Support", "Agent", "Return processing")
        Component(route_detect, "Route Detection", "Agent", "Delay monitoring")
    }

    Container_Boundary(agents_prod, "Product Mgmt Agents") {
        Component(normalize, "Normalization", "Agent", "Data cleaning")
        Component(acp, "ACP Transform", "Agent", "Schema conversion")
        Component(validate, "Validation", "Agent", "Consistency checks")
        Component(assortment, "Assortment", "Agent", "SKU optimization")
    }

    Container_Boundary(data, "Data Layer") {
        ComponentDb(cosmos, "Cosmos DB", "NoSQL", "10 containers")
        ComponentDb(redis, "Redis Cache", "In-memory", "Hot tier memory")
        ComponentDb(blob, "Blob Storage", "Object store", "Cold tier memory")
        ComponentQueue(eventhub, "Event Hubs", "Messaging", "5 topics")
    }

    Container_Boundary(platform, "Azure Platform") {
        Component(monitor, "Azure Monitor", "Observability", "Logs, metrics, traces")
        Component(keyvault, "Key Vault", "Secrets", "Connection strings")
    }

    ' Frontend to Gateway
    Rel(nextjs, apim, "HTTPS", "REST/JSON")

    ' Gateway to CRUD
    Rel(apim, crud_api, "HTTPS", "Transactions")
    
    ' Gateway to Agents (Direct)
    Rel(apim, catalog_search, "HTTPS", "Semantic search")
    Rel(apim, campaign, "HTTPS", "Analytics (staff only)")

    ' CRUD to Data
    Rel(crud_repos, cosmos, "TCP", "CRUD operations")
    Rel(crud_api, redis, "TCP", "Session cache")

    ' CRUD to Event Hubs
    Rel(event_pub, eventhub, "AMQP", "Publishes events")

    ' CRUD to Agents (Sync with circuit breaker)
    Rel(agent_client, enrichment, "HTTP", "Product enrichment (500ms timeout)")
    Rel(agent_client, cart_intel, "HTTP", "Recommendations (500ms timeout)")

    ' Event Hubs to Agents (Async)
    Rel(eventhub, catalog_search, "AMQP", "product-events")
    Rel(eventhub, enrichment, "AMQP", "product-events")
    Rel(eventhub, cart_intel, "AMQP", "order-events")
    Rel(eventhub, order_status, "AMQP", "order-events")
    Rel(eventhub, profile_agg, "AMQP", "user-events, order-events")
    Rel(eventhub, segmentation, "AMQP", "order-events")
    Rel(eventhub, campaign, "AMQP", "order-events, payment-events")
    Rel(eventhub, health, "AMQP", "order-events, inventory-events")
    Rel(eventhub, replenish, "AMQP", "inventory-events")
    Rel(eventhub, reservation, "AMQP", "order-events")
    Rel(eventhub, alerts, "AMQP", "inventory-events")
    Rel(eventhub, eta, "AMQP", "order-events")
    Rel(eventhub, carrier, "AMQP", "order-events")
    Rel(eventhub, returns, "AMQP", "order-events")
    Rel(eventhub, route_detect, "AMQP", "order-events")
    Rel(eventhub, normalize, "AMQP", "product-events")
    Rel(eventhub, acp, "AMQP", "product-events")
    Rel(eventhub, validate, "AMQP", "product-events")
    Rel(eventhub, assortment, "AMQP", "order-events, product-events")

    ' Agents to Data
    Rel(catalog_search, cosmos, "TCP", "Search index")
    Rel(enrichment, cosmos, "TCP", "Enrichments")
    Rel(profile_agg, cosmos, "TCP", "Profiles")
    Rel(all_agents, redis, "TCP", "Hot memory")
    Rel(all_agents, blob, "HTTPS", "Cold memory")

    ' Platform
    Rel(crud_api, monitor, "HTTPS", "Telemetry")
    Rel(all_agents, monitor, "HTTPS", "Telemetry")
    Rel(crud_api, keyvault, "HTTPS", "Secrets")
    Rel(all_agents, keyvault, "HTTPS", "Secrets")

    UpdateLayoutConfig($c4ShapeInRow="4", $c4BoundaryInRow="2")
```

---

## Success Criteria

### Phase 1: MCP Adapter Layer
- [ ] Base CRUD adapter framework completed
- [ ] Base external API adapter template completed
- [ ] All 21 agents have CRUD adapters with MCP tools
- [ ] 5+ 3rd party API adapters implemented (carrier, payment, warehouse, etc.)
- [ ] Agents successfully call CRUD operations via MCP tools
- [ ] Agents successfully call 3rd party APIs via MCP tools
- [ ] Unit test coverage ≥ 75% for all adapters
- [ ] Integration tests passing

### Phase 2: Event Handlers
- [ ] All 21 agents subscribe to relevant Event Hub topics
- [ ] Event processing latency < 2 seconds (P95)
- [ ] Zero message loss (exactly-once semantics)
- [ ] Consumer groups configured per agent
- [ ] Agents use MCP tools from adapters when processing events
- [ ] Unit test coverage ≥ 75%

### Phase 3: Resilience
- [ ] Circuit breaker configured (5 failures, 60s recovery)
- [ ] Timeout set to 500ms for sync calls
- [ ] Retry logic with exponential backoff (2 attempts max)
- [ ] Fallback strategies defined for all sync calls
- [ ] Monitoring alerts configured

### Phase 4: API Gateway & Testing
- [ ] Semantic search exposed via `/agents/catalog-search/semantic`
- [ ] Campaign analytics exposed via `/agents/campaign-intelligence/analytics`
- [ ] Rate limiting: 100 req/min per IP
- [ ] RBAC enforced (staff role required for analytics)
- [ ] Frontend integration complete with fallback to CRUD
- [ ] Integration tests passing (75% coverage)
- [ ] Load tests: 1000 concurrent users, P99 < 500ms
- [ ] Helm charts created and tested
- [ ] Production deployment successful
- [ ] Monitoring dashboards live

---

## Risk Management

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| MCP adapter implementation complexity | High | High | Start with base adapters, iterate per domain |
| MCP tool registration errors | Medium | High | Comprehensive unit tests, schema validation |
| Adapter performance overhead | Medium | Medium | Cache adapter instances, optimize HTTP clients |
| Event Hub throttling | Medium | High | Configure dedicated namespace with auto-inflate |
| Circuit breaker too aggressive | Low | Medium | Monitor open rate, tune thresholds |
| Agent latency > 500ms | Medium | Medium | Add caching layer, optimize queries |
| Consumer group conflicts | Low | High | Use unique consumer groups per agent |
| Secret management issues | Low | High | Use Key Vault references, not inline secrets |

---

## Post-Implementation

### Week 17: Validation
- Run smoke tests in production
- Monitor dashboards for 7 days
- Collect performance metrics
- Document lessons learned
- Validate MCP adapter performance

### Week 18: Optimization
- Tune circuit breaker thresholds based on data
- Optimize agent query performance
- Right-size agent replicas based on load
- Optimize MCP adapter response times
- Cache frequently used MCP tool results
- Update ADRs with findings

### Ongoing: Maintenance
- Monthly review of event handler performance
- Quarterly review of circuit breaker effectiveness
- Continuous monitoring of agent latency
- Regular updates to fallback strategies

---

## Appendix: Event Schema Reference

### user-events
```json
{
  "event_type": "user.registered | user.updated",
  "data": {
    "user_id": "uuid",
    "email": "string",
    "name": "string",
    "created_at": "iso8601"
  }
}
```

### product-events
```json
{
  "event_type": "product.created | product.updated | product.deleted",
  "data": {
    "product_id": "uuid",
    "sku": "string",
    "name": "string",
    "category": "string",
    "price": "decimal"
  }
}
```

### order-events
```json
{
  "event_type": "order.placed | order.status_changed | order.cancelled",
  "data": {
    "order_id": "uuid",
    "user_id": "uuid",
    "status": "string",
    "total": "decimal",
    "items": [{"sku": "string", "quantity": "int"}]
  }
}
```

### inventory-events
```json
{
  "event_type": "inventory.low_stock | inventory.out_of_stock",
  "data": {
    "sku": "string",
    "quantity": "int",
    "warehouse": "string"
  }
}
```

### payment-events
```json
{
  "event_type": "payment.succeeded | payment.failed",
  "data": {
    "order_id": "uuid",
    "amount": "decimal",
    "payment_method": "string"
  }
}
```

---

**End of Implementation Plan**
