"""Ecommerce Checkout Support service entrypoint."""

from ecommerce_checkout_support.agents import CheckoutSupportAgent, register_mcp_tools
from ecommerce_checkout_support.event_handlers import build_event_handlers
from holiday_peak_lib import create_standard_app
from holiday_peak_lib.utils import EventHubSubscription

SERVICE_NAME = "ecommerce-checkout-support"
app = create_standard_app(
    require_foundry_readiness=True,
    disable_tracing_without_foundry=True,
    service_name=SERVICE_NAME,
    agent_class=CheckoutSupportAgent,
    mcp_setup=register_mcp_tools,
    subscriptions=[
        EventHubSubscription("order-events", "checkout-group"),
        EventHubSubscription("inventory-events", "checkout-group"),
    ],
    handlers=build_event_handlers(),
)
