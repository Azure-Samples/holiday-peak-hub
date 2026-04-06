"""Ecommerce Order Status service entrypoint."""

from ecommerce_order_status.agents import OrderStatusAgent, register_mcp_tools
from ecommerce_order_status.event_handlers import build_event_handlers
from holiday_peak_lib import create_standard_app
from holiday_peak_lib.utils import EventHubSubscription

SERVICE_NAME = "ecommerce-order-status"
app = create_standard_app(
    require_foundry_readiness=True,
    disable_tracing_without_foundry=True,
    service_name=SERVICE_NAME,
    agent_class=OrderStatusAgent,
    mcp_setup=register_mcp_tools,
    subscriptions=[
        EventHubSubscription("order-events", "order-status-group"),
        EventHubSubscription("shipment-events", "order-status-group"),
    ],
    handlers=build_event_handlers(),
)
