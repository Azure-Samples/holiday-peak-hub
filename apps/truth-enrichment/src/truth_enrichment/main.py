"""Truth Enrichment service entrypoint."""

from holiday_peak_lib import create_standard_app
from holiday_peak_lib.utils import (
    PLATFORM_JOBS_EVENT_HUB_CONNECTION_STRING_ENV,
    PLATFORM_JOBS_EVENT_HUB_NAMESPACE_ENV,
    EventHubSubscription,
)
from truth_enrichment.agents import TruthEnrichmentAgent, register_mcp_tools
from truth_enrichment.event_handlers import build_event_handlers
from truth_enrichment.routes import router

SERVICE_NAME = "truth-enrichment"


app = create_standard_app(
    require_foundry_readiness=True,
    disable_tracing_without_foundry=True,
    service_name=SERVICE_NAME,
    agent_class=TruthEnrichmentAgent,
    mcp_setup=register_mcp_tools,
    subscriptions=[
        EventHubSubscription(
            "enrichment-jobs",
            "enrichment-engine",
            namespace_env=PLATFORM_JOBS_EVENT_HUB_NAMESPACE_ENV,
            connection_string_env=PLATFORM_JOBS_EVENT_HUB_CONNECTION_STRING_ENV,
        ),
    ],
    handlers=build_event_handlers(),
)

app.include_router(router)
