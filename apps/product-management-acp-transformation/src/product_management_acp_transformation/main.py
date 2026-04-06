"""ACP transformation service."""

from holiday_peak_lib import create_standard_app
from holiday_peak_lib.utils import EventHubSubscription
from product_management_acp_transformation.agents import (
    ProductAcpTransformationAgent,
    register_mcp_tools,
)
from product_management_acp_transformation.event_handlers import build_event_handlers

SERVICE_NAME = "product-management-acp-transformation"
app = create_standard_app(
    require_foundry_readiness=True,
    disable_tracing_without_foundry=True,
    service_name=SERVICE_NAME,
    agent_class=ProductAcpTransformationAgent,
    mcp_setup=register_mcp_tools,
    subscriptions=[
        EventHubSubscription("product-events", "acp-transform-group"),
    ],
    handlers=build_event_handlers(),
)
