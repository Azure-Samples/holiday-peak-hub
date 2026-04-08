"""Logistics returns support service."""

from holiday_peak_lib import create_standard_app
from holiday_peak_lib.utils import EventHubSubscription
from logistics_returns_support.agents import ReturnsSupportAgent, register_mcp_tools
from logistics_returns_support.event_handlers import build_event_handlers

SERVICE_NAME = "logistics-returns-support"
app = create_standard_app(
    require_foundry_readiness=True,
    disable_tracing_without_foundry=True,
    service_name=SERVICE_NAME,
    agent_class=ReturnsSupportAgent,
    mcp_setup=register_mcp_tools,
    subscriptions=[
        EventHubSubscription("order-events", "returns-group"),
        EventHubSubscription("return-events", "returns-group"),
    ],
    handlers=build_event_handlers(),
)
