"""Inventory alerts and triggers service."""

from holiday_peak_lib import create_standard_app
from holiday_peak_lib.utils import EventHubSubscription
from inventory_alerts_triggers.agents import InventoryAlertsAgent, register_mcp_tools
from inventory_alerts_triggers.event_handlers import build_event_handlers

SERVICE_NAME = "inventory-alerts-triggers"
app = create_standard_app(
    require_foundry_readiness=True,
    disable_tracing_without_foundry=True,
    service_name=SERVICE_NAME,
    agent_class=InventoryAlertsAgent,
    mcp_setup=register_mcp_tools,
    subscriptions=[
        EventHubSubscription("inventory-events", "alerts-group"),
    ],
    handlers=build_event_handlers(),
)
