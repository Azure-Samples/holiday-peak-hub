"""CRM campaign intelligence service."""

from crm_campaign_intelligence.agents import (
    CampaignIntelligenceAgent,
    register_mcp_tools,
)
from crm_campaign_intelligence.event_handlers import build_event_handlers
from holiday_peak_lib import create_standard_app
from holiday_peak_lib.utils import EventHubSubscription

SERVICE_NAME = "crm-campaign-intelligence"
app = create_standard_app(
    require_foundry_readiness=True,
    disable_tracing_without_foundry=True,
    service_name=SERVICE_NAME,
    agent_class=CampaignIntelligenceAgent,
    mcp_setup=register_mcp_tools,
    subscriptions=[
        EventHubSubscription("user-events", "campaign-intel-group"),
        EventHubSubscription("order-events", "campaign-intel-group"),
        EventHubSubscription("payment-events", "campaign-intel-group"),
    ],
    handlers=build_event_handlers(),
)
