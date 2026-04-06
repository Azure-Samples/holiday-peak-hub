"""Truth Export service entry point."""

from fastapi import FastAPI
from holiday_peak_lib import create_standard_app
from holiday_peak_lib.utils import EventHubSubscription
from truth_export.agents import TruthExportAgent, register_mcp_tools
from truth_export.event_handlers import build_event_handlers
from truth_export.routes import router as export_router

SERVICE_NAME = "truth-export"


app: FastAPI = create_standard_app(
    require_foundry_readiness=True,
    disable_tracing_without_foundry=True,
    service_name=SERVICE_NAME,
    agent_class=TruthExportAgent,
    mcp_setup=register_mcp_tools,
    subscriptions=[
        EventHubSubscription("export-jobs", "export-engine"),
    ],
    handlers=build_event_handlers(),
)

app.include_router(export_router)
