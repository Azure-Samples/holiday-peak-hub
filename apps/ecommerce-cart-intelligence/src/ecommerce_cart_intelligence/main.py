"""Ecommerce Cart Intelligence service entrypoint."""

from ecommerce_cart_intelligence.agents import CartIntelligenceAgent, register_mcp_tools
from ecommerce_cart_intelligence.event_handlers import build_event_handlers
from holiday_peak_lib import create_standard_app
from holiday_peak_lib.utils import EventHubSubscription

SERVICE_NAME = "ecommerce-cart-intelligence"
app = create_standard_app(
    require_foundry_readiness=True,
    disable_tracing_without_foundry=True,
    service_name=SERVICE_NAME,
    agent_class=CartIntelligenceAgent,
    mcp_setup=register_mcp_tools,
    subscriptions=[
        EventHubSubscription("order-events", "cart-intel-group"),
    ],
    handlers=build_event_handlers(),
)
