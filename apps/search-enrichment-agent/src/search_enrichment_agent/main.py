"""Search enrichment agent service entrypoint."""

from holiday_peak_lib import create_standard_app
from holiday_peak_lib.utils import EventHubSubscription
from search_enrichment_agent.agents import SearchEnrichmentAgent, register_mcp_tools
from search_enrichment_agent.event_handlers import build_event_handlers

SERVICE_NAME = "search-enrichment-agent"


app = create_standard_app(
    require_foundry_readiness=True,
    disable_tracing_without_foundry=True,
    service_name=SERVICE_NAME,
    agent_class=SearchEnrichmentAgent,
    mcp_setup=register_mcp_tools,
    subscriptions=[EventHubSubscription("search-enrichment-jobs", "search-enrichment-agent")],
    handlers=build_event_handlers(),
)
