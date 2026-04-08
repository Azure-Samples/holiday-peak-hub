"""Product normalization and classification service."""

from holiday_peak_lib import create_standard_app
from holiday_peak_lib.utils import EventHubSubscription
from product_management_normalization_classification.agents import (
    ProductNormalizationAgent,
    register_mcp_tools,
)
from product_management_normalization_classification.event_handlers import (
    build_event_handlers,
)

SERVICE_NAME = "product-management-normalization-classification"


app = create_standard_app(
    require_foundry_readiness=True,
    disable_tracing_without_foundry=True,
    service_name=SERVICE_NAME,
    agent_class=ProductNormalizationAgent,
    mcp_setup=register_mcp_tools,
    subscriptions=[
        EventHubSubscription("product-events", "normalization-group"),
    ],
    handlers=build_event_handlers(),
)
