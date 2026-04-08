"""Inventory reservation validation service."""

from holiday_peak_lib import create_standard_app
from holiday_peak_lib.utils import EventHubSubscription
from inventory_reservation_validation.agents import (
    ReservationValidationAgent,
    register_mcp_tools,
)
from inventory_reservation_validation.event_handlers import build_event_handlers

SERVICE_NAME = "inventory-reservation-validation"
app = create_standard_app(
    require_foundry_readiness=True,
    disable_tracing_without_foundry=True,
    service_name=SERVICE_NAME,
    agent_class=ReservationValidationAgent,
    mcp_setup=register_mcp_tools,
    subscriptions=[
        EventHubSubscription("order-events", "reservation-group"),
    ],
    handlers=build_event_handlers(),
)
