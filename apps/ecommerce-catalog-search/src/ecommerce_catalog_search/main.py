"""Ecommerce Catalog Search service entrypoint."""
from holiday_peak_lib.app_factory import build_service_app


SERVICE_NAME = "ecommerce-catalog-search"
app = build_service_app(SERVICE_NAME)
