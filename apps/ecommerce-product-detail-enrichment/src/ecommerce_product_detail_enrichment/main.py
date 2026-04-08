"""Ecommerce Product Detail Enrichment service entrypoint."""

from ecommerce_product_detail_enrichment.agents import (
    ProductDetailEnrichmentAgent,
    register_mcp_tools,
)
from ecommerce_product_detail_enrichment.event_handlers import build_event_handlers
from holiday_peak_lib import create_standard_app
from holiday_peak_lib.utils import EventHubSubscription

SERVICE_NAME = "ecommerce-product-detail-enrichment"
app = create_standard_app(
    require_foundry_readiness=True,
    disable_tracing_without_foundry=True,
    service_name=SERVICE_NAME,
    agent_class=ProductDetailEnrichmentAgent,
    mcp_setup=register_mcp_tools,
    subscriptions=[
        EventHubSubscription("product-events", "enrichment-group"),
    ],
    handlers=build_event_handlers(),
)
