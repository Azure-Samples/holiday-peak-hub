"""Truth Ingestion service entrypoint."""

from holiday_peak_lib import create_standard_app
from holiday_peak_lib.utils import EventHubSubscription
from truth_ingestion.agents import TruthIngestionAgent, register_mcp_tools
from truth_ingestion.event_handlers import build_event_handlers
from truth_ingestion.routes import router as ingestion_router

SERVICE_NAME = "truth-ingestion"


app = create_standard_app(
    require_foundry_readiness=True,
    disable_tracing_without_foundry=True,
    service_name=SERVICE_NAME,
    agent_class=TruthIngestionAgent,
    mcp_setup=register_mcp_tools,
    subscriptions=[
        EventHubSubscription("ingest-jobs", "ingestion-group"),
    ],
    handlers=build_event_handlers(),
)

app.include_router(ingestion_router)
