"""Inventory JIT replenishment service."""

from holiday_peak_lib import create_standard_app
from holiday_peak_lib.utils import EventHubSubscription
from inventory_jit_replenishment.agents import (
    InventoryReplenishmentAgent,
    register_mcp_tools,
)
from inventory_jit_replenishment.event_handlers import build_event_handlers

SERVICE_NAME = "inventory-jit-replenishment"
app = create_standard_app(
    require_foundry_readiness=True,
    disable_tracing_without_foundry=True,
    service_name=SERVICE_NAME,
    agent_class=InventoryReplenishmentAgent,
    mcp_setup=register_mcp_tools,
    subscriptions=[
        EventHubSubscription("inventory-events", "replenishment-group"),
    ],
    handlers=build_event_handlers(),
)
