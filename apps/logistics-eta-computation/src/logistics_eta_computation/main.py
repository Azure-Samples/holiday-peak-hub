"""Logistics ETA computation service."""

from holiday_peak_lib import create_standard_app
from holiday_peak_lib.utils import EventHubSubscription
from logistics_eta_computation.agents import EtaComputationAgent, register_mcp_tools
from logistics_eta_computation.event_handlers import build_event_handlers

SERVICE_NAME = "logistics-eta-computation"
app = create_standard_app(
    require_foundry_readiness=True,
    disable_tracing_without_foundry=True,
    service_name=SERVICE_NAME,
    agent_class=EtaComputationAgent,
    mcp_setup=register_mcp_tools,
    subscriptions=[
        EventHubSubscription("order-events", "eta-group"),
        EventHubSubscription("shipment-events", "eta-group"),
    ],
    handlers=build_event_handlers(),
)
