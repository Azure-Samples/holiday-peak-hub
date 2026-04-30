# CRM Campaign Creation Demo

**Scenario**: Customer Data → Segmentation → Campaign Design → Personalization → ROI Analysis  
**Duration**: 15-20 minutes  
**Agents Involved**: 5  
**Status**: Phase 3 - Planned

---

## Overview

This scenario demonstrates intelligent customer segmentation, personalized product recommendations, and ROI-optimized campaign generation using customer profile aggregation and ML-driven insights.

---

## Scenario Flow

### Step 1: Profile Aggregation
**Agent**: `crm-profile-aggregation` (Port 8010)  
**Goal**: Aggregate customer data from multiple touchpoints into a unified profile

**Request**:
```json
POST http://localhost:8010/invoke
{
  "user_id": "user-12345",
  "include_sources": ["orders", "browsing", "support_tickets", "reviews"]
}
```

**Expected Output**:
```json
{
  "unified_profile": {
    "user_id": "user-12345",
    "name": "Customer A2B3C4",
    "lifetime_value": 1247.50,
    "total_orders": 8,
    "average_order_value": 155.94,
    "preferred_categories": ["Electronics", "Home & Kitchen"],
    "last_purchase": "2026-04-15T10:30:00Z",
    "engagement_score": 0.82,
    "touchpoints": {
      "orders": 8,
      "browsing_sessions": 45,
      "support_tickets": 2,
      "reviews_submitted": 3
    },
    "preferences": {
      "communication_channel": "email",
      "shopping_time": "evening",
      "price_sensitivity": "medium",
      "brand_loyalty": "high"
    },
    "recent_activity": [
      {"type": "browse", "item": "Wireless Noise-Cancelling Headphones", "timestamp": "2026-04-28"},
      {"type": "browse", "item": "Smart Fitness Tracker", "timestamp": "2026-04-27"},
      {"type": "purchase", "item": "USB-C Hub 8-in-1", "timestamp": "2026-04-15"}
    ]
  },
  "data_freshness": "2026-04-30T14:00:00Z"
}
```

**MCP Tool Calls** (internal):
- `/mcp/get_order_history` → CRUD service
- `/mcp/get_browsing_data` → Analytics adapter
- `/mcp/get_support_history` → Support assistance agent
- `/mcp/get_review_activity` → CRUD service

**Memory Usage**:
- Hot (Redis): Profile cache (15 min TTL)
- Warm (Cosmos): Full profile history

---

### Step 2: Customer Segmentation
**Agent**: `crm-segmentation-personalization` (Port 8011)  
**Goal**: Classify customer into dynamic segments using RFM-enhanced model

**Request**:
```json
POST http://localhost:8011/invoke
{
  "user_id": "user-12345",
  "segmentation_model": "rfm_enhanced",
  "personalization_context": "campaign_targeting"
}
```

**Expected Output**:
```json
{
  "segmentation": {
    "primary_segment": "high_value_loyalist",
    "rfm_scores": {
      "recency": 9,
      "frequency": 7,
      "monetary": 8
    },
    "behavioral_tags": ["tech_enthusiast", "weekend_shopper", "deal_seeker"],
    "churn_risk": 0.12,
    "next_purchase_prediction": {
      "probability": 0.78,
      "expected_within_days": 14,
      "likely_category": "Electronics"
    }
  },
  "personalization": {
    "recommended_products": [
      {"sku": "d9c3b1de-7158-5ea1-9f33-7bdaec2f0462", "name": "Wireless Noise-Cancelling Headphones", "affinity_score": 0.92},
      {"sku": "517290d8-2941-5c34-9382-7aa988f91458", "name": "Smart Fitness Tracker", "affinity_score": 0.85},
      {"sku": "b275a1b3-9f9f-5161-bd44-d5098f9f114a", "name": "True Wireless Earbuds Pro", "affinity_score": 0.79}
    ],
    "optimal_send_time": "2026-05-01T19:00:00Z",
    "preferred_channel": "email",
    "discount_threshold": "10-15%"
  }
}
```

**Memory Usage**:
- Warm (Cosmos): Segment history and transitions
- Cold (Blob): ML model artifacts and training data

**SLM vs LLM**:
- **SLM** handles standard RFM scoring (90% of cases)
- **LLM** escalates for complex behavioral analysis

---

### Step 3: Campaign Content Generation
**Agent**: `crm-campaign-intelligence` (Port 8012)  
**Goal**: Generate personalized campaign content with ROI prediction

**Request**:
```json
POST http://localhost:8012/invoke
{
  "campaign_type": "holiday_promotion",
  "target_segment": "high_value_loyalist",
  "budget": 5000,
  "channel": "email",
  "products_to_feature": [
    "d9c3b1de-7158-5ea1-9f33-7bdaec2f0462",
    "517290d8-2941-5c34-9382-7aa988f91458"
  ]
}
```

**Expected Output**:
```json
{
  "campaign": {
    "campaign_id": "CAMP-2026-05-ELECTRONICS",
    "name": "Tech Essentials — Exclusive for You",
    "subject_line": "Your perfect audio upgrade is waiting (15% off)",
    "preview_text": "Premium headphones & fitness tech handpicked for you",
    "content": {
      "hero_product": {
        "sku": "d9c3b1de-7158-5ea1-9f33-7bdaec2f0462",
        "headline": "Silence the world. Hear what matters.",
        "offer": "15% off Wireless Noise-Cancelling Headphones"
      },
      "secondary_products": [
        {
          "sku": "517290d8-2941-5c34-9382-7aa988f91458",
          "headline": "Track every milestone",
          "offer": "10% off Smart Fitness Tracker"
        }
      ],
      "cta": "Shop Now — Offer ends May 7"
    },
    "targeting": {
      "segment": "high_value_loyalist",
      "estimated_recipients": 2340,
      "send_time": "2026-05-01T19:00:00Z"
    }
  },
  "roi_prediction": {
    "expected_revenue": 18500,
    "expected_cost": 5000,
    "predicted_roi": 2.7,
    "confidence": 0.82,
    "expected_conversions": 187,
    "expected_open_rate": 0.42,
    "expected_click_rate": 0.15
  }
}
```

**MCP Tool Calls** (internal):
- `/mcp/get_product_details` → Product enrichment agent
- `/mcp/get_segment_performance` → Historical campaign data
- `/mcp/predict_roi` → ML prediction model

**Memory Usage**:
- Warm (Cosmos): Campaign templates and performance history
- Cold (Blob): Historical campaign analytics

**SLM vs LLM**:
- **LLM** required for content generation (subject lines, copy)
- Token usage: ~2,500 tokens per campaign

---

### Step 4: Campaign Intelligence & Optimization
**Agent**: `crm-campaign-intelligence` (Port 8012)  
**Goal**: A/B test recommendations and real-time optimization

**Request** (post-send analysis):
```json
POST http://localhost:8012/invoke
{
  "campaign_id": "CAMP-2026-05-ELECTRONICS",
  "action": "analyze_performance",
  "metrics_window": "24h"
}
```

**Expected Output**:
```json
{
  "performance": {
    "campaign_id": "CAMP-2026-05-ELECTRONICS",
    "sent": 2340,
    "delivered": 2298,
    "opened": 966,
    "clicked": 345,
    "converted": 52,
    "revenue_generated": 8750.48,
    "open_rate": 0.42,
    "click_rate": 0.15,
    "conversion_rate": 0.022
  },
  "ab_test_results": {
    "variant_a": {"subject": "Your perfect audio upgrade is waiting (15% off)", "open_rate": 0.42},
    "variant_b": {"subject": "Premium tech, exclusive price — just for you", "open_rate": 0.38},
    "winner": "variant_a",
    "confidence": 0.94
  },
  "optimization_suggestions": [
    "Increase discount to 20% for users who opened but didn't convert (estimated +35 conversions)",
    "Send follow-up to non-openers at alternate time (morning send predicted 8% higher open rate)",
    "Add urgency element: '48 hours left' for clicked-but-not-converted segment"
  ],
  "next_actions": [
    {"action": "send_follow_up", "segment": "opened_not_clicked", "recommended_time": "2026-05-03T10:00:00Z"},
    {"action": "increase_offer", "segment": "clicked_not_converted", "recommended_discount": "20%"}
  ]
}
```

---

### Step 5: Post-Campaign Support
**Agent**: `crm-support-assistance` (Port 8013)  
**Goal**: Handle inbound support tickets generated by campaign engagement

**Request**:
```json
POST http://localhost:8013/invoke
{
  "ticket_id": "TKT-77801",
  "user_id": "user-12345",
  "query": "I received the promotion email but the 15% discount code is not working at checkout",
  "context": {
    "campaign_id": "CAMP-2026-05-ELECTRONICS",
    "product_sku": "d9c3b1de-7158-5ea1-9f33-7bdaec2f0462"
  }
}
```

**Expected Output**:
```json
{
  "resolution": {
    "ticket_id": "TKT-77801",
    "status": "resolved",
    "action_taken": "discount_applied_manually",
    "response": "I've applied the 15% discount directly to your cart. The promotional code TECH15 was case-sensitive — I've also updated your account so it works automatically. Your Wireless Noise-Cancelling Headphones are now $212.49 (was $249.99). Ready to checkout!",
    "discount_applied": {
      "code": "TECH15",
      "amount": 37.50,
      "applied_to_sku": "d9c3b1de-7158-5ea1-9f33-7bdaec2f0462"
    }
  },
  "customer_sentiment": "frustrated_but_recoverable",
  "escalation_needed": false,
  "follow_up": {
    "scheduled": true,
    "type": "satisfaction_check",
    "time": "2026-05-02T10:00:00Z"
  }
}
```

**MCP Tool Calls** (internal):
- `/mcp/get_campaign_context` → Campaign intelligence agent
- `/mcp/apply_discount` → CRUD service
- `/mcp/get_user_profile` → Profile aggregation agent

**Memory Usage**:
- Hot (Redis): Active ticket context (session TTL)
- Warm (Cosmos): Ticket history, resolution patterns

---

## Event Choreography

### Campaign Lifecycle Events
```
[Profile Aggregation] → crm-events.profile_updated
     │
     ▼
[Segmentation] → crm-events.segment_assigned
     │
     ▼
[Campaign Intelligence] → crm-events.campaign_created
     │
     ▼
[Email Service] → crm-events.campaign_sent
     │
     ├───────────────────────────────────┐
     ▼                                   ▼
[Analytics: opens/clicks]          [Support Assistance]
  crm-events.engagement_tracked     (handles inbound tickets)
     │
     ▼
[Campaign Optimization]
  crm-events.optimization_applied
```

---

## Performance Metrics

### Processing Time Breakdown
- **Profile Aggregation**: 180ms (parallel source queries)
- **Segmentation**: 120ms (SLM + cached model)
- **Campaign Generation**: 1.2s (LLM for content)
- **ROI Prediction**: 250ms (ML model inference)
- **Support Resolution**: 400ms (SLM for simple, LLM for complex)

### Campaign KPIs (Benchmark)

| Metric | Industry Average | With Agents | Improvement |
|--------|-----------------|-------------|-------------|
| Open Rate | 21% | 42% | +100% |
| Click Rate | 2.6% | 15% | +477% |
| Conversion Rate | 1.2% | 2.2% | +83% |
| Revenue per Email | $0.08 | $3.74 | +4575% |
| Support Resolution Time | 4 hours | 8 minutes | -97% |

---

## Running the Demo

### Prerequisites
```bash
# Start CRUD service
cd apps/crud-service/src && uvicorn crud_service.main:app --reload --port 8000

# Start CRM agents
cd apps/crm-profile-aggregation/src && uvicorn main:app --reload --port 8010 &
cd apps/crm-segmentation-personalization/src && uvicorn main:app --reload --port 8011 &
cd apps/crm-campaign-intelligence/src && uvicorn main:app --reload --port 8012 &
cd apps/crm-support-assistance/src && uvicorn main:app --reload --port 8013 &
```

### Run Step-by-Step
```bash
# Step 1: Aggregate profile
curl -X POST http://localhost:8010/invoke \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user-12345","include_sources":["orders","browsing","support_tickets","reviews"]}'

# Step 2: Segment customer
curl -X POST http://localhost:8011/invoke \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user-12345","segmentation_model":"rfm_enhanced","personalization_context":"campaign_targeting"}'

# Step 3: Generate campaign
curl -X POST http://localhost:8012/invoke \
  -H "Content-Type: application/json" \
  -d '{"campaign_type":"holiday_promotion","target_segment":"high_value_loyalist","budget":5000,"channel":"email","products_to_feature":["d9c3b1de-7158-5ea1-9f33-7bdaec2f0462","517290d8-2941-5c34-9382-7aa988f91458"]}'

# Step 4: Analyze performance (after campaign sent)
curl -X POST http://localhost:8012/invoke \
  -H "Content-Type: application/json" \
  -d '{"campaign_id":"CAMP-2026-05-ELECTRONICS","action":"analyze_performance","metrics_window":"24h"}'

# Step 5: Handle support ticket
curl -X POST http://localhost:8013/invoke \
  -H "Content-Type: application/json" \
  -d '{"ticket_id":"TKT-77801","user_id":"user-12345","query":"I received the promotion email but the 15% discount code is not working at checkout","context":{"campaign_id":"CAMP-2026-05-ELECTRONICS","product_sku":"d9c3b1de-7158-5ea1-9f33-7bdaec2f0462"}}'
```

---

## Related Demos
- [Customer Journey](customer-journey.md) - Customer interactions
- [Product Lifecycle](product-lifecycle.md) - Product recommendations
- [Order Fulfillment](order-fulfillment.md) - Post-purchase analysis
