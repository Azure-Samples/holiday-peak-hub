# Sequence Diagram: Logistics Returns Support Flow

This diagram illustrates the returns processing workflow in the Holiday Peak Hub accelerator.

## Flow Overview

1. **User Initiates Return** → Submit return request
2. **Shipment Validation** → Verify order and shipment status
3. **Policy Evaluation** → Check eligibility (time window, condition)
4. **LLM Guidance** → Generate natural language return instructions
5. **Label Generation** → Create return shipping label
6. **Orchestration** → Coordinate warehouse, carrier, refund

## Sequence Diagram

```mermaid
sequenceDiagram
    actor Customer
    participant API as FastAPI App
    participant Agent as Returns Support Agent
    participant Router as Model Router
    participant LLM as GPT-4o
    participant Logistics as Logistics Adapter
    participant CRM as CRM Adapter
    participant Funnel as Funnel Adapter
    participant Memory as Memory Stack
    participant EventHub as Event Hub
    participant Carrier as Carrier API
    participant WMS as Warehouse System

    Customer->>API: POST /invoke {"order_id": "ORD-123", "reason": "wrong size"}
    API->>Agent: process_return(order_id, reason)
    
    Note over Agent: Step 1: Fetch Order Context
    Agent->>Memory: get(order_context)
    Memory-->>Agent: null (cache miss)
    
    Agent->>Funnel: get_order(order_id)
    activate Funnel
    Funnel->>Funnel: Query order DB
    Funnel-->>Agent: Order {items, total, status: "delivered"}
    deactivate Funnel
    
    Agent->>Memory: set(order_context, order, ttl=900)
    Memory-->>Agent: OK
    
    Note over Agent: Step 2: Validate Shipment Status
    Agent->>Logistics: get_shipment(order_id)
    activate Logistics
    Logistics->>Carrier: track_shipment(tracking_id)
    Carrier-->>Logistics: {status: "delivered", date: "2026-01-20"}
    Logistics-->>Agent: Shipment {status, events, carrier}
    deactivate Logistics
    
    Note over Agent: Step 3: Check Return Eligibility
    Agent->>Agent: calculate_return_window()
    Agent->>Agent: delivered_date + 30 days
    
    alt Return Window Expired
        Agent-->>API: ReturnResponse {eligible: false, reason: "expired"}
        API-->>Customer: 400 Bad Request {message: "Return window closed"}
    else Return Eligible
        Note over Agent: Step 4: Fetch User Profile
        Agent->>CRM: get_customer(customer_id)
        activate CRM
        CRM->>CRM: Query CRM DB
        CRM-->>Agent: Customer {tier: "VIP", return_history: []}
        deactivate CRM
        
        Note over Agent: Step 5: Generate Return Instructions (LLM)
        Agent->>Router: assess_complexity(return_request)
        Router-->>Agent: complexity = COMPLEX (needs explanation)
        
        Agent->>LLM: invoke({order, shipment, reason, customer})
        activate LLM
        LLM->>LLM: Multi-step reasoning
        LLM->>LLM: 1. Validate item condition requirements
        LLM->>LLM: 2. Determine return method (drop-off vs pickup)
        LLM->>LLM: 3. Calculate refund amount
        LLM->>LLM: 4. Generate instructions
        LLM-->>Agent: ReturnPlan {method, refund, instructions}
        deactivate LLM
        
        Note over Agent: Step 6: Create Return Label
        Agent->>Logistics: create_return_label(order, shipment)
        activate Logistics
        Logistics->>Carrier: generate_label(from, to, weight)
        Carrier-->>Logistics: {label_url, tracking_id}
        Logistics-->>Agent: ReturnLabel {url, tracking_id}
        deactivate Logistics
        
        Note over Agent: Step 7: Store Return Record
        Agent->>Memory: upsert(return_record, ttl=7776000)
        activate Memory
        Memory->>Memory: Store in Warm (Cosmos DB)
        Memory-->>Agent: OK
        deactivate Memory
        
        Note over Agent: Step 8: Trigger SAGA Workflow
        Agent->>EventHub: publish(returns.initiated)
        activate EventHub
        EventHub-->>Agent: Message ID: msg-12345
        deactivate EventHub
        
        Agent-->>API: ReturnResponse {eligible: true, label_url, tracking_id}
        API-->>Customer: 200 OK {instructions, label_url}
    end
    
    Note over EventHub,WMS: SAGA Choreography: Returns Workflow
    
    EventHub->>WMS: consume(returns.initiated)
    activate WMS
    WMS->>WMS: Create inbound receipt
    WMS->>EventHub: publish(returns.receipt_created)
    deactivate WMS
    
    EventHub->>Carrier: consume(returns.receipt_created)
    activate Carrier
    Carrier->>Carrier: Schedule pickup
    Carrier->>EventHub: publish(returns.pickup_scheduled)
    deactivate Carrier
    
    Note over Customer: Customer ships item
    
    Carrier->>EventHub: publish(returns.in_transit)
    EventHub->>Agent: consume(returns.in_transit)
    Agent->>Customer: Send email: "Return in transit"
    
    Carrier->>EventHub: publish(returns.delivered_to_warehouse)
    EventHub->>WMS: consume(returns.delivered_to_warehouse)
    
    activate WMS
    WMS->>WMS: Inspect item
    
    alt Item Acceptable
        WMS->>WMS: Update inventory (+1)
        WMS->>EventHub: publish(returns.accepted)
        
        EventHub->>Funnel: consume(returns.accepted)
        activate Funnel
        Funnel->>Funnel: Process refund
        Funnel->>EventHub: publish(returns.refunded)
        deactivate Funnel
        
        EventHub->>Agent: consume(returns.refunded)
        Agent->>Customer: Send email: "Refund processed"
    else Item Damaged
        WMS->>EventHub: publish(returns.rejected)
        
        EventHub->>Agent: consume(returns.rejected)
        Agent->>LLM: generate_rejection_explanation(inspection_notes)
        LLM-->>Agent: explanation
        Agent->>Customer: Send email: "Return rejected" + explanation
    end
    deactivate WMS
    
    Note over Customer,WMS: VIP Fast-Track Flow
    
    Customer->>API: POST /invoke {"order_id": "ORD-456", "vip": true}
    API->>Agent: process_return(order_id)
    
    Agent->>CRM: get_customer(customer_id)
    CRM-->>Agent: Customer {tier: "VIP"}
    
    Note over Agent: VIP: Skip inspection, instant refund
    Agent->>EventHub: publish(returns.vip_initiated)
    EventHub->>Funnel: consume(returns.vip_initiated)
    
    activate Funnel
    Funnel->>Funnel: Process refund immediately
    Funnel->>EventHub: publish(returns.refunded)
    deactivate Funnel
    
    Agent-->>API: ReturnResponse {fast_track: true, refund_status: "processed"}
    API-->>Customer: 200 OK {message: "Refund processed, return at your convenience"}
```

## Policy Evaluation Rules

### 1. Return Window Check
```python
def check_return_window(order: Order, shipment: Shipment) -> bool:
    """Validate return request is within allowed window."""
    delivered_date = shipment.events[-1].timestamp
    days_since_delivery = (datetime.now() - delivered_date).days
    
    # Standard: 30 days
    # VIP: 60 days
    # Electronics: 14 days
    window = {
        "standard": 30,
        "vip": 60,
        "electronics": 14
    }
    
    customer_tier = order.customer.tier
    category = order.items[0].category
    
    if category == "electronics":
        return days_since_delivery <= window["electronics"]
    elif customer_tier == "VIP":
        return days_since_delivery <= window["vip"]
    else:
        return days_since_delivery <= window["standard"]
```

### 2. Item Condition Check
```python
def check_item_condition(return_request: ReturnRequest) -> tuple[bool, str]:
    """Validate item meets return conditions."""
    
    # Non-returnable categories
    if return_request.category in ["perishable", "personalized", "intimate"]:
        return False, "Category not eligible for return"
    
    # Must have original packaging
    if not return_request.has_original_packaging:
        return False, "Original packaging required"
    
    # Must be unused (unless defective)
    if not return_request.unused and return_request.reason != "defective":
        return False, "Item must be unused"
    
    return True, "Eligible"
```

### 3. Return Reason Validation
```python
def validate_return_reason(reason: str, order: Order) -> tuple[bool, str]:
    """Check if return reason is valid."""
    
    valid_reasons = [
        "wrong_size",
        "wrong_item",
        "defective",
        "not_as_described",
        "changed_mind",
        "damaged_in_shipping"
    ]
    
    if reason not in valid_reasons:
        return False, "Invalid return reason"
    
    # Special handling for defective items
    if reason == "defective":
        # Auto-approve, no restocking fee
        return True, "Defect claim - expedited processing"
    
    # Restocking fee for "changed mind"
    if reason == "changed_mind":
        return True, "15% restocking fee applies"
    
    return True, "Standard return processing"
```

## LLM Return Guidance

### Prompt Template
```python
RETURN_GUIDANCE_PROMPT = """
You are a helpful returns specialist. Generate clear, empathetic return instructions for the customer.

Order Details:
- Order ID: {order_id}
- Items: {items}
- Total: ${total}
- Delivered: {delivery_date}

Return Request:
- Reason: {reason}
- Customer Message: {customer_message}

Customer Profile:
- Tier: {tier}
- Previous Returns: {return_history}

Shipment Info:
- Carrier: {carrier}
- Original Tracking: {tracking_id}

Generate:
1. A personalized greeting acknowledging their request
2. Step-by-step return instructions
3. Timeline for refund
4. Any fees or conditions
5. Contact info for questions

Tone: Professional, empathetic, clear
Length: 150-250 words
"""

async def generate_return_instructions(context: dict) -> str:
    """Use LLM to generate personalized return instructions."""
    prompt = RETURN_GUIDANCE_PROMPT.format(**context)
    response = await llm.invoke(prompt, max_tokens=500)
    return response.text
```

### Example Output
```
Hi Sarah,

We've received your return request for your recent order (#ORD-123). We're sorry the 
size wasn't quite right!

Here's how to return your items:

1. **Package Your Item**: Place the shoes back in the original box with all tags attached.

2. **Print Your Label**: Use the return label attached to this email. If you can't print, 
   visit any FedEx location and show them this email.

3. **Drop Off**: Take your package to any FedEx location. Find one near you at 
   fedex.com/locator.

4. **Track Your Return**: You'll receive tracking updates via email. Your return tracking 
   number is RTN-456789.

5. **Refund Timeline**: Once we receive your item (typically 5-7 business days), we'll 
   inspect it and process your refund within 2 business days. You'll receive $89.99 back 
   to your original payment method.

As a VIP member, we've waived the return shipping fee for you!

Questions? Reply to this email or call us at 1-800-RETAIL.

Thank you for shopping with us!
```

## SAGA Orchestration

### Event-Driven Workflow
```python
# Event definitions
@dataclass
class ReturnsInitiatedEvent:
    return_id: str
    order_id: str
    customer_id: str
    items: list[str]
    timestamp: str

@dataclass
class ReturnsAcceptedEvent:
    return_id: str
    inspection_notes: str
    timestamp: str

@dataclass
class ReturnsRefundedEvent:
    return_id: str
    amount: float
    refund_id: str
    timestamp: str

# Event handlers
async def handle_returns_initiated(event: ReturnsInitiatedEvent):
    """Warehouse handler: Create inbound receipt."""
    await wms.create_receipt(
        return_id=event.return_id,
        items=event.items,
        expected_date=datetime.now() + timedelta(days=7)
    )
    
    await event_hub.publish(ReturnsReceiptCreatedEvent(
        return_id=event.return_id,
        receipt_id=receipt_id
    ))

async def handle_returns_accepted(event: ReturnsAcceptedEvent):
    """Funnel handler: Process refund."""
    order = await get_order(event.return_id)
    
    refund = await payment_gateway.refund(
        transaction_id=order.payment.transaction_id,
        amount=order.total
    )
    
    await event_hub.publish(ReturnsRefundedEvent(
        return_id=event.return_id,
        amount=order.total,
        refund_id=refund.id
    ))
```

## Performance Characteristics

| Step | Target Latency | Optimization |
|------|----------------|--------------|
| Order fetch | < 200ms | Cached |
| Shipment validation | < 500ms | Carrier API |
| LLM guidance | < 3s | GPT-4o |
| Label generation | < 1s | Carrier API |
| Event publishing | < 100ms | Async |
| **Total (P95)** | **< 5s** | |

## Observability

### Metrics Tracked
```python
# Returns metrics
metrics.counter("returns.initiated")
metrics.counter("returns.approved")
metrics.counter("returns.rejected", {"reason": "expired|damaged|invalid"})
metrics.histogram("returns.processing_time_ms", duration)

# Policy metrics
metrics.counter("returns.policy_violation", {"type": "window|condition|category"})
metrics.gauge("returns.approval_rate", rate)

# Refund metrics
metrics.counter("returns.refunded", {"method": "standard|vip_fast_track"})
metrics.histogram("returns.refund_amount", amount)
metrics.histogram("returns.time_to_refund_days", days)

# LLM guidance
metrics.histogram("returns.llm_latency_ms", duration)
metrics.counter("returns.llm_fallback")
```

### Distributed Tracing
```python
with tracer.span(name="process_return") as span:
    span.add_attribute("order_id", order_id)
    span.add_attribute("customer_tier", customer.tier)
    
    with tracer.span(name="validate_eligibility"):
        eligible = await check_eligibility(order, shipment)
    
    if eligible:
        with tracer.span(name="generate_guidance"):
            instructions = await llm.generate(context)
        
        with tracer.span(name="create_label"):
            label = await logistics.create_label(order)
```

## Related Documentation
- [ADR-013: SLM-First Model Routing](../adrs/adr-013-model-routing.md)
- [ADR-007: SAGA Choreography with Event Hubs](../adrs/adr-007-saga-choreography.md)
- [Logistics Returns Support Component](../components/apps/logistics-returns-support.md)
- [Playbook: Tool Call Failures](../playbooks/playbook-tool-call-failures.md)
