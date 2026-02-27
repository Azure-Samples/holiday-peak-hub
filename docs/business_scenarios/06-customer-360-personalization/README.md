# Business Scenario 06: Customer 360 & Personalization

## Overview

**Customer 360 & Personalization** describes the continuous process of building comprehensive customer profiles, computing lifetime value (LTV), segmenting audiences, and delivering personalized campaign content. Holiday Peak Hub uses a cascade of CRM agents — from profile aggregation through segmentation to campaign intelligence — that react to user events and maintain an always-current view of every customer.

## Business Importance for Retail

| Metric | Impact |
|--------|--------|
| **Revenue Uplift** | Personalized recommendations drive 15–30% of eCommerce revenue |
| **Conversion Rate** | Personalized experiences convert 2–3× better than generic ones |
| **Customer Retention** | Effective segmentation reduces churn by 20–40% |
| **Campaign ROI** | AI-driven campaigns achieve 3–5× higher click-through rates |
| **CLV Accuracy** | Accurate LTV scoring improves acquisition spend efficiency by 25% |
| **Peak Conversion** | During holidays, personalized promotions capture higher share of wallet |

Retailers compete on customer experience. The ability to recognize returning customers, understand their preferences, predict their needs, and tailor communications in real-time differentiates winners from commodity players — especially during high-traffic peak periods.

## Traditional Challenges

1. **Data Silos**: Customer data fragmented across CRM, eCommerce, support, and marketing platforms
2. **Batch Processing**: Profiles updated nightly; campaigns based on stale segments
3. **Manual Segmentation**: Marketing teams manually define segments using rigid rule-based criteria
4. **Static Campaigns**: One-size-fits-all messaging, regardless of customer behavior or context
5. **LTV Guesswork**: No real-time lifetime value calculation; acquisition budgets based on averages
6. **No Attribution**: Unable to link campaign engagement back to purchase behavior in real-time

## How Holiday Peak Hub Addresses It

### Event-Driven Profile Pipeline

```
user.registered → profile-aggregation creates profile
user.browsed / user.searched → profile updates hot memory
order.placed → profile-aggregation → LTV recalculation
LTV updated → segmentation-personalization → segment assignment
segment assigned → campaign-intelligence → campaign content generated
```

### Three-Tier Profile Memory

| Tier | Store | Content | TTL |
|------|-------|---------|-----|
| **Hot** | Redis | Active session context, recent browsing, cart state | 15 min |
| **Warm** | Cosmos DB | Full profile, purchase history, LTV score, segments | Persistent |
| **Cold** | Blob Storage | Historical interaction logs, archive | Persistent |

The profile is assembled progressively: hot memory captures real-time session behavior, warm memory maintains the canonical profile, and cold stores long-tail history for deep analytics.

## Process Flow

### Profile Creation & Enrichment

1. **Customer registers** → `user.registered` event published
2. **Profile Aggregation Agent** (`crm-profile-aggregation`) receives event:
   - Creates initial profile in Cosmos DB (warm memory)
   - Sets default segment: "new_customer"
   - Initializes LTV at $0 with acquisition channel metadata
   - Stores session data in Redis (hot memory)

### Real-Time Behavioral Updates

3. **Customer browses / searches / interacts** → `user.browsed`, `user.searched` events
4. **Profile Aggregation Agent** updates hot memory:
   - Appends browsing categories, search queries, product views
   - Calculates engagement score (session depth, time on site)
   - Tracks affinity signals (frequently viewed categories, price ranges)

### Purchase & LTV Recalculation

5. **Customer places order** → `order.placed` event published
6. **Profile Aggregation Agent** receives `order.placed`:
   - Adds order to purchase history
   - Recalculates LTV using:
     - Total spend to date
     - Purchase frequency
     - Average order value
     - Recency weighting
   - Updates profile in Cosmos DB

### Segmentation

7. **Segmentation & Personalization Agent** (`crm-segmentation-personalization`) receives updated profile:
   - AI evaluates profile against multiple dimensions:
     - Value tier: VIP / High / Medium / Low / At-Risk
     - Lifecycle stage: New / Active / Dormant / Churning / Win-Back
     - Behavioral cluster: Bargain Hunter / Brand Loyal / Impulse / Researcher
   - SLM handles standard segmentation; LLM for complex edge cases
   - Assigns segment labels to profile
   - Publishes `SegmentUpdated` event

### Campaign Attribution & Content

8. **Campaign Intelligence Agent** (`crm-campaign-intelligence`) receives segment update:
   - Generates personalized campaign recommendations:
     - Email subject lines optimized per segment
     - Product recommendations based on purchase/browse history
     - Discount strategies aligned with value tier and lifecycle
   - Tracks campaign attribution:
     - Links campaign engagement to subsequent purchases
     - Calculates campaign-specific ROI
   - Stores campaign recommendations in warm memory for marketing tools

## Agents Involved

| Agent | Role | Trigger | Output |
|-------|------|---------|--------|
| `crm-profile-aggregation` | Profile assembly and LTV | `user.registered`, `user.browsed`, `order.placed` | Updated profile, LTV score |
| `crm-segmentation-personalization` | AI segmentation and segment assignment | Profile update events | `SegmentUpdated` |
| `crm-campaign-intelligence` | Campaign content and attribution | `SegmentUpdated` | Campaign recommendations |

## Event Hub Topology

```
user-events (user.registered)  ──→  crm-profile-aggregation
user-events (user.browsed)     ──→  crm-profile-aggregation
order-events (order.placed)    ──→  crm-profile-aggregation
user-events (profile.updated)  ──→  crm-segmentation-personalization
user-events (segment.updated)  ──→  crm-campaign-intelligence
```

## Key Performance Indicators

| KPI | Target | Measurement |
|-----|--------|-------------|
| Profile freshness | < 5 seconds | Time from event to profile update in warm memory |
| LTV accuracy | > 85% | Predicted vs. actual 12-month customer value |
| Segment coverage | 100% | Percentage of profiles with assigned segments |
| Campaign personalization rate | > 90% | Campaigns using AI-generated content vs. generic |
| Campaign click-through uplift | > 2× | Personalized vs. non-personalized CTR |
| Attribution accuracy | > 80% | Purchases correctly linked to triggering campaign |

## BPMN Diagram

See [customer-360-personalization.drawio](customer-360-personalization.drawio) for the complete BPMN 2.0 process diagram showing:
- **4 pools**: Customer Events, Profile Aggregation Agent, Segmentation Agent, Campaign Intelligence Agent
- **Progressive enrichment**: Registration → browsing → purchase → LTV → segment → campaign
- **Three-tier memory**: Hot (Redis) → Warm (Cosmos DB) → Cold (Blob) data flow
- **AI gateways**: SLM/LLM routing for complex segmentation
