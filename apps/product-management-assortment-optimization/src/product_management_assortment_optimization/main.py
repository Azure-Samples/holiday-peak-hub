"""Assortment optimization service."""

from holiday_peak_lib import create_standard_app
from holiday_peak_lib.utils import EventHubSubscription
from product_management_assortment_optimization.agents import (
    AssortmentOptimizationAgent,
    register_mcp_tools,
)
from product_management_assortment_optimization.event_handlers import (
    build_event_handlers,
)

SERVICE_NAME = "product-management-assortment-optimization"
app = create_standard_app(
    require_foundry_readiness=True,
    disable_tracing_without_foundry=True,
    service_name=SERVICE_NAME,
    agent_class=AssortmentOptimizationAgent,
    mcp_setup=register_mcp_tools,
    subscriptions=[
        EventHubSubscription("order-events", "assortment-group"),
        EventHubSubscription("product-events", "assortment-group"),
    ],
    handlers=build_event_handlers(),
)
