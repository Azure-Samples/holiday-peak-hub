# CRM Segmentation and Personalization Service

Intelligent agent service for dynamic customer segmentation and personalized content recommendations based on engagement behavior and profile attributes.

## Overview

The CRM Segmentation and Personalization service provides AI-powered customer segmentation by analyzing interaction patterns, engagement levels, and opt-in status. It delivers personalized channel and content recommendations to optimize marketing effectiveness and customer experience.

## Architecture

### Components

```
crm-segmentation-personalization/
├── agents.py              # SegmentationPersonalizationAgent with SLM/LLM routing
├── adapters.py            # CRM and segmentation adapters
├── event_handlers.py      # Event Hub subscriber for order events
└── main.py                # FastAPI application with MCP tools
```

### Communication Patterns

1. **Agent REST Endpoints** (`/invoke`): Synchronous segmentation requests from frontend/CRUD
2. **MCP Tools**: Agent-to-agent communication for segment and personalization context
3. **Event Handlers**: Asynchronous processing of order events for re-segmentation

## Features

### 🎯 Dynamic Segmentation
- **Behavior-Based Segmentation**: Classify contacts based on interaction frequency and engagement
- **Rule-Based Classification**: Heuristic segmentation rules (new-lead, nurture, engaged, do-not-contact)
- **Real-Time Updates**: Re-segment customers as new interactions occur
- **Account Tier Integration**: Factor in account-level attributes (enterprise, SMB, trial)

**Segment Types:**
- **do-not-contact**: Marketing opt-out (respect preferences)
- **new-lead**: Zero interactions (onboarding focus)
- **nurture**: 1-4 interactions (education phase)
- **engaged**: 5+ interactions (conversion ready)

### 🤖 AI-Powered Personalization
- **SLM-First Routing**: Fast responses for simple segment lookups
- **LLM Escalation**: Complex recommendations requiring multi-factor analysis
- **Channel Preference**: Identify preferred channels (email, web, phone, chat) from interaction history
- **Content Recommendations**: AI-generated content suggestions per segment

### 📊 Real-Time Event Processing
- **Order Events**: Re-segment customers after purchase to update engagement status
- **Interaction Tracking**: Monitor channel usage to refine personalization

## Configuration

### Required Environment Variables

```bash
# Azure AI Foundry Configuration
PROJECT_ENDPOINT=https://your-project.cognitiveservices.azure.com/
FOUNDRY_AGENT_ID_FAST=<slm-agent-id>          # Small language model (GPT-4o-mini)
FOUNDRY_AGENT_ID_RICH=<llm-agent-id>          # Large language model (GPT-4o)
MODEL_DEPLOYMENT_NAME_FAST=<slm-deployment>
MODEL_DEPLOYMENT_NAME_RICH=<llm-deployment>
FOUNDRY_PROJECT_NAME=<project-name>           # Optional
FOUNDRY_STREAM=false                          # Enable streaming responses

# Memory Configuration (Three-Tier Architecture)
REDIS_URL=redis://localhost:6379/0            # Hot memory (session context)
COSMOS_ACCOUNT_URI=<cosmos-uri>               # Warm memory (recent interactions)
COSMOS_DATABASE=holiday-peak
COSMOS_CONTAINER=agent-memory
BLOB_ACCOUNT_URL=<blob-uri>                   # Cold memory (historical data)
BLOB_CONTAINER=agent-memory

# Event Hub Configuration
EVENTHUB_NAMESPACE=<namespace>.servicebus.windows.net
EVENTHUB_CONNECTION_STRING=<connection-string>
# Subscriptions: order-events
# Consumer Group: segmentation-group

# CRUD Service Integration (for MCP tools)
CRUD_SERVICE_URL=http://localhost:8000
```

## API Reference

### Agent REST Endpoint

**POST** `/invoke` - Generate customer segmentation and personalization recommendations

**Request Body:**
```json
{
  "contact_id": "user-789",
  "interaction_limit": 20,
  "query": "What segment is this customer in?"
}
```

**Response:**
```json
{
  "service": "crm-segmentation-personalization",
  "contact_id": "user-789",
  "crm_context": {
    "contact": {
      "contact_id": "user-789",
      "email": "user@example.com",
      "marketing_opt_in": true,
      "tags": ["vip", "enterprise"]
    },
    "account": {
      "account_id": "account-456",
      "name": "Acme Corp",
      "tier": "Enterprise"
    },
    "interactions": [...]
  },
  "segmentation": {
    "segment": "engaged",
    "interaction_count": 15,
    "personalization": {
      "preferred_channel": "email",
      "recommended_content": [
        "Upgrade offer",
        "Loyalty program",
        "Cross-sell bundle"
      ]
    },
    "tags": ["vip", "enterprise"],
    "account_tier": "Enterprise"
  }
}
```

### MCP Tools (Agent-to-Agent Communication)

#### 1. Get Contact Context
**POST** `/mcp/crm/segmentation/context`

```json
{
  "contact_id": "user-789",
  "interaction_limit": 20
}
```

Returns full CRM context for segmentation analysis.

**Response:**
```json
{
  "crm_context": {
    "contact": { ... },
    "account": { ... },
    "interactions": [ ... ]
  }
}
```

#### 2. Get Segment
**POST** `/mcp/crm/segmentation/segment`

```json
{
  "contact_id": "user-789"
}
```

Returns customer segment classification and metadata.

**Response:**
```json
{
  "segmentation": {
    "segment": "engaged",
    "interaction_count": 15,
    "personalization": {
      "preferred_channel": "email",
      "recommended_content": [
        "Upgrade offer",
        "Loyalty program",
        "Cross-sell bundle"
      ]
    },
    "tags": ["vip", "enterprise"],
    "account_tier": "Enterprise"
  }
}
```

#### 3. Get Personalization
**POST** `/mcp/crm/segmentation/personalization`

```json
{
  "contact_id": "user-789"
}
```

Returns personalization recommendations only (channel + content).

**Response:**
```json
{
  "personalization": {
    "preferred_channel": "email",
    "recommended_content": [
      "Upgrade offer",
      "Loyalty program",
      "Cross-sell bundle"
    ]
  }
}
```

## Segmentation Logic

### Segment Classification Rules

```python
if not marketing_opt_in:
    segment = "do-not-contact"  # Respect privacy preferences
elif interaction_count == 0:
    segment = "new-lead"         # No engagement yet
elif interaction_count >= 5:
    segment = "engaged"          # High engagement
else:
    segment = "nurture"          # Low-moderate engagement (1-4)
```

### Preferred Channel Detection

Analyzes interaction history to identify most-used channel:

```python
# Count interactions per channel
email: 8 interactions
web: 5 interactions
phone: 2 interactions
chat: 0 interactions

# Result: preferred_channel = "email"
```

### Content Recommendations Per Segment

| Segment | Recommended Content |
|---------|-------------------|
| **do-not-contact** | Respect opt-out; account-level updates only |
| **new-lead** | Welcome series, Onboarding tips, Product overview |
| **nurture** | Education series, Case studies, Trial extension |
| **engaged** | Upgrade offer, Loyalty program, Cross-sell bundle |

## Event Processing

### Subscribed Events

| Event Hub | Consumer Group | Purpose |
|-----------|----------------|---------|
| `order-events` | `segmentation-group` | Re-segment customers after purchase interactions |

### Event Handling Logic

1. **Extract Contact ID**: Parse `contact_id`, `user_id`, `customer_id`, or `id` from event payload
2. **Skip Invalid Events**: Log and skip events without identifiable contact
3. **Build CRM Context**: Fetch contact context including interaction history
4. **Calculate Segment**: Apply segmentation rules based on engagement
5. **Determine Personalization**: Identify preferred channel and content recommendations
6. **Log Processing**: Structured logging with segment and channel info

## Development

### Running Locally

```bash
# Install dependencies (from repository root)
uv sync

# Set environment variables
export PROJECT_ENDPOINT=https://your-project.cognitiveservices.azure.com/
export FOUNDRY_AGENT_ID_FAST=<slm-agent-id>
export REDIS_URL=redis://localhost:6379/0

# Run service
uvicorn crm_segmentation_personalization.main:app --reload --port 8012
```

### Testing

```bash
# Run unit tests
pytest apps/crm-segmentation-personalization/tests/

# Test agent endpoint
curl -X POST http://localhost:8012/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "contact_id": "user-789",
    "query": "What segment is this customer?"
  }'

# Test MCP tool - Get Segment
curl -X POST http://localhost:8012/mcp/crm/segmentation/segment \
  -H "Content-Type: application/json" \
  -d '{"contact_id": "user-789"}'

# Test MCP tool - Get Personalization
curl -X POST http://localhost:8012/mcp/crm/segmentation/personalization \
  -H "Content-Type: application/json" \
  -d '{"contact_id": "user-789"}'
```

## Dependencies

- **holiday-peak-lib**: Shared framework (agents, adapters, memory, utilities)
- **FastAPI**: REST API and MCP server
- **Azure Event Hubs**: Async event processing
- **Azure AI Foundry**: SLM/LLM inference
- **Redis**: Hot memory (session context)
- **Azure Cosmos DB**: Warm memory (recent interactions)
- **Azure Blob Storage**: Cold memory (historical data)

## Agent Behavior

### System Instructions

The agent is instructed to:
- **Segment based on behavior**: Use engagement and opt-in status to classify
- **Recommend channels**: Identify preferred communication channel from interaction history
- **Suggest content tone**: Match messaging to segment (education vs conversion)
- **Highlight gaps**: Call out missing data (no channel preference, no account tier)
- **Provide next steps**: Suggest safe actions (respect opt-out, nurture new leads)

### SLM vs LLM Routing

| Query Type | Model | Reasoning |
|------------|-------|-----------|
| "What segment is user-789 in?" | SLM | Simple classification lookup |
| "Get preferred channel for user-789" | SLM | Direct aggregation from interactions |
| "Compare segments across enterprise accounts" | LLM | Cross-account analysis |
| "Predict segment migration for user-789" | LLM | Predictive modeling |
| "Why is engagement declining?" | LLM | Causal analysis |

## Integration Examples

### From Frontend (Direct Call)

```typescript
// React component
const { data, isLoading } = useQuery({
  queryKey: ['customer-segment', contactId],
  queryFn: () => 
    fetch(`${AGENT_URL}/invoke`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contact_id: contactId,
        query: 'Get customer segment'
      })
    }).then(r => r.json())
});
```

### From CRUD Service (Via Agent Client)

```python
# CRUD service calling segmentation
from crud_service.integrations.agent_client import get_agent_client

agent_client = get_agent_client()
segment = await agent_client.call_endpoint(
    agent_url=settings.segmentation_agent_url,
    endpoint="/invoke",
    data={"contact_id": "user-789"},
    fallback_value={"segmentation": {"segment": "nurture"}}
)
```

### From Another Agent (MCP Tool)

```python
# Campaign intelligence agent calling segmentation via MCP
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://crm-segmentation-personalization:8012/mcp/crm/segmentation/personalization",
        json={"contact_id": "user-789"}
    )
    personalization = response.json()
```

## Use Cases

### 1. Targeted Email Campaigns
Filter contacts by segment and preferred channel:
```python
# Get all engaged customers who prefer email
segments = await get_segments_for_campaign()
email_engaged = [c for c in segments if c.segment == "engaged" and c.preferred_channel == "email"]
# Send upgrade offer campaign
```

### 2. Dynamic Website Personalization
Show different content based on segment:
```python
segment = await get_segment(contact_id)
if segment == "new-lead":
    show_onboarding_banner()
elif segment == "engaged":
    show_upgrade_cta()
else:
    show_education_content()
```

### 3. Customer Support Prioritization
Route high-value segments to senior agents:
```python
segment = await get_segment(contact_id)
if segment == "engaged" and account_tier == "Enterprise":
    route_to_senior_support()
else:
    route_to_standard_queue()
```

### 4. Opt-Out Compliance
Automatically exclude do-not-contact segments:
```python
segment = await get_segment(contact_id)
if segment == "do-not-contact":
    skip_marketing_send()
    log_compliance_skip()
```

### 5. Re-Engagement Campaigns
Target nurture segment with educational content:
```python
nurture_contacts = await get_segment_members("nurture")
for contact in nurture_contacts:
    personalization = await get_personalization(contact.id)
    send_content(contact, personalization.recommended_content)
```

## Monitoring & Observability

### Key Metrics

- `segmentation_event_processed`: Event processing count with segment distribution
- `segmentation_event_skipped`: Events without identifiable contact
- `segmentation_event_missing_contact`: Events where contact lookup failed
- `agent_invocation_duration`: Agent response time (SLM vs LLM)
- `segment_distribution`: Histogram of contacts per segment

### Logs

All operations emit structured logs with correlation IDs:

```json
{
  "event": "segmentation_event_processed",
  "event_type": "order.created",
  "contact_id": "user-789",
  "segment": "engaged",
  "preferred_channel": "email",
  "timestamp": "2026-02-03T10:30:00Z"
}
```

## Production Considerations

### Resilience
- **Circuit Breaker**: CRM adapter calls have circuit breakers
- **Fallback**: Returns default segment ("nurture") if CRM adapter unavailable
- **Timeout**: Fast timeouts prevent cascading failures

### Scalability
- **Stateless Agent**: Horizontal scaling via Kubernetes/Container Apps
- **Event Processing**: Consumer group allows parallel processing across partitions
- **Memory Tiering**: Hot (Redis) → Warm (Cosmos) → Cold (Blob) for efficient context retrieval

### Performance
- **Interaction Limit**: Default 20 interactions per analysis (configurable)
- **Caching**: Hot memory (Redis) caches segment results
- **Heuristic Rules**: Fast rule-based segmentation (no ML inference latency)

### Security
- **Authentication**: Azure Managed Identity for Event Hubs, Cosmos DB, Blob Storage
- **API Keys**: Azure AI Foundry uses key-based auth (rotate regularly)
- **PII Protection**: Contact data encrypted at rest
- **Network Isolation**: Deploy in private subnet with service endpoints

### Compliance
- **Opt-Out Respect**: "do-not-contact" segment enforced across all campaigns
- **GDPR**: Support right-to-erasure via contact deletion
- **Audit Trail**: All segment changes logged with timestamps
- **Data Retention**: Configurable retention periods per compliance requirements

## Advanced Segmentation (Future)

Current implementation uses heuristic rules. Future enhancements:

### ML-Based Segmentation
- **K-Means Clustering**: Unsupervised segmentation based on engagement vectors
- **RFM Analysis**: Recency, Frequency, Monetary value scoring
- **Predictive Segments**: Churn risk, lifetime value, conversion probability

### Multi-Dimensional Segmentation
- **Behavioral**: Engagement level, channel preference, content affinity
- **Demographic**: Industry, company size, role, geography
- **Firmographic**: Account tier, contract value, renewal date
- **Technographic**: Product usage, feature adoption, integrations

### Real-Time Personalization
- **Dynamic Content**: A/B testing content recommendations
- **Contextual Offers**: Personalize based on current session behavior
- **Next Best Action**: Recommend optimal next interaction per segment

## Related Services

- **crm-profile-aggregation**: Provides unified profile context for segmentation
- **crm-campaign-intelligence**: Uses segments for campaign targeting
- **crm-support-assistance**: Uses segments for support prioritization
- **crud-service**: Transactional API for CRM data (called via MCP tools)

## License

See repository root for license information.
