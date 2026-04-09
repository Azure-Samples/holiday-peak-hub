"""Truth HITL service entrypoint."""

from holiday_peak_lib import create_standard_app
from holiday_peak_lib.utils import (
    PLATFORM_JOBS_EVENT_HUB_CONNECTION_STRING_ENV,
    PLATFORM_JOBS_EVENT_HUB_NAMESPACE_ENV,
    EventHubSubscription,
)
from truth_hitl.adapters import build_hitl_adapters
from truth_hitl.agents import TruthHITLAgent, register_mcp_tools
from truth_hitl.event_handlers import build_event_handlers
from truth_hitl.routes import build_review_router

SERVICE_NAME = "truth-hitl"

_adapters = build_hitl_adapters()


app = create_standard_app(
    require_foundry_readiness=True,
    disable_tracing_without_foundry=True,
    service_name=SERVICE_NAME,
    agent_class=TruthHITLAgent,
    mcp_setup=register_mcp_tools,
    subscriptions=[
        EventHubSubscription(
            "hitl-jobs",
            "hitl-service",
            namespace_env=PLATFORM_JOBS_EVENT_HUB_NAMESPACE_ENV,
            connection_string_env=PLATFORM_JOBS_EVENT_HUB_CONNECTION_STRING_ENV,
        ),
    ],
    handlers=build_event_handlers(adapters=_adapters),
)

_adapters.export_publisher.attach_self_healing(app.state.self_healing_kernel)
_adapters.search_enrichment_publisher.attach_self_healing(app.state.self_healing_kernel)

# Mount the review REST routes
app.include_router(build_review_router(_adapters))
