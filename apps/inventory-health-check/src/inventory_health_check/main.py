"""Inventory health check service."""

from holiday_peak_lib import create_standard_app
from holiday_peak_lib.utils import EventHubSubscription
from inventory_health_check.agents import InventoryHealthAgent, register_mcp_tools
from inventory_health_check.event_handlers import build_event_handlers

SERVICE_NAME = "inventory-health-check"
app = create_standard_app(
    require_foundry_readiness=True,
    disable_tracing_without_foundry=True,
    service_name=SERVICE_NAME,
    agent_class=InventoryHealthAgent,
    mcp_setup=register_mcp_tools,
    subscriptions=[
        EventHubSubscription("order-events", "health-check-group"),
        EventHubSubscription("inventory-events", "health-check-group"),
    ],
    handlers=build_event_handlers(),
)
