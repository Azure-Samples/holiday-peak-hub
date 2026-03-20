"""Ecommerce Catalog Search service entrypoint."""

from ecommerce_catalog_search.agents import CatalogSearchAgent, register_mcp_tools
from ecommerce_catalog_search.event_handlers import build_event_handlers
from holiday_peak_lib import create_standard_app
from holiday_peak_lib.utils import EventHubSubscription

SERVICE_NAME = "ecommerce-catalog-search"
app = create_standard_app(
    service_name=SERVICE_NAME,
    agent_class=CatalogSearchAgent,
    mcp_setup=register_mcp_tools,
    subscriptions=[
        EventHubSubscription("product-events", "catalog-search-group"),
    ],
    handlers=build_event_handlers(),
)
