# Business Scenario 03: Returns & Refund Processing

## Overview

**Returns & Refund Processing** manages the reverse logistics pipeline — from the moment a customer requests a return through evaluation, approval, inventory restocking, and refund issuance. In Holiday Peak Hub, this process combines **AI-powered evaluation** (the returns support agent assesses return eligibility) with **event-driven choreography** for inventory updates and refund processing.

## Business Importance for Retail

| Metric | Impact |
|--------|--------|
| **Return Rate** | E-commerce average is 20–30%; holiday season can reach 40% |
| **Customer Retention** | Smooth return experience increases repeat purchase probability by 95% |
| **Processing Cost** | Manual return evaluation costs $8–15 per case; AI reduces this to $0.50–2 |
| **Inventory Recovery** | Fast restocking of returned items prevents lost sales on returnable goods |
| **Fraud Prevention** | AI pattern detection reduces return fraud (wardrobing, receipt fraud) by 30–50% |
| **Refund Speed** | Customers expect refunds within 3–5 business days; delays trigger chargebacks |

Post-holiday return surges (January "Returnuary") create massive operational pressure. Automating the evaluation and processing pipeline is critical for maintaining customer satisfaction while controlling costs.

## Traditional Challenges

1. **Manual Evaluation**: Returns staff must individually assess each return request — slow and inconsistent
2. **Inventory Blindness**: Returned items sit in limbo, not available for resale until manually processed
3. **Refund Delays**: Multi-step approval chains delay refunds, triggering customer complaints and chargebacks
4. **Fraud Vulnerability**: Without pattern analysis, serial returners and wardrobers exploit lenient policies
5. **Label Generation**: Creating return shipping labels requires manual carrier coordination
6. **Cross-System Updates**: Order status, inventory, payment, and CRM systems need coordinated updates

## How Holiday Peak Hub Addresses It

### AI-Assisted Return Evaluation

The `logistics-returns-support` agent evaluates return requests using:
- Purchase history analysis (repeat returner? high-value customer?)
- Product condition assessment (from customer description/photos)
- Policy rule matching (within return window? eligible category?)
- SLM handles straightforward cases; LLM evaluates edge cases

### Event-Driven Processing Pipeline

```
ReturnRequested → Agent Evaluates → Staff Approves → ReturnApproved
                                                        ↓
                            Inventory Restocked ← inventory-health-check
                                                        ↓
                            Refund Issued ← Payment Service → RefundProcessed
```

## Process Flow

### Return Request & Evaluation

1. **Customer** initiates return on `/order/[id]` page → `POST /api/orders/{id}/return`
2. **CRUD Service** creates return request (status: `requested`), publishes `ReturnRequested` to `order-events`
3. **Returns Support Agent** (`logistics-returns-support`) receives `ReturnRequested`:
   - Fetches order details and customer history
   - Evaluates return eligibility (SLM-first, LLM for complex cases)
   - Generates return authorization with conditions (full refund, partial, store credit)
   - Auto-approves simple cases (within policy, no flags)
   - Flags complex cases for human review
4. **Staff** reviews flagged cases on admin panel → approves/denies

### Return Approval & Fulfillment

5. **CRUD Service** publishes `ReturnApproved` to `order-events`
6. **Returns Support Agent** generates return shipping label:
   - Selects optimal return carrier (cost, pickup availability)
   - Generates prepaid label
   - Publishes `ReturnLabelGenerated` event
   - Sends label to customer via email
7. **Customer** ships item back using provided label

### Inventory Restocking

8. **Inventory Health Check Agent** (`inventory-health-check`) receives `ReturnApproved`:
   - Updates expected inbound inventory count
   - When item received and inspected: restocks available inventory
   - Publishes `InventoryRestocked` to `inventory-events`
   - If item returned in poor condition → updates as damaged/write-off

### Refund Processing

9. **Payment Service** receives `ReturnApproved`:
   - Initiates refund to original payment method
   - Partial refund if conditions apply (restocking fee, damage deduction)
   - Publishes `RefundProcessed` to `payment-events`
10. **CRUD Service** receives `RefundProcessed`:
    - Updates order status to `refunded`
    - Sends refund confirmation to customer

### CRM & Support Updates

11. **Support Assistance Agent** (`crm-support-assistance`) receives `ReturnRequested`:
    - Logs return reason in knowledge base
    - Detects patterns (product defect trends, sizing issues)
    - Updates FAQ articles if common return reason identified
12. **CRM Campaign Intelligence** receives `RefundProcessed`:
    - Updates customer lifetime value (LTV reduction)
    - Adjusts segmentation (frequent returner flag)

## Agents Involved

| Agent | Role | Trigger Event | Output |
|-------|------|--------------|--------|
| `logistics-returns-support` | Evaluate return eligibility, generate label | `ReturnRequested` | Authorization, return label |
| `inventory-health-check` | Restock returned inventory | `ReturnApproved` | `InventoryRestocked` |
| `crm-support-assistance` | Log return reasons, detect patterns | `ReturnRequested` | KB updates, pattern alerts |
| `crm-campaign-intelligence` | Update customer metrics | `RefundProcessed` | LTV adjustment |

## Event Hub Topology

```
order-events (ReturnRequested)    ──→  logistics-returns-support, crm-support-assistance
order-events (ReturnApproved)     ──→  inventory-health-check, payment-service
payment-events (RefundProcessed)  ──→  crm-campaign-intelligence, crud-service
```

## Key Performance Indicators

| KPI | Target | Measurement |
|-----|--------|-------------|
| Return evaluation time | < 30 seconds (auto) | Time from request to AI recommendation |
| Auto-approval rate | > 70% | Returns resolved without human intervention |
| Refund processing time | < 3 business days | Request to refund confirmation |
| Inventory recovery rate | > 85% | Returned items successfully restocked |
| Fraud detection rate | > 90% | Flagged fraudulent returns / total fraud |
| Return reason capture | 100% | Returns with categorized reason codes |

## BPMN Diagram

See [returns-refund-processing.drawio](returns-refund-processing.drawio) for the complete BPMN 2.0 process diagram showing:
- **6 pools**: Customer, CRUD Service, Event Hub, Returns Agent, Inventory Agent, Payment Service
- **AI evaluation gateway**: Auto-approve vs. human review decision
- **Parallel processing**: Inventory restock and refund happen concurrently after approval
- **Compensation**: CRM updates triggered by refund completion
