# CRM Support Assistance Service

Intelligent agent service for customer support assistance, providing contextual customer insights, sentiment analysis, and prioritized next-best actions for support teams.

## Overview

The CRM Support Assistance service provides AI-powered support guidance by analyzing customer profiles, interaction history, and sentiment. It generates support briefs with risk assessment and recommended actions to help support agents resolve issues efficiently and maintain customer satisfaction.

## Architecture

### Components

```
crm-support-assistance/
├── agents.py              # SupportAssistanceAgent with SLM/LLM routing
├── adapters.py            # CRM and support assistant adapters
├── event_handlers.py      # Event Hub subscriber for order events
└── main.py                # FastAPI application with MCP tools
```

### Communication Patterns

1. **Agent REST Endpoints** (`/invoke`): Synchronous support brief requests from frontend/CRUD
2. **MCP Tools**: Agent-to-agent communication for support context sharing
3. **Event Handlers**: Asynchronous processing of order events for proactive support

## Features

### 🎯 Support Brief Generation
- **Customer Context**: Unified view of contact, account, and interaction history
- **Sentiment Analysis**: Identify customer mood from recent interactions (positive, neutral, negative, angry)
- **Risk Assessment**: Automatic escalation flagging based on sentiment and account tier
- **Next Best Actions**: Prioritized action recommendations for support agents

**Risk Levels:**
- **High**: Negative/angry sentiment (requires escalation)
- **Low**: Positive/neutral sentiment (standard flow)

### 🤖 AI-Powered Intelligence
- **SLM-First Routing**: Fast responses for simple support context lookups
- **LLM Escalation**: Complex analysis requiring historical pattern recognition
- **Contextual Recommendations**: AI-generated next steps based on customer profile
- **Escalation Criteria**: Smart suggestions for when to involve senior support

### 📊 Real-Time Event Processing
- **Order Events**: Proactive support brief generation when issues detected in orders
- **Interaction Tracking**: Monitor channel usage and sentiment trends

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
# Consumer Group: support-group

# CRUD Service Integration (for MCP tools)
CRUD_SERVICE_URL=http://localhost:8000
```

## API Reference

### Agent REST Endpoint

**POST** `/invoke` - Generate support brief with customer context and recommendations

**Request Body:**
```json
{
  "contact_id": "user-789",
  "issue_summary": "Payment failed during checkout",
  "interaction_limit": 20,
  "query": "Help me assist this customer"
}
```

**Response:**
```json
{
  "service": "crm-support-assistance",
  "contact_id": "user-789",
  "crm_context": {
    "contact": {
      "contact_id": "user-789",
      "email": "user@example.com",
      "first_name": "Jane",
      "last_name": "Smith",
      "account_id": "account-456",
      "tags": ["vip", "enterprise"]
    },
    "account": {
      "account_id": "account-456",
      "name": "Acme Corp",
      "tier": "Enterprise"
    },
    "interactions": [
      {
        "interaction_id": "int-001",
        "channel": "chat",
        "occurred_at": "2026-02-03T09:45:00Z",
        "sentiment": "negative"
      }
    ]
  },
  "support_brief": {
    "contact_id": "user-789",
    "account_id": "account-456",
    "last_interaction_at": "2026-02-03T09:45:00Z",
    "last_channel": "chat",
    "sentiment": "negative",
    "risk": "high",
    "issue_summary": "Payment failed during checkout",
    "next_best_actions": [
      "Acknowledge issue",
      "Confirm resolution criteria",
      "Escalate to senior support",
      "Apply Enterprise account SLA"
    ]
  }
}
```

### MCP Tools (Agent-to-Agent Communication)

#### 1. Get Support Brief
**POST** `/mcp/crm/support/brief`

```json
{
  "contact_id": "user-789",
  "issue_summary": "Payment failed during checkout"
}
```

Returns complete support brief with risk assessment and next actions.

**Response:**
```json
{
  "support_brief": {
    "contact_id": "user-789",
    "account_id": "account-456",
    "last_interaction_at": "2026-02-03T09:45:00Z",
    "last_channel": "chat",
    "sentiment": "negative",
    "risk": "high",
    "issue_summary": "Payment failed during checkout",
    "next_best_actions": [
      "Acknowledge issue",
      "Confirm resolution criteria",
      "Escalate to senior support",
      "Apply Enterprise account SLA"
    ]
  }
}
```

#### 2. Get Contact Context
**POST** `/mcp/crm/support/contact-context`

```json
{
  "contact_id": "user-789",
  "interaction_limit": 20
}
```

Returns full CRM context for support analysis.

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

#### 3. Get Interaction Summary
**POST** `/mcp/crm/support/interaction-summary`

```json
{
  "contact_id": "user-789"
}
```

Returns condensed view of recent interactions (last 10) with sentiment.

**Response:**
```json
{
  "interactions": [
    {
      "interaction_id": "int-001",
      "channel": "chat",
      "occurred_at": "2026-02-03T09:45:00Z",
      "sentiment": "negative"
    },
    {
      "interaction_id": "int-002",
      "channel": "email",
      "occurred_at": "2026-02-02T14:30:00Z",
      "sentiment": "neutral"
    }
  ]
}
```

## Support Brief Logic

### Risk Assessment Rules

```python
# Determine risk level based on most recent interaction sentiment
if last_interaction.sentiment in {"negative", "angry"}:
    risk = "high"  # Requires escalation
else:
    risk = "low"   # Standard handling
```

### Next Best Actions

Base actions (all cases):
1. **Acknowledge issue** - Confirm receipt and understanding
2. **Confirm resolution criteria** - Set clear expectations

High-risk additions:
3. **Escalate to senior support** - Involve experienced agents

Account tier handling:
4. **Apply [Tier] account SLA** - Follow tier-specific response times (e.g., "Apply Enterprise account SLA")

**Example:**
```json
{
  "risk": "high",
  "account_tier": "Enterprise",
  "next_best_actions": [
    "Acknowledge issue",
    "Confirm resolution criteria",
    "Escalate to senior support",
    "Apply Enterprise account SLA"
  ]
}
```

## Event Processing

### Subscribed Events

| Event Hub | Consumer Group | Purpose |
|-----------|----------------|---------|
| `order-events` | `support-group` | Proactive support brief generation for order issues |

### Event Handling Logic

1. **Extract Contact ID**: Parse `contact_id`, `user_id`, `customer_id`, or `id` from event payload
2. **Skip Invalid Events**: Log and skip events without identifiable contact
3. **Build CRM Context**: Fetch contact context including interaction history
4. **Extract Issue**: Use `issue_summary` from payload or default to event type
5. **Generate Brief**: Create support brief with risk assessment and next actions
6. **Log Processing**: Structured logging with risk level and action count

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
uvicorn crm_support_assistance.main:app --reload --port 8013
```

### Testing

```bash
# Run unit tests
pytest apps/crm-support-assistance/tests/

# Test agent endpoint
curl -X POST http://localhost:8013/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "contact_id": "user-789",
    "issue_summary": "Payment failed during checkout",
    "query": "Help me assist this customer"
  }'

# Test MCP tool - Support Brief
curl -X POST http://localhost:8013/mcp/crm/support/brief \
  -H "Content-Type: application/json" \
  -d '{
    "contact_id": "user-789",
    "issue_summary": "Order not received"
  }'

# Test MCP tool - Interaction Summary
curl -X POST http://localhost:8013/mcp/crm/support/interaction-summary \
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
- **Summarize customer situation**: Provide concise overview of contact status
- **Prioritize next steps**: Rank actions by urgency and importance
- **Suggest escalation criteria**: Call out when to involve senior support
- **Keep responses action-oriented**: Focus on what to do, not just analysis
- **Flag high-risk cases**: Emphasize negative sentiment or VIP accounts

### SLM vs LLM Routing

| Query Type | Model | Reasoning |
|------------|-------|-----------|
| "Get support brief for user-789" | SLM | Direct data retrieval + simple rules |
| "Show recent interactions for user-789" | SLM | Simple aggregation |
| "Compare this issue to similar past cases" | LLM | Historical pattern analysis |
| "Predict escalation likelihood" | LLM | Predictive modeling |
| "Why is this customer frustrated?" | LLM | Causal analysis requiring context |

## Integration Examples

### From Frontend (Support Dashboard)

```typescript
// React component - Support ticket view
const { data: supportBrief, isLoading } = useQuery({
  queryKey: ['support-brief', contactId, issueId],
  queryFn: () => 
    fetch(`${AGENT_URL}/invoke`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contact_id: contactId,
        issue_summary: ticketDescription,
        query: 'Generate support brief'
      })
    }).then(r => r.json())
});

// Display risk badge and recommended actions
<RiskBadge level={supportBrief?.support_brief?.risk} />
<ActionList actions={supportBrief?.support_brief?.next_best_actions} />
```

### From CRUD Service (Via Agent Client)

```python
# CRUD service calling support assistance
from crud_service.integrations.agent_client import get_agent_client

agent_client = get_agent_client()
brief = await agent_client.call_endpoint(
    agent_url=settings.support_assistance_agent_url,
    endpoint="/invoke",
    data={
        "contact_id": "user-789",
        "issue_summary": "Payment failed"
    },
    fallback_value={"support_brief": {"risk": "low"}}
)
```

### From Another Agent (MCP Tool)

```python
# Order status agent calling support assistance via MCP
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://crm-support-assistance:8013/mcp/crm/support/brief",
        json={
            "contact_id": "user-789",
            "issue_summary": "Order delayed"
        }
    )
    support_brief = response.json()
```

## Use Cases

### 1. Support Ticket Dashboard
Display contextual customer information when agent opens ticket:
```python
brief = await get_support_brief(contact_id, issue_summary)
display_customer_card(brief.crm_context)
display_risk_badge(brief.support_brief.risk)
display_action_checklist(brief.support_brief.next_best_actions)
display_sentiment_trend(brief.crm_context.interactions)
```

### 2. Automatic Ticket Routing
Route high-risk tickets to senior agents:
```python
brief = await get_support_brief(contact_id, issue_summary)
if brief.support_brief.risk == "high":
    route_to_senior_queue()
elif brief.crm_context.account.tier == "Enterprise":
    route_to_enterprise_queue()
else:
    route_to_standard_queue()
```

### 3. SLA Management
Apply tier-specific SLAs automatically:
```python
brief = await get_support_brief(contact_id)
if "Enterprise" in brief.support_brief.next_best_actions[-1]:
    sla_hours = 2  # Enterprise: 2-hour response
elif "Premium" in brief.support_brief.next_best_actions[-1]:
    sla_hours = 4  # Premium: 4-hour response
else:
    sla_hours = 24  # Standard: 24-hour response
```

### 4. Proactive Support
Trigger outreach for negative sentiment trends:
```python
interactions = await get_interaction_summary(contact_id)
negative_count = sum(1 for i in interactions if i.sentiment == "negative")
if negative_count >= 2:
    trigger_proactive_outreach()
```

### 5. Agent Training
Use support briefs for training and quality assurance:
```python
brief = await get_support_brief(contact_id, issue_summary)
# Compare agent's actions vs recommended next_best_actions
training_gap = set(brief.next_best_actions) - set(agent_actions_taken)
if training_gap:
    log_training_opportunity(agent_id, training_gap)
```

## Sentiment Analysis

Current implementation uses sentiment from CRM interactions:

| Sentiment | Risk Level | Handling |
|-----------|------------|----------|
| **angry** | High | Immediate escalation |
| **negative** | High | Escalate to senior support |
| **neutral** | Low | Standard workflow |
| **positive** | Low | Standard workflow |
| *null* | Low | No sentiment data (default) |

**Future Enhancement**: Integrate real-time sentiment analysis using Azure AI Language for ticket text:
```python
from azure.ai.textanalytics import TextAnalyticsClient
sentiment = client.analyze_sentiment([ticket_text])[0].sentiment
```

## Monitoring & Observability

### Key Metrics

- `support_event_processed`: Event processing count with risk distribution
- `support_event_skipped`: Events without identifiable contact
- `support_event_missing_contact`: Events where contact lookup failed
- `agent_invocation_duration`: Agent response time (SLM vs LLM)
- `risk_level_distribution`: Histogram of high vs low risk cases
- `escalation_rate`: Percentage of cases requiring senior support

### Logs

All operations emit structured logs with correlation IDs:

```json
{
  "event": "support_event_processed",
  "event_type": "order.failed",
  "contact_id": "user-789",
  "risk": "high",
  "next_steps": 4,
  "timestamp": "2026-02-03T10:30:00Z"
}
```

## Production Considerations

### Resilience
- **Circuit Breaker**: CRM adapter calls have circuit breakers
- **Fallback**: Returns basic brief (low risk) if CRM adapter unavailable
- **Timeout**: Fast timeouts prevent cascading failures

### Scalability
- **Stateless Agent**: Horizontal scaling via Kubernetes/Container Apps
- **Event Processing**: Consumer group allows parallel processing across partitions
- **Memory Tiering**: Hot (Redis) → Warm (Cosmos) → Cold (Blob) for efficient context retrieval

### Performance
- **Interaction Limit**: Default 20 interactions per brief (configurable)
- **Summary Cache**: Interaction summaries cached in hot memory (Redis)
- **Lazy Loading**: Only fetch full context when needed

### Security
- **Authentication**: Azure Managed Identity for Event Hubs, Cosmos DB, Blob Storage
- **API Keys**: Azure AI Foundry uses key-based auth (rotate regularly)
- **PII Protection**: Mask sensitive customer data in logs
- **Network Isolation**: Deploy in private subnet with service endpoints

### Compliance
- **Audit Trail**: All support briefs logged with timestamps
- **Data Retention**: Configurable retention periods per compliance requirements
- **Access Control**: RBAC for support agent access to customer data
- **GDPR**: Support right-to-erasure via contact deletion

## Advanced Features (Future)

### AI-Powered Enhancements
- **Resolution Prediction**: Estimate time-to-resolution based on issue complexity
- **Knowledge Base Integration**: Suggest relevant KB articles per issue type
- **Automated Response Templates**: Generate draft responses based on issue and sentiment
- **Similar Case Matching**: Find similar past tickets for reference

### Multi-Channel Support
- **Live Chat Integration**: Real-time support brief updates during chat sessions
- **Phone Call Context**: Pre-load brief before agent answers call
- **Social Media Monitoring**: Track sentiment across Twitter, Facebook mentions

### Proactive Support
- **Churn Risk Detection**: Flag customers at risk of churning
- **Health Score**: Calculate customer health based on interaction patterns
- **Automated Outreach**: Trigger proactive contact for at-risk customers

## Related Services

- **crm-profile-aggregation**: Provides unified customer profiles for support context
- **crm-segmentation-personalization**: Segment-based support prioritization
- **crm-campaign-intelligence**: Identify if support issues correlate with campaigns
- **crud-service**: Transactional API for CRM data (called via MCP tools)

## License

See repository root for license information.
