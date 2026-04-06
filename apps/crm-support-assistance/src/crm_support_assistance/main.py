"""CRM support assistance service."""

from crm_support_assistance.agents import SupportAssistanceAgent, register_mcp_tools
from crm_support_assistance.event_handlers import build_event_handlers
from holiday_peak_lib import create_standard_app
from holiday_peak_lib.utils import EventHubSubscription

SERVICE_NAME = "crm-support-assistance"
app = create_standard_app(
    require_foundry_readiness=True,
    disable_tracing_without_foundry=True,
    service_name=SERVICE_NAME,
    agent_class=SupportAssistanceAgent,
    mcp_setup=register_mcp_tools,
    subscriptions=[
        EventHubSubscription("order-events", "support-group"),
        EventHubSubscription("return-events", "support-group"),
    ],
    handlers=build_event_handlers(),
)
