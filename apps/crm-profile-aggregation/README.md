# CRM Profile Aggregation Service

Intelligent agent service for aggregating customer profiles across multiple data sources and building unified customer context.

## Overview

The CRM Profile Aggregation service provides AI-powered customer profile consolidation by combining contact information, account data, interaction history, and engagement metrics. It processes real-time user and order events to maintain up-to-date customer profiles and exposes both REST and MCP endpoints for downstream consumption.

## Architecture

### Components

```
crm-profile-aggregation/
├── agents.py              # ProfileAggregationAgent with SLM/LLM routing
├── adapters.py            # CRM and analytics adapters
├── event_handlers.py      # Event Hub subscribers for user/order events
└── main.py                # FastAPI application with MCP tools
```

### Communication Patterns

1. **Agent REST Endpoints** (`/invoke`): Synchronous profile retrieval from frontend/CRUD
2. **MCP Tools**: Agent-to-agent communication for profile context sharing
3. **Event Handlers**: Asynchronous processing of user and order events

## Features

### 👤 Profile Aggregation
- **Unified Contact View**: Consolidate contact details, account information, and metadata
- **Interaction History**: Track customer interactions across channels (email, web, phone, chat)
- **Engagement Scoring**: Calculate engagement metrics based on interaction frequency
- **Account Linking**: Automatically link contacts to parent accounts (B2B scenarios)

### 🤖 AI-Powered Intelligence
- **SLM-First Routing**: Fast responses for simple profile lookups and summaries
- **LLM Escalation**: Complex analysis requiring multi-source data correlation
- **Contextual Summaries**: AI-generated profile highlights with actionable insights
- **Data Gap Detection**: Identify missing profile information and suggest collection strategies

### 📊 Real-Time Event Processing
- **User Events**: Track registration, profile updates, preference changes, segment assignments
- **Order Events**: Monitor purchase history and link transactions to customer profiles

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
# Subscriptions: user-events, order-events
# Consumer Group: profile-agg-group

# CRUD Service Integration (for MCP tools)
CRUD_SERVICE_URL=http://localhost:8000
```

## API Reference

### Agent REST Endpoint

**POST** `/invoke` - Aggregate customer profile with AI insights

**Request Body:**
```json
{
  "contact_id": "user-789",
  "interaction_limit": 20,
  "query": "Summarize this customer's engagement"
}
```

**Response:**
```json
{
  "service": "crm-profile-aggregation",
  "contact_id": "user-789",
  "profile_context": {
    "contact": {
      "contact_id": "user-789",
      "email": "user@example.com",
      "first_name": "Jane",
      "last_name": "Smith",
      "account_id": "account-456",
      "marketing_opt_in": true,
      "tags": ["vip", "enterprise"]
    },
    "account": {
      "account_id": "account-456",
      "name": "Acme Corp",
      "industry": "Technology",
      "tier": "Enterprise"
    },
    "interactions": [
      {
        "interaction_id": "int-001",
        "channel": "email",
        "occurred_at": "2026-02-01T10:30:00Z",
        "metadata": { "campaign_id": "campaign-123" }
      }
    ]
  },
  "profile_summary": {
    "contact_id": "user-789",
    "account_id": "account-456",
    "marketing_opt_in": true,
    "interaction_count": 15,
    "recent_channels": ["email", "web", "phone"],
    "last_interaction_at": "2026-02-01T10:30:00Z",
    "engagement_score": 0.75,
    "tags": ["vip", "enterprise"]
  }
}
```

### MCP Tools (Agent-to-Agent Communication)

#### 1. Get Contact Context
**POST** `/mcp/crm/profile/context`

```json
{
  "contact_id": "user-789",
  "interaction_limit": 20
}
```

Returns full CRM context including contact, account, and interaction history.

**Response:**
```json
{
  "profile_context": {
    "contact": { ... },
    "account": { ... },
    "interactions": [ ... ]
  }
}
```

#### 2. Get Profile Summary
**POST** `/mcp/crm/profile/summary`

```json
{
  "contact_id": "user-789",
  "interaction_limit": 20
}
```

Returns condensed profile summary with engagement metrics.

**Response:**
```json
{
  "profile_summary": {
    "contact_id": "user-789",
    "account_id": "account-456",
    "interaction_count": 15,
    "recent_channels": ["email", "web"],
    "engagement_score": 0.75
  }
}
```

#### 3. Get Account Summary
**POST** `/mcp/crm/profile/account`

```json
{
  "account_id": "account-456"
}
```

Or use `contact_id` to automatically resolve account:

```json
{
  "contact_id": "user-789"
}
```

Returns account information (B2B scenarios).

**Response:**
```json
{
  "account": {
    "account_id": "account-456",
    "name": "Acme Corp",
    "industry": "Technology",
    "tier": "Enterprise"
  }
}
```

## Event Processing

### Subscribed Events

| Event Hub | Consumer Group | Purpose |
|-----------|----------------|---------|
| `user-events` | `profile-agg-group` | Track user registration, profile updates, preference changes |
| `order-events` | `profile-agg-group` | Link purchase history to customer profiles |

### Event Handling Logic

1. **Extract Contact ID**: Parse `contact_id`, `user_id`, `customer_id`, or `id` from event payload
2. **Skip Invalid Events**: Log and skip events without identifiable contact
3. **Build CRM Context**: Fetch full contact context including account and interactions
4. **Generate Summary**: Calculate engagement metrics (interaction count, channels, score)
5. **Log Processing**: Structured logging with engagement metrics

**Engagement Score Calculation:**
```python
engagement_score = min(interaction_count / 10, 1.0)
# 0 interactions = 0.0, 10+ interactions = 1.0 (linear scale)
```

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
uvicorn crm_profile_aggregation.main:app --reload --port 8011
```

### Testing

```bash
# Run unit tests
pytest apps/crm-profile-aggregation/tests/

# Test agent endpoint
curl -X POST http://localhost:8011/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "contact_id": "user-789",
    "query": "Summarize customer engagement"
  }'

# Test MCP tool - Profile Summary
curl -X POST http://localhost:8011/mcp/crm/profile/summary \
  -H "Content-Type: application/json" \
  -d '{"contact_id": "user-789"}'

# Test MCP tool - Account Summary
curl -X POST http://localhost:8011/mcp/crm/profile/account \
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
- **Summarize key signals**: Identity, account, engagement level, preferred channels
- **Highlight gaps**: Call out missing profile data (e.g., no phone number, no industry)
- **Suggest next steps**: Recommend data collection strategies
- **Return concise bullets**: Focus on actionable context, not verbose descriptions

### SLM vs LLM Routing

| Query Type | Model | Reasoning |
|------------|-------|-----------|
| "Get profile for user-789" | SLM | Direct data retrieval |
| "What channels does this user prefer?" | SLM | Simple aggregation from interactions |
| "Compare engagement across all VIP customers" | LLM | Cross-profile analysis |
| "Predict churn risk for user-789" | LLM | Predictive modeling |
| "Why did engagement drop last month?" | LLM | Temporal pattern analysis |

## Integration Examples

### From Frontend (Direct Call)

```typescript
// React component
const { data, isLoading } = useQuery({
  queryKey: ['customer-profile', contactId],
  queryFn: () => 
    fetch(`${AGENT_URL}/invoke`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contact_id: contactId,
        query: 'Get customer profile'
      })
    }).then(r => r.json())
});
```

### From CRUD Service (Via Agent Client)

```python
# CRUD service calling profile aggregation
from crud_service.integrations.agent_client import get_agent_client

agent_client = get_agent_client()
profile = await agent_client.call_endpoint(
    agent_url=settings.profile_aggregation_agent_url,
    endpoint="/invoke",
    data={"contact_id": "user-789"},
    fallback_value={"profile_context": None}
)
```

### From Another Agent (MCP Tool)

```python
# Campaign intelligence agent calling profile aggregation via MCP
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://crm-profile-aggregation:8011/mcp/crm/profile/summary",
        json={"contact_id": "user-789", "interaction_limit": 20}
    )
    profile_summary = response.json()
```

## Use Cases

### 1. Customer Support Dashboard
Display unified customer view when support agent opens ticket:
- Contact details + account information
- Recent interaction history across all channels
- Engagement score to prioritize high-value customers
- Tags (VIP, enterprise, at-risk) for context

### 2. Personalization Engine
Retrieve customer preferences for personalized recommendations:
- Preferred communication channels (email vs SMS vs push)
- Interaction frequency (daily, weekly, monthly)
- Account tier (enterprise vs SMB) for feature gating
- Tags for segment-based personalization

### 3. Campaign Targeting
Identify eligible customers for marketing campaigns:
- Filter by `marketing_opt_in` status
- Target specific segments via tags
- Exclude recently contacted customers (last_interaction_at)
- Score by engagement level

### 4. Churn Prediction
Analyze engagement trends for proactive retention:
- Declining interaction frequency
- Channel abandonment (stopped opening emails)
- Low engagement score (< 0.3)
- No recent orders (via order events)

## Monitoring & Observability

### Key Metrics

- `profile_event_processed`: Event processing count by event type and scope
- `profile_event_skipped`: Events without identifiable contact
- `profile_event_missing_contact`: Events where contact lookup failed
- `agent_invocation_duration`: Agent response time (SLM vs LLM)

### Logs

All operations emit structured logs with correlation IDs:

```json
{
  "event": "profile_event_processed",
  "event_type": "user.updated",
  "scope": "user",
  "contact_id": "user-789",
  "interaction_count": 15,
  "engagement_score": 0.75,
  "timestamp": "2026-02-03T10:30:00Z"
}
```

## Production Considerations

### Resilience
- **Circuit Breaker**: CRM adapter calls have circuit breakers
- **Fallback**: Returns mock data if CRM adapter unavailable
- **Timeout**: Fast timeouts prevent cascading failures

### Scalability
- **Stateless Agent**: Horizontal scaling via Kubernetes/Container Apps
- **Event Processing**: Consumer group allows parallel processing across partitions
- **Memory Tiering**: Hot (Redis) → Warm (Cosmos) → Cold (Blob) for efficient context retrieval

### Performance
- **Interaction Limit**: Default 20 interactions per profile (configurable)
- **Caching**: Hot memory (Redis) caches frequently accessed profiles
- **Pagination**: Large interaction histories paginated to prevent memory issues

### Security
- **Authentication**: Azure Managed Identity for Event Hubs, Cosmos DB, Blob Storage
- **API Keys**: Azure AI Foundry uses key-based auth (rotate regularly)
- **PII Protection**: Contact data encrypted at rest (Cosmos DB, Blob Storage)
- **Network Isolation**: Deploy in private subnet with service endpoints

### Data Privacy
- **GDPR Compliance**: Support right-to-erasure via contact deletion
- **Opt-Out Handling**: Respect `marketing_opt_in` flag
- **Data Retention**: Cold storage for audit trails (configurable retention period)

## Related Services

- **crm-campaign-intelligence**: Uses profile context for campaign analysis
- **crm-segmentation-personalization**: Uses profiles for dynamic segmentation
- **crm-support-assistance**: Uses profiles for customer support context
- **crud-service**: Transactional API for CRM data (called via MCP tools)

## License

See repository root for license information.
