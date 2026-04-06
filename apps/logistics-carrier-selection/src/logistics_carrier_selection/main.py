"""Logistics carrier selection service."""

from holiday_peak_lib import create_standard_app
from holiday_peak_lib.utils import EventHubSubscription
from logistics_carrier_selection.agents import CarrierSelectionAgent, register_mcp_tools
from logistics_carrier_selection.event_handlers import build_event_handlers

SERVICE_NAME = "logistics-carrier-selection"
app = create_standard_app(
    require_foundry_readiness=True,
    disable_tracing_without_foundry=True,
    service_name=SERVICE_NAME,
    agent_class=CarrierSelectionAgent,
    mcp_setup=register_mcp_tools,
    subscriptions=[
        EventHubSubscription("order-events", "carrier-group"),
        EventHubSubscription("shipment-events", "carrier-group"),
    ],
    handlers=build_event_handlers(),
)
