"""Product consistency validation service."""

import os

from holiday_peak_lib import create_standard_app
from holiday_peak_lib.utils import EventHubSubscription
from product_management_consistency_validation.agents import (
    ProductConsistencyAgent,
    register_mcp_tools,
)
from product_management_consistency_validation.event_consumer import (
    build_completeness_event_handlers,
)
from product_management_consistency_validation.event_handlers import (
    build_event_handlers,
)

SERVICE_NAME = "product-management-consistency-validation"


# Merge product-events handlers (backward compat) with completeness-jobs handlers
_all_handlers = {
    **build_event_handlers(),
    **build_completeness_event_handlers(
        completeness_threshold=float(os.getenv("COMPLETENESS_THRESHOLD", "0.7"))
    ),
}

app = create_standard_app(
    require_foundry_readiness=True,
    disable_tracing_without_foundry=True,
    service_name=SERVICE_NAME,
    agent_class=ProductConsistencyAgent,
    mcp_setup=register_mcp_tools,
    subscriptions=[
        EventHubSubscription("product-events", "validation-group"),
        EventHubSubscription("completeness-jobs", "completeness-engine"),
    ],
    handlers=_all_handlers,
)
