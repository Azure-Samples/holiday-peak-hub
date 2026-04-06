"""Logistics route issue detection service."""

from holiday_peak_lib import create_standard_app
from holiday_peak_lib.utils import EventHubSubscription
from logistics_route_issue_detection.agents import (
    RouteIssueDetectionAgent,
    register_mcp_tools,
)
from logistics_route_issue_detection.event_handlers import build_event_handlers

SERVICE_NAME = "logistics-route-issue-detection"
app = create_standard_app(
    require_foundry_readiness=True,
    disable_tracing_without_foundry=True,
    service_name=SERVICE_NAME,
    agent_class=RouteIssueDetectionAgent,
    mcp_setup=register_mcp_tools,
    subscriptions=[
        EventHubSubscription("order-events", "route-detect-group"),
    ],
    handlers=build_event_handlers(),
)
