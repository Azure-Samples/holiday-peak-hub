"""CRM segmentation and personalization service."""

from crm_segmentation_personalization.agents import (
    SegmentationPersonalizationAgent,
    register_mcp_tools,
)
from crm_segmentation_personalization.event_handlers import build_event_handlers
from holiday_peak_lib import create_standard_app
from holiday_peak_lib.utils import EventHubSubscription

SERVICE_NAME = "crm-segmentation-personalization"
app = create_standard_app(
    require_foundry_readiness=True,
    disable_tracing_without_foundry=True,
    service_name=SERVICE_NAME,
    agent_class=SegmentationPersonalizationAgent,
    mcp_setup=register_mcp_tools,
    subscriptions=[
        EventHubSubscription("order-events", "segmentation-group"),
    ],
    handlers=build_event_handlers(),
)
